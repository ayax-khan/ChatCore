"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [authenticated, setAuthenticated] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      window.location.href = "/auth/login";
    } else {
      setAuthenticated(true);
    }
  }, []);

  if (!authenticated) {
    return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50 flex">
      <aside className="w-64 bg-white border-r min-h-screen flex flex-col">
        <div className="p-4 border-b">
          <div className="text-xl font-bold text-primary-700">ChatCore</div>
          <div className="text-xs text-gray-500 mt-1">Admin Dashboard</div>
        </div>
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          <a href="/dashboard" className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-gray-100 text-sm font-medium transition-colors">
            <span>Dashboard</span>
          </a>
          <a href="/dashboard/sites" className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-gray-100 text-sm font-medium transition-colors">
            <span>Websites</span>
          </a>
          <a href="/dashboard/chat" className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-gray-100 text-sm font-medium transition-colors">
            <span>Chat</span>
          </a>
          <a href="/dashboard/chat-sessions" className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-gray-100 text-sm font-medium transition-colors">
            <span>History</span>
          </a>
          <a href="/dashboard/analytics" className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-gray-100 text-sm font-medium transition-colors">
            <span>Analytics</span>
          </a>
          <a href="/dashboard/users" className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-gray-100 text-sm font-medium transition-colors">
            <span>Team</span>
          </a>
          <a href="/dashboard/billing" className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-gray-100 text-sm font-medium transition-colors">
            <span>Billing</span>
          </a>
          <a href="/dashboard/settings" className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-gray-100 text-sm font-medium transition-colors">
            <span>Settings</span>
          </a>
        </nav>
        <div className="p-4 border-t">
          <button
            onClick={() => { localStorage.removeItem("access_token"); window.location.href = "/auth/login"; }}
            className="w-full text-left px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg"
          >
            Sign Out
          </button>
        </div>
      </aside>
      <main className="flex-1 p-8 overflow-y-auto">{children}</main>
    </div>
  );
}
