'use client';

import React from 'react';
import { X } from 'lucide-react';
import { MatchRadar } from './MatchRadar';
import { MatchBreakdown } from '../lib/api';

interface Props {
  matchScore: number;
  matchBreakdown?: MatchBreakdown;
  isHighMatch?: boolean;
  strengths?: string[];
  missingSkills?: string[];
  tailoredAdvice?: string;
  isOpen: boolean;
  onClose: () => void;
}

export function MatchRadarModal({
  matchScore,
  matchBreakdown,
  isHighMatch,
  strengths,
  missingSkills,
  tailoredAdvice,
  isOpen,
  onClose,
}: Props) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto glass-panel rounded-3xl border border-slate-700 p-6 shadow-2xl">
        <button
          onClick={onClose}
          className="absolute top-5 right-5 text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition z-10"
        >
          <X className="w-5 h-5" />
        </button>
        <div className="pt-2">
          <MatchRadar
            matchScore={matchScore}
            matchBreakdown={matchBreakdown}
            isHighMatch={isHighMatch}
            strengths={strengths}
            missingSkills={missingSkills}
            tailoredAdvice={tailoredAdvice}
          />
        </div>
      </div>
    </div>
  );
}
