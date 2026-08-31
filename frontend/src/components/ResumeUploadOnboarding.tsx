'use client';

import React, { useState, useRef } from 'react';
import {
  UploadCloud,
  FileText,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  ShieldCheck,
  Zap,
  RefreshCw
} from 'lucide-react';
import { api, UserProfile } from '../lib/api';

interface Props {
  user: UserProfile;
  onUploaded: (updatedUser: UserProfile) => void;
  onSkip?: () => void;
}

export function ResumeUploadOnboarding({ user, onUploaded, onSkip }: Props) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      validateAndSetFile(file);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      validateAndSetFile(file);
    }
  };

  const validateAndSetFile = (file: File) => {
    setErrorMessage('');
    const validExtensions = ['.pdf', '.docx', '.doc', '.txt'];
    const hasValidExt = validExtensions.some((ext) => file.name.toLowerCase().endsWith(ext));
    if (!hasValidExt) {
      setErrorMessage('Please upload a valid PDF or DOCX document.');
      return;
    }
    if (file.size > 15 * 1024 * 1024) {
      setErrorMessage('File size exceeds 15MB limit.');
      return;
    }
    setSelectedFile(file);
  };

  const handleUploadAndIngest = async () => {
    if (!selectedFile) return;
    setIsUploading(true);
    setErrorMessage('');
    try {
      const res = await api.uploadResumeDocument(selectedFile, user?.userId);
      if (res.user) {
        onUploaded(res.user);
      }
    } catch (err: any) {
      console.error('Ingestion error:', err);
      setErrorMessage(err.message || 'Failed to ingest document with Gemini. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="min-h-[85vh] flex items-center justify-center p-4">
      <div className="w-full max-w-2xl glass-panel rounded-3xl border border-slate-800 p-8 sm:p-10 shadow-2xl space-y-7 animate-fadeIn text-slate-100">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 mb-1">
            <UploadCloud className="w-6 h-6" />
          </div>
          <h2 className="text-2xl font-black text-white">Upload Your Resume Document</h2>
          <p className="text-xs text-slate-400 max-w-md mx-auto leading-relaxed">
            Gemini 3.7 directly ingests your PDF/DOCX document to extract your tech stack, career achievements, and compute ATS semantic match scores.
          </p>
        </div>

        {/* Drag & Drop Zone */}
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragOver(true);
          }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={handleFileDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`relative border-2 border-dashed rounded-3xl p-8 sm:p-12 text-center cursor-pointer transition-all duration-200 ${
            isDragOver
              ? 'border-emerald-400 bg-emerald-950/30 shadow-lg shadow-emerald-500/10 scale-[1.01]'
              : selectedFile
              ? 'border-emerald-500/60 bg-slate-900/80'
              : 'border-slate-700/80 bg-slate-900/40 hover:border-slate-600 hover:bg-slate-900/60'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.doc,.txt"
            onChange={handleFileChange}
            className="hidden"
          />

          {!selectedFile ? (
            <div className="space-y-3 flex flex-col items-center">
              <div className="w-14 h-14 rounded-2xl bg-slate-800/80 border border-slate-700 flex items-center justify-center text-slate-300">
                <FileText className="w-7 h-7 text-emerald-400" />
              </div>
              <div>
                <p className="text-sm font-bold text-white">
                  Drop your resume PDF here, or <span className="text-emerald-400 underline">browse files</span>
                </p>
                <p className="text-[11px] text-slate-500 mt-1">Supports PDF, DOCX up to 15MB</p>
              </div>
            </div>
          ) : (
            <div className="space-y-2 flex flex-col items-center">
              <div className="w-14 h-14 rounded-2xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400">
                <CheckCircle2 className="w-7 h-7" />
              </div>
              <div>
                <p className="text-sm font-bold text-white">{selectedFile.name}</p>
                <p className="text-[11px] text-emerald-400 font-mono mt-0.5">
                  {(selectedFile.size / 1024).toFixed(1)} KB • Ready for Gemini Ingestion
                </p>
              </div>
              <span className="text-[11px] text-slate-400 hover:underline pt-1">Click to change file</span>
            </div>
          )}
        </div>

        {/* Error Alert */}
        {errorMessage && (
          <div className="p-3 rounded-xl bg-rose-950/30 border border-rose-500/40 text-rose-300 text-xs flex items-center gap-2 animate-fadeIn">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Actions */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
          {onSkip ? (
            <button
              type="button"
              onClick={onSkip}
              className="text-xs text-slate-400 hover:text-slate-200 transition"
            >
              Skip to Dashboard
            </button>
          ) : <div />}

          <button
            type="button"
            onClick={handleUploadAndIngest}
            disabled={!selectedFile || isUploading}
            className="w-full sm:w-auto px-8 py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-slate-950 font-bold text-xs flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/20 transition transform active:scale-95 disabled:opacity-50"
          >
            {isUploading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Ingesting into Gemini Multimodal API...</span>
              </>
            ) : (
              <>
                <span>Ingest & Unlock Matched Jobs</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
