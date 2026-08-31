'use client';

import React, { useState, useEffect } from 'react';
import { api, UserProfile } from '@/lib/api';
import { CheckCircle2, AlertCircle, RefreshCw, X, ArrowRight, ExternalLink, Eye, EyeOff, Terminal } from 'lucide-react';

interface ConnectedAccountsModalProps {
  user: UserProfile;
  isOpen: boolean;
  onClose: () => void;
  onProfileUpdated: (updatedProfile: UserProfile) => void;
  latestEvent?: any;
}

export const ConnectedAccountsModal: React.FC<ConnectedAccountsModalProps> = ({
  user,
  isOpen,
  onClose,
  onProfileUpdated,
  latestEvent,
}) => {
  const [activeTab, setActiveTab] = useState<'linkedin' | 'naukri' | 'google'>('linkedin');

  // LinkedIn State
  const [linkedinUrl, setLinkedinUrl] = useState(
    user.connectedAccounts?.linkedin?.profileUrl || 'https://www.linkedin.com/in/abhimanyu-candidate/'
  );
  const [linkedinText, setLinkedinText] = useState('');
  const [linkedinLoading, setLinkedinLoading] = useState(false);
  const [linkedinSuccess, setLinkedinSuccess] = useState(false);

  // Naukri State
  const [naukriSyncMethod, setNaukriSyncMethod] = useState<'credentials' | 'text'>('credentials');
  const [naukriEmail, setNaukriEmail] = useState('');
  const [naukriPassword, setNaukriPassword] = useState('');
  const [naukriShowPassword, setNaukriShowPassword] = useState(false);
  const [browserLogs, setBrowserLogs] = useState<string[]>([]);

  const [noticePeriod, setNoticePeriod] = useState<number>(user.noticePeriodDays || 30);
  const [currentCtc, setCurrentCtc] = useState<number>(user.currentCtcLpa || 18);
  const [expectedCtc, setExpectedCtc] = useState<number>(user.expectedCtcLpa || 28);
  const [naukriText, setNaukriText] = useState('');
  const [naukriLoading, setNaukriLoading] = useState(false);
  const [naukriSuccess, setNaukriSuccess] = useState(false);

  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Listen to WebSocket integration logs
  useEffect(() => {
    if (
      latestEvent?.event === 'INTEGRATION_SYNC_LOG' &&
      latestEvent?.payload?.service === 'naukri'
    ) {
      setBrowserLogs((prev) => [...prev, latestEvent.payload.message]);
    }
  }, [latestEvent]);

  if (!isOpen) return null;

  const handleSyncLinkedIn = async () => {
    setLinkedinLoading(true);
    setErrorMsg(null);
    try {
      const res = await api.syncLinkedIn({
        userId: user.userId,
        profileUrl: linkedinUrl,
        profileText: linkedinText || undefined,
      });

      setLinkedinSuccess(true);
      onProfileUpdated(res.updatedProfile);
      setTimeout(() => setLinkedinSuccess(false), 4000);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to sync LinkedIn profile.');
    } finally {
      setLinkedinLoading(false);
    }
  };

  const handleSyncNaukri = async () => {
    setNaukriLoading(true);
    setBrowserLogs([]);
    setErrorMsg(null);
    try {
      const res = await api.syncNaukri({
        userId: user.userId,
        syncMethod: naukriSyncMethod.toUpperCase(),
        username: naukriSyncMethod === 'credentials' ? naukriEmail : undefined,
        password: naukriSyncMethod === 'credentials' ? naukriPassword : undefined,
        profileText: naukriSyncMethod === 'text' ? naukriText : undefined,
        noticePeriodDays: noticePeriod,
        currentCtcLpa: currentCtc,
        expectedCtcLpa: expectedCtc,
      });

      setNaukriSuccess(true);
      onProfileUpdated(res.updatedProfile);
      setTimeout(() => setNaukriSuccess(false), 4000);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to sync Naukri profile.');
    } finally {
      setNaukriLoading(false);
    }
  };

  const isLinkedInConnected = user.connectedAccounts?.linkedin?.connected;
  const isNaukriConnected = user.connectedAccounts?.naukri?.connected;
  const isGoogleConnected = user.connectedAccounts?.google?.connected;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-xl glass-panel rounded-2xl border border-slate-700/80 shadow-2xl p-6 space-y-6 text-xs text-white max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <span>🔗</span> Connected Profiles & Integrations
            </h2>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Sync skills, CTC, and career history directly from your professional accounts.
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Integration Status Badges */}
        <div className="grid grid-cols-3 gap-2.5">
          <button
            onClick={() => setActiveTab('linkedin')}
            className={`p-3 rounded-xl border transition text-left flex flex-col justify-between cursor-pointer ${
              activeTab === 'linkedin'
                ? 'bg-blue-950/40 border-blue-500/60 ring-1 ring-blue-500/50'
                : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="font-bold text-blue-400">💼 LinkedIn</span>
              <span
                className={`w-2 h-2 rounded-full ${
                  isLinkedInConnected ? 'bg-emerald-400 shadow-sm shadow-emerald-400/50' : 'bg-slate-600'
                }`}
              />
            </div>
            <span className="text-[10px] text-slate-400 mt-2 block">
              {isLinkedInConnected ? 'Synced & Active' : 'Not Connected'}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('naukri')}
            className={`p-3 rounded-xl border transition text-left flex flex-col justify-between cursor-pointer ${
              activeTab === 'naukri'
                ? 'bg-amber-950/40 border-amber-500/60 ring-1 ring-amber-500/50'
                : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="font-bold text-amber-400">🔶 Naukri</span>
              <span
                className={`w-2 h-2 rounded-full ${
                  isNaukriConnected ? 'bg-emerald-400 shadow-sm shadow-emerald-400/50' : 'bg-slate-600'
                }`}
              />
            </div>
            <span className="text-[10px] text-slate-400 mt-2 block">
              {isNaukriConnected ? 'Synced (India CTC)' : 'Not Connected'}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('google')}
            className={`p-3 rounded-xl border transition text-left flex flex-col justify-between cursor-pointer ${
              activeTab === 'google'
                ? 'bg-emerald-950/40 border-emerald-500/60 ring-1 ring-emerald-500/50'
                : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="font-bold text-emerald-400">🔵 Google</span>
              <span
                className={`w-2 h-2 rounded-full ${
                  isGoogleConnected ? 'bg-emerald-400 shadow-sm shadow-emerald-400/50' : 'bg-emerald-400'
                }`}
              />
            </div>
            <span className="text-[10px] text-slate-400 mt-2 block">
              {isGoogleConnected ? 'Primary Auth' : 'Connected'}
            </span>
          </button>
        </div>

        {errorMsg && (
          <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-500/40 text-rose-300 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Tab 1: LinkedIn Integration */}
        {activeTab === 'linkedin' && (
          <div className="space-y-4 animate-fadeIn">
            <div className="p-4 rounded-xl bg-blue-950/20 border border-blue-500/30 space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-blue-300">LinkedIn Profile Sync</span>
                <span className="text-[10px] text-slate-400">AI-powered skill & experience extractor</span>
              </div>

              <div className="space-y-1.5">
                <label className="text-[11px] text-slate-300 font-medium">Public LinkedIn Profile URL</label>
                <div className="relative">
                  <input
                    type="url"
                    value={linkedinUrl}
                    onChange={(e) => setLinkedinUrl(e.target.value)}
                    placeholder="https://www.linkedin.com/in/username"
                    className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
                  />
                  <ExternalLink className="w-3.5 h-3.5 text-slate-500 absolute right-3 top-1/2 -translate-y-1/2" />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-[11px] text-slate-300 font-medium">
                  Optional: Paste LinkedIn "About" or Experience text (for deep parsing)
                </label>
                <textarea
                  value={linkedinText}
                  onChange={(e) => setLinkedinText(e.target.value)}
                  rows={3}
                  placeholder="Paste your LinkedIn summary, key responsibilities, or skills here..."
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
                />
              </div>

              {linkedinSuccess && (
                <div className="p-2.5 rounded-lg bg-emerald-950/40 border border-emerald-500/40 text-emerald-300 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>LinkedIn profile synced successfully! Skills and headline updated.</span>
                </div>
              )}

              <button
                onClick={handleSyncLinkedIn}
                disabled={linkedinLoading}
                className="w-full py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs shadow-lg shadow-blue-600/20 transition cursor-pointer flex items-center justify-center gap-2 disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${linkedinLoading ? 'animate-spin' : ''}`} />
                <span>{linkedinLoading ? 'Extracting & Syncing...' : 'Sync Candidate Details from LinkedIn'}</span>
              </button>
            </div>
          </div>
        )}

        {/* Tab 2: Naukri Integration */}
        {activeTab === 'naukri' && (
          <div className="space-y-4 animate-fadeIn">
            <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-500/30 space-y-4">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-amber-300">Naukri.com India Profile Sync</span>
                <span className="text-[10px] text-slate-400">Notice period & CTC matching</span>
              </div>

              {/* Sync Method Switcher */}
              <div className="flex bg-slate-900/60 p-0.5 rounded-lg border border-slate-800">
                <button
                  type="button"
                  onClick={() => setNaukriSyncMethod('credentials')}
                  className={`flex-1 py-1 rounded-md text-[11px] font-semibold transition cursor-pointer ${
                    naukriSyncMethod === 'credentials'
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  🌐 Headless Browser Agent
                </button>
                <button
                  type="button"
                  onClick={() => setNaukriSyncMethod('text')}
                  className={`flex-1 py-1 rounded-md text-[11px] font-semibold transition cursor-pointer ${
                    naukriSyncMethod === 'text'
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  📝 Manual Copy-Paste
                </button>
              </div>

              {naukriSyncMethod === 'credentials' ? (
                <div className="space-y-3">
                  <div className="p-2.5 rounded-lg bg-amber-500/5 border border-amber-500/10 text-[10px] text-amber-400 leading-relaxed">
                    ⚠️ <strong>How it works:</strong> Your credentials are sent securely to launch a transient headless Playwright Chromium worker, navigate to your profile dashboard, scrape parameters, and exit. No passwords are persisted.
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div className="space-y-1">
                      <label className="text-[10px] text-slate-300 font-medium">Naukri Username/Email</label>
                      <input
                        type="email"
                        value={naukriEmail}
                        onChange={(e) => setNaukriEmail(e.target.value)}
                        placeholder="candidate@email.com"
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-amber-500"
                      />
                    </div>

                    <div className="space-y-1">
                      <label className="text-[10px] text-slate-300 font-medium">Naukri Password</label>
                      <div className="relative">
                        <input
                          type={naukriShowPassword ? 'text' : 'password'}
                          value={naukriPassword}
                          onChange={(e) => setNaukriPassword(e.target.value)}
                          placeholder="••••••••"
                          className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-amber-500 pr-8"
                        />
                        <button
                          type="button"
                          onClick={() => setNaukriShowPassword(!naukriShowPassword)}
                          className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200"
                        >
                          {naukriShowPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="grid grid-cols-3 gap-2">
                    <div className="space-y-1">
                      <label className="text-[10px] text-slate-400">Notice Period</label>
                      <select
                        value={noticePeriod}
                        onChange={(e) => setNoticePeriod(Number(e.target.value))}
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2 py-1.5 text-xs text-white"
                      >
                        <option value={0}>Immediate (0d)</option>
                        <option value={15}>15 Days</option>
                        <option value={30}>30 Days</option>
                        <option value={60}>60 Days</option>
                        <option value={90}>90 Days</option>
                      </select>
                    </div>

                    <div className="space-y-1">
                      <label className="text-[10px] text-slate-400">Current CTC</label>
                      <div className="relative">
                        <input
                          type="number"
                          value={currentCtc}
                          onChange={(e) => setCurrentCtc(Number(e.target.value))}
                          className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2 py-1.5 text-xs text-white pr-7"
                        />
                        <span className="absolute right-2 top-1.5 text-[10px] text-slate-500 font-bold">LPA</span>
                      </div>
                    </div>

                    <div className="space-y-1">
                      <label className="text-[10px] text-slate-400">Expected CTC</label>
                      <div className="relative">
                        <input
                          type="number"
                          value={expectedCtc}
                          onChange={(e) => setExpectedCtc(Number(e.target.value))}
                          className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2 py-1.5 text-xs text-white pr-7"
                        />
                        <span className="absolute right-2 top-1.5 text-[10px] text-amber-400 font-bold">LPA</span>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-[11px] text-slate-300 font-medium">
                      Paste Naukri Key Skills or Resume Details
                    </label>
                    <textarea
                      value={naukriText}
                      onChange={(e) => setNaukriText(e.target.value)}
                      rows={3}
                      placeholder="e.g. Python, FastAPI, PostgreSQL, Docker, AWS, Microservices..."
                      className="w-full bg-slate-900 border border-slate-700 rounded-xl p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-amber-500"
                    />
                  </div>
                </div>
              )}

              {/* Browser Automation Terminal Logs */}
              {naukriLoading && browserLogs.length > 0 && (
                <div className="space-y-1.5">
                  <div className="flex items-center gap-1.5 text-slate-400">
                    <Terminal className="w-3.5 h-3.5 text-amber-400" />
                    <span className="text-[10px] font-bold uppercase tracking-wider font-mono">Live Browser Log Console</span>
                  </div>
                  <div className="bg-slate-950/90 font-mono text-[10px] text-amber-300 p-3 rounded-lg border border-slate-800 h-32 overflow-y-auto space-y-1.5 scrollbar-thin">
                    {browserLogs.map((log, idx) => (
                      <div key={idx} className="flex items-start gap-1">
                        <span className="text-slate-600 select-none">&gt;</span>
                        <span>{log}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {naukriSuccess && (
                <div className="p-2.5 rounded-lg bg-emerald-950/40 border border-emerald-500/40 text-emerald-300 flex items-center gap-2 animate-fadeIn">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>Naukri parameters & expected CTC updated in profile!</span>
                </div>
              )}

              <button
                onClick={handleSyncNaukri}
                disabled={naukriLoading || (naukriSyncMethod === 'credentials' && (!naukriEmail || !naukriPassword))}
                className="w-full py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs shadow-lg shadow-amber-500/20 transition cursor-pointer flex items-center justify-center gap-2 disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${naukriLoading ? 'animate-spin' : ''}`} />
                <span>
                  {naukriLoading
                    ? naukriSyncMethod === 'credentials'
                      ? 'Automating Browser Sync...'
                      : 'Syncing...'
                    : 'Sync Candidate Details from Naukri'}
                </span>
              </button>
            </div>
          </div>
        )}

        {/* Tab 3: Google Identity */}
        {activeTab === 'google' && (
          <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-500/30 space-y-3 animate-fadeIn">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-emerald-300">Google OAuth Identity</span>
              <span className="px-2 py-0.5 rounded-full bg-emerald-900/60 text-emerald-400 font-bold text-[10px]">
                Connected
              </span>
            </div>

            <div className="space-y-2 text-slate-300 text-xs">
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-400">Authenticated Email:</span>
                <span className="font-semibold text-white">{user.email || 'abhimanyu.candidate@gmail.com'}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-400">Identity Provider:</span>
                <span className="font-semibold text-emerald-400">Google Identity Services</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-400">Security Mode:</span>
                <span className="font-semibold text-slate-300">OAuth 2.0 / JWT Verified</span>
              </div>
            </div>
          </div>
        )}

        {/* Footer Actions */}
        <div className="pt-3 border-t border-slate-800 flex justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-semibold transition cursor-pointer"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
