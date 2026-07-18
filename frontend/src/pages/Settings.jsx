import React, { useState, useEffect } from 'react';
import { Settings, Bell, CircleSlash, Eye, Mail, Lock, ShieldCheck, MailCheck, BellPlus } from 'lucide-react';
import { api } from '../utils/api';

export default function SettingsPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Sliders parameters
  const [attentionThreshold, setAttentionThreshold] = useState(25);
  const [drowsinessThreshold, setDrowsinessThreshold] = useState(2.0);
  const [confidenceThreshold, setConfidenceThreshold] = useState(40);

  // Notification Options
  const [desktopEnabled, setDesktopEnabled] = useState(true);
  const [emailEnabled, setEmailEnabled] = useState(true);
  const [emailRecipient, setEmailRecipient] = useState('');
  const [fcmEnabled, setFcmEnabled] = useState(false);
  const [fcmToken, setFcmToken] = useState('');

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    setLoading(true);
    try {
      const data = await api.notifications.getSettings();
      setDesktopEnabled(data.desktop_enabled);
      setEmailEnabled(data.email_enabled);
      setEmailRecipient(data.email_recipient || '');
      setFcmEnabled(data.fcm_enabled);
      setFcmToken(data.fcm_token || '');
    } catch (err) {
      setError('Could not retrieve settings details');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');
    try {
      await api.notifications.updateSettings({
        desktop_enabled: desktopEnabled,
        email_enabled: emailEnabled,
        email_recipient: emailRecipient || null,
        fcm_enabled: fcmEnabled,
        fcm_token: fcmToken || null
      });
      setSuccess('Settings adjustments saved successfully.');
      
      // Save local sliders mock state
      localStorage.setItem("attention_th", attentionThreshold);
      localStorage.setItem("drowsiness_th", drowsinessThreshold);
      localStorage.setItem("confidence_th", confidenceThreshold);
      
    } catch (err) {
      setError('Error saving settings configurations.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Messages flags */}
      {success && (
        <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs px-4 py-3 rounded-xl flex items-center gap-2">
          <ShieldCheck size={16} />
          <span>{success}</span>
        </div>
      )}
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-xs px-4 py-3 rounded-xl flex items-center gap-2">
          <CircleSlash size={16} />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-6">
        {/* --- SECTION 1: AI VISION PARAMETERS --- */}
        <div className="glass-card p-6 border-white/5 space-y-5">
          <h4 className="text-white text-xs font-bold uppercase tracking-wider flex items-center gap-2 border-b border-white/5 pb-3">
            <Eye size={16} className="text-indigo-400" />
            <span>AI Tracker Detection Guardrails</span>
          </h4>
          
          <div className="space-y-4">
            {/* Attention Yaw limit */}
            <div>
              <div className="flex justify-between text-xs mb-2">
                <span className="text-zinc-400 font-medium">Gaze Attention Angular Limit (Degrees)</span>
                <span className="font-semibold text-indigo-400">{attentionThreshold}°</span>
              </div>
              <input
                type="range"
                min="10"
                max="45"
                value={attentionThreshold}
                onChange={(e) => setAttentionThreshold(parseInt(e.target.value))}
                className="w-full h-1 bg-white/5 rounded-lg appearance-none cursor-pointer accent-indigo-500"
              />
              <p className="text-[10px] text-zinc-500 mt-1">Yaw/Pitch offset limits (MediaPipe estimated) before flagging "Looking Away".</p>
            </div>

            {/* Drowsiness seconds limit */}
            <div>
              <div className="flex justify-between text-xs mb-2">
                <span className="text-zinc-400 font-medium">Closed Eyes Drowsiness Trigger (Seconds)</span>
                <span className="font-semibold text-indigo-400">{drowsinessThreshold}s</span>
              </div>
              <input
                type="range"
                min="1"
                max="5"
                step="0.5"
                value={drowsinessThreshold}
                onChange={(e) => setDrowsinessThreshold(parseFloat(e.target.value))}
                className="w-full h-1 bg-white/5 rounded-lg appearance-none cursor-pointer accent-indigo-500"
              />
              <p className="text-[10px] text-zinc-500 mt-1">Eye closed duration (EAR threshold) before triggering "Sleeping" alerts.</p>
            </div>

            {/* Phone Confidence ratio limit */}
            <div>
              <div className="flex justify-between text-xs mb-2">
                <span className="text-zinc-400 font-medium">YOLOv11 Inference Confidence (%)</span>
                <span className="font-semibold text-indigo-400">{confidenceThreshold}%</span>
              </div>
              <input
                type="range"
                min="25"
                max="80"
                value={confidenceThreshold}
                onChange={(e) => setConfidenceThreshold(parseInt(e.target.value))}
                className="w-full h-1 bg-white/5 rounded-lg appearance-none cursor-pointer accent-indigo-500"
              />
              <p className="text-[10px] text-zinc-500 mt-1">Minimum object classification confidence value mapping target bounds boxes.</p>
            </div>
          </div>
        </div>

        {/* --- SECTION 2: NOTIFICATIONS POLICIES --- */}
        <div className="glass-card p-6 border-white/5 space-y-6">
          <h4 className="text-white text-xs font-bold uppercase tracking-wider flex items-center gap-2 border-b border-white/5 pb-3">
            <Bell size={16} className="text-indigo-400" />
            <span>Alerts Rules Notification Preferences</span>
          </h4>

          <div className="space-y-6">
            {/* Desktop Notifications Toggle */}
            <div className="flex items-start justify-between">
              <div>
                <h5 className="text-white text-xs font-semibold">HTML5 Desktop Alerts</h5>
                <p className="text-[10px] text-zinc-500 mt-0.5">Show real-time alert notifications directly on browser dashboard workspace.</p>
              </div>
              <button
                type="button"
                onClick={() => setDesktopEnabled(prev => !prev)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-all duration-300 ${
                  desktopEnabled ? 'bg-indigo-600' : 'bg-white/10'
                }`}
              >
                <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-all duration-300 ${
                  desktopEnabled ? 'translate-x-6' : 'translate-x-1'
                }`} />
              </button>
            </div>

            {/* Email warning toggle */}
            <div className="flex flex-col gap-3 pt-4 border-t border-white/5">
              <div className="flex items-start justify-between">
                <div>
                  <h5 className="text-white text-xs font-semibold">SMTP Email Forwarder</h5>
                  <p className="text-[10px] text-zinc-500 mt-0.5">Dispatch notification warnings to SMTP mailboxes during idle transitions.</p>
                </div>
                <button
                  type="button"
                  onClick={() => setEmailEnabled(prev => !prev)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-all duration-300 ${
                    emailEnabled ? 'bg-indigo-600' : 'bg-white/10'
                  }`}
                >
                  <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-all duration-300 ${
                    emailEnabled ? 'translate-x-6' : 'translate-x-1'
                  }`} />
                </button>
              </div>
              
              {emailEnabled && (
                <div className="animate-slideDown relative">
                  <span className="absolute left-4 top-3.5 text-zinc-500">
                    <MailCheck size={14} />
                  </span>
                  <input
                    type="email"
                    value={emailRecipient}
                    onChange={(e) => setEmailRecipient(e.target.value)}
                    className="w-full bg-[#0d0e12] border border-white/5 rounded-xl py-3 pl-12 pr-4 text-xs text-white placeholder-white/20 focus:outline-none focus:border-indigo-500/40"
                    placeholder="Enter recipient email (e.g. manager@firm.com)"
                    required={emailEnabled}
                  />
                </div>
              )}
            </div>

            {/* Firebase token push toggle */}
            <div className="flex flex-col gap-3 pt-4 border-t border-white/5">
              <div className="flex items-start justify-between">
                <div>
                  <h5 className="text-white text-xs font-semibold">Firebase Push Notifications (FCM)</h5>
                  <p className="text-[10px] text-zinc-500 mt-0.5">Push alert events payloads straight to connected Android/iOS device configurations.</p>
                </div>
                <button
                  type="button"
                  onClick={() => setFcmEnabled(prev => !prev)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-all duration-300 ${
                    fcmEnabled ? 'bg-indigo-600' : 'bg-white/10'
                  }`}
                >
                  <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-all duration-300 ${
                    fcmEnabled ? 'translate-x-6' : 'translate-x-1'
                  }`} />
                </button>
              </div>

              {fcmEnabled && (
                <div className="animate-slideDown relative col-span-2">
                  <span className="absolute left-4 top-3.5 text-zinc-500">
                    <BellPlus size={14} />
                  </span>
                  <input
                    type="text"
                    value={fcmToken}
                    onChange={(e) => setFcmToken(e.target.value)}
                    className="w-full bg-[#0d0e12] border border-white/5 rounded-xl py-3 pl-12 pr-4 text-xs text-white placeholder-white/20 focus:outline-none focus:border-indigo-500/40 font-mono"
                    placeholder="Enter FCM registration token"
                    required={fcmEnabled}
                  />
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Form buttons */}
        <div className="flex justify-end gap-3 pt-2">
          <button type="button" onClick={fetchSettings} className="hud-btn-secondary text-xs">Reset Changes</button>
          <button type="submit" disabled={loading} className="hud-btn-primary text-xs shrink-0">
            {loading ? 'Processing...' : 'Save Settings'}
          </button>
        </div>
      </form>
    </div>
  );
}
