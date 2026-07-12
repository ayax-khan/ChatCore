"use client";

import { useEffect, useState } from "react";

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

  const fetchSites = async () => {
    const token = localStorage.getItem("access_token");
    const res = await fetch("/api/v1/sites/", {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) {
      setSites(await res.json());
    }
  };

  useEffect(() => {
    fetchSites();
  }, []);

  const addSite = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = localStorage.getItem("access_token");
    const res = await fetch("/api/v1/sites/", {
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
              </tr>
            </thead>
            <tbody>
              {sites.map((site) => (
                <tr key={site.id} className="border-b">
                  <td className="p-3">{site.name}</td>
                  <td className="p-3 text-sm text-muted-foreground">{site.url}</td>
                  <td className="p-3">
                    <span className="text-sm px-2 py-1 rounded bg-green-100 text-green-700">
                      {site.status}
                    </span>
                  </td>
                  <td className="p-3 text-sm text-muted-foreground">
                    {site.last_crawled_at || "Never"}
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
