"use client";

import { useEffect, useState, useCallback } from "react";

interface Site {
  id: number;
  name: string;
  url: string;
  status: string;
  last_crawled_at: string | null;
}

export default function SitesPage() {
  const [sites, setSites] = useState<Site[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [progress, setProgress] = useState<Record<number, number>>({});
  const [error, setError] = useState("");

  const fetchSites = useCallback(async () => {
    try {
      const token = localStorage.getItem("access_token");
      if (!token) return;
      const res = await fetch("/api/v1/sites", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setSites(data);
        data.forEach((s: Site) => {
          if (s.status === "running") {
            pollProgress(s.id);
          }
        });
      }
    } catch (e) {
      console.error("fetchSites error:", e);
    }
  }, []);

  const pollProgress = async (siteId: number) => {
    const token = localStorage.getItem("access_token");
    if (!token) return;
    try {
      const res = await fetch(`/api/v1/sites/${siteId}/progress`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setProgress((prev) => ({ ...prev, [siteId]: data.progress }));
        if (data.progress < 100) {
          setTimeout(() => pollProgress(siteId), 2000);
        } else {
          setTimeout(() => fetchSites(), 1000);
        }
      }
    } catch {}
  };

  useEffect(() => {
    fetchSites();
  }, [fetchSites]);

  const addSite = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const token = localStorage.getItem("access_token");
      if (!token) return;
      const res = await fetch("/api/v1/sites", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ name, url }),
      });
      if (res.ok) {
        setName("");
        setUrl("");
        setShowForm(false);
        fetchSites();
      }
    } catch (e) {
      console.error("addSite error:", e);
    }
  };

  const deleteSite = async (siteId: number) => {
    try {
      const token = localStorage.getItem("access_token");
      if (!token) return;
      const res = await fetch(`/api/v1/sites/${siteId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setError("");
        fetchSites();
      } else {
        const data = await res.json().catch(() => ({}));
        setError(data.detail || "Delete failed");
      }
    } catch (e) {
      console.error("deleteSite error:", e);
    }
  };

  const statusBadge = (site: Site) => {
    const prog = progress[site.id];
    if (site.status === "running" || (site.status === "pending" && prog !== undefined)) {
      return (
        <div className="flex items-center gap-2">
          <div className="w-20 bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all"
              style={{ width: `${prog || 0}%` }}
            />
          </div>
          <span className="text-xs text-gray-500">{prog || 0}%</span>
        </div>
      );
    }
    const colors: Record<string, string> = {
      active: "bg-green-100 text-green-700",
      running: "bg-blue-100 text-blue-700",
      pending: "bg-yellow-100 text-yellow-700",
      failed: "bg-red-100 text-red-700",
    };
    return (
      <span className={`text-sm px-2 py-1 rounded ${colors[site.status] || "bg-gray-100"}`}>
        {site.status}
      </span>
    );
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Websites</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700"
        >
          Add Website
        </button>
      </div>

      {error && (
        <div className="bg-red-50 text-red-600 p-3 rounded mb-4 text-sm">{error}</div>
      )}

      {showForm && (
        <form onSubmit={addSite} className="bg-white p-4 rounded-lg shadow mb-6 space-y-3">
          <input
            type="text"
            placeholder="Site Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full border rounded px-3 py-2"
            required
          />
          <input
            type="url"
            placeholder="https://example.com"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="w-full border rounded px-3 py-2"
            required
          />
          <button type="submit" className="bg-primary-600 text-white px-4 py-2 rounded">
            Add Site
          </button>
        </form>
      )}

      <div className="bg-white rounded-lg shadow">
        {sites.length === 0 ? (
          <p className="p-6 text-muted-foreground">No websites added yet.</p>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b">
                <th className="text-left p-3">Name</th>
                <th className="text-left p-3">URL</th>
                <th className="text-left p-3">Status</th>
                <th className="text-left p-3">Last Crawled</th>
                <th className="text-left p-3"></th>
              </tr>
            </thead>
            <tbody>
              {sites.map((site) => (
                <tr key={site.id} className="border-b">
                  <td className="p-3">{site.name}</td>
                  <td className="p-3 text-sm text-muted-foreground">{site.url}</td>
                  <td className="p-3">{statusBadge(site)}</td>
                  <td className="p-3 text-sm text-muted-foreground">
                    {site.last_crawled_at || "Never"}
                  </td>
                  <td className="p-3">
                    <button
                      onClick={() => deleteSite(site.id)}
                      className="text-red-600 hover:text-red-800 text-sm"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
