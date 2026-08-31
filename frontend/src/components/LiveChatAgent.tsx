'use client';

import React, { useState, useEffect } from 'react';
import {
  Bot,
  Send,
  Sparkles,
  HelpCircle,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
  Trash2,
  Clock,
  Terminal,
  Maximize2,
  Minimize2
} from 'lucide-react';
import { AgentLogStep, QuestionRequest, HitlReviewPayload } from '../hooks/useAgentSocket';

interface Props {
  isConnected: boolean;
  logs: AgentLogStep[];
  activeQuestion: QuestionRequest | null;
  hitlReview: HitlReviewPayload | null;
  onAnswerQuestion: (qKey: string, answer: string) => void;
  onOpenHitlModal: () => void;
  onClearLogs: () => void;
}

export function LiveChatAgent({
  isConnected,
  logs,
  activeQuestion,
  hitlReview,
  onAnswerQuestion,
  onOpenHitlModal,
  onClearLogs,
}: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const [answerInput, setAnswerInput] = useState('');

  // Automatically expand if a question or HITL action is required
  useEffect(() => {
    if (activeQuestion || hitlReview) {
      setIsOpen(true);
    }
  }, [activeQuestion, hitlReview]);

  const handleAnswerSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!answerInput.trim() || !activeQuestion) return;
    onAnswerQuestion(activeQuestion.questionKey, answerInput.trim());
    setAnswerInput('');
  };

  const latestLog = logs[0];

  return (
    <div className="fixed bottom-5 right-5 z-40">
      {!isOpen ? (
        /* Minimized Sleek Pill */
        <button
          onClick={() => setIsOpen(true)}
          className="flex items-center gap-2.5 px-4 py-2.5 rounded-full glass-panel border border-emerald-500/40 hover:border-emerald-400 shadow-xl transition transform hover:scale-105 active:scale-95 group"
        >
          <div className="relative">
            <div className="w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
              <Bot className="w-3.5 h-3.5" />
            </div>
            <span
              className={`absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full border-2 border-slate-900 ${
                isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'
              }`}
            />
          </div>

          <div className="text-left text-xs font-semibold text-slate-200">
            {hitlReview ? (
              <span className="text-emerald-400 font-bold flex items-center gap-1 animate-pulse">
                <ShieldCheck className="w-3.5 h-3.5" /> HITL Action Ready
              </span>
            ) : activeQuestion ? (
              <span className="text-amber-400 font-bold flex items-center gap-1">
                <HelpCircle className="w-3.5 h-3.5" /> Answer Required
              </span>
            ) : latestLog ? (
              <span className="text-slate-300 font-mono text-[11px] truncate max-w-[180px] inline-block">
                {latestLog.step.replace(/_/g, ' ')}
              </span>
            ) : (
              <span>Agent Live</span>
            )}
          </div>
        </button>
      ) : (
        /* Expanded Floating Card */
        <div className="w-full max-w-sm sm:max-w-md glass-panel rounded-3xl border border-slate-700/80 shadow-2xl overflow-hidden flex flex-col text-slate-100 animate-fadeIn">
          {/* Header */}
          <div className="bg-slate-900/90 px-4 py-3 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
                <Bot className="w-4 h-4" />
              </div>
              <div>
                <span className="text-xs font-bold text-white block">Gemini 3.7 Autonomous Agent</span>
                <span className="text-[10px] text-emerald-400 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  {isConnected ? 'Connected to WebSocket' : 'Connecting...'}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-1">
              <button
                onClick={onClearLogs}
                title="Clear Logs"
                className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
              >
                <Minimize2 className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Content Body */}
          <div className="p-4 space-y-3 max-h-80 overflow-y-auto bg-slate-950/70 text-xs">
            {/* HITL Ready Banner */}
            {hitlReview && (
              <div className="p-3 rounded-2xl bg-emerald-950/40 border border-emerald-500/40 flex items-center justify-between gap-3 shadow-md">
                <div className="flex items-center gap-2 text-emerald-300">
                  <ShieldCheck className="w-5 h-5 text-emerald-400 shrink-0" />
                  <div>
                    <span className="font-bold text-white block">HITL Verification Gate</span>
                    <span className="text-[11px]">Form ready for 1-click submit.</span>
                  </div>
                </div>
                <button
                  onClick={onOpenHitlModal}
                  className="px-3 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-bold transition whitespace-nowrap"
                >
                  Review
                </button>
              </div>
            )}

            {/* Question Request Box */}
            {activeQuestion && (
              <div className="p-3 rounded-2xl bg-amber-950/30 border border-amber-500/40 space-y-2">
                <div className="flex items-center gap-1.5 text-amber-300 font-semibold">
                  <HelpCircle className="w-4 h-4 text-amber-400" />
                  <span>Clarification required:</span>
                </div>
                <p className="text-slate-200">{activeQuestion.questionData.label}</p>
                <form onSubmit={handleAnswerSubmit} className="flex gap-2 pt-1">
                  <input
                    type="text"
                    value={answerInput}
                    onChange={(e) => setAnswerInput(e.target.value)}
                    placeholder={activeQuestion.questionData.placeholder || 'Type answer...'}
                    className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white outline-none focus:border-amber-400"
                    autoFocus
                  />
                  <button
                    type="submit"
                    className="px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold"
                  >
                    Send
                  </button>
                </form>
              </div>
            )}

            {/* Step Logs */}
            <div className="space-y-1.5">
              {logs.length === 0 ? (
                <div className="py-6 text-center text-slate-500 flex flex-col items-center gap-2">
                  <Terminal className="w-5 h-5 text-slate-600" />
                  <span>Agent is listening. Click "Apply" on any job to launch Playwright browser worker.</span>
                </div>
              ) : (
                logs.map((log) => (
                  <div
                    key={log.id}
                    className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800/80 flex items-start gap-2"
                  >
                    <Sparkles className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                        <span>{(log.step || 'STATUS').replace(/_/g, ' ')}</span>
                        <span>{log.timestamp}</span>
                      </div>
                      <p className="text-slate-300 leading-snug mt-0.5">{log.message}</p>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
