'use client';

import React from 'react';
import { Target, CheckCircle2, AlertCircle, Sparkles, Zap, MapPin, DollarSign, Briefcase, Server } from 'lucide-react';
import { MatchBreakdown } from '../lib/api';

interface Props {
  matchScore: number;
  matchBreakdown?: MatchBreakdown;
  isHighMatch?: boolean;
  strengths?: string[];
  missingSkills?: string[];
  tailoredAdvice?: string;
}

interface FactorConfig {
  key: keyof MatchBreakdown;
  label: string;
  weight: string;
  icon: React.ReactNode;
  gradient: string;
  track: string;
}

const FACTORS: FactorConfig[] = [
  {
    key: 'hardSkills',
    label: 'Tech Stack & Skills',
    weight: '35%',
    icon: <Zap className="w-3.5 h-3.5 text-amber-400" />,
    gradient: 'from-amber-500 to-emerald-500',
    track: 'bg-amber-950/40',
  },
  {
    key: 'experienceFit',
    label: 'Experience Band Fit',
    weight: '25%',
    icon: <Briefcase className="w-3.5 h-3.5 text-sky-400" />,
    gradient: 'from-sky-500 to-blue-500',
    track: 'bg-sky-950/40',
  },
  {
    key: 'domainFit',
    label: 'Domain Depth (Cloud/DB/Arch)',
    weight: '20%',
    icon: <Server className="w-3.5 h-3.5 text-purple-400" />,
    gradient: 'from-purple-500 to-pink-500',
    track: 'bg-purple-950/40',
  },
  {
    key: 'locationFit',
    label: 'Location / Remote Fit',
    weight: '10%',
    icon: <MapPin className="w-3.5 h-3.5 text-rose-400" />,
    gradient: 'from-rose-500 to-orange-500',
    track: 'bg-rose-950/40',
  },
  {
    key: 'ctcAlignment',
    label: 'CTC Alignment',
    weight: '10%',
    icon: <DollarSign className="w-3.5 h-3.5 text-teal-400" />,
    gradient: 'from-teal-500 to-cyan-500',
    track: 'bg-teal-950/40',
  },
];

function ScoreRing({ score }: { score: number }) {
  const radius = 44;
  const circ = 2 * Math.PI * radius;
  const dash = (score / 100) * circ;
  const color = score >= 80 ? '#34d399' : score >= 65 ? '#60a5fa' : '#f59e0b';

  return (
    <div className="relative flex items-center justify-center w-28 h-28">
      <svg className="w-28 h-28 -rotate-90" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r={radius} fill="none" stroke="#1e293b" strokeWidth="8" />
        <circle
          cx="50" cy="50" r={radius} fill="none"
          stroke={color} strokeWidth="8"
          strokeDasharray={`${dash} ${circ}`}
          strokeLinecap="round"
          style={{ transition: 'stroke-dasharray 1s ease' }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-2xl font-black font-mono" style={{ color }}>{score.toFixed(0)}</span>
        <span className="text-[10px] text-slate-400 font-medium">Match %</span>
      </div>
    </div>
  );
}

export function MatchRadar({
  matchScore,
  matchBreakdown,
  isHighMatch,
  strengths,
  missingSkills,
  tailoredAdvice,
}: Props) {
  const breakdown: MatchBreakdown = matchBreakdown || {
    hardSkills: 85,
    experienceFit: 85,
    domainFit: 80,
    locationFit: 90,
    ctcAlignment: 75,
    softSkillsAndPedigree: 85,
  };

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 space-y-5 text-slate-100">
      {/* Header + Ring */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Target className="w-5 h-5 text-emerald-400" />
            <h4 className="text-sm font-bold text-white">5-Factor ATS Match Score</h4>
          </div>
          {isHighMatch && (
            <span className="inline-flex px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 items-center gap-1">
              <Sparkles className="w-3 h-3" /> High Match — Auto-Apply Eligible
            </span>
          )}
          <p className="text-[11px] text-slate-500 mt-1 leading-snug">
            Weighted composite scoring across tech stack, experience, domain depth, location & CTC
          </p>
        </div>
        <ScoreRing score={matchScore} />
      </div>

      {/* 5-Factor Bars */}
      <div className="space-y-2.5 text-xs">
        {FACTORS.map((factor) => {
          const val = breakdown[factor.key] ?? 75;
          return (
            <div key={factor.key}>
              <div className="flex justify-between text-slate-400 mb-1">
                <span className="flex items-center gap-1.5 text-slate-300">
                  {factor.icon}
                  <span>{factor.label}</span>
                  <span className="text-slate-500">({factor.weight})</span>
                </span>
                <span
                  className={`font-mono font-bold ${
                    val >= 80 ? 'text-emerald-400' : val >= 65 ? 'text-sky-400' : 'text-amber-400'
                  }`}
                >
                  {typeof val === 'number' ? val.toFixed(0) : val}%
                </span>
              </div>
              <div className={`w-full ${factor.track} h-2.5 rounded-full overflow-hidden border border-slate-700/40`}>
                <div
                  className={`h-full bg-gradient-to-r ${factor.gradient} rounded-full transition-all duration-700`}
                  style={{ width: `${Math.min(val, 100)}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Strengths & Missing Skills */}
      <div className="pt-1 grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
        {strengths && strengths.length > 0 && (
          <div className="p-3 rounded-xl bg-emerald-950/20 border border-emerald-500/20 space-y-1.5">
            <span className="font-semibold text-emerald-300 flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Key Match Strengths
            </span>
            <ul className="text-slate-400 space-y-1 text-[11px]">
              {(strengths || []).map((s, idx) => (
                <li key={idx} className="leading-snug">• {s}</li>
              ))}
            </ul>
          </div>
        )}

        {missingSkills && missingSkills.length > 0 && (
          <div className="p-3 rounded-xl bg-slate-800/40 border border-slate-700/60 space-y-1.5">
            <span className="font-semibold text-slate-300 flex items-center gap-1.5">
              <AlertCircle className="w-3.5 h-3.5 text-amber-400" /> Skill Gaps to Address
            </span>
            <div className="flex flex-wrap gap-1.5 pt-0.5">
              {(missingSkills || []).map((m, idx) => (
                <span key={idx} className="px-2 py-0.5 rounded-md text-[10px] bg-amber-950/30 text-amber-300 border border-amber-700/40">
                  {m}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Tailored Advice */}
      {tailoredAdvice && (
        <div className="p-3 rounded-xl bg-sky-950/20 border border-sky-500/20 text-xs text-sky-200/90 leading-relaxed">
          <strong className="text-sky-300">💡 ATS Strategy: </strong>{tailoredAdvice}
        </div>
      )}
    </div>
  );
}
