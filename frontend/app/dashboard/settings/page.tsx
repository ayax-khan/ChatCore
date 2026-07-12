"use client";

export default function SettingsPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Settings</h1>
      <div className="bg-white p-6 rounded-lg shadow space-y-4">
        <div>
          <h3 className="font-medium mb-2">Widget Configuration</h3>
          <p className="text-sm text-muted-foreground mb-4">
            Add this script to your website to enable the chat widget.
          </p>
          <pre className="bg-gray-100 p-3 rounded text-sm overflow-x-auto">
            {`<script src="https://cdn.chatcore.dev/widget.js" data-site-id="YOUR_SITE_ID" async></script>`}
          </pre>
        </div>
      </div>
    </div>
  );
}
