'use client';

import { useState, useEffect, useRef, useCallback } from 'react';

export interface AgentLogStep {
  id: string;
  step: string;
  message: string;
  timestamp: string;
  extra?: any;
  companyName?: string;
}

export interface QuestionRequest {
  applicationId: string;
  questionKey: string;
  questionData: {
    questionKey: string;
    label: string;
    type: string;
    placeholder?: string;
  };
}

export interface HitlReviewPayload {
  applicationId: string;
  hitlPackage: {
    screenshotStorageUrl: string;
    filledFieldsSummary: Record<string, string>;
    reviewToken: string;
    generatedAt: string;
  };
}

export function useAgentSocket(userId?: string) {
  const [isConnected, setIsConnected] = useState(false);
  const [logs, setLogs] = useState<AgentLogStep[]>([]);
  const [activeQuestion, setActiveQuestion] = useState<QuestionRequest | null>(null);
  const [hitlReview, setHitlReview] = useState<HitlReviewPayload | null>(null);
  const [latestEvent, setLatestEvent] = useState<any>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    if (!userId || userId.trim() === '') {
      setIsConnected(false);
      return;
    }

    try {
      const wsUrl = process.env.NEXT_PUBLIC_WS_URL || `ws://127.0.0.1:8000/ws/agent-feed/${userId}`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        console.log(`Agent WebSocket connected for ${userId}.`);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          const { event: eventType, payload } = data;
          setLatestEvent({ event: eventType, payload });

          if (eventType === 'AGENT_STATUS_UPDATE') {
            setLogs((prev) => [
              {
                id: `${Date.now()}-${Math.random()}`,
                step: payload.step,
                message: payload.message,
                timestamp: new Date().toLocaleTimeString(),
                extra: payload.extra,
                companyName: payload.companyName,
              },
              ...prev.slice(0, 49),
            ]);

            if (payload.extra && payload.extra.hitlPackage) {
              setHitlReview({
                applicationId: payload.applicationId || payload.extra.applicationId,
                hitlPackage: payload.extra.hitlPackage,
              });
            }
          } else if (eventType === 'AGENT_QUESTION_REQUEST') {
            setActiveQuestion(payload);
          } else if (eventType === 'HITL_REVIEW_READY') {
            setHitlReview(payload);
          } else if (eventType === 'HITL_DECISION_RECORDED') {
            setHitlReview(null);
            setLogs((prev) => [
              {
                id: `${Date.now()}`,
                step: 'DECISION_FINALIZED',
                message: `Verification complete: Application ${payload.applicationId} ${payload.decision}.`,
                timestamp: new Date().toLocaleTimeString(),
              },
              ...prev,
            ]);
          }
        } catch (e) {
          console.error('Failed to parse WS payload:', e);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        if (userId) {
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, 3000);
        }
      };

      ws.onerror = () => {
        setIsConnected(false);
      };
    } catch (e) {
      console.warn('WebSocket connection attempt error:', e);
    }
  }, [userId]);

  useEffect(() => {
    if (userId) {
      connect();
    }
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [connect, userId]);

  const triggerManualApply = (jobId: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          event: 'TRIGGER_MANUAL_APPLY',
          payload: { jobId },
        })
      );
    }
  };

  const answerQuestion = (questionKey: string, answer: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          event: 'ANSWER_QUESTION',
          payload: { questionKey, answer },
        })
      );
      setActiveQuestion(null);
    }
  };

  const submitHitlDecision = (applicationId: string, decision: 'APPROVE' | 'REJECT', token: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          event: 'HITL_DECISION',
          payload: { applicationId, decision, token },
        })
      );
    }
    setHitlReview(null);
  };

  const clearLogs = () => setLogs([]);

  return {
    isConnected,
    logs,
    activeQuestion,
    hitlReview,
    latestEvent,
    triggerManualApply,
    answerQuestion,
    submitHitlDecision,
    clearLogs,
  };
}
