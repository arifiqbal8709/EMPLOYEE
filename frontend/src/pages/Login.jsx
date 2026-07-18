import React, { useState } from 'react';
import { ShieldAlert, Lock, User, AlertCircle, Loader } from 'lucide-react';
import { api } from '../utils/api';

export default function Login({ onLoginSuccess }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username || !password) {
      setError('Please fill in all inputs fields.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await api.auth.login(username, password);
      onLoginSuccess();
    } catch (err) {
      setError(err.message || 'Login failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-[#030407]">
      <div className="glass-card w-full max-w-md p-8 border border-white/5 shadow-2xl relative overflow-hidden">
        {/* Neon light flare */}
        <div className="absolute -top-12 -left-12 h-36 w-36 bg-indigo-500/10 rounded-full blur-[40px] pointer-events-none" />
        <div className="absolute -bottom-12 -right-12 h-36 w-36 bg-purple-500/10 rounded-full blur-[40px] pointer-events-none" />

        {/* Head Branding Header */}
        <div className="flex flex-col items-center mb-8 relative">
          <div className="bg-indigo-600/15 text-indigo-400 p-4 rounded-2xl border border-indigo-500/20 shadow-xl shadow-indigo-600/5 mb-4 mb-3">
            <ShieldAlert size={28} className="animate-pulse" />
          </div>
          <h2 className="text-white text-xl font-bold tracking-tight">AI FOCUS PORTAL</h2>
          <p className="text-xs text-zinc-400 mt-1">Authenticate to monitor performance</p>
        </div>

        {/* Error notifications */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-xs px-4 py-3 rounded-xl flex items-center gap-2 mb-6 animate-shake">
            <AlertCircle size={14} className="shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-zinc-400 text-xs font-semibold uppercase tracking-wider mb-2">Username</label>
            <div className="relative">
              <span className="absolute left-4 top-3.5 text-zinc-500">
                <User size={16} />
              </span>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-white/5 border border-white/5 rounded-xl py-3 pl-12 pr-4 text-white text-sm focus:outline-none focus:border-indigo-500/50 transition-all duration-200"
                placeholder="Enter Username"
                disabled={loading}
              />
            </div>
          </div>

          <div>
            <label className="block text-zinc-400 text-xs font-semibold uppercase tracking-wider mb-2">Password</label>
            <div className="relative">
              <span className="absolute left-4 top-3.5 text-zinc-500">
                <Lock size={16} />
              </span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-white/5 border border-white/5 rounded-xl py-3 pl-12 pr-4 text-white text-sm focus:outline-none focus:border-indigo-500/50 transition-all duration-200"
                placeholder="Enter Password"
                disabled={loading}
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-3 rounded-xl transition-all duration-200 active:scale-[0.98] shadow-lg shadow-indigo-600/35 border border-indigo-500/30 flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader size={16} className="animate-spin" />
                <span>Authenticating...</span>
              </>
            ) : (
              <span>Authorize Login</span>
            )}
          </button>
        </form>

        <div className="mt-8 text-center border-t border-white/5 pt-4 text-[10px] text-zinc-500 tracking-wider">
          SECURED VIA SHA-256 JWT ENCRYPTION
        </div>
      </div>
    </div>
  );
}
