'use client';

import React, { useState } from 'react';
import { IndianRupee, TrendingUp, Award, Shield, AlertTriangle, Lightbulb, Star, Info } from 'lucide-react';
import { SalaryIntelligence } from '../lib/api';

interface Props {
  salaryData: SalaryIntelligence;
  onClose?: () => void;
}

export function SalaryBandChart({ salaryData, onClose }: Props) {
  const [targetCtc, setTargetCtc] = useState(salaryData.estimated_ctc_median_lpa);

  // Dynamic monthly in-hand calculation for slider
  const fixedGrossAnnual = (targetCtc * (salaryData.fixed_base_percentage / 100)) * 100000;
  const annualPf = Math.min(fixedGrossAnnual * 0.12 * 0.5, 216000);
  let taxable = Math.max(0, fixedGrossAnnual - 75000);
  let tax = 0;
  if (taxable > 1500000) { tax += (taxable - 1500000) * 0.30; taxable = 1500000; }
  if (taxable > 1200000) { tax += (taxable - 1200000) * 0.20; taxable = 1200000; }
  if (taxable > 1000000) { tax += (taxable - 1000000) * 0.15; taxable = 1000000; }
  if (taxable > 700000) { tax += (taxable - 700000) * 0.10; taxable = 700000; }
  if (taxable > 300000) { tax += (taxable - 300000) * 0.05; }
  const taxWithCess = tax * 1.04;
  const netAnnual = fixedGrossAnnual - annualPf - taxWithCess;
  const computedMonthlyTakeHome = Math.max(0, Math.round(netAnnual / 12));

  return (
    <div className="glass-panel rounded-2xl border border-slate-700/60 p-6 shadow-xl space-y-6 text-slate-100">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-sky-500/20 text-sky-400 border border-sky-500/30">
              Deep Compensation Intelligence
            </span>
            <span className="text-xs text-slate-400">{salaryData.experience_bracket}</span>
          </div>
          <h3 className="text-lg font-bold text-white mt-1">
            {salaryData.company_name} — {salaryData.designation}
          </h3>
        </div>

        {/* Ratings */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 bg-slate-800/80 px-3 py-1.5 rounded-xl border border-slate-700">
            <Star className="w-4 h-4 text-amber-400 fill-amber-400" />
            <span className="text-xs font-bold text-white">{salaryData.ambitionbox_rating}</span>
            <span className="text-[10px] text-slate-400">AmbitionBox</span>
          </div>
          <div className="flex items-center gap-1.5 bg-slate-800/80 px-3 py-1.5 rounded-xl border border-slate-700">
            <Star className="w-4 h-4 text-emerald-400 fill-emerald-400" />
            <span className="text-xs font-bold text-white">{salaryData.glassdoor_rating}</span>
            <span className="text-[10px] text-slate-400">Glassdoor</span>
          </div>
        </div>
      </div>

      {/* Salary Range & Take-Home Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Min Bracket */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-col justify-between">
          <span className="text-xs text-slate-400">Min Base Range</span>
          <div className="text-xl font-bold text-slate-200 mt-1">
            ₹{salaryData.estimated_ctc_min_lpa} <span className="text-xs text-slate-400 font-normal">LPA</span>
          </div>
          <span className="text-[11px] text-slate-500 mt-1">~₹{(salaryData.monthly_in_hand_min_inr || 110000).toLocaleString('en-IN')}/mo in-hand</span>
        </div>

        {/* Median / Target */}
        <div className="p-4 rounded-xl bg-gradient-to-b from-emerald-950/40 to-slate-900 border border-emerald-500/40 flex flex-col justify-between shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-emerald-400">Market Median CTC</span>
            <TrendingUp className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-black text-white mt-1">
            ₹{salaryData.estimated_ctc_median_lpa} <span className="text-sm text-emerald-400 font-normal">LPA</span>
          </div>
          <span className="text-[11px] text-emerald-300/80 mt-1">
            ~₹{(salaryData.monthly_in_hand_median_inr || 145000).toLocaleString('en-IN')}/mo net take-home
          </span>
        </div>

        {/* Max / Stretch */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-col justify-between">
          <span className="text-xs text-slate-400">Top Quartile / Max</span>
          <div className="text-xl font-bold text-sky-400 mt-1">
            ₹{salaryData.estimated_ctc_max_lpa} <span className="text-xs text-slate-400 font-normal">LPA</span>
          </div>
          <span className="text-[11px] text-slate-500 mt-1">~₹{(salaryData.monthly_in_hand_max_inr || 190000).toLocaleString('en-IN')}/mo in-hand</span>
        </div>
      </div>

      {/* Interactive Take-Home Calculator Slider */}
      <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <IndianRupee className="w-4 h-4 text-emerald-400" />
            <span className="text-xs font-semibold text-slate-200">Interactive CTC to Monthly Take-Home Calculator</span>
          </div>
          <span className="text-xs font-mono font-bold text-emerald-400">
            ₹{targetCtc.toFixed(1)} LPA CTC
          </span>
        </div>

        <input
          type="range"
          min={salaryData.estimated_ctc_min_lpa}
          max={salaryData.estimated_ctc_max_lpa}
          step={0.5}
          value={targetCtc}
          onChange={(e) => setTargetCtc(parseFloat(e.target.value))}
          className="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-emerald-500"
        />

        <div className="flex items-center justify-between text-xs pt-1">
          <span className="text-slate-400">Estimated Monthly In-Hand (After New Tax Slabs & PF):</span>
          <span className="text-sm font-bold text-white font-mono bg-emerald-950/60 px-2.5 py-1 rounded border border-emerald-500/30">
            ₹{computedMonthlyTakeHome.toLocaleString('en-IN')} / month
          </span>
        </div>
      </div>

      {/* CTC Breakdown Components */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
        <div className="p-3.5 rounded-xl bg-slate-900/40 border border-slate-800/80 space-y-2">
          <span className="font-semibold text-slate-300 flex items-center gap-1.5">
            <Award className="w-4 h-4 text-sky-400" />
            Fixed Base vs. Variable Pay
          </span>
          <p className="text-slate-400 leading-relaxed">
            <strong className="text-slate-200">{salaryData.fixed_base_percentage}% Fixed Base component</strong>. Variable bonus: {salaryData.variable_pay_details}.
          </p>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-900/40 border border-slate-800/80 space-y-2">
          <span className="font-semibold text-slate-300 flex items-center gap-1.5">
            <Shield className="w-4 h-4 text-amber-400" />
            ESOP & Equity Vesting
          </span>
          <p className="text-slate-400 leading-relaxed">
            {salaryData.esop_details || 'Standard 4-year ESOP vesting schedule with 1-year cliff.'}
          </p>
        </div>
      </div>

      {/* Negotiation Leverage & Employee Sentiment */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
        {/* Pros & Cons */}
        <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800/80 space-y-2.5">
          <span className="font-semibold text-slate-200 flex items-center gap-1.5">
            <Info className="w-4 h-4 text-emerald-400" />
            Culture & Employee Sentiment
          </span>
          <ul className="space-y-1 text-slate-400">
            {(salaryData.pros_summary || []).map((pro, idx) => (
              <li key={idx} className="flex items-start gap-1.5 text-emerald-400/90">
                <span className="font-bold">+</span>
                <span>{pro}</span>
              </li>
            ))}
            {(salaryData.cons_summary || []).map((con, idx) => (
              <li key={idx} className="flex items-start gap-1.5 text-rose-400/90">
                <span className="font-bold">-</span>
                <span>{con}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Negotiation Tactics */}
        <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-500/30 space-y-2.5">
          <span className="font-semibold text-amber-300 flex items-center gap-1.5">
            <Lightbulb className="w-4 h-4 text-amber-400" />
            Indian Market Negotiation Leverage
          </span>
          <ul className="space-y-1.5 text-slate-300">
            {(salaryData.negotiation_leverage_tips || []).map((tip, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span className="text-amber-400 font-bold">⚡</span>
                <span className="leading-relaxed">{tip}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
