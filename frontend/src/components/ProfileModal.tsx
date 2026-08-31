'use client';

import React, { useState, useRef } from 'react';
import {
  X,
  User,
  Sparkles,
  Save,
  Check,
  Building,
  Briefcase,
  MapPin,
  Calendar,
  IndianRupee,
  ShieldAlert,
  UploadCloud,
  FileText,
  RefreshCw
} from 'lucide-react';
import { UserProfile, api } from '../lib/api';

interface Props {
  profile: UserProfile;
  isOpen: boolean;
  onClose: () => void;
  onUpdate: (updated: UserProfile) => void;
}

export function ProfileModal({ profile, isOpen, onClose, onUpdate }: Props) {
  const [formData, setFormData] = useState<UserProfile>(profile);
  const [isSaving, setIsSaving] = useState(false);
  const [isUploadingResume, setIsUploadingResume] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      const updated = await api.updateProfile(formData.userId, formData);
      onUpdate(updated);
      onClose();
    } catch (err) {
      console.error('Failed to update profile:', err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setIsUploadingResume(true);
      try {
        const res = await api.uploadResumeDocument(file, formData.userId);
        if (res.user) {
          setFormData(res.user);
          onUpdate(res.user);
          setUploadSuccess(true);
          setTimeout(() => setUploadSuccess(false), 3000);
        }
      } catch (err) {
        console.error('Failed to ingest resume document:', err);
      } finally {
        setIsUploadingResume(false);
      }
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto glass-panel rounded-2xl border border-slate-700 p-6 shadow-2xl text-slate-100">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <User className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Candidate Master Persona & Resume</h3>
              <p className="text-xs text-slate-400">Used by Gemini & Playwright to autofill job applications</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Account Integrations Bar */}
        <div className="grid grid-cols-2 gap-2.5 my-3">
          <div className="p-3 rounded-xl bg-blue-950/20 border border-blue-500/30 flex items-center justify-between">
            <div>
              <div className="flex items-center gap-1.5 font-bold text-blue-300 text-xs">
                <span>💼</span> LinkedIn Profile
              </div>
              <p className="text-[10px] text-slate-400">
                {formData.connectedAccounts?.linkedin?.connected ? 'Synced' : 'Import skills & experience'}
              </p>
            </div>
            <button
              type="button"
              onClick={async () => {
                const url = prompt('Enter your LinkedIn profile URL:', formData.connectedAccounts?.linkedin?.profileUrl || 'https://www.linkedin.com/in/candidate');
                if (url) {
                  try {
                    const res = await api.syncLinkedIn({ userId: formData.userId, profileUrl: url });
                    setFormData(res.updatedProfile);
                    onUpdate(res.updatedProfile);
                    alert('LinkedIn profile synced successfully!');
                  } catch (e: any) {
                    alert('Sync failed: ' + e.message);
                  }
                }
              }}
              className="px-2.5 py-1 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-bold text-[11px] transition cursor-pointer"
            >
              Sync
            </button>
          </div>

          <div className="p-3 rounded-xl bg-amber-950/20 border border-amber-500/30 flex items-center justify-between">
            <div>
              <div className="flex items-center gap-1.5 font-bold text-amber-300 text-xs">
                <span>🔶</span> Naukri India
              </div>
              <p className="text-[10px] text-slate-400">
                {formData.connectedAccounts?.naukri?.connected ? 'Synced' : 'Import CTC & Notice Period'}
              </p>
            </div>
            <button
              type="button"
              onClick={async () => {
                const text = prompt('Enter your Naukri key skills or profile details text:', 'Python, FastAPI, PostgreSQL, Docker, AWS, 30 days notice');
                if (text) {
                  try {
                    const res = await api.syncNaukri({ userId: formData.userId, syncMethod: 'TEXT', profileText: text });
                    setFormData(res.updatedProfile);
                    onUpdate(res.updatedProfile);
                    alert('Naukri profile synced successfully!');
                  } catch (e: any) {
                    alert('Sync failed: ' + e.message);
                  }
                }
              }}
              className="px-2.5 py-1 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-[11px] transition cursor-pointer"
            >
              Sync
            </button>
          </div>
        </div>

        {/* Gemini Direct Document Ingestion */}
        <div className="my-4 p-4 rounded-xl bg-gradient-to-r from-emerald-950/30 to-sky-950/30 border border-emerald-500/30 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-emerald-300 flex items-center gap-1.5">
              <Sparkles className="w-4 h-4 text-emerald-400" />
              Direct Resume Ingestion (Gemini Multimodal API)
            </span>
            {uploadSuccess && (
              <span className="text-xs text-emerald-400 flex items-center gap-1 font-bold">
                <Check className="w-3.5 h-3.5" /> Enriched!
              </span>
            )}
          </div>
          <p className="text-xs text-slate-400">
            Upload your latest resume PDF / DOCX to refresh your skills, experience, and profile details via Gemini.
          </p>
          <div className="pt-1">
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.doc,.txt"
              onChange={handleFileUpload}
              className="hidden"
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploadingResume}
              className="w-full py-2.5 px-4 rounded-xl border border-emerald-500/40 bg-emerald-950/40 hover:bg-emerald-900/40 text-emerald-300 text-xs font-bold transition flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {isUploadingResume ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Ingesting Document into Gemini Multimodal API...</span>
                </>
              ) : (
                <>
                  <UploadCloud className="w-4 h-4" />
                  <span>Upload & Ingest Resume Document (PDF / DOCX)</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Master Form */}
        <form onSubmit={handleSave} className="space-y-4 text-xs">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-slate-400 font-medium block mb-1">Full Name</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-white focus:border-emerald-500 outline-none"
              />
            </div>
            <div>
              <label className="text-slate-400 font-medium block mb-1">Email</label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-white focus:border-emerald-500 outline-none"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="text-slate-400 font-medium block mb-1">Phone Number</label>
              <input
                type="text"
                value={formData.phone || ''}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-white focus:border-emerald-500 outline-none"
              />
            </div>
            <div>
              <label className="text-slate-400 font-medium block mb-1">Current Location</label>
              <input
                type="text"
                value={formData.location || ''}
                onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-white focus:border-emerald-500 outline-none"
              />
            </div>
            <div>
              <label className="text-slate-400 font-medium block mb-1">Experience (Years)</label>
              <input
                type="number"
                step="0.5"
                value={formData.experienceYears || 0}
                onChange={(e) => setFormData({ ...formData, experienceYears: parseFloat(e.target.value) || 0 })}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-white focus:border-emerald-500 outline-none"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-slate-400 font-medium block mb-1">Recommended Target Position (AI Target)</label>
              <input
                type="text"
                value={formData.recommendedPosition || ''}
                onChange={(e) => setFormData({ ...formData, recommendedPosition: e.target.value })}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-white focus:border-emerald-500 outline-none"
                placeholder="e.g. Senior Software Engineer"
              />
            </div>
            <div>
              <label className="text-slate-400 font-medium block mb-1">Recommended Domain (AI Target)</label>
              <input
                type="text"
                value={formData.recommendedDomain || ''}
                onChange={(e) => setFormData({ ...formData, recommendedDomain: e.target.value })}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-white focus:border-emerald-500 outline-none"
                placeholder="e.g. FinTech, SaaS, E-commerce"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="text-slate-400 font-medium block mb-1">Current CTC (LPA)</label>
              <input
                type="number"
                step="0.5"
                value={formData.currentCtcLpa || 0}
                onChange={(e) => setFormData({ ...formData, currentCtcLpa: parseFloat(e.target.value) || 0 })}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-white focus:border-emerald-500 outline-none"
              />
            </div>
            <div>
              <label className="text-slate-400 font-medium block mb-1">Expected CTC (LPA)</label>
              <input
                type="number"
                step="0.5"
                value={formData.expectedCtcLpa || 0}
                onChange={(e) => setFormData({ ...formData, expectedCtcLpa: parseFloat(e.target.value) || 0 })}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-white focus:border-emerald-500 outline-none"
              />
            </div>
            <div>
              <label className="text-slate-400 font-medium block mb-1">Notice Period (Days)</label>
              <input
                type="number"
                value={formData.noticePeriodDays || 0}
                onChange={(e) => setFormData({ ...formData, noticePeriodDays: parseInt(e.target.value) || 0 })}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-white focus:border-emerald-500 outline-none"
              />
            </div>
          </div>

          <div>
            <label className="text-slate-400 font-medium block mb-1">Primary Tech Stack (Comma separated)</label>
            <input
              type="text"
              value={(() => {
                if (Array.isArray(formData.skills)) return formData.skills.join(', ');
                if (typeof formData.skills === 'object' && formData.skills !== null) {
                  return [
                    ...(formData.skills.primarySkills || []),
                    ...(formData.skills.secondarySkills || []),
                    ...(formData.skills.domainExpertise || []),
                  ].join(', ');
                }
                return String(formData.skills || '');
              })()}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  skills: e.target.value.split(',').map((s) => s.trim()).filter(Boolean),
                })
              }
              className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-white focus:border-emerald-500 outline-none"
            />
          </div>

          <div>
            <label className="text-slate-400 font-medium block mb-1">Auto-Apply Match Threshold (%)</label>
            <div className="flex items-center gap-3">
              <input
                type="range"
                min="60"
                max="95"
                step="5"
                value={formData.autoApplyThreshold || 80}
                onChange={(e) => setFormData({ ...formData, autoApplyThreshold: parseFloat(e.target.value) })}
                className="flex-1 h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-emerald-500"
              />
              <span className="font-mono font-bold text-emerald-400">{formData.autoApplyThreshold || 80}%</span>
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl border border-slate-700 text-slate-300 hover:bg-slate-800 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSaving}
              className="px-6 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold flex items-center gap-2 transition"
            >
              <Save className="w-4 h-4" />
              {isSaving ? 'Saving...' : 'Save Persona'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
