import React from 'react';
import { LayoutDashboard, Users, Camera, Settings, LogOut, ShieldAlert } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Sidebar({ currentView, setView, onLogout }) {
  const { user, logout } = useAuth();
  const role = user?.role || localStorage.getItem("role") || "employee";
  const username = user?.username || localStorage.getItem("username") || "User";

  const handleLogoutClick = () => {
    logout();
    if (onLogout) {
      onLogout();
    }
  };

  const navItems = [
    { id: 'dashboard', name: 'Dashboard', icon: LayoutDashboard, roles: ['admin', 'manager', 'employee'] },
    { id: 'employees', name: 'Employee Directory', icon: Users, roles: ['admin', 'manager', 'employee'] },
    { id: 'cameras', name: 'Camera Monitoring', icon: Camera, roles: ['admin', 'manager', 'employee'] },
    { id: 'settings', name: 'Settings', icon: Settings, roles: ['admin', 'manager', 'employee'] },
  ];

  return (
    <aside className="w-64 glass-card h-screen fixed left-0 top-0 flex flex-col p-6 m-0 rounded-none border-r border-y-0 border-l-0 border-white/5 z-20">
      {/* HUD App Header */}
      <div className="flex items-center gap-3 mb-10">
        <div className="bg-indigo-600/20 text-indigo-400 p-2.5 rounded-xl border border-indigo-500/20 shadow-lg shadow-indigo-500/10">
          <ShieldAlert size={22} className="animate-pulse" />
        </div>
        <div>
          <h1 className="text-white font-bold text-base leading-tight">AI PRO-MONITOR</h1>
          <p className="text-[10px] text-zinc-400 uppercase tracking-widest">Secure Sentinel</p>
        </div>
      </div>

      {/* Navigation Options list */}
      <nav className="flex-1 space-y-2">
        {navItems.map((item) => {
          if (!item.roles.includes(role)) return null;
          const Icon = item.icon;
          const isActive = currentView === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setView(item.id)}
              className={`w-full flex items-center gap-3.5 px-4 py-3.5 rounded-xl text-sm font-medium transition-all duration-200 ${
                isActive
                  ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20 border border-indigo-500/30'
                  : 'text-zinc-400 hover:text-white hover:bg-white/5 border border-transparent'
              }`}
            >
              <Icon size={18} />
              <span>{item.name}</span>
            </button>
          );
        })}
      </nav>

      {/* User Session profile Info Box */}
      <div className="pt-4 border-t border-white/5 mt-auto flex flex-col gap-4">
        <div className="flex items-center gap-3 pl-1">
          <div className="h-9 w-9 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-500 flex items-center justify-center font-bold text-white text-sm shadow-md">
            {username.substring(0, 2).toUpperCase()}
          </div>
          <div>
            <h4 className="text-white text-xs font-semibold">{username}</h4>
            <p className="text-[10px] text-indigo-400 font-medium uppercase tracking-wider">{role}</p>
          </div>
        </div>

        <button
          onClick={handleLogoutClick}
          className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-red-400 hover:text-red-300 hover:bg-red-500/10 transition-all duration-200 border border-transparent hover:border-red-500/20"
        >
          <LogOut size={18} />
          <span>Logout</span>
        </button>
      </div>
    </aside>
  );
}
