"use client";

import { useEffect, useState } from "react";

interface Site {
  id: number;
  name: string;
  url: string;
}

export default function SettingsPage() {
  const [sites, setSites] = useState<Site[]>([]);
  const [selectedSiteId, setSelectedSiteId] = useState<number | null>(null);

  useEffect(() => {
    const fetchSites = async () => {
      const token = localStorage.getItem("access_token");
      if (!token) return;
      try {
        const res = await fetch("/api/v1/sites", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) setSites(await res.json());
      } catch {}
    };
    fetchSites();
  }, []);

  const baseUrl = typeof window !== "undefined" ? window.location.origin : "http://localhost:3000";

  const popupCode = selectedSiteId
    ? `<script>
(function() {
  var btn = document.createElement('button');
  btn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>';
  btn.style.cssText = 'position:fixed;bottom:20px;right:20px;width:56px;height:56px;border-radius:50%;background:#3b82f6;color:white;border:none;cursor:pointer;box-shadow:0 4px 12px rgba(0,0,0,0.25);z-index:999999;display:flex;align-items:center;justify-content:center;transition:transform 0.2s';
  btn.onmouseover = function(){ this.style.transform = 'scale(1.1)' };
  btn.onmouseout = function(){ this.style.transform = 'scale(1)' };
  btn.onclick = function(){
    var w = Math.min(420, window.innerWidth - 40);
    var h = Math.min(640, window.innerHeight - 40);
    var left = Math.max(0, (window.innerWidth - w) / 2);
    var top = Math.max(0, (window.innerHeight - h) / 2);
    window.open('${baseUrl}/widget/${selectedSiteId}', 'chatcore', 'width='+w+',height='+h+',left='+left+',top='+top+',resizable=yes');
  };
  document.body.appendChild(btn);
})();
</script>`
    : "Select a site first.";

  const iframeCode = selectedSiteId
    ? `<iframe src="${baseUrl}/widget/${selectedSiteId}" style="position:fixed;bottom:20px;right:20px;width:400px;height:600px;border:none;border-radius:12px;box-shadow:0 8px 32px rgba(0,0,0,0.2);z-index:999999;" title="ChatCore"></iframe>`
    : "Select a site first.";

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Settings</h1>

      <div className="bg-white p-6 rounded-lg shadow space-y-6">
        <div>
          <h3 className="font-medium mb-1">Select Website</h3>
          <p className="text-sm text-gray-500 mb-3">Choose which site's chatbot to embed on your website.</p>
          <select
            value={selectedSiteId || ""}
            onChange={(e) => setSelectedSiteId(e.target.value ? Number(e.target.value) : null)}
            className="border rounded px-3 py-2 text-sm w-full max-w-xs"
          >
            <option value="">Select a site...</option>
            {sites.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        </div>

        {selectedSiteId && (
          <>
            <div>
              <h3 className="font-medium mb-1">Option 1: Popup Button</h3>
              <p className="text-sm text-gray-500 mb-2">Adds a floating chat button to your site that opens the chat in a popup.</p>
              <pre className="bg-gray-100 p-3 rounded text-sm overflow-x-auto whitespace-pre-wrap">{popupCode}</pre>
              <button
                onClick={() => navigator.clipboard.writeText(popupCode)}
                className="mt-2 text-sm text-primary-600 hover:underline"
              >
                Copy to clipboard
              </button>
            </div>

            <div>
              <h3 className="font-medium mb-1">Option 2: Iframe Embed</h3>
              <p className="text-sm text-gray-500 mb-2">Embeds the chat directly on your page (fixed position).</p>
              <pre className="bg-gray-100 p-3 rounded text-sm overflow-x-auto">{iframeCode}</pre>
              <button
                onClick={() => navigator.clipboard.writeText(iframeCode)}
                className="mt-2 text-sm text-primary-600 hover:underline"
              >
                Copy to clipboard
              </button>
            </div>

            <div className="bg-blue-50 border border-blue-200 p-4 rounded text-sm text-blue-800">
              <strong>Note:</strong> Jab production deploy karein ge to <code className="bg-blue-100 px-1 rounded">{baseUrl}</code> ki jagah apna actual domain ayega.
            </div>
          </>
        )}
      </div>
    </div>
  );
}
