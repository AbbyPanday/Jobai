'use client';

import React, { useState } from 'react';
import {
  Building2,
  MapPin,
  IndianRupee,
  Sparkles,
  ExternalLink,
  Play,
  TrendingUp,
  Target,
  Clock
} from 'lucide-react';
import { Job, SalaryIntelligence } from '../lib/api';
import { MatchRadarModal } from './MatchRadarModal';
import { SalaryModal } from './SalaryModal';

interface Props {
  job: Job;
  onApply: (jobId: string) => void;
  isApplying?: boolean;
}

export function JobCard({ job, onApply, isApplying }: Props) {
  const [isRadarOpen, setIsRadarOpen] = useState(false);
  const [isSalaryOpen, setIsSalaryOpen] = useState(false);

  const matchScore = job.matchScore || 85.0;
  const isHighMatch = matchScore >= 80.0;

  const sourceBadge = {
    LINKEDIN: 'bg-blue-950/40 text-blue-400 border-blue-500/20',
    NAUKRI: 'bg-amber-950/40 text-amber-400 border-amber-500/20',
    GOOGLE_SEARCH: 'bg-emerald-950/40 text-emerald-400 border-emerald-500/20',
  }[job.source] || 'bg-slate-800 text-slate-400 border-slate-700';

  return (
    <>
      <div
        className={`glass-panel rounded-2xl p-5 transition-all duration-200 glass-card-hover border ${
          isHighMatch ? 'border-emerald-500/30 bg-slate-900/60' : 'border-slate-800/80 bg-slate-900/40'
        }`}
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          {/* Left info: Title, Company, Location, Tags */}
          <div className="space-y-2 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className={`px-2 py-0.5 rounded-md text-[10px] font-semibold border ${sourceBadge}`}>
                {(job.source || 'PORTAL').replace('_', ' ')}
              </span>
              {isHighMatch && (
                <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                  <Sparkles className="w-2.5 h-2.5" /> High Match
                </span>
              )}
              <span className="text-[11px] text-slate-400">
                {job.location || 'India'}
              </span>
            </div>

            <div>
              <h3 className="text-base font-bold text-white hover:text-emerald-400 transition inline-flex items-center gap-1.5 cursor-pointer">
                {job.title || 'Software Opportunity'}
                {job.externalUrl && (
                  <a
                    href={job.externalUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="text-slate-400 hover:text-white"
                    title="Open Portal"
                  >
                    <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </h3>
              <div className="text-xs text-slate-300 font-medium flex items-center gap-1.5 mt-0.5">
                <Building2 className="w-3.5 h-3.5 text-sky-400" />
                <span>{job.companyName || 'Technology Company'}</span>
              </div>
            </div>

            {/* Concise skill pills */}
            <div className="flex flex-wrap gap-1 pt-1">
              {(job.extractedRequirements || []).slice(0, 5).map((req, idx) => (
                <span
                  key={idx}
                  className="px-2 py-0.5 rounded-md text-[10px] bg-slate-800/80 text-slate-300 border border-slate-700/50 font-mono"
                >
                  {req}
                </span>
              ))}
              {(job.extractedRequirements || []).length > 5 && (
                <span className="px-1.5 py-0.5 rounded-md text-[10px] text-slate-400">
                  +{(job.extractedRequirements || []).length - 5}
                </span>
              )}
            </div>
          </div>

          {/* Right info & actions */}
          <div className="flex sm:flex-col items-end justify-between sm:justify-center gap-3 sm:border-l sm:border-slate-800/80 sm:pl-5">
            {/* Quick Metrics */}
            <div className="text-right flex sm:flex-col items-center sm:items-end gap-3 sm:gap-1">
              <div className="flex items-baseline gap-1 font-mono">
                <span className="text-[11px] text-slate-400">Match:</span>
                <span className={`text-sm font-black ${isHighMatch ? 'text-emerald-400' : 'text-slate-200'}`}>
                  {matchScore.toFixed(0)}%
                </span>
              </div>

              {job.salaryIntelligence && (
                <div className="text-xs font-bold text-slate-200 font-mono">
                  ₹{job.salaryIntelligence.estimated_ctc_min_lpa}-{job.salaryIntelligence.estimated_ctc_max_lpa} <span className="text-[10px] text-emerald-400 font-normal">LPA</span>
                </div>
              )}
            </div>

            {/* Action buttons */}
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setIsRadarOpen(true)}
                title="View ATS Match Breakdown"
                className="p-2 rounded-xl text-slate-400 hover:text-white bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 transition"
              >
                <Target className="w-4 h-4 text-emerald-400" />
              </button>

              {job.salaryIntelligence && (
                <button
                  onClick={() => setIsSalaryOpen(true)}
                  title="View Deep Compensation & In-Hand"
                  className="p-2 rounded-xl text-sky-400 hover:text-sky-300 bg-sky-950/40 hover:bg-sky-900/50 border border-sky-500/30 transition"
                >
                  <TrendingUp className="w-4 h-4" />
                </button>
              )}

              <button
                onClick={() => onApply(job.jobId)}
                disabled={isApplying}
                className="px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-slate-950 text-xs font-bold shadow-md shadow-emerald-500/10 flex items-center gap-1.5 transition disabled:opacity-50"
              >
                <Play className="w-3 h-3 fill-slate-950" />
                <span>Apply</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Progressive Disclosure Dialogs */}
      <MatchRadarModal
        isOpen={isRadarOpen}
        onClose={() => setIsRadarOpen(false)}
        matchScore={matchScore}
        matchBreakdown={job.matchBreakdown}
        isHighMatch={isHighMatch}
        strengths={job.strengths}
        missingSkills={job.missingSkills}
        tailoredAdvice={job.tailoredAdvice}
      />

      <SalaryModal
        isOpen={isSalaryOpen}
        onClose={() => setIsSalaryOpen(false)}
        salaryData={job.salaryIntelligence || null}
      />
    </>
  );
}
