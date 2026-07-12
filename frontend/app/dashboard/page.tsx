"use client";

import { useEffect, useState } from "react";

export default function DashboardPage() {
  const [stats, setStats] = useState({ total_sessions: 0, total_messages: 0 });

  useEffect(() => {
    const fetchStats = async () => {
      const token = localStorage.getItem("access_token");
      try {
        const res = await fetch("/api/v1/analytics/usage", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setStats(data);
        }
      } catch {
        console.error("Failed to fetch stats");
      }
    };
    fetchStats();
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-sm text-muted-foreground">Total Sessions</h3>
          <p className="text-3xl font-bold mt-2">{stats.total_sessions}</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-sm text-muted-foreground">Total Messages</h3>
          <p className="text-3xl font-bold mt-2">{stats.total_messages}</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-sm text-muted-foreground">Status</h3>
          <p className="text-3xl font-bold mt-2 text-green-600">Active</p>
        </div>
      </div>
    </div>
  );
}
