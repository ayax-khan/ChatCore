"use client";

import { useEffect, useState } from "react";

interface UsageData {
  total_sessions: number;
  total_messages: number;
  active_users_today: number;
  total_sites: number;
  total_chunks: number;
}

export default function ChatSessionsPage() {
  const [usage, setUsage] = useState<UsageData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchUsage = async () => {
      const token = localStorage.getItem("access_token");
      if (!token) return;
      try {
        const res = await fetch("/api/v1/analytics/usage", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setUsage(data);
        } else if (res.status === 403) {
          setError("You need admin or owner role to view analytics.");
        } else {
          setError("Failed to load analytics data.");
        }
      } catch {
        setError("Failed to connect to server.");
      }
    };
    fetchUsage();
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Chat Sessions</h1>

      {error && (
        <div className="bg-red-50 text-red-600 p-4 rounded-lg text-sm mb-6">{error}</div>
      )}

      {usage && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-2xl font-bold text-primary-600">{usage.total_sessions}</div>
            <div className="text-xs text-gray-500 mt-1">Total Sessions</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-2xl font-bold text-primary-600">{usage.total_messages}</div>
            <div className="text-xs text-gray-500 mt-1">Messages</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-2xl font-bold text-primary-600">{usage.active_users_today}</div>
            <div className="text-xs text-gray-500 mt-1">Active Today</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-2xl font-bold text-primary-600">{usage.total_sites}</div>
            <div className="text-xs text-gray-500 mt-1">Sites</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-2xl font-bold text-primary-600">{usage.total_chunks}</div>
            <div className="text-xs text-gray-500 mt-1">Indexed Chunks</div>
          </div>
        </div>
      )}

      {!usage && !error && (
        <div className="bg-white rounded-lg shadow p-6 text-center text-gray-400 text-sm">
          Loading analytics...
        </div>
      )}
    </div>
  );
}
