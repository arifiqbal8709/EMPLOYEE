import React from 'react';
import { Wifi, Calendar } from 'lucide-react';

export default function Navbar({ title }) {
  const today = new Date().toLocaleDateString(undefined, { 
    weekday: 'short', 
    year: 'numeric', 
    month: 'short', 
    day: 'numeric' 
  });

  return (
    <header className="h-20 bg-dark-bg/40 backdrop-blur-md border-b border-white/5 flex items-center justify-between px-8 fixed top-0 right-0 left-64 z-10">
      {/* Dynamic View Header */}
      <div>
        <h2 className="text-white text-lg font-bold tracking-tight">{title}</h2>
      </div>

      {/* Network and date status pills */}
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2 text-zinc-400 bg-white/5 py-1.5 px-3.5 border border-white/5 rounded-full text-xs">
          <Calendar size={13} className="text-zinc-500" />
          <span>{today}</span>
        </div>

        <div className="flex items-center gap-2 bg-emerald-500/10 text-emerald-400 py-1.5 px-3.5 border border-emerald-500/20 rounded-full text-xs font-semibold shadow-lg shadow-emerald-500/5">
          <Wifi size={13} className="animate-pulse" />
          <span>SYSTEM ACTIVE</span>
        </div>
      </div>
    </header>
  );
}
