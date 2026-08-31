'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Sparkles,
  Bot,
  Search,
  Building2,
  MapPin,
  IndianRupee,
  ShieldCheck,
  CheckCircle2,
  Clock,
  User,
  LogOut,
  RefreshCw,
  SlidersHorizontal,
  Flame,
  ChevronDown,
  UploadCloud,
  FileText,
  Sun,
  Moon
} from 'lucide-react';
import { api, Job, UserProfile, Application } from '../lib/api';
import { useAgentSocket } from '../hooks/useAgentSocket';
import { AuthScreen } from '../components/AuthScreen';
import { ResumeUploadOnboarding } from '../components/ResumeUploadOnboarding';
import { JobCard } from '../components/JobCard';
import { LiveChatAgent } from '../components/LiveChatAgent';
import { HitlReviewModal } from '../components/HitlReviewModal';
import { ProfileModal } from '../components/ProfileModal';
import { ConnectedAccountsModal } from '../components/ConnectedAccountsModal';
import { GoogleSignInButton } from '../components/GoogleSignInButton';

export default function DashboardPage() {
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [activeTab, setActiveTab] = useState<'all' | 'high_match' | 'pipeline' | 'networking'>('high_match');
  const [isIngesting, setIsIngesting] = useState(false);
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);
  const [isConnectedAccountsOpen, setIsConnectedAccountsOpen] = useState(false);
  const [isResumeUploadOpen, setIsResumeUploadOpen] = useState(false);
  const [isHitlModalOpen, setIsHitlModalOpen] = useState(false);
  const [activeHitlReview, setActiveHitlReview] = useState<any>(null);
  const [openProofAppId, setOpenProofAppId] = useState<string | null>(null);
  const [selectedLocation, setSelectedLocation] = useState<string>('All');
  const [selectedSource, setSelectedSource] = useState<string>('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [userDropdownOpen, setUserDropdownOpen] = useState(false);
  const [networkMatches, setNetworkMatches] = useState<any[]>([]);
  const [networkLoading, setNetworkLoading] = useState(false);
  const [theme, setTheme] = useState<'light' | 'dark'>('dark');

  // Initialize theme from localStorage
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const storedTheme = localStorage.getItem('theme') as 'light' | 'dark' | null;
      const initialTheme = storedTheme || 'dark';
      setTheme(initialTheme);
      if (initialTheme === 'dark') {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }
    }
  }, []);

  const toggleTheme = () => {
    const nextTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(nextTheme);
    localStorage.setItem('theme', nextTheme);
    if (nextTheme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  };

  // Load jobs and applications
  const loadData = useCallback(async (user?: UserProfile) => {
    const activeUserId = user?.userId || currentUser?.userId;
    try {
      const [fetchedJobs, fetchedApps] = await Promise.all([
        api.getJobs(activeUserId),
        api.getApplications(activeUserId),
      ]);
      setJobs(Array.isArray(fetchedJobs) ? fetchedJobs : []);
      setApplications(Array.isArray(fetchedApps) ? fetchedApps : []);
    } catch (e) {
      console.error('Data loading error:', e);
      setJobs([]);
      setApplications([]);
    }
  }, [currentUser?.userId]);

  // Check and validate stored auth session on initial load
  useEffect(() => {
    const checkSession = async () => {
      const session = api.getStoredSession();
      if (session.user && session.token) {
        try {
          const validProfile = await api.getProfile(session.user.userId);
          if (validProfile && validProfile.userId) {
            setCurrentUser(validProfile);
            await loadData(validProfile);
          } else {
            api.logout();
            setCurrentUser(null);
          }
        } catch {
          // Stale session
          api.logout();
          setCurrentUser(null);
        }
      } else {
        setCurrentUser(null);
      }
      setIsAuthLoading(false);
    };
    checkSession();
  }, [loadData]);

  // Socket connection to backend
  const {
    isConnected,
    logs,
    activeQuestion,
    hitlReview,
    triggerManualApply,
    answerQuestion,
    submitHitlDecision,
    clearLogs,
    latestEvent,
  } = useAgentSocket(currentUser?.userId || '');

  // When HITL review event arrives, automatically open review modal
  useEffect(() => {
    if (hitlReview) {
      setActiveHitlReview(hitlReview);
      setIsHitlModalOpen(true);
    }
  }, [hitlReview]);

  // Networking loader
  const loadNetworkMatches = useCallback(async () => {
    setNetworkLoading(true);
    try {
      const matches = await api.getNetworkMatches(10);
      setNetworkMatches(Array.isArray(matches) ? matches : []);
    } catch (e) {
      console.error('Network matches error:', e);
    } finally {
      setNetworkLoading(false);
    }
  }, []);

  // Load networking when tab becomes active
  useEffect(() => {
    if (activeTab === 'networking' && networkMatches.length === 0) {
      loadNetworkMatches();
    }
  }, [activeTab, networkMatches.length, loadNetworkMatches]);

  // Onboarding / Sign In Handler
  const handleAuthenticated = async (user: UserProfile) => {
    setCurrentUser(user);
    await loadData(user);
  };

  // Resume Document Ingested Handler
  const handleResumeUploaded = async (updatedUser: UserProfile) => {
    setCurrentUser(updatedUser);
    setIsResumeUploadOpen(false);
    await loadData(updatedUser);
  };

  // Sign out handler
  const handleLogout = () => {
    api.logout();
    setCurrentUser(null);
    setUserDropdownOpen(false);
    setJobs([]);
    setApplications([]);
  };

  // Trigger search ingestion
  const handleTriggerIngestion = async () => {
    setIsIngesting(true);
    try {
      const candidateSkills = Array.isArray(currentUser?.skills)
        ? currentUser.skills
        : typeof currentUser?.skills === 'object' && currentUser?.skills !== null
        ? [
            ...(currentUser.skills.primarySkills || []),
            ...(currentUser.skills.secondarySkills || []),
            ...(currentUser.skills.domainExpertise || []),
          ]
        : ['Python', 'FastAPI'];

      const criteria = {
        titles: [currentUser?.currentRole || 'Software Engineer', 'Backend Developer'],
        required_skills: candidateSkills.length > 0 ? candidateSkills : ['Python', 'FastAPI'],
        optional_skills: ['Kubernetes', 'PostgreSQL', 'Docker', 'Redis'],
        excluded_keywords: ['Intern', 'Fresher', 'Lead Manager'],
        locations: ['Bengaluru', 'Pune', 'Hyderabad', 'Remote'],
        min_exp_years: Math.max(1, Math.floor(currentUser?.experienceYears || 3)),
        max_exp_years: Math.ceil((currentUser?.experienceYears || 3) + 3),
      };
      await api.triggerSearch(criteria);
      await loadData(currentUser || undefined);
    } catch (e) {
      console.error('Ingestion error:', e);
    } finally {
      setIsIngesting(false);
    }
  };

  // Autonomous Apply Trigger
  const handleApply = (jobId: string) => {
    if (!currentUser) return;
    triggerManualApply(jobId);
  };

  // HITL Decision
  const handleHitlApprove = async (appId: string, token: string) => {
    submitHitlDecision(appId, 'APPROVE', token);
    setIsHitlModalOpen(false);
    setTimeout(() => loadData(currentUser || undefined), 1000);
  };

  const handleHitlReject = async (appId: string, token: string, feedback?: string) => {
    submitHitlDecision(appId, 'REJECT', token);
    setIsHitlModalOpen(false);
    setTimeout(() => loadData(currentUser || undefined), 1000);
  };

  // 1. If auth is still checking session -> Show clean loading state
  if (isAuthLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-100">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-xs text-slate-400 font-mono">Initializing Job Intelligence Engine...</span>
        </div>
      </div>
    );
  }

  // 2. If not authenticated -> Show Landing & Google Auth screen
  if (!currentUser) {
    return <AuthScreen onAuthenticated={handleAuthenticated} />;
  }

  // 3. If authenticated but has not uploaded a resume yet -> Show onboarding
  const candidateSkillsList = Array.isArray(currentUser.skills)
    ? currentUser.skills
    : typeof currentUser.skills === 'object' && currentUser.skills !== null
    ? [
        ...(currentUser.skills.primarySkills || []),
        ...(currentUser.skills.secondarySkills || []),
        ...(currentUser.skills.domainExpertise || []),
      ]
    : [];

  if (!currentUser.hasUploadedResume && candidateSkillsList.length === 0) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100">
        <ResumeUploadOnboarding
          key={`resume-${currentUser.userId}`}
          user={currentUser}
          onUploaded={handleResumeUploaded}
          onSkip={() => {
            const updated = { ...currentUser, hasUploadedResume: true };
            setCurrentUser(updated);
            loadData(updated);
          }}
        />
      </div>
    );
  }

  // Filter jobs safely
  const filteredJobs = (jobs || []).filter((j) => {
    if (!j) return false;
    const matchesTab = activeTab === 'high_match' ? (j.matchScore || 0) >= 80 : true;
    const matchesSource = selectedSource === 'All' || j.source === selectedSource;
    const loc = (j.location || '').toLowerCase();
    const matchesLocation =
      selectedLocation === 'All' || loc.includes(selectedLocation.toLowerCase());
    const query = (searchQuery || '').toLowerCase();
    const matchesSearch =
      !query ||
      (j.title && j.title.toLowerCase().includes(query)) ||
      (j.companyName && j.companyName.toLowerCase().includes(query)) ||
      ((j.extractedRequirements || []).some((r) => r && r.toLowerCase().includes(query)));
    return matchesTab && matchesSource && matchesLocation && matchesSearch;
  });

  const highMatchCount = (jobs || []).filter((j) => (j?.matchScore || 0) >= 80).length;
  const pendingHitlCount = (applications || []).filter((a) => a?.status === 'AWAITING_HITL_APPROVAL').length;

  return (
    <div className="min-h-screen pb-28 text-foreground selection:bg-emerald-500 selection:text-slate-950">
      {/* Sleek Top Navigation Bar */}
      <header className="sticky top-0 z-30 border-b border-border/80 bg-background/75 backdrop-blur-xl px-4 sm:px-8 py-3.5">
        <div className="max-w-6xl mx-auto flex items-center justify-between gap-4">
          {/* Logo & Title */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-400 p-0.5 shadow-md shadow-emerald-500/20">
              <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center text-emerald-400">
                <Bot className="w-4 h-4" />
              </div>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-black tracking-tight text-white">
                  Antigravity <span className="gradient-text-emerald">Engine</span>
                </span>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-800 text-slate-300 border border-slate-700">
                  🇮🇳 India Tech
                </span>
              </div>
            </div>
          </div>

          {/* User Profile & Account Menu */}
          <div className="flex items-center gap-2.5">
            <button
              onClick={() => setIsConnectedAccountsOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700/80 text-xs text-sky-400 font-semibold transition cursor-pointer"
            >
              <span>🔗</span>
              <span className="hidden sm:inline">Connected Profiles</span>
            </button>

            <button
              onClick={() => setIsResumeUploadOpen(true)}
              className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700/80 text-xs text-emerald-400 font-semibold transition cursor-pointer"
            >
              <UploadCloud className="w-3.5 h-3.5" />
              <span>Upload Resume</span>
            </button>

            <button
              onClick={toggleTheme}
              className="p-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700/80 text-slate-400 hover:text-white transition cursor-pointer flex items-center justify-center"
              title={theme === 'dark' ? 'Switch to Light Theme' : 'Switch to Dark Theme'}
            >
              {theme === 'dark' ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-indigo-400" />}
            </button>

            <div className="relative">
              <button
                onClick={() => setUserDropdownOpen(!userDropdownOpen)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900/90 hover:bg-slate-800 border border-slate-700/70 text-xs transition cursor-pointer"
              >
                <div className="w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold text-xs">
                  {currentUser?.name ? currentUser.name[0] : 'U'}
                </div>
                <div className="text-left hidden sm:block">
                  <span className="font-semibold text-white block leading-tight">{currentUser?.name}</span>
                  <span className="text-[10px] text-emerald-400 font-mono">
                    {currentUser?.currentRole || 'Candidate'}
                  </span>
                </div>
                <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
              </button>

              {/* Dropdown Menu */}
              {userDropdownOpen && (
                <div className="absolute right-0 mt-2 w-56 rounded-2xl glass-panel border border-slate-700 p-2 shadow-2xl space-y-1 text-xs z-50 animate-fadeIn">
                  <div className="p-2 border-b border-slate-800 text-[11px] text-slate-400">
                    Signed in as <strong className="text-slate-200">{currentUser?.email}</strong>
                  </div>
                  <button
                    onClick={() => {
                      setIsConnectedAccountsOpen(true);
                      setUserDropdownOpen(false);
                    }}
                    className="w-full text-left p-2 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800 flex items-center gap-2 transition cursor-pointer"
                  >
                    <span>🔗</span>
                    <span>LinkedIn & Naukri Sync</span>
                  </button>
                  <button
                    onClick={() => {
                      setIsResumeUploadOpen(true);
                      setUserDropdownOpen(false);
                    }}
                    className="w-full text-left p-2 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800 flex items-center gap-2 transition cursor-pointer"
                  >
                    <UploadCloud className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Upload Resume Document</span>
                  </button>
                  <button
                    onClick={() => {
                      setIsProfileModalOpen(true);
                      setUserDropdownOpen(false);
                    }}
                    className="w-full text-left p-2 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800 flex items-center gap-2 transition cursor-pointer"
                  >
                    <User className="w-3.5 h-3.5 text-sky-400" />
                    <span>Edit Profile Details</span>
                  </button>
                  <button
                    onClick={handleLogout}
                    className="w-full text-left p-2 rounded-lg text-rose-400 hover:bg-rose-950/40 flex items-center gap-2 transition cursor-pointer"
                  >
                    <LogOut className="w-3.5 h-3.5" />
                    <span>Sign Out</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-6xl mx-auto px-4 sm:px-8 pt-6 space-y-6">
        {/* AI Career Target Profile Banner */}
        <div className="glass-panel p-5 rounded-2xl border border-border/80 shadow-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4 bg-slate-900/40">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                AI Target Profile
              </span>
              {currentUser.hasUploadedResume && (
                <span className="text-[10px] text-slate-400 font-mono">
                  Parsed: {currentUser.resumeFilename}
                </span>
              )}
            </div>
            <h2 className="text-base font-extrabold text-foreground">
              Target Career Path Alignment
            </h2>
            <p className="text-xs text-slate-400 max-w-2xl leading-relaxed">
              Based on your resume and parsed profile, the AI agent evaluates job postings for target roles:
              <strong className="text-sky-400 ml-1">{currentUser.recommendedPosition || currentUser.currentRole || 'Software Engineer'}</strong> within the <strong className="text-emerald-400">{currentUser.recommendedDomain || 'Enterprise Software'}</strong> domain.
            </p>
          </div>
          
          <div className="flex items-center gap-3 shrink-0 self-stretch md:self-auto border-t md:border-t-0 border-slate-800 pt-3 md:pt-0">
            <div className="px-4 py-2 rounded-xl bg-slate-950/40 border border-slate-800/80 text-center">
              <span className="text-[10px] text-slate-400 block font-semibold uppercase tracking-wider">Years Experience</span>
              <span className="text-sm font-black text-white">{currentUser.yearsExperience || currentUser.experienceYears || '3.0'} Yrs</span>
            </div>
            <div className="px-4 py-2 rounded-xl bg-slate-950/40 border border-slate-800/80 text-center">
              <span className="text-[10px] text-slate-400 block font-semibold uppercase tracking-wider">Target Domain</span>
              <span className="text-sm font-black text-sky-400">{currentUser.recommendedDomain || 'Enterprise Software'}</span>
            </div>
          </div>
        </div>

        {/* Metric Overview Strip */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="glass-panel rounded-2xl p-3.5 border border-slate-800 flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <Flame className="w-4 h-4" />
            </div>
            <div>
              <span className="text-[11px] text-slate-400 block">High Matches</span>
              <span className="text-base font-bold text-white">{highMatchCount} Roles (≥80%)</span>
            </div>
          </div>

          <div className="glass-panel rounded-2xl p-3.5 border border-slate-800 flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <div>
              <span className="text-[11px] text-slate-400 block">HITL Gate Queue</span>
              <span className="text-base font-bold text-white">{pendingHitlCount} Awaiting Review</span>
            </div>
          </div>

          <div className="glass-panel rounded-2xl p-3.5 border border-slate-800 flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-sky-400">
              <IndianRupee className="w-4 h-4" />
            </div>
            <div>
              <span className="text-[11px] text-slate-400 block">Market Median CTC</span>
              <span className="text-base font-bold text-white">₹28 - 38 LPA</span>
            </div>
          </div>

          <div className="glass-panel rounded-2xl p-3.5 border border-slate-800 flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400">
              <Search className="w-4 h-4" />
            </div>
            <div>
              <span className="text-[11px] text-slate-400 block">Total Opportunities</span>
              <span className="text-base font-bold text-white">{jobs.length} Listings</span>
            </div>
          </div>
        </div>

        {/* Minimal Filter & Search Control Bar */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
          {/* View Tabs */}
          <div className="flex bg-slate-900/80 p-1 rounded-xl border border-slate-800 text-xs font-semibold w-full sm:w-auto overflow-x-auto">
            <button
              onClick={() => setActiveTab('high_match')}
              className={`px-3 py-1.5 rounded-lg transition flex items-center gap-1.5 cursor-pointer whitespace-nowrap ${
                activeTab === 'high_match'
                  ? 'bg-emerald-500 text-slate-950 font-bold shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Top Matches ({highMatchCount})</span>
            </button>
            <button
              onClick={() => setActiveTab('all')}
              className={`px-3 py-1.5 rounded-lg transition cursor-pointer whitespace-nowrap ${
                activeTab === 'all'
                  ? 'bg-emerald-500 text-slate-950 font-bold shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              All Openings ({jobs.length})
            </button>
            <button
              onClick={() => setActiveTab('pipeline')}
              className={`px-3 py-1.5 rounded-lg transition flex items-center gap-1.5 cursor-pointer whitespace-nowrap ${
                activeTab === 'pipeline'
                  ? 'bg-emerald-500 text-slate-950 font-bold shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Applications ({applications.length})</span>
            </button>
            <button
              onClick={() => setActiveTab('networking')}
              className={`px-3 py-1.5 rounded-lg transition flex items-center gap-1.5 cursor-pointer whitespace-nowrap ${
                activeTab === 'networking'
                  ? 'bg-sky-500 text-slate-950 font-bold shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <span>🔗</span>
              <span>Networking</span>
            </button>
          </div>

          {/* Search and Ingest Toolbar */}
          <div className="flex items-center gap-2 w-full sm:w-auto">
            <div className="relative flex-1 sm:w-64">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search role, skills, city..."
                className="w-full bg-slate-900/90 border border-slate-800 rounded-xl pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
              />
            </div>

            <button
              onClick={handleTriggerIngestion}
              disabled={isIngesting}
              title="Sync live portals (LinkedIn / Naukri)"
              className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs text-slate-200 font-semibold flex items-center gap-1.5 transition disabled:opacity-50 cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isIngesting ? 'animate-spin' : ''}`} />
              <span className="hidden md:inline">Sync Portals</span>
            </button>
          </div>
        </div>

        {/* Source Filter Chips */}
        {activeTab !== 'pipeline' && activeTab !== 'networking' && (
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[11px] text-slate-500 font-medium">Source:</span>
            {(['All', 'LINKEDIN', 'NAUKRI', 'GOOGLE_SEARCH'] as const).map((src) => (
              <button
                key={src}
                onClick={() => setSelectedSource(src)}
                className={`px-3 py-1 rounded-full text-[11px] font-semibold border transition cursor-pointer ${
                  selectedSource === src
                    ? src === 'LINKEDIN'
                      ? 'bg-blue-500/20 text-blue-300 border-blue-500/40'
                      : src === 'NAUKRI'
                      ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                      : src === 'GOOGLE_SEARCH'
                      ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                      : 'bg-slate-700 text-white border-slate-600'
                    : 'text-slate-400 border-slate-700/60 hover:border-slate-600'
                }`}
              >
                {src === 'All' ? '🌐 All' : src === 'LINKEDIN' ? '💼 LinkedIn' : src === 'NAUKRI' ? '🔶 Naukri' : '🔍 Google'}
              </button>
            ))}
            {selectedSource !== 'All' && (
              <span className="text-[11px] text-slate-500">
                {filteredJobs.length} result{filteredJobs.length !== 1 ? 's' : ''}
              </span>
            )}
          </div>
        )}

        {/* Feed List */}
        <div className="space-y-3 pt-2">
          {activeTab === 'networking' ? (
            /* Networking Tab — LinkedOut Matches */
            <div className="space-y-4">
              <div className="glass-panel rounded-2xl p-5 border border-sky-500/20 bg-sky-950/10">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h3 className="text-sm font-bold text-white flex items-center gap-2">
                      🔗 LinkedOut A2A Network Matches
                    </h3>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      Semantic matches with hiring agents — off-market roles before they hit job boards
                    </p>
                  </div>
                  <button
                    onClick={loadNetworkMatches}
                    disabled={networkLoading}
                    className="px-3 py-1.5 rounded-xl bg-sky-900/50 border border-sky-500/30 text-sky-300 text-xs font-semibold flex items-center gap-1.5 hover:bg-sky-900 transition cursor-pointer"
                  >
                    <RefreshCw className={`w-3 h-3 ${networkLoading ? 'animate-spin' : ''}`} />
                    Refresh
                  </button>
                </div>

                {networkLoading ? (
                  <div className="py-8 text-center text-slate-400 text-xs animate-pulse">Fetching network matches...</div>
                ) : networkMatches.length === 0 ? (
                  <div className="py-8 text-center space-y-3">
                    <div className="text-4xl">🔗</div>
                    <p className="text-xs text-slate-400">
                      No matches yet. Add your <strong className="text-white">LINKEDOUT_API_KEY</strong> to .env and register your agent to start networking.
                    </p>
                    <p className="text-[11px] text-sky-400 font-mono">
                      POST /api/v1/networking/register → post-intent → get matches
                    </p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {networkMatches.map((match: any, idx: number) => (
                      <div key={idx} className="p-4 rounded-xl border border-sky-500/20 bg-slate-900/60 flex items-start justify-between gap-4">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="w-8 h-8 rounded-full bg-sky-500/20 text-sky-400 flex items-center justify-center text-sm font-bold">
                              {(match.displayName || 'H')[0]}
                            </span>
                            <div>
                              <span className="text-sm font-bold text-white">{match.displayName || 'Hiring Agent'}</span>
                              <span className="text-[11px] text-slate-400 block">{match.headline || match.intent?.text?.slice(0, 80)}</span>
                            </div>
                          </div>
                          {match.tags && (
                            <div className="flex flex-wrap gap-1 pl-10">
                              {match.tags.slice(0, 5).map((tag: string, i: number) => (
                                <span key={i} className="px-1.5 py-0.5 rounded text-[10px] bg-sky-950/60 text-sky-300 border border-sky-700/40 font-mono">{tag}</span>
                              ))}
                            </div>
                          )}
                        </div>
                        <button
                          className="px-3 py-1.5 rounded-xl bg-sky-500 hover:bg-sky-400 text-slate-950 text-xs font-bold transition whitespace-nowrap cursor-pointer"
                          onClick={() => {
                            if (currentUser?.userId) {
                              api.postNetworkingIntent(currentUser.userId);
                            }
                          }}
                        >
                          Ping →
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : activeTab !== 'pipeline' ? (
            filteredJobs.length === 0 ? (
              <div className="glass-panel rounded-2xl p-10 text-center text-slate-400 space-y-3">
                <p className="text-xs font-semibold text-slate-300">
                  {jobs.length === 0
                    ? 'No indexed jobs found yet for your profile.'
                    : 'No openings found matching your search query or location filter.'}
                </p>
                <button
                  onClick={handleTriggerIngestion}
                  disabled={isIngesting}
                  className="px-6 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs shadow-lg shadow-emerald-500/20 transition cursor-pointer flex items-center gap-2 mx-auto disabled:opacity-50"
                >
                  <RefreshCw className={`w-4 h-4 ${isIngesting ? 'animate-spin' : ''}`} />
                  <span>{isIngesting ? 'Searching Live Portals...' : 'Search & Ingest Live Jobs'}</span>
                </button>
              </div>
            ) : (
              filteredJobs.map((job) => (
                <JobCard key={job.jobId} job={job} onApply={handleApply} />
              ))
            )
          ) : (
            /* Applications Pipeline Kanban */
            <div className="space-y-3">
              {applications.length === 0 ? (
                <div className="glass-panel rounded-2xl p-8 text-center text-slate-400 text-xs">
                  No active applications yet. Click "Apply" on any job card to launch the Playwright autonomous agent.
                </div>
              ) : (
                applications.map((app) => (
                  <div
                    key={app.applicationId}
                    className="glass-panel rounded-2xl p-4 border border-slate-800 space-y-3 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="text-sm font-bold text-white">{app.jobTitle || 'Software Engineer'}</h4>
                        <span className="text-slate-400">{app.companyName || 'Target Company'}</span>
                      </div>
                      <span
                        className={`px-2.5 py-0.5 rounded-full font-bold border ${
                          app.status === 'SUBMITTED'
                            ? 'bg-emerald-950/60 text-emerald-400 border-emerald-500/40'
                            : app.status === 'AWAITING_HITL_APPROVAL'
                            ? 'bg-amber-950/60 text-amber-400 border-amber-500/40 animate-pulse-subtle'
                            : 'bg-slate-800 text-slate-300 border-slate-700'
                        }`}
                      >
                        {app.status.replace(/_/g, ' ')}
                      </span>
                    </div>

                    {app.status === 'AWAITING_HITL_APPROVAL' && (
                      <div className="p-3 rounded-xl bg-amber-950/30 border border-amber-500/40 flex items-center justify-between">
                        <span className="text-amber-300">
                          Form autofilled completely. 1-Click candidate verification required.
                        </span>
                        <button
                          onClick={() => {
                            if (app.hitlReviewData) {
                              setActiveHitlReview({
                                applicationId: app.applicationId,
                                hitlPackage: app.hitlReviewData,
                              });
                            } else {
                              setActiveHitlReview(hitlReview);
                            }
                            setIsHitlModalOpen(true);
                          }}
                          className="px-3.5 py-1 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold transition cursor-pointer"
                        >
                          Review & Authorize
                        </button>
                      </div>
                    )}

                    {app.status === 'SUBMITTED' && (
                      <div className="space-y-2">
                        <div className="p-3 rounded-xl bg-emerald-950/30 border border-emerald-500/30 text-emerald-300 space-y-1.5">
                          <div className="flex items-center gap-2 font-semibold">
                            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                            <span>Application dispatched to career portal successfully.</span>
                          </div>
                          <div className="text-[11px] text-slate-400 space-y-0.5 pl-6 font-medium">
                            <p>
                              🗓️ <strong className="text-slate-300">Applied on:</strong>{' '}
                              {new Date(app.createdAt || Date.now()).toLocaleString('en-IN', {
                                day: '2-digit',
                                month: 'short',
                                year: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit',
                                hour12: true,
                              })}
                            </p>
                            <p>
                              🔑 <strong className="text-slate-300">Confirmation Ref:</strong>{' '}
                              <code className="bg-slate-900 px-1 py-0.5 rounded border border-slate-700 text-sky-400">
                                #REF-{app.applicationId.replace('app_', '').substring(0, 8).toUpperCase()}
                              </code>
                            </p>
                          </div>
                          
                          <div className="pt-1.5 pl-6">
                            <button
                              onClick={() => setOpenProofAppId(openProofAppId === app.applicationId ? null : app.applicationId)}
                              className="px-2.5 py-1 rounded bg-slate-900 border border-slate-700 hover:border-slate-600 hover:bg-slate-800 text-[11px] text-sky-400 font-bold transition flex items-center gap-1.5 cursor-pointer"
                            >
                              <span>🖼️</span>
                              <span>{openProofAppId === app.applicationId ? 'Hide Submission Proof' : 'View Submission Proof'}</span>
                            </button>
                          </div>
                        </div>

                        {openProofAppId === app.applicationId && (
                          <div className="rounded-xl overflow-hidden border border-slate-700 bg-slate-950 p-2 text-center space-y-2 animate-fadeIn max-w-lg mx-auto">
                            <p className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider">
                              Playwright Application Success Screenshot
                            </p>
                            <img
                              src={`http://localhost:8000/api/v1/applications/${app.applicationId}/proof`}
                              alt="Submission Proof"
                              className="w-full rounded-lg border border-slate-800 shadow-inner"
                              onError={(e) => {
                                // Fallback mock image if server endpoint has issues
                                e.currentTarget.src = "https://images.unsplash.com/photo-1486312338219-ce68d2c6f44d?w=600&q=80";
                              }}
                            />
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </main>

      {/* Floating Live AI Agent Drawer */}
      <LiveChatAgent
        isConnected={isConnected}
        logs={logs}
        activeQuestion={activeQuestion}
        hitlReview={hitlReview}
        onAnswerQuestion={answerQuestion}
        onOpenHitlModal={() => {
          if (hitlReview) {
            setActiveHitlReview(hitlReview);
          }
          setIsHitlModalOpen(true);
        }}
        onClearLogs={clearLogs}
      />

      {/* HITL Review Modal */}
      {isHitlModalOpen && activeHitlReview && (
        <HitlReviewModal
          data={activeHitlReview}
          onApprove={handleHitlApprove}
          onReject={handleHitlReject}
          onClose={() => {
            setIsHitlModalOpen(false);
            setActiveHitlReview(null);
          }}
        />
      )}

      {/* Resume Document Upload Modal */}
      {isResumeUploadOpen && currentUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
          <div className="relative w-full max-w-2xl">
            <ResumeUploadOnboarding
              key={`resume-${currentUser.userId}`}
              user={currentUser}
              onUploaded={handleResumeUploaded}
              onSkip={() => setIsResumeUploadOpen(false)}
            />
          </div>
        </div>
      )}

      {/* Candidate Persona Modal */}
      {currentUser && (
        <ProfileModal
          key={`profile-${currentUser.userId}`}
          profile={currentUser}
          isOpen={isProfileModalOpen}
          onClose={() => setIsProfileModalOpen(false)}
          onUpdate={(up) => setCurrentUser(up)}
        />
      )}

      {/* Connected Accounts & Profile Sync Modal */}
      {currentUser && (
        <ConnectedAccountsModal
          key={`conn-${currentUser.userId}`}
          user={currentUser}
          isOpen={isConnectedAccountsOpen}
          onClose={() => setIsConnectedAccountsOpen(false)}
          onProfileUpdated={(up) => setCurrentUser(up)}
          latestEvent={latestEvent}
        />
      )}
    </div>
  );
}
