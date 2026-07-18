import React, { useState, useEffect } from 'react';
import { Camera, Radio, Plus, Trash2, ShieldAlert, CheckCircle, XCircle, Info, RefreshCw } from 'lucide-react';
import { api } from '../utils/api';

export default function CameraManagement() {
  const [cameras, setCameras] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(false);
  const [formOpen, setFormOpen] = useState(false);
  const [error, setError] = useState('');

  // Form parameters
  const [name, setName] = useState('');
  const [type, setType] = useState('usb');
  const [source, setSource] = useState('0');
  const [userId, setUserId] = useState('');

  // Telemetries tracking
  const [telemetry, setTelemetry] = useState({});

  useEffect(() => {
    fetchData();
  }, []);

  // Poll live JSON coordinate parameters every 1.5 seconds for actively connected cameras
  useEffect(() => {
    const timer = setInterval(() => {
      cameras.forEach((cam) => {
        if (cam.status === 'connected') {
          api.cameras.getTelemetry(cam.id)
            .then((data) => {
              setTelemetry((prev) => ({
                ...prev,
                [cam.id]: data
              }));
            })
            .catch(() => {});
        }
      });
    }, 1500);
    return () => clearInterval(timer);
  }, [cameras]);

  const fetchData = async () => {
    setLoading(true);
    setError('');
    try {
      const camData = await api.cameras.list();
      setCameras(camData);
      
      // Load employees list to bind camera mapping option
      const empData = await api.employees.list();
      setEmployees(empData);
    } catch (err) {
      setError('Could not fetch cameras data registry');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!name || !source) {
      setError('Name and Source are required.');
      return;
    }
    setLoading(true);
    try {
      await api.cameras.create({
        name,
        type,
        source,
        user_id: userId ? parseInt(userId) : null
      });
      setFormOpen(false);
      setName('');
      setSource('0');
      setUserId('');
      fetchData();
    } catch (err) {
      setError(err.message || 'Error saving camera config');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Disconnect and remove this camera configuration?")) return;
    setLoading(true);
    try {
      await api.cameras.delete(id);
      fetchData();
    } catch (err) {
      setError('Error deleting camera configuration');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleConnection = async (cam, action) => {
    setLoading(true);
    try {
      await api.cameras.update(cam.id, {
        status: action === 'connect' ? 'connected' : 'disconnected'
      });
      fetchData();
    } catch (err) {
      setError('Error toggling connection state');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Error Bar */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-xs px-4 py-3 rounded-xl flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldAlert size={15} />
            <span>{error}</span>
          </div>
          <button onClick={() => setError('')}><Trash2 size={14} /></button>
        </div>
      )}

      {/* Controller header */}
      <div className="flex items-center justify-between">
        <h3 className="text-white font-bold text-sm tracking-wide">CAMERA MANAGEMENT BOARD</h3>
        
        <div className="flex items-center gap-3">
          <button onClick={fetchData} className="bg-white/5 hover:bg-white/10 border border-white/10 p-2.5 rounded-xl text-zinc-400 hover:text-white transition-all">
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
          
          <button
            onClick={() => setFormOpen(prev => !prev)}
            className="hud-btn-primary text-xs shrink-0 flex items-center gap-2"
          >
            <Plus size={14} />
            <span>Add Camera</span>
          </button>
        </div>
      </div>

      {/* --- ADD CAMERA SUB-PANEL FORM --- */}
      {formOpen && (
        <div className="glass-card p-6 border-indigo-500/10 animate-slideDown">
          <h4 className="text-white text-xs font-bold uppercase tracking-wider mb-4 border-b border-white/5 pb-2">Configure Camera Endpoint</h4>
          <form onSubmit={handleCreate} className="grid grid-cols-4 gap-4 items-end">
            <div>
              <label className="block text-zinc-400 text-[10px] font-bold uppercase tracking-wider mb-2">Camera Label Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full bg-[#0d0e12] border border-white/5 rounded-xl px-4 py-2.5 text-xs text-white placeholder-white/20 focus:outline-none focus:border-indigo-500/40"
                placeholder="e.g. Workspace Left Cam"
                required
              />
            </div>
            
            <div>
              <label className="block text-zinc-400 text-[10px] font-bold uppercase tracking-wider mb-2">Device Type</label>
              <select
                value={type}
                onChange={(e) => {
                  setType(e.target.value);
                  setSource(e.target.value === 'usb' ? '0' : 'rtsp://');
                }}
                className="w-full bg-[#0d0e12] border border-white/5 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-500/40"
              >
                <option value="usb">USB Camera Index</option>
                <option value="rtsp">IP / RTSP Address</option>
              </select>
            </div>

            <div>
              <label className="block text-zinc-400 text-[10px] font-bold uppercase tracking-wider mb-2">Source Endpoint</label>
              <input
                type="text"
                value={source}
                onChange={(e) => setSource(e.target.value)}
                className="w-full bg-[#0d0e12] border border-white/5 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-500/40 font-mono"
                placeholder="e.g. 0 or rtsp://..."
                required
              />
            </div>

            <div>
              <label className="block text-zinc-400 text-[10px] font-bold uppercase tracking-wider mb-2">Bind Employee</label>
              <select
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                className="w-full bg-[#0d0e12] border border-white/5 rounded-xl px-4 py-2.5 text-xs text-zinc-300 focus:outline-none focus:border-indigo-500/40"
              >
                <option value="">Unassigned</option>
                {employees.map((emp) => (
                  <option key={emp.id} value={emp.id}>{emp.username} ({emp.employee_id})</option>
                ))}
              </select>
            </div>

            <div className="col-span-4 flex justify-end gap-2 border-t border-white/5 pt-4 mt-2">
              <button type="button" onClick={() => setFormOpen(false)} className="hud-btn-secondary text-xs">Disconnect</button>
              <button type="submit" disabled={loading} className="hud-btn-primary text-xs shrink-0">Connect Feed</button>
            </div>
          </form>
        </div>
      )}

      {/* --- CAMERAS MONITOR GRID LIST --- */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {cameras.map((cam) => {
          const camTelemetry = telemetry[cam.id] || {
            is_present: false, looking_at_monitor: false, sleeping: false, phone_detected: false, keyboard_active: false, mouse_active: false, score: 0, fps: 0
          };
          const associatedUser = employees.find(e => e.id === cam.user_id);

          return (
            <div key={cam.id} className="glass-card p-5 border-white/5 flex flex-col gap-4 relative overflow-hidden">
              {/* Badge Overlay */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className={`h-2 w-2 rounded-full ${
                    cam.status === 'connected' ? 'bg-emerald-400 animate-pulse' : cam.status === 'disconnected' ? 'bg-zinc-500' : 'bg-red-500'
                  }`} />
                  <span className="text-white text-xs font-bold">{cam.name}</span>
                </div>
                
                <span className="text-[10px] text-zinc-400 bg-white/5 py-1 px-2.5 border border-white/5 rounded-full font-mono">
                  {cam.type.toUpperCase()}: {cam.source.length > 25 ? `${cam.source.substring(0,25)}...` : cam.source}
                </span>
              </div>

              {/* Feed window container */}
              <div className="w-full h-48 bg-[#0b0c10] border border-white/5 rounded-xl flex items-center justify-center relative overflow-hidden">
                {cam.status === 'connected' ? (
                  <img
                    src={api.cameras.getStreamUrl(cam.id)}
                    className="w-full h-full object-cover"
                    alt={cam.name}
                    onError={(e) => {
                      e.target.style.display = 'none';
                    }}
                  />
                ) : (
                  <div className="flex flex-col items-center gap-2 text-zinc-600">
                    <Radio size={28} className="text-zinc-700" />
                    <span className="text-[10px] uppercase font-bold tracking-wider">Feed Standby</span>
                  </div>
                )}
                
                {/* Linked Employee tag overlay */}
                {associatedUser && (
                  <div className="absolute bottom-3 left-3 bg-black/70 backdrop-blur-md border border-white/5 px-2.5 py-1 rounded-lg text-[10px] text-zinc-300 font-semibold flex items-center gap-1.5 shadow-lg">
                    <span className="shrink-0 bg-indigo-500/20 text-indigo-400 px-1 py-0.5 rounded text-[8px] font-bold">EMP</span>
                    <span>{associatedUser.username}</span>
                  </div>
                )}
                
                {/* Output FPS indicator overlay */}
                {cam.status === 'connected' && (
                  <div className="absolute top-3 right-3 bg-indigo-600/90 text-white font-mono text-[9px] font-bold px-2 py-0.5 rounded border border-indigo-400/20">
                    FPS: {camTelemetry.fps}
                  </div>
                )}
              </div>

              {/* Telemtry HUD details */}
              {cam.status === 'connected' && (
                <div className="bg-white/5 border border-white/5 p-4 rounded-xl grid grid-cols-2 gap-3 text-[10px]">
                  <div className="flex items-center justify-between border-b border-white/5 pb-1.5">
                    <span className="text-zinc-500">Focus Score:</span>
                    <span className={`font-bold font-mono ${
                      camTelemetry.score > 75 ? 'text-emerald-400' : camTelemetry.score > 40 ? 'text-amber-400' : 'text-red-400'
                    }`}>
                      {camTelemetry.score}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between border-b border-white/5 pb-1.5">
                    <span className="text-zinc-500">Employee Present:</span>
                    <span className={`font-bold ${camTelemetry.is_present ? 'text-emerald-400' : 'text-red-400'}`}>
                      {camTelemetry.is_present ? 'YES' : 'NO'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between border-b border-white/5 pb-1.5">
                    <span className="text-zinc-500">Attention Gaze:</span>
                    <span className={`font-bold ${camTelemetry.looking_at_monitor ? 'text-emerald-400' : 'text-amber-400'}`}>
                      {camTelemetry.looking_at_monitor ? 'Looking Monitor' : 'Looking Away'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between border-b border-white/5 pb-1.5">
                    <span className="text-zinc-500">Phone usage:</span>
                    <span className={`font-bold ${camTelemetry.phone_detected ? 'text-red-400 animate-pulse' : 'text-emerald-400'}`}>
                      {camTelemetry.phone_detected ? 'Distraction Alert' : 'None'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between col-span-2">
                    <span className="text-zinc-500">Drowsiness state:</span>
                    <span className={`font-bold ${camTelemetry.sleeping ? 'text-red-400 animate-pulse' : 'text-emerald-400'}`}>
                      {camTelemetry.sleeping ? 'Sleeping Alert' : 'Active'}
                    </span>
                  </div>
                </div>
              )}

              {/* Action Buttons panel */}
              <div className="flex justify-between items-center pt-2 border-t border-white/5">
                <div className="space-x-2">
                  {cam.status === 'connected' ? (
                    <button
                      onClick={() => handleToggleConnection(cam, 'disconnect')}
                      className="bg-zinc-800 hover:bg-zinc-700 text-zinc-300 font-medium text-[10px] px-3.5 py-2 rounded-lg transition-all"
                    >
                      Disconnect Feed
                    </button>
                  ) : (
                    <button
                      onClick={() => handleToggleConnection(cam, 'connect')}
                      className="bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-[10px] px-3.5 py-2 rounded-lg transition-all"
                    >
                      Connect Feed
                    </button>
                  )}
                </div>

                <button
                  onClick={() => handleDelete(cam.id)}
                  className="bg-red-500/10 hover:bg-red-500/20 text-red-400 p-2 rounded-lg border border-red-500/15 transition-all inline-flex"
                  title="Remove Camera config"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            </div>
          );
        })}
        {cameras.length === 0 && (
          <div className="col-span-2 bg-dark-card border border-dark-border p-16 rounded-2xl text-center text-zinc-500">
            <Radio size={36} className="mx-auto text-zinc-700 mb-3" />
            <p className="text-xs font-semibold">No cameras registered on this network yet.</p>
            <p className="text-[10px] text-zinc-600 mt-1">Click Add Camera to connect a local USB webcam or RTSP network link.</p>
          </div>
        )}
      </div>
    </div>
  );
}
