"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";

export default function KnowledgeBasePage() {
  const [sites, setSites] = useState<any[]>([]);
  const [selectedSite, setSelectedSite] = useState<number | null>(null);
  const [chunks, setChunks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/api/v1/sites/")
      .then((res) => setSites(res.data || []))
      .catch(() => setSites([]))
      .finally(() => setLoading(false));
  }, []);

  const viewChunks = async (siteId: number) => {
    setSelectedSite(siteId);
    try {
      const res = await api.get(`/api/v1/sites/${siteId}`);
      setChunks(res.data?.chunks || []);
    } catch {
      setChunks([]);
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Knowledge Base</h1>
      {loading ? (
        <p>Loading...</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="md:col-span-1">
            <h2 className="text-lg font-semibold mb-3">Sites</h2>
            <div className="space-y-2">
              {sites.map((site: any) => (
                <button
                  key={site.id}
                  onClick={() => viewChunks(site.id)}
                  className={`w-full text-left px-4 py-2 rounded ${
                    selectedSite === site.id ? "bg-blue-100 text-blue-800" : "bg-gray-50 hover:bg-gray-100"
                  }`}
                >
                  <div className="font-medium">{site.name}</div>
                  <div className="text-sm text-gray-500">{site.url}</div>
                  <div className="text-xs mt-1">
                    <span className={`px-2 py-0.5 rounded ${
                      site.status === "indexed" ? "bg-green-100 text-green-800" :
                      site.status === "crawling" ? "bg-yellow-100 text-yellow-800" :
                      "bg-gray-100 text-gray-800"
                    }`}>{site.status}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>
          <div className="md:col-span-2">
            {selectedSite ? (
              <>
                <h2 className="text-lg font-semibold mb-3">Indexed Chunks</h2>
                {chunks.length === 0 ? (
                  <p className="text-gray-500">No chunks indexed yet.</p>
                ) : (
                  <div className="space-y-3">
                    {chunks.map((chunk: any) => (
                      <div key={chunk.id} className="p-4 bg-gray-50 rounded border">
                        <p className="text-sm text-gray-500 mb-1">Order: {chunk.chunk_order}</p>
                        <p className="text-sm">{chunk.content?.substring(0, 300)}...</p>
                      </div>
                    ))}
                  </div>
                )}
            </div>
          ) : (
            <div className="md:col-span-2">
              <p className="text-gray-500">Select a site to view indexed content.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
