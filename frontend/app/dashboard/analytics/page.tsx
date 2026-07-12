"use client";

import { useEffect, useState } from "react";

export default function AnalyticsPage() {
  const [stats, setStats] = useState({ total_sessions: 0, total_messages: 0 });

  useEffect(() => {
    const fetchAnalytics = async () => {
      const token = localStorage.getItem("access_token");
      const res = await fetch("/api/v1/analytics/usage", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setStats(await res.json());
      }
    };
    fetchAnalytics();
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Analytics</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-sm text-muted-foreground">Chat Sessions</h3>
          <p className="text-3xl font-bold mt-2">{stats.total_sessions}</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-sm text-muted-foreground">Messages</h3>
          <p className="text-3xl font-bold mt-2">{stats.total_messages}</p>
        </div>
      </div>
    </div>
  );
}
