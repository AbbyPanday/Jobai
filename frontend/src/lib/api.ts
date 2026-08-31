const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface SalaryIntelligence {
  company_name: string;
  designation: string;
  experience_bracket: string;
  estimated_ctc_min_lpa: number;
  estimated_ctc_max_lpa: number;
  estimated_ctc_median_lpa: number;
  fixed_base_percentage: number;
  variable_pay_details: string;
  esop_details?: string;
  ambitionbox_rating: number;
  glassdoor_rating: number;
  pros_summary: string[];
  cons_summary: string[];
  negotiation_leverage_tips: string[];
  monthly_in_hand_min_inr?: number;
  monthly_in_hand_median_inr?: number;
  monthly_in_hand_max_inr?: number;
}

export interface MatchBreakdown {
  hardSkills: number;
  experienceFit: number;
  domainFit: number;
  locationFit: number;
  ctcAlignment: number;
  softSkillsAndPedigree: number;
}

export interface Job {
  jobId: string;
  source: 'LINKEDIN' | 'NAUKRI' | 'GOOGLE_SEARCH';
  externalUrl: string;
  companyName: string;
  title: string;
  location: string;
  rawDescription: string;
  salaryIntelligence?: SalaryIntelligence;
  extractedRequirements: string[];
  postedAt: string;
  matchScore?: number;
  matchBreakdown?: MatchBreakdown;
  isHighMatch?: boolean;
  missingSkills?: string[];
  strengths?: string[];
  tailoredAdvice?: string;
}

export interface UserProfile {
  userId: string;
  name: string;
  fullName?: string;
  email: string;
  phone?: string;
  location?: string;
  currentRole?: string;
  headline?: string;
  experienceYears?: number;
  yearsExperience?: number;
  currentCtcLpa?: number;
  expectedCtcLpa?: number;
  noticePeriodDays?: number;
  skills: string[] | any;
  additionalSkills?: string[];
  summary?: string;
  hasUploadedResume?: boolean;
  resumeFilename?: string;
  picture?: string;
  profilePicture?: string;
  linkedInConnected?: boolean;
  naukriConnected?: boolean;
  recommendedPosition?: string;
  recommendedDomain?: string;
  autoApplyThreshold?: number;
  connectedAccounts?: {
    google?: { connected?: boolean; email?: string; picture?: string; [key: string]: any };
    linkedin?: { connected?: boolean; profileUrl?: string; syncedSkillsCount?: number; headline?: string; currentRole?: string; currentCompany?: string; [key: string]: any };
    naukri?: { connected?: boolean; naukriProfileUrl?: string; noticePeriodDays?: number; expectedCtcLpa?: number; currentCtcLpa?: number; syncedSkillsCount?: number; designation?: string; [key: string]: any };
    [key: string]: any;
  };
}

export interface Application {
  applicationId: string;
  userId: string;
  jobId: string;
  companyName?: string;
  jobTitle?: string;
  location?: string;
  matchScore: number;
  matchBreakdown?: MatchBreakdown;
  status: 'INITIALIZING' | 'AWAITING_HITL_APPROVAL' | 'SUBMITTED' | 'REJECTED_BY_USER';
  statusHistory: Array<{ status: string; timestamp: string; detail?: string }>;
  hitlReviewData?: {
    screenshotStorageUrl: string;
    filledFieldsSummary: Record<string, string>;
    reviewToken: string;
  };
  submissionProofUrl?: string;
  createdAt: string;
}

