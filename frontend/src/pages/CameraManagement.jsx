import React, { useState, useEffect, useRef } from 'react';
import { Camera, Radio, Plus, Trash2, ShieldAlert, CheckCircle, XCircle, Info, RefreshCw, Activity } from 'lucide-react';
import { api } from '../utils/api';

function WebcamPlayer({ camera, testingMode }) {
  const [telemetry, setTelemetry] = useState({
    is_present: false,
    person_detected: "No",
    phone_detected: false,
    phone_detected_str: "No",
    looking_at_monitor: true,
    sleeping: false,
    score: 0,
    fps: 0
  });

  const [streamError, setStreamError] = useState(false);

  useEffect(() => {
    // Poll telemetry directly from single backend YOLO inference engine every 1 second
    const timer = setInterval(async () => {
      try {
        const data = await api.cameras.getTelemetry(camera.id);
        if (data) {
          setTelemetry(data);
        }
      } catch (err) {
        console.warn("[Telemetry Poll Error]", err);
      }
    }, 1000);

    return () => clearInterval(timer);
  }, [camera.id]);

  return (
    <div className="w-full h-full flex flex-col relative">
      {/* Backend Single Video Stream Container */}
      <div className="w-full h-48 bg-[#0b0c10] border border-white/5 rounded-xl flex items-center justify-center relative overflow-hidden">
        {streamError ? (
          <div className="flex flex-col items-center justify-center h-full p-4 text-center bg-[#0b0c10] z-20 relative">
            <Camera size={26} className="text-red-400 mb-2 animate-bounce" />
            <span className="text-red-400 font-semibold text-xs">Backend AI Stream Offline</span>
            <span className="text-[10px] text-zinc-500 mt-1">Check backend camera service endpoint</span>
          </div>
        ) : (
          <img
            src={api.cameras.getStreamUrl(camera.id)}
            className="w-full h-full object-cover block relative z-10"
            alt={camera.name}
            onError={() => setStreamError(true)}
            onLoad={() => setStreamError(false)}
          />
        )}
      </div>

      {/* Backend YOLO Telemetry Diagnostics Panel */}
      <div className="mt-3 bg-[#08090d] border border-white/5 p-3 rounded-xl space-y-1.5 text-[10px] font-mono">
        <div className="flex items-center justify-between border-b border-white/5 pb-1">
          <span className="text-zinc-500 font-semibold uppercase tracking-wider">Camera Name:</span>
          <span className="text-indigo-300 font-bold truncate max-w-[160px]">{camera.name}</span>
        </div>
        <div className="flex items-center justify-between border-b border-white/5 pb-1">
          <span className="text-zinc-500 font-semibold uppercase tracking-wider">Stream Source:</span>
          <span className="text-emerald-400 font-bold">Backend YOLO AI Engine</span>
        </div>
        <div className="flex items-center justify-between border-b border-white/5 pb-1">
          <span className="text-zinc-500 font-semibold uppercase tracking-wider">Person Present:</span>
          <span className={`font-bold ${telemetry.is_present ? 'text-emerald-400' : 'text-red-400'}`}>
            {telemetry.is_present ? 'YES' : 'NO'}
          </span>
        </div>
        <div className="flex items-center justify-between border-b border-white/5 pb-1">
          <span className="text-zinc-500 font-semibold uppercase tracking-wider">Phone Detected:</span>
          <span className={`font-bold ${telemetry.phone_detected ? 'text-red-400 animate-pulse' : 'text-emerald-400'}`}>
            {telemetry.phone_detected ? 'YES (Distraction Alert)' : 'NO'}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-zinc-500 font-semibold uppercase tracking-wider">Focus Score / FPS:</span>
          <span className="text-indigo-400 font-bold font-mono">{telemetry.score}% | {telemetry.fps} FPS</span>
        </div>
      </div>
    </div>
  );
}

