import json
import logging
import asyncio
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.gcp_clients import db
from app.services.agent.browser_worker import browser_worker
from app.services.agent.hitl_controller import hitl_controller
from app.services.matching.ats_scorer import ats_scorer

logger = logging.getLogger(__name__)
ws_router = APIRouter()

class ConnectionManager:
    def __init__(self):
        # userId -> Set[WebSocket]
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.pending_answers: Dict[str, asyncio.Event] = {}
        self.user_answers: Dict[str, Dict[str, str]] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        uid = user_id or "anonymous"
        if uid not in self.active_connections:
            self.active_connections[uid] = set()
        self.active_connections[uid].add(websocket)
        logger.info(f"WebSocket client connected for user {uid}. Total active: {len(self.active_connections[uid])}")

    def disconnect(self, user_id: str, websocket: WebSocket):
        uid = user_id or "anonymous"
        if uid in self.active_connections:
            self.active_connections[uid].discard(websocket)
            if not self.active_connections[uid]:
                del self.active_connections[uid]
        logger.info(f"WebSocket client disconnected for user {uid}")

    async def send_event(self, user_id: str, event_type: str, data: dict):
        uid = user_id or "anonymous"
        if uid in self.active_connections:
            message = json.dumps({"event": event_type, "payload": data})
            to_remove = set()
            for ws in self.active_connections[uid]:
                try:
                    await ws.send_text(message)
                except Exception as e:
                    logger.warning(f"Failed to send to user {uid}: {e}")
                    to_remove.add(ws)
            for dead in to_remove:
                self.active_connections[uid].discard(dead)

manager = ConnectionManager()

@ws_router.websocket("/ws/agent-feed/{user_id}")
@ws_router.websocket("/ws/agent-feed")
async def agent_websocket_endpoint(websocket: WebSocket, user_id: str = "anonymous"):
    uid = user_id if user_id else "anonymous"
    await manager.connect(uid, websocket)
    try:
        await websocket.send_text(json.dumps({
            "event": "AGENT_CONNECTED",
            "payload": {
                "userId": uid,
                "status": "ONLINE",
                "message": "Autonomous Agent connected and listening to live job match feed & HITL gates."
            }
        }))

        while True:
            raw_text = await websocket.receive_text()
            try:
                msg = json.loads(raw_text)
                event_type = msg.get("event")
                payload = msg.get("payload", {})

                logger.info(f"Received WS event from {uid}: {event_type}")

                if event_type == "TRIGGER_MANUAL_APPLY":
                    job_id = payload.get("jobId")
                    asyncio.create_task(handle_manual_apply(uid, job_id))

                elif event_type == "HITL_DECISION":
                    app_id = payload.get("applicationId")
                    decision = payload.get("decision", "APPROVE")
                    token = payload.get("token", "")
                    feedback = payload.get("feedback")
                    
                    res = hitl_controller.process_user_decision(app_id, decision, token, feedback)
                    await manager.send_event(uid, "HITL_DECISION_RECORDED", {
                        "applicationId": app_id,
                        "decision": decision,
                        "application": res
                    })

                elif event_type == "ANSWER_QUESTION":
                    q_key = payload.get("questionKey")
                    answer_val = payload.get("answer")
                    if uid not in manager.user_answers:
                        manager.user_answers[uid] = {}
                    manager.user_answers[uid][q_key] = answer_val
                    
                    # Update user persona if user exists
                    user = db.get_user(uid) or {}
                    if q_key == "notice_period":
                        try:
                            user["noticePeriodDays"] = int(answer_val)
                            db.save_user(uid, user)
                        except Exception:
                            pass
                    elif q_key == "expected_ctc":
                        try:
                            user["expectedCtcLpa"] = float(answer_val)
                            db.save_user(uid, user)
                        except Exception:
                            pass

                    await manager.send_event(uid, "AGENT_STATUS_UPDATE", {
                        "step": "ANSWER_SAVED",
                        "message": f"Answer recorded for '{q_key}' and saved to candidate persona."
                    })

            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received from user {uid}")

    except WebSocketDisconnect:
        manager.disconnect(uid, websocket)
    except Exception as e:
        logger.error(f"WebSocket error for user {uid}: {e}")
        manager.disconnect(uid, websocket)


async def handle_manual_apply(user_id: str, job_id: str):
    """Orchestrates an autonomous application loop triggered via chat or dashboard."""
    user = db.get_user(user_id) or {"userId": user_id, "name": "Candidate"}
    job = db.get_job(job_id)
    if not job:
        await manager.send_event(user_id, "AGENT_ERROR", {"message": f"Job {job_id} not found."})
        return

    app_id = f"app_{job_id.replace('job_', '')}_{user_id.replace('usr_', '')}"

    eval_res = await ats_scorer.evaluate_match(user, job)

    db.save_application(app_id, {
        "applicationId": app_id,
        "userId": user_id,
        "jobId": job_id,
        "matchScore": eval_res.matchScore,
        "matchBreakdown": eval_res.matchBreakdown.model_dump(),
        "status": "INITIALIZING",
        "statusHistory": [
            {"status": "INITIALIZING", "timestamp": "now", "detail": "Starting autonomous application pipeline."}
        ]
    })

    async def on_progress(step: str, message: str, extra: dict):
        await manager.send_event(user_id, "AGENT_STATUS_UPDATE", {
            "applicationId": app_id,
            "jobId": job_id,
            "companyName": job.get("companyName"),
            "step": step,
            "message": message,
            "extra": extra
        })

    async def on_question(q_key: str, q_data: dict):
        await manager.send_event(user_id, "AGENT_QUESTION_REQUEST", {
            "applicationId": app_id,
            "questionKey": q_key,
            "questionData": q_data
        })

    custom_answers = manager.user_answers.get(user_id, {})
    await browser_worker.execute_application_flow(
        user_profile=user,
        job_details=job,
        application_id=app_id,
        custom_answers=custom_answers,
        progress_callback=on_progress,
        question_request_callback=on_question
    )
