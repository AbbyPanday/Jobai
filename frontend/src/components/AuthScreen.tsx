'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Bot,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  Zap,
  Mail,
  User,
  AlertCircle,
  Eye,
  EyeOff
} from 'lucide-react';
import { api, UserProfile } from '../lib/api';

interface Props {
  onAuthenticated: (user: UserProfile) => void;
}

export function AuthScreen({ onAuthenticated }: Props) {
  const [isRegistering, setIsRegistering] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [targetRole, setTargetRole] = useState('Software Engineer');
  const [expectedCtc, setExpectedCtc] = useState('25');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [googleClientId, setGoogleClientId] = useState<string | null>(null);
  const [gsiLoaded, setGsiLoaded] = useState(false);
  const googleButtonRef = useRef<HTMLDivElement>(null);

  // Fetch auth config from backend to check if Google Client ID is available
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/auth/config`);
        if (res.ok) {
          const config = await res.json();
          if (config.googleClientId) {
            setGoogleClientId(config.googleClientId);
          }
        }
      } catch {
        // Config endpoint unavailable - proceed without Google OAuth
      }
    };
    fetchConfig();
  }, []);

  // Load Google Identity Services SDK when client ID is available
  useEffect(() => {
    if (!googleClientId) return;

    const existingScript = document.getElementById('gsi-script');
    if (existingScript) {
      // Script already loaded, just initialize
      initializeGSI();
      return;
    }

    const script = document.createElement('script');
    script.id = 'gsi-script';
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = () => {
      setGsiLoaded(true);
      initializeGSI();
    };
    script.onerror = () => {
      console.warn('Failed to load Google Identity Services SDK');
    };
    document.head.appendChild(script);
  }, [googleClientId]);

  const initializeGSI = useCallback(() => {
    if (!googleClientId || !(window as any).google?.accounts?.id) return;

    (window as any).google.accounts.id.initialize({
      client_id: googleClientId,
      callback: handleGoogleCredentialResponse,
      auto_select: false,
      cancel_on_tap_outside: true,
    });

    // Render the official Google button
    if (googleButtonRef.current) {
      googleButtonRef.current.innerHTML = '';
      (window as any).google.accounts.id.renderButton(googleButtonRef.current, {
        type: 'standard',
        theme: 'filled_black',
        size: 'large',
        text: 'continue_with',
        shape: 'pill',
        width: googleButtonRef.current.offsetWidth,
        logo_alignment: 'left',
      });
    }
  }, [googleClientId]);

  // Re-render Google button when GSI loads
  useEffect(() => {
    if (gsiLoaded && googleClientId) {
      // Small delay to ensure DOM is ready
      setTimeout(initializeGSI, 100);
    }
  }, [gsiLoaded, googleClientId, initializeGSI]);

  // Handle the Google credential response (JWT ID token)
  const handleGoogleCredentialResponse = async (response: any) => {
    setIsLoading(true);
    setErrorMessage('');
    try {
      // Decode the JWT to get user info (the backend will verify the token)
      const payload = JSON.parse(atob(response.credential.split('.')[1]));

      const res = await api.googleAuth({
        email: payload.email,
        name: payload.name,
        googleId: payload.sub,
        picture: payload.picture,
        idToken: response.credential,
      });
      onAuthenticated(res.user);
    } catch (err: any) {
      console.error('Google Auth Error:', err);
      setErrorMessage(err.message || 'Google authentication failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  // Fallback Google sign-in without GSI (when no Client ID is configured)
  const handleGoogleFallback = async () => {
    if (!email.trim()) {
      setErrorMessage('Enter your email address first, then click "Continue with Google".');
      return;
    }
    setIsLoading(true);
    setErrorMessage('');
    try {
      const res = await api.googleAuth({
        email: email.trim(),
        name: name.trim() || email.split('@')[0],
        googleId: `gid_${Date.now()}`,
      });
      onAuthenticated(res.user);
    } catch (err: any) {
      console.error('Auth Error:', err);
      setErrorMessage(err.message || 'Authentication failed.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleEmailAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password.trim()) {
      setErrorMessage('Please enter both email and password.');
      return;
    }

    setIsLoading(true);
    setErrorMessage('');
    try {
      if (isRegistering) {
        if (!name.trim()) {
          setErrorMessage('Please enter your full name.');
          setIsLoading(false);
          return;
        }
        const res = await api.register({
          name: name.trim(),
          email: email.trim(),
          password: password.trim(),
          targetRole: targetRole.trim(),
          expectedCtcLpa: parseFloat(expectedCtc) || 25.0
        });
        onAuthenticated(res.user);
      } else {
        const res = await api.login(email.trim(), password.trim());
        onAuthenticated(res.user);
      }
    } catch (err: any) {
      console.error('Auth Error:', err);
      setErrorMessage(err.message || 'Authentication error. Please check your credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 sm:p-6 bg-slate-950 text-slate-100 selection:bg-emerald-500 selection:text-slate-950">
      {/* Background Glow */}
      <div className="fixed inset-0 pointer-events-none opacity-30">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_15%,#1e3a8a_0%,transparent_65%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_80%_80%,#064e3b_0%,transparent_45%)]" />
      </div>

      <div className="relative w-full max-w-md glass-panel rounded-3xl border border-slate-800 p-8 sm:p-10 shadow-2xl space-y-6 animate-fadeIn">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-tr from-emerald-500 to-teal-400 p-0.5 shadow-lg shadow-emerald-500/20 mb-2">
            <div className="w-full h-full bg-slate-950 rounded-[14px] flex items-center justify-center text-emerald-400">
              <Bot className="w-7 h-7" />
            </div>
          </div>
          <h1 className="text-2xl font-black tracking-tight text-white">
            Job Intelligence <span className="gradient-text-emerald">Engine</span>
          </h1>
          <p className="text-xs text-slate-400 max-w-xs mx-auto leading-relaxed">
            AI-powered job matching, salary research & autonomous applications for India's tech market
          </p>
        </div>

        {/* Google Sign-In — Real GSI or Fallback */}
        <div className="space-y-3">
          {googleClientId ? (
            /* Real Google Identity Services button */
            <div className="w-full flex justify-center">
              <div ref={googleButtonRef} className="w-full min-h-[44px] flex items-center justify-center" />
            </div>
          ) : (
            /* Fallback — quick sign-in using email */
            <button
              type="button"
              onClick={handleGoogleFallback}
              disabled={isLoading}
              className="w-full py-3 px-4 rounded-xl bg-white hover:bg-slate-100 text-slate-900 font-bold text-xs flex items-center justify-center gap-3 shadow-md transition transform active:scale-[0.98] disabled:opacity-60"
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17z" />
                <path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.15C3.26 21.36 7.34 24 12 24z" />
                <path fill="#FBBC05" d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.25C.45 8.18 0 9.98 0 12s.45 3.82 1.25 5.42l4.03-3.15z" />
                <path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.34 0 3.26 2.64 1.25 6.58l4.03 3.15c.95-2.83 3.6-4.98 6.72-4.98z" />
              </svg>
              <span>Continue with Google</span>
            </button>
          )}

          {/* Divider */}
          <div className="flex items-center gap-3 py-1">
            <div className="flex-1 h-px bg-slate-800" />
            <span className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold">Or with Email</span>
            <div className="flex-1 h-px bg-slate-800" />
          </div>
        </div>

        {/* Error Alert */}
        {errorMessage && (
          <div className="p-3 rounded-xl bg-rose-950/30 border border-rose-500/40 text-rose-300 text-xs flex items-start gap-2 animate-fadeIn">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Email & Password Form */}
        <form onSubmit={handleEmailAuth} className="space-y-3.5 text-xs">
          {isRegistering && (
            <div>
              <label className="text-slate-400 block mb-1 font-medium">Full Name</label>
              <div className="relative">
                <User className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Your full name"
                  required
                  className="w-full bg-slate-900 border border-slate-700/80 rounded-xl pl-9 pr-3 py-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition"
                />
              </div>
            </div>
          )}

          <div>
            <label className="text-slate-400 block mb-1 font-medium">Email Address</label>
            <div className="relative">
              <Mail className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@company.com"
                required
                className="w-full bg-slate-900 border border-slate-700/80 rounded-xl pl-9 pr-3 py-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition"
              />
            </div>
          </div>

          <div>
            <label className="text-slate-400 block mb-1 font-medium">Password</label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                className="w-full bg-slate-900 border border-slate-700/80 rounded-xl pl-3 pr-10 py-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition"
                tabIndex={-1}
              >
                {showPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>

          {isRegistering && (
            <div className="grid grid-cols-2 gap-3 pt-1">
              <div>
                <label className="text-slate-400 block mb-1 font-medium">Target Role</label>
                <input
                  type="text"
                  value={targetRole}
                  onChange={(e) => setTargetRole(e.target.value)}
                  placeholder="Senior Backend Engineer"
                  className="w-full bg-slate-900 border border-slate-700/80 rounded-xl p-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1 font-medium">Expected CTC (LPA)</label>
                <input
                  type="number"
                  value={expectedCtc}
                  onChange={(e) => setExpectedCtc(e.target.value)}
                  placeholder="28"
                  className="w-full bg-slate-900 border border-slate-700/80 rounded-xl p-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition"
                />
              </div>
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-slate-950 font-bold text-xs flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/20 transition transform active:scale-[0.98] disabled:opacity-50"
          >
            {isLoading ? (
              <div className="w-4 h-4 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />
            ) : (
              <>
                <span>{isRegistering ? 'Create Account' : 'Sign In'}</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        {/* Toggle Mode */}
        <div className="text-center text-xs text-slate-400">
          {isRegistering ? (
            <span>
              Already have an account?{' '}
              <button
                type="button"
                onClick={() => { setIsRegistering(false); setErrorMessage(''); }}
                className="text-emerald-400 hover:underline font-bold"
              >
                Sign In
              </button>
            </span>
          ) : (
            <span>
              Don&apos;t have an account?{' '}
              <button
                type="button"
                onClick={() => { setIsRegistering(true); setErrorMessage(''); }}
                className="text-emerald-400 hover:underline font-bold"
              >
                Create Account
              </button>
            </span>
          )}
        </div>

        {/* Trust Badges */}
        <div className="pt-3 border-t border-slate-800/80 flex items-center justify-center gap-6 text-[11px] text-slate-400">
          <div className="flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>Secure Auth</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Zap className="w-3.5 h-3.5 text-sky-400" />
            <span>Gemini AI Powered</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            <span>India Focus</span>
          </div>
        </div>
      </div>
    </div>
  );
}
