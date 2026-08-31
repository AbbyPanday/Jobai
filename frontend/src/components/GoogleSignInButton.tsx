'use client';

import React, { useState } from 'react';
import { api, UserProfile } from '@/lib/api';

interface GoogleSignInButtonProps {
  onSuccess: (user: UserProfile, token: string) => void;
  currentUser?: UserProfile | null;
  onSignOut?: () => void;
}

export const GoogleSignInButton: React.FC<GoogleSignInButtonProps> = ({
  onSuccess,
  currentUser,
  onSignOut,
}) => {
  const [loading, setLoading] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);

  const handleDevGoogleLogin = async () => {
    setLoading(true);
    try {
      const email = prompt('Enter your Google email (or click OK for default demo):', 'abhimanyu.candidate@gmail.com');
      if (!email) {
        setLoading(false);
        return;
      }

      const res = await api.googleAuth({
        email,
        name: email.split('@')[0].replace('.', ' ').replace(/(^\w|\s\w)/g, m => m.toUpperCase()),
        picture: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=128&q=80',
        idToken: `mock_google_id_token_${Date.now()}`,
      });

      onSuccess(res.user, res.token);
    } catch (err: any) {
      alert(`Google Auth failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  if (currentUser) {
    return (
      <div className="relative">
        <button
          onClick={() => setShowDropdown(!showDropdown)}
          className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900 border border-slate-700/80 hover:border-slate-500 transition cursor-pointer text-xs"
        >
          <div className="w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 font-bold flex items-center justify-center text-xs overflow-hidden">
            {((currentUser.fullName || currentUser.name || 'G')[0] || 'G').toUpperCase()}
          </div>
          <span className="text-slate-200 font-medium max-w-[100px] truncate">
            {currentUser.fullName || currentUser.name || 'Candidate'}
          </span>
          <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
        </button>

        {showDropdown && (
          <div className="absolute right-0 mt-2 w-56 glass-panel rounded-xl p-3 border border-slate-700 shadow-2xl z-50 space-y-2 text-xs">
            <div className="border-b border-slate-800 pb-2">
              <p className="font-bold text-white truncate">{currentUser.fullName || currentUser.name || 'Candidate'}</p>
              <p className="text-slate-400 text-[11px] truncate">{currentUser.email || 'Google Connected'}</p>
            </div>

            <div className="space-y-1 text-slate-300">
              <div className="flex justify-between py-1">
                <span className="text-slate-400">Auth:</span>
                <span className="font-semibold text-emerald-400 flex items-center gap-1">
                  <span>🔵</span> Google
                </span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-400">Exp:</span>
                <span className="font-semibold text-white">{currentUser.yearsExperience || 3} Yrs</span>
              </div>
            </div>

            {onSignOut && (
              <button
                onClick={() => {
                  setShowDropdown(false);
                  onSignOut();
                }}
                className="w-full text-left px-2 py-1.5 rounded-lg text-rose-400 hover:bg-rose-500/10 transition cursor-pointer font-semibold"
              >
                Sign Out
              </button>
            )}
          </div>
        )}
      </div>
    );
  }

  return (
    <button
      onClick={handleDevGoogleLogin}
      disabled={loading}
      className="flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white hover:bg-slate-100 text-slate-900 font-semibold text-xs transition shadow-sm hover:shadow cursor-pointer disabled:opacity-50"
    >
      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24">
        <path
          fill="#4285F4"
          d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
        />
        <path
          fill="#34A853"
          d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
        />
        <path
          fill="#FBBC05"
          d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
        />
        <path
          fill="#EA4335"
          d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
        />
      </svg>
      <span>{loading ? 'Signing in...' : 'Sign in with Google'}</span>
    </button>
  );
};