export const api = {
  // Google OAuth Auth
  async googleAuth(payload: { email: string; name: string; googleId?: string; picture?: string; idToken?: string }): Promise<{ token: string; user: UserProfile }> {
    const res = await fetch(`${API_BASE}/auth/google`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Google authentication failed');
    }
    const data = await res.json();
    if (typeof window !== 'undefined') {
      localStorage.setItem('auth_token', data.token);
      localStorage.setItem('auth_user', JSON.stringify(data.user));
    }
    return data;
  },

  // Direct Document Upload to Gemini
  async uploadResumeDocument(file: File, userId?: string): Promise<{ token: string; user: UserProfile; message: string }> {
    const formData = new FormData();
    formData.append('file', file);
    if (userId) {
      formData.append('userId', userId);
    }

    const res = await fetch(`${API_BASE}/auth/upload-resume`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Resume document upload and Gemini ingestion failed');
    }
    const data = await res.json();
    if (typeof window !== 'undefined') {
      localStorage.setItem('auth_token', data.token);
      localStorage.setItem('auth_user', JSON.stringify(data.user));
    }
    return data;
  },

  async login(email: string, password?: string): Promise<{ token: string; user: UserProfile }> {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Login failed');
    }
    const data = await res.json();
    if (typeof window !== 'undefined') {
      localStorage.setItem('auth_token', data.token);
      localStorage.setItem('auth_user', JSON.stringify(data.user));
    }
    return data;
  },

  async register(payload: { name: string; email: string; password: string; targetRole?: string; expectedCtcLpa?: number }): Promise<{ token: string; user: UserProfile }> {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Registration failed');
    }
    const data = await res.json();
    if (typeof window !== 'undefined') {
      localStorage.setItem('auth_token', data.token);
      localStorage.setItem('auth_user', JSON.stringify(data.user));
    }
    return data;
  },

  getStoredSession(): { token: string | null; user: UserProfile | null } {
    if (typeof window === 'undefined') return { token: null, user: null };
    try {
      const token = localStorage.getItem('auth_token');
      const userStr = localStorage.getItem('auth_user');
      return {
        token,
        user: userStr ? JSON.parse(userStr) : null,
      };
    } catch {
      return { token: null, user: null };
    }
  },

  logout() {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('auth_user');
    }
  },

  // Jobs
  async getJobs(userId?: string, minMatch = 0, source?: string, minCtc?: number, maxCtc?: number): Promise<Job[]> {
    try {
      let query = userId ? `?user_id=${userId}&min_match=${minMatch}` : `?min_match=${minMatch}`;
      if (source) query += `&source=${source}`;
      if (minCtc != null) query += `&min_ctc=${minCtc}`;
      if (maxCtc != null) query += `&max_ctc=${maxCtc}`;
      const res = await fetch(`${API_BASE}/jobs${query}`, { cache: 'no-store' });
      if (!res.ok) throw new Error('Failed to fetch jobs');
      return await res.json();
    } catch (e) {
      console.warn('API getJobs fallback:', e);
      return [];
    }
  },

  async triggerSearch(criteria: any): Promise<Job[]> {
    const res = await fetch(`${API_BASE}/jobs/ingest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ criteria }),
    });
    if (!res.ok) throw new Error('Ingestion failed');
    return await res.json();
  },

  async getSalaryResearch(company: string, role: string, expYears = 4): Promise<SalaryIntelligence> {
    const res = await fetch(`${API_BASE}/jobs/research/salary?company=${encodeURIComponent(company)}&role=${encodeURIComponent(role)}&exp_years=${expYears}`);
    if (!res.ok) throw new Error('Salary research failed');
    return await res.json();
  },

  // Profile
  async getProfile(userId: string): Promise<UserProfile> {
    const res = await fetch(`${API_BASE}/profile/${userId}`, { cache: 'no-store' });
    if (!res.ok) throw new Error('Failed to fetch profile');
    return await res.json();
  },

  async updateProfile(userId: string, updates: Partial<UserProfile>): Promise<UserProfile> {
    const res = await fetch(`${API_BASE}/profile/${userId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    });
    if (!res.ok) throw new Error('Failed to update profile');
    const updated = await res.json();
    if (typeof window !== 'undefined') {
      localStorage.setItem('auth_user', JSON.stringify(updated));
    }
    return updated;
  },

  // Applications & HITL
  async getApplications(userId?: string): Promise<Application[]> {
    try {
      const query = userId ? `?user_id=${userId}` : '';
      const res = await fetch(`${API_BASE}/applications${query}`, { cache: 'no-store' });
      if (!res.ok) throw new Error('Failed to fetch applications');
      return await res.json();
    } catch (e) {
      console.warn('API getApplications fallback:', e);
      return [];
    }
  },

  async applyToJob(jobId: string, userId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/applications/apply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ jobId, userId }),
    });
    if (!res.ok) throw new Error('Failed to trigger apply');
    return await res.json();
  },

  async submitHitlDecision(applicationId: string, decision: 'APPROVE' | 'REJECT', token: string, feedback?: string): Promise<any> {
    const res = await fetch(`${API_BASE}/applications/${applicationId}/decision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision, token, feedback }),
    });
    if (!res.ok) throw new Error('Failed to submit HITL decision');
    return await res.json();
  },

  // Networking (LinkedOut)
  async getNetworkingStatus(): Promise<{ configured: boolean; authenticated: boolean; agentId?: string; message: string }> {
    try {
      const res = await fetch(`${API_BASE}/networking/status`);
      if (!res.ok) throw new Error();
      return await res.json();
    } catch {
      return { configured: false, authenticated: false, message: 'Networking unavailable' };
    }
  },

  async postNetworkingIntent(userId: string): Promise<{ success: boolean; intent?: any }> {
    const res = await fetch(`${API_BASE}/networking/post-intent?userId=${userId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{}',
    });
    if (!res.ok) throw new Error('Failed to post intent');
    return await res.json();
  },

  async getNetworkMatches(limit = 10): Promise<any[]> {
    try {
      const res = await fetch(`${API_BASE}/networking/matches?limit=${limit}&category=jobs`);
      if (!res.ok) throw new Error();
      return await res.json();
    } catch {
      return [];
    }
  },

  async getNetworkFeed(limit = 20): Promise<any[]> {
    try {
      const res = await fetch(`${API_BASE}/networking/feed?limit=${limit}&category=jobs`);
      if (!res.ok) throw new Error();
      return await res.json();
    } catch {
      return [];
    }
  },

  // Account Integrations (LinkedIn & Naukri)
  async syncLinkedIn(payload: { userId: string; profileUrl?: string; profileText?: string }): Promise<{ success: boolean; extracted: any; updatedProfile: UserProfile }> {
    const res = await fetch(`${API_BASE}/integrations/linkedin/sync`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'LinkedIn profile sync failed');
    }
    return await res.json();
  },

  async syncNaukri(payload: {
    userId: string;
    syncMethod: string;
    username?: string;
    password?: string;
    profileText?: string;
    noticePeriodDays?: number;
    currentCtcLpa?: number;
    expectedCtcLpa?: number;
  }): Promise<{ success: boolean; extracted: any; updatedProfile: UserProfile }> {
    const res = await fetch(`${API_BASE}/integrations/naukri/sync`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Naukri profile sync failed');
    }
    return await res.json();
  },

  async getIntegrationStatus(userId: string): Promise<{ userId: string; connectedAccounts: any; totalSkills: number }> {
    try {
      const res = await fetch(`${API_BASE}/integrations/status/${userId}`);
      if (!res.ok) throw new Error();
      return await res.json();
    } catch {
      return {
        userId,
        connectedAccounts: {
          google: { connected: false },
          linkedin: { connected: false },
          naukri: { connected: false },
        },
        totalSkills: 0,
      };
    }
  },
};
