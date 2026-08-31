import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Job Intelligence Engine — AI-Powered Job Matching for India',
  description: 'AI-native job intelligence, AmbitionBox & Glassdoor compensation synthesis, and autonomous job application with Human-in-the-Loop verification for India\'s tech market.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet" />
      </head>
      <body className="antialiased selection:bg-emerald-500 selection:text-slate-950">
        {children}
      </body>
    </html>
  );
}
