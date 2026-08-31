'use client';

import React, { useState } from 'react';
import { ShieldCheck, XCircle, CheckCircle2, FileText, AlertCircle, Sparkles, ExternalLink, Globe } from 'lucide-react';
import { HitlReviewPayload } from '../hooks/useAgentSocket';

interface Props {
  data: HitlReviewPayload | null;
  onApprove: (appId: string, token: string) => void;
  onReject: (appId: string, token: string, feedback?: string) => void;
  onClose: () => void;
}

export function HitlReviewModal({ data, onApprove, onReject, onClose }: Props) {
  const [rejectReason, setRejectReason] = useState('');
  const [isRejecting, setIsRejecting] = useState(false);

  if (!data) return null;

  const applicationId = data.applicationId || '';
  const hitlPackage = data.hitlPackage || { filledFieldsSummary: {}, reviewToken: '' };
  const filledFieldsSummary = hitlPackage.filledFieldsSummary || {};
  const reviewToken = hitlPackage.reviewToken || '';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-4xl max-h-[90vh] overflow-y-auto glass-panel rounded-2xl border border-emerald-500/40 p-6 md:p-8 shadow-2xl text-slate-100">
        {/* Header */}
        <div className="flex items-start justify-between pb-6 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400">
              <ShieldCheck className="w-6 h-6 animate-pulse-subtle" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                  HITL Gate Triggered
                </span>
                <span className="text-xs text-slate-400 font-mono">Token: {reviewToken.substring(0, 14)}...</span>
              </div>
              <h2 className="text-xl font-bold text-white mt-1">
                Human-in-the-Loop: Review Before Final Submission
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                The Playwright + Gemini agent completed form filling. Verify autofilled fields below before authorizing dispatch.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
          >
            <XCircle className="w-6 h-6" />
          </button>
        </div>

        {/* Content Grid: Viewport Preview + Form Data */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 my-6">
          {/* Left Column: Simulated Browser Viewport Review */}
          <div className="lg:col-span-5 flex flex-col gap-3">
            <div className="flex items-center justify-between text-xs text-slate-400 px-1">
              <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                <Globe className="w-3.5 h-3.5 text-sky-400" />
                Live Browser Snapshot
              </span>
              <span className="text-emerald-400 text-[11px] bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-500/20">
                Ready for Submit
              </span>
            </div>

            {/* Viewport Mock Card */}
            <div className="relative rounded-xl overflow-hidden border border-slate-700 bg-slate-900/90 shadow-inner flex flex-col min-h-[260px]">
              {/* Browser Bar */}
              <div className="bg-slate-800/80 px-3 py-2 flex items-center gap-2 border-b border-slate-700">
                <div className="flex gap-1.5">
                  <div className="w-2.5 h-2.5 rounded-full bg-rose-500/80" />
                  <div className="w-2.5 h-2.5 rounded-full bg-amber-500/80" />
                  <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/80" />
                </div>
                <div className="bg-slate-950 text-slate-400 text-[10px] px-2.5 py-0.5 rounded-md font-mono flex-1 truncate">
                  careers.portal/apply/review-stage?id={applicationId}
                </div>
              </div>

              {/* Viewport Body Simulation */}
              <div className="p-4 flex-1 flex flex-col justify-between bg-gradient-to-b from-slate-900 to-slate-950">
                <div className="space-y-2.5">
                  <div className="h-3.5 w-3/4 bg-slate-700/60 rounded animate-pulse" />
                  <div className="h-2.5 w-1/2 bg-slate-800 rounded" />
                  <div className="p-3 bg-emerald-950/20 border border-emerald-500/30 rounded-lg text-[11px] text-emerald-300 flex items-start gap-2">
                    <Sparkles className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                    <span>Gemini Vision mapped 14 form fields and attached candidate PDF without errors.</span>
                  </div>
                </div>

                <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/60 text-xs text-slate-400 space-y-1">
                  <div className="flex justify-between">
                    <span>Target Portal:</span>
                    <span className="font-semibold text-slate-200">{filledFieldsSummary['Target Company'] || 'Career Portal'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Target Designation:</span>
                    <span className="font-semibold text-slate-200">{filledFieldsSummary['Target Role'] || 'Backend Engineer'}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Key Extracted Values Table */}
          <div className="lg:col-span-7 flex flex-col gap-3">
            <div className="text-xs font-semibold text-slate-300 px-1 flex items-center justify-between">
              <span>Autofilled Candidate Persona</span>
              <span className="text-slate-400 font-normal">All fields verified</span>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 divide-y divide-slate-800/80 text-xs space-y-2">
              {Object.entries(filledFieldsSummary).map(([key, val]) => (
                <div key={key} className="pt-2 first:pt-0 flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                  <span className="text-slate-400 font-medium">{key}</span>
                  <span className="text-slate-100 font-semibold font-mono bg-slate-800/60 px-2 py-0.5 rounded border border-slate-700/50 text-right truncate max-w-xs">
                    {String(val || '—')}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Rejection input area if toggled */}
        {isRejecting && (
          <div className="mb-6 p-4 rounded-xl bg-rose-950/30 border border-rose-500/30 text-xs space-y-2 animate-fadeIn">
            <label className="font-semibold text-rose-300">Reason for aborting / edit instructions:</label>
            <input
              type="text"
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="e.g. Expected CTC should be 30 LPA instead, or wrong resume version."
              className="w-full bg-slate-900 border border-rose-500/40 rounded-lg p-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-rose-400"
            />
          </div>
        )}

        {/* Footer Actions */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-6 border-t border-slate-800">
          <div className="text-xs text-slate-400 flex items-center gap-1.5">
            <AlertCircle className="w-4 h-4 text-amber-400" />
            <span>Autonomous agent will NOT click final submit without explicit approval.</span>
          </div>

          <div className="flex items-center gap-3 w-full sm:w-auto">
            {!isRejecting ? (
              <>
                <button
                  onClick={() => setIsRejecting(true)}
                  className="flex-1 sm:flex-initial px-4 py-2.5 rounded-xl border border-rose-500/40 bg-rose-950/20 text-rose-300 hover:bg-rose-900/40 text-xs font-semibold transition"
                >
                  Reject & Abort
                </button>
                <button
                  onClick={() => onApprove(applicationId, reviewToken)}
                  className="flex-1 sm:flex-initial px-6 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-slate-950 text-xs font-bold shadow-lg shadow-emerald-500/20 flex items-center justify-center gap-2 transition transform active:scale-95"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  1-Click Approve & Submit
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => setIsRejecting(false)}
                  className="px-4 py-2.5 rounded-xl border border-slate-700 bg-slate-800 text-slate-300 text-xs font-semibold hover:bg-slate-700 transition"
                >
                  Cancel
                </button>
                <button
                  onClick={() => onReject(applicationId, reviewToken, rejectReason)}
                  className="px-5 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold transition"
                >
                  Confirm Rejection
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
