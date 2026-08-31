'use client';

import React, { useEffect } from 'react';
import { AlertCircle, RefreshCw, LogOut } from 'lucide-react';
import { api } from '../lib/api';

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('Application Error caught by ErrorBoundary:', error);
  }, [error]);

  const handleResetSession = () => {
    try {
      api.logout();
      window.location.href = '/';
    } catch {
      window.location.reload();
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-slate-950 text-slate-100">
      <div className="max-w-lg w-full glass-panel rounded-3xl border border-rose-500/40 p-8 shadow-2xl space-y-6 text-center animate-fadeIn">
        <div className="w-14 h-14 rounded-2xl bg-rose-500/20 border border-rose-500/40 flex items-center justify-center text-rose-400 mx-auto">
          <AlertCircle className="w-7 h-7" />
        </div>

        <div className="space-y-2">
          <h2 className="text-xl font-black text-white">Something went wrong</h2>
          <p className="text-xs text-slate-400 leading-relaxed">
            The application encountered a client error during state transition.
          </p>
        </div>

        {error?.message && (
          <div className="p-3.5 rounded-xl bg-rose-950/40 border border-rose-500/30 text-left font-mono text-[11px] text-rose-300 overflow-x-auto max-h-36">
            {error.message}
          </div>
        )}

        <div className="flex flex-col sm:flex-row items-center gap-3 pt-2">
          <button
            onClick={() => reset()}
            className="w-full sm:flex-1 py-2.5 px-4 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/20 transition cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Try Again</span>
          </button>

          <button
            onClick={handleResetSession}
            className="w-full sm:flex-1 py-2.5 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs flex items-center justify-center gap-2 border border-slate-700 transition cursor-pointer"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Clear Session & Reload</span>
          </button>
        </div>
      </div>
    </div>
  );
}
