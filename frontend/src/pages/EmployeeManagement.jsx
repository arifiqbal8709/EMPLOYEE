import React, { useState, useEffect } from 'react';
import { Search, UserPlus, Edit, Trash2, X, PlusCircle, AlertCircle, RefreshCw } from 'lucide-react';
import { api } from '../utils/api';

export default function EmployeeManagement() {
  const role = localStorage.getItem("role") || "employee";
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Filter conditions
  const [nameFilter, setNameFilter] = useState('');
  const [idFilter, setIdFilter] = useState('');
  const [deptFilter, setDeptFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  // Modal control triggers
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);

  // Form parameters
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [employeeId, setEmployeeId] = useState('');
  const [department, setDepartment] = useState('');
  const [cameraId, setCameraId] = useState('0');
  const [userStatus, setUserStatus] = useState('absent');

  useEffect(() => {
    fetchEmployees();
  }, [nameFilter, idFilter, deptFilter, statusFilter]);

  const fetchEmployees = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.employees.list({
        username: nameFilter,
        employee_id: idFilter,
        department: deptFilter,
        status: statusFilter
      });
      setEmployees(data);
    } catch (err) {
      setError(err.message || 'Error fetching employees list');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenAdd = () => {
    setError('');
    setUsername('');
    setPassword('');
    setEmployeeId('');
    setDepartment('');
    setCameraId('0');
    setUserStatus('absent');
    setAddModalOpen(true);
  };

  const handleOpenEdit = (emp) => {
    setError('');
    setSelectedUser(emp);
    setUsername(emp.username);
    setPassword(''); // Leave password empty unless updating
    setEmployeeId(emp.employee_id || '');
    setDepartment(emp.department || '');
    setCameraId(emp.camera_id || '0');
    setUserStatus(emp.status || 'absent');
    setEditModalOpen(true);
  };

  // Dispatch POST Create
  const handleCreate = async (e) => {
    e.preventDefault();
    setError('');
    if (!username || !password) {
      setError('Username and Password are required.');
      return;
    }
    setLoading(true);
    try {
      await api.employees.create({
        username: username.trim(),
        password,
        employee_id: employeeId.trim() || null,
        department: department.trim() || null,
        camera_id: cameraId.trim() || '0',
        status: userStatus
      });
      setAddModalOpen(false);
      fetchEmployees();
    } catch (err) {
      setError(err.message || 'Could not create employee profile');
    } finally {
      setLoading(false);
    }
  };

  // Dispatch PUT Update
  const handleUpdate = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await api.employees.update(selectedUser.id, {
        username: username.trim(),
        password: password ? password : null,
        employee_id: employeeId.trim() || null,
        department: department.trim() || null,
        camera_id: cameraId.trim() || '0',
        status: userStatus
      });
      setEditModalOpen(false);
      fetchEmployees();
    } catch (err) {
      setError(err.message || 'Could not update employee details');
    } finally {
      setLoading(false);
    }
  };

  // Dispatch DELETE
  const handleDelete = async (id) => {
    if (!window.confirm("Are you sure you want to delete this employee?")) return;
    setLoading(true);
    try {
      await api.employees.delete(id);
      fetchEmployees();
    } catch (err) {
      setError(err.message || 'Could not delete employee');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Notifications Warn */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-xs px-4 py-3 rounded-xl flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle size={15} />
            <span>{error}</span>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={fetchEmployees}
              className="bg-red-500/20 hover:bg-red-500/30 text-white px-3 py-1 rounded-lg flex items-center gap-1 font-medium transition-all"
            >
              <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
              <span>Retry</span>
            </button>
            <button onClick={() => setError('')}><X size={14} /></button>
          </div>
        </div>
      )}

      {/* Grid Filters Control Bar */}
      <div className="glass-card p-6 flex flex-wrap items-center gap-4 border-white/5 justify-between">
        <div className="flex flex-wrap items-center gap-3 flex-1">
          {/* Name Filter */}
          <div className="relative">
            <Search size={14} className="absolute left-3.5 top-3.5 text-zinc-500" />
            <input
              type="text"
              value={nameFilter}
              onChange={(e) => setNameFilter(e.target.value)}
              className="bg-white/5 border border-white/5 rounded-xl pl-10 pr-4 py-2.5 text-xs text-white placeholder-white/30 focus:outline-none focus:border-indigo-500/40 w-44"
              placeholder="Search Name..."
            />
          </div>

          {/* ID Filter */}
          <input
            type="text"
            value={idFilter}
            onChange={(e) => setIdFilter(e.target.value)}
            className="bg-white/5 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-white placeholder-white/30 focus:outline-none focus:border-indigo-500/40 w-36"
            placeholder="Search Employee ID..."
          />

          {/* Department Filter */}
          <input
            type="text"
            value={deptFilter}
            onChange={(e) => setDeptFilter(e.target.value)}
            className="bg-white/5 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-white placeholder-white/30 focus:outline-none focus:border-indigo-500/40 w-40"
            placeholder="Search Department..."
          />

          {/* Status Filter Selector */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-white/5 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-zinc-400 focus:outline-none focus:border-indigo-500/40 focus:text-white"
          >
            <option value="">All Statuses</option>
            <option value="active">Active</option>
            <option value="idle">Idle</option>
            <option value="absent">Absent</option>
          </select>

          <button onClick={fetchEmployees} className="bg-white/5 hover:bg-white/10 border border-white/10 p-2.5 rounded-xl text-zinc-400 hover:text-white transition-all">
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
        </div>

        {/* Add Employee Action */}
        <button
          onClick={handleOpenAdd}
          className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-xs px-4 py-3 rounded-xl active:scale-[0.98] transition-all flex items-center gap-2 shadow-lg shadow-indigo-600/15 border border-indigo-500/30 shrink-0"
        >
          <UserPlus size={14} />
          <span>Add Employee</span>
        </button>
      </div>

      {/* Directory Table */}
      <div className="glass-card border-white/5 overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-white/5 border-b border-white/5 text-[10px] text-zinc-400 font-bold uppercase tracking-wider">
              <th className="px-6 py-4">Employee ID</th>
              <th className="px-6 py-4">Name</th>
              <th className="px-6 py-4">Department</th>
              <th className="px-6 py-4 text-center">Camera Link ID</th>
              <th className="px-6 py-4">Current Status</th>
              <th className="px-6 py-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 text-xs">
            {employees.length === 0 ? (
              <tr>
                <td colSpan="6" className="text-center py-10 text-zinc-500 font-medium">
                  {loading ? 'Initializing search...' : 'No employees matching filter criteria found.'}
                </td>
              </tr>
            ) : (
              employees.map((emp) => (
                <tr key={emp.id} className="hover:bg-white/[0.01] transition-all">
                  <td className="px-6 py-4 font-mono text-zinc-400">{emp.employee_id || 'N/A'}</td>
                  <td className="px-6 py-4 font-semibold text-white">{emp.username}</td>
                  <td className="px-6 py-4 text-zinc-300">{emp.department || 'N/A'}</td>
                  <td className="px-6 py-4 text-center font-semibold text-indigo-400 font-mono">CAM-{emp.camera_id || '0'}</td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                      emp.status === 'active' 
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/10' 
                        : emp.status === 'idle'
                        ? 'bg-amber-500/10 text-amber-400 border border-amber-500/10'
                        : 'bg-red-500/10 text-red-400 border border-red-500/10'
                    }`}>
                      <span className={`h-1.5 w-1.5 rounded-full ${
                        emp.status === 'active' ? 'bg-emerald-400' : emp.status === 'idle' ? 'bg-amber-400' : 'bg-red-400'
                      }`} />
                      {emp.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right space-x-1.5">
                    <button
                      onClick={() => handleOpenEdit(emp)}
                      className="bg-white/5 hover:bg-white/10 text-white p-2 rounded-lg border border-white/10 transition-all inline-flex"
                      title="Edit Profile"
                    >
                      <Edit size={13} />
                    </button>
                    {role === 'admin' && (
                      <button
                        onClick={() => handleDelete(emp.id)}
                        className="bg-red-500/10 hover:bg-red-500/20 text-red-400 p-2 rounded-lg border border-red-500/15 transition-all inline-flex"
                        title="Delete Profile"
                      >
                        <Trash2 size={13} />
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* --- ADD MODAL DIALOG --- */}
      {addModalOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-card w-full max-w-lg p-6 border-white/5 animate-scaleUp">
            <div className="flex items-center justify-between border-b border-white/5 pb-4 mb-5">
              <h3 className="text-white text-base font-bold flex items-center gap-2">
                <PlusCircle size={18} className="text-indigo-400" />
                <span>Add New Employee Profile</span>
              </h3>
              <button onClick={() => setAddModalOpen(false)} className="text-zinc-500 hover:text-white transition-all">
                <X size={18} />
              </button>
            </div>
            
            {error && (
              <div className="mb-4 bg-red-500/10 border border-red-500/20 text-red-400 text-xs px-4 py-3 rounded-xl flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <AlertCircle size={15} />
                  <span>{error}</span>
                </div>
                <button type="button" onClick={() => setError('')}><X size={14} /></button>
              </div>
            )}
            
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-zinc-400 text-[10px] font-bold uppercase tracking-wider mb-2">Username</label>
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="w-full bg-white/5 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-500/40"
                    placeholder="e.g. johndoe"
                    required
                  />
                </div>
                <div>
                  <label className="block text-zinc-400 text-[10px] font-bold uppercase tracking-wider mb-2">Password</label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full bg-white/5 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-500/40"
                    placeholder="Enter raw password"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-zinc-400 text-[10px] font-bold uppercase tracking-wider mb-2">Employee ID</label>
                  <input
                    type="text"
                    value={employeeId}
                    onChange={(e) => setEmployeeId(e.target.value)}
                    className="w-full bg-white/5 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-500/40 font-mono"
                    placeholder="e.g. EMP-105"
                  />
                </div>
                <div>
                  <label className="block text-zinc-400 text-[10px] font-bold uppercase tracking-wider mb-2">Department</label>
                  <input
                    type="text"
                    value={department}
                    onChange={(e) => setDepartment(e.target.value)}
                    className="w-full bg-white/5 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-500/40"
                    placeholder="e.g. Backend Dev"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-zinc-400 text-[10px] font-bold uppercase tracking-wider mb-2">Camera Link ID</label>
                  <input
                    type="text"
                    value={cameraId}
                    onChange={(e) => setCameraId(e.target.value)}
                    className="w-full bg-white/5 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-500/40 font-mono"
                    placeholder="e.g. 0 or 1"
                  />
                </div>
                <div>
                  <label className="block text-zinc-400 text-[10px] font-bold uppercase tracking-wider mb-2">Initial Status</label>
                  <select
                    value={userStatus}
                    onChange={(e) => setUserStatus(e.target.value)}
                    className="w-full bg-white/5 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-zinc-300 focus:outline-none focus:border-indigo-500/40"
                  >
                    <option value="absent">Absent</option>
                    <option value="active">Active</option>
                    <option value="idle">Idle</option>
                  </select>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-white/5 mt-5">
                <button type="button" onClick={() => setAddModalOpen(false)} className="hud-btn-secondary text-xs">Cancel</button>
                <button type="submit" disabled={loading} className="hud-btn-primary text-xs shrink-0">
                  {loading ? 'Creating...' : 'Register Employee'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* --- EDIT MODAL DIALOG --- */}
      {editModalOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-card w-full max-w-lg p-6 border-white/5 animate-scaleUp">
            <div className="flex items-center justify-between border-b border-white/5 pb-4 mb-5">
              <h3 className="text-white text-base font-bold flex items-center gap-2">
                <Edit size={18} className="text-indigo-400" />
                <span>Modify Employee Details</span>
              </h3>
              <button onClick={() => setEditModalOpen(false)} className="text-zinc-500 hover:text-white transition-all">
                <X size={18} />
              </button>
            </div>
            
            {error && (
              <div className="mb-4 bg-red-500/10 border border-red-500/20 text-red-400 text-xs px-4 py-3 rounded-xl flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <AlertCircle size={15} />
                  <span>{error}</span>
                </div>
                <button type="button" onClick={() => setError('')}><X size={14} /></button>
              </div>
            )}
            
            <form onSubmit={handleUpdate} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-zinc-400 text-[10px] font-bold uppercase tracking-wider mb-2">Username</label>
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="w-full bg-white/5 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-500/40"
                    required
                  />
                </div>
                <div>
                  <label className="block text-zinc-400 text-[10px] font-bold uppercase tracking-wider mb-2">Password (Leave blank to keep current)</label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full bg-white/5 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-500/40"
                    placeholder="Enter new password"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-zinc-400 text-[10px] font-bold uppercase tracking-wider mb-2">Employee ID</label>
                  <input
                    type="text"
                    value={employeeId}
                    onChange={(e) => setEmployeeId(e.target.value)}
                    className="w-full bg-white/5 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-500/40 font-mono"
                  />
                </div>
                <div>
                  <label className="block text-zinc-400 text-[10px] font-bold uppercase tracking-wider mb-2">Department</label>
                  <input
                    type="text"
                    value={department}
                    onChange={(e) => setDepartment(e.target.value)}
                    className="w-full bg-white/5 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-500/40"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-zinc-400 text-[10px] font-bold uppercase tracking-wider mb-2">Camera Link ID</label>
                  <input
                    type="text"
                    value={cameraId}
                    onChange={(e) => setCameraId(e.target.value)}
                    className="w-full bg-white/5 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-500/40 font-mono"
                  />
                </div>
                <div>
                  <label className="block text-zinc-400 text-[10px] font-bold uppercase tracking-wider mb-2">Current Status</label>
                  <select
                    value={userStatus}
                    onChange={(e) => setUserStatus(e.target.value)}
                    className="w-full bg-white/5 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-zinc-300 focus:outline-none focus:border-indigo-500/40"
                  >
                    <option value="absent">Absent</option>
                    <option value="active">Active</option>
                    <option value="idle">Idle</option>
                  </select>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-white/5 mt-5">
                <button type="button" onClick={() => setEditModalOpen(false)} className="hud-btn-secondary text-xs">Cancel</button>
                <button type="submit" disabled={loading} className="hud-btn-primary text-xs shrink-0">
                  {loading ? 'Submitting...' : 'Save Adjustments'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
