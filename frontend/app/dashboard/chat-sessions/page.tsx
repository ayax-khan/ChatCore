"use client";

import { useEffect, useState } from "react";

interface Session {
  id: number;
  session_id: string;
  started_at: string;
  message_count: number;
}

export default function ChatSessionsPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  useEffect(() => {
    const fetchSessions = async () => {
      const token = localStorage.getItem("access_token");
      const res = await fetch("/api/v1/analytics/usage", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setSessions([
          { id: 1, session_id: "session-1", started_at: new Date().toISOString(), message_count: data.total_messages || 0 },
        ]);
      }
    };
    fetchSessions();
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Chat Sessions</h1>
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left p-3 text-sm font-medium text-gray-500">Session ID</th>
              <th className="text-left p-3 text-sm font-medium text-gray-500">Messages</th>
              <th className="text-left p-3 text-sm font-medium text-gray-500">Started</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((s) => (
              <tr key={s.id} className="border-t hover:bg-gray-50 cursor-pointer" onClick={() => setExpandedId(expandedId === s.id ? null : s.id)}>
                <td className="p-3 text-sm font-mono">{s.session_id}</td>
                <td className="p-3 text-sm">{s.message_count}</td>
                <td className="p-3 text-sm text-gray-500">{new Date(s.started_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