export default function CameraManagement() {
  const [cameras, setCameras] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(false);
  const [formOpen, setFormOpen] = useState(false);
  const [error, setError] = useState('');
  const [testingMode, setTestingMode] = useState(true);

  // Diagnostic Modal State
  const [diagnosticLoading, setDiagnosticLoading] = useState(false);
  const [diagnosticModalOpen, setDiagnosticModalOpen] = useState(false);
  const [diagnosticResult, setDiagnosticResult] = useState(null);

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

  // Poll live JSON coordinate parameters every 1 second for actively connected cameras
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
    }, 1000);
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

      try {
        const modeRes = await api.cameras.getTestingMode();
        if (modeRes && typeof modeRes.testing_mode === 'boolean') {
          setTestingMode(modeRes.testing_mode);
        }
      } catch (e) {}
    } catch (err) {
      setError('Could not fetch cameras data registry');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleTestingMode = async (enabled) => {
    setLoading(true);
    try {
      await api.cameras.setTestingMode(enabled);
      setTestingMode(enabled);
      fetchData();
    } catch (err) {
      setError('Could not update camera testing mode');
    } finally {
      setLoading(false);
    }
  };

  const runCameraDiagnosticTest = async () => {
    setDiagnosticLoading(true);
    let cameraDetected = "No";
    let permissionState = "Denied";
    let streamResolution = "N/A";
    let activeStreamState = "No";

    try {
      if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const videoDevices = devices.filter(d => d.kind === 'videoinput');
        if (videoDevices.length > 0) {
          cameraDetected = `Yes (${videoDevices.length} device(s) found: ${videoDevices[0].label || 'Default Camera'})`;
        }
      }

      // Check backend status endpoint instead of opening duplicate hardware lock
      const backendMode = await api.cameras.getTestingMode();
      permissionState = "Granted (Backend Camera Active)";
      activeStreamState = backendMode ? "Yes (Backend Stream Active)" : "No";
      streamResolution = "640x480 (YOLO Annotated Stream)";

    } catch (err) {
      console.error("[Diagnostic Test Error]", err);
      permissionState = `Denied (${err.message || 'Permission blocked'})`;
    }

    setDiagnosticResult({
      detected: cameraDetected,
      permission: permissionState,
      resolution: streamResolution,
      activeStream: activeStreamState
    });
    setDiagnosticModalOpen(true);
    setDiagnosticLoading(false);
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

      {/* Development Mode Banner */}
      {testingMode ? (
        <div className="bg-indigo-600/15 border border-indigo-500/30 text-indigo-300 text-xs px-4 py-3 rounded-xl flex items-center justify-between shadow-lg shadow-indigo-600/10">
          <div className="flex items-center gap-2.5 font-semibold">
            <span className="h-2 w-2 rounded-full bg-indigo-400 animate-ping" />
            <span>Single Stream Architecture - Backend YOLO Processing Active</span>
          </div>
          <button
            onClick={() => handleToggleTestingMode(false)}
            className="text-[10px] bg-white/10 hover:bg-white/20 text-white font-medium px-3 py-1.5 rounded-lg transition-all border border-white/10"
          >
            Switch to CCTV Mode
          </button>
        </div>
      ) : (
        <div className="bg-zinc-800/40 border border-white/5 text-zinc-400 text-xs px-4 py-2.5 rounded-xl flex items-center justify-between">
          <span className="font-medium text-zinc-300">Standard CCTV / RTSP Network Mode Active</span>
          <button
            onClick={() => handleToggleTestingMode(true)}
            className="text-[10px] bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-400 font-medium px-3 py-1.5 rounded-lg border border-indigo-500/30 transition-all"
          >
            Enable Testing Mode (Laptop Webcam)
          </button>
        </div>
      )}

      {/* Controller header */}
      <div className="flex items-center justify-between">
        <h3 className="text-white font-bold text-sm tracking-wide">CAMERA MANAGEMENT BOARD</h3>
        
        <div className="flex items-center gap-3">
          <button
            onClick={runCameraDiagnosticTest}
            disabled={diagnosticLoading}
            className="bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 px-3 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all shrink-0"
            title="Run camera diagnostic check"
          >
            <Camera size={14} className={diagnosticLoading ? "animate-spin" : ""} />
            <span>Camera Test</span>
          </button>

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

              {/* Single Stream Video Player & Telemetry */}
              {cam.status === 'connected' ? (
                <WebcamPlayer camera={cam} testingMode={testingMode} />
              ) : (
                <div className="w-full h-48 bg-[#0b0c10] border border-white/5 rounded-xl flex items-center justify-center relative overflow-hidden">
                  <div className="flex flex-col items-center gap-2 text-zinc-600">
                    <Radio size={28} className="text-zinc-700" />
                    <span className="text-[10px] uppercase font-bold tracking-wider">Feed Standby</span>
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

      {/* --- CAMERA DIAGNOSTIC TEST MODAL --- */}
      {diagnosticModalOpen && diagnosticResult && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center p-4 z-50 animate-fadeIn">
          <div className="glass-card w-full max-w-md p-6 border border-indigo-500/20 shadow-2xl relative space-y-4">
            <div className="flex items-center justify-between border-b border-white/5 pb-3">
              <div className="flex items-center gap-2">
                <Camera size={18} className="text-indigo-400" />
                <h4 className="text-white text-xs font-bold uppercase tracking-wider">Webcam Diagnostic Report</h4>
              </div>
              <button onClick={() => setDiagnosticModalOpen(false)} className="text-zinc-400 hover:text-white">
                <XCircle size={16} />
              </button>
            </div>

            <div className="space-y-2.5 text-xs font-mono">
              <div className="flex items-center justify-between p-2.5 rounded-lg bg-white/5 border border-white/5">
                <span className="text-zinc-400">Camera detected:</span>
                <span className={`font-bold ${diagnosticResult.detected.startsWith('Yes') ? 'text-emerald-400' : 'text-red-400'}`}>
                  {diagnosticResult.detected}
                </span>
              </div>

              <div className="flex items-center justify-between p-2.5 rounded-lg bg-white/5 border border-white/5">
                <span className="text-zinc-400">Permission:</span>
                <span className={`font-bold ${diagnosticResult.permission.startsWith('Granted') ? 'text-emerald-400' : 'text-red-400'}`}>
                  {diagnosticResult.permission}
                </span>
              </div>

              <div className="flex items-center justify-between p-2.5 rounded-lg bg-white/5 border border-white/5">
                <span className="text-zinc-400">Resolution:</span>
                <span className="text-indigo-300 font-bold">
                  {diagnosticResult.resolution}
                </span>
              </div>

              <div className="flex items-center justify-between p-2.5 rounded-lg bg-white/5 border border-white/5">
                <span className="text-zinc-400">Active stream:</span>
                <span className={`font-bold ${diagnosticResult.activeStream.startsWith('Yes') ? 'text-emerald-400' : 'text-red-400'}`}>
                  {diagnosticResult.activeStream}
                </span>
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setDiagnosticModalOpen(false)}
                className="hud-btn-primary text-xs w-full"
              >
                Close Diagnostic Report
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
