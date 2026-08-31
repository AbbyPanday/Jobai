'use client';

import React from 'react';
import { X } from 'lucide-react';
import { SalaryBandChart } from './SalaryBandChart';
import { SalaryIntelligence } from '../lib/api';

interface Props {
  salaryData: SalaryIntelligence | null;
  isOpen: boolean;
  onClose: () => void;
}

export function SalaryModal({ salaryData, isOpen, onClose }: Props) {
  if (!isOpen || !salaryData) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-3xl max-h-[90vh] overflow-y-auto glass-panel rounded-3xl border border-slate-700 p-6 shadow-2xl">
        <button
          onClick={onClose}
          className="absolute top-5 right-5 text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition z-10"
        >
          <X className="w-5 h-5" />
        </button>
        <SalaryBandChart salaryData={salaryData} onClose={onClose} />
      </div>
    </div>
  );
}
