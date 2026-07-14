"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import ReactMarkdown from "react-markdown";

interface Site {
  id: number;
  name: string;
  url: string;
}

interface Message {
  id: string;
  sender: "user" | "ai";
  text: string;
  timestamp: number;
  sources?: { url: string; snippet: string; score: number }[];
  confidence?: number;
}

export default function ChatPage() {
  const [sites, setSites] = useState<Site[]>([]);
  const [selectedSiteId, setSelectedSiteId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([
    { id: "welcome", sender: "ai", text: "Hello! Select a website and ask me anything about its content.", timestamp: Date.now() },
  ]);
  const [input, setInput] = useState("");
  const [isConnected, setIsConnected] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentAnswer, setCurrentAnswer] = useState("");
  const [error, setError] = useState("");
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, currentAnswer, scrollToBottom]);

  useEffect(() => {
    const fetchSites = async () => {
      const token = localStorage.getItem("access_token");
      if (!token) return;
      try {
        const res = await fetch("/api/v1/sites", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setSites(data);
        }
      } catch {}
    };
    fetchSites();
  }, []);

  const connectWebSocket = useCallback((siteId: number) => {
    const token = localStorage.getItem("access_token");
    if (!token) return;

    if (wsRef.current) {
      wsRef.current.close();
    }

    const sessionId = `sess_${Math.random().toString(36).substring(2, 15)}`;
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/api/ws/chat?token=${token}&session_id=${sessionId}&site_id=${siteId}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      setError("");
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      switch (data.type) {
        case "token":
          setCurrentAnswer((prev) => prev + data.content);
          break;
        case "typing":
          setIsTyping(data.content);
          break;
        case "done":
          setMessages((prev) => [
            ...prev,
            {
              id: `ai_${Date.now()}`,
              sender: "ai",
              text: currentAnswer || data.answer || "",
              timestamp: Date.now(),
              sources: data.sources,
              confidence: data.confidence,
            },
          ]);
          setCurrentAnswer("");
          setIsStreaming(false);
          setIsTyping(false);
          break;
        case "error":
          setMessages((prev) => [
            ...prev,
            { id: `err_${Date.now()}`, sender: "ai", text: `Error: ${data.content}`, timestamp: Date.now() },
          ]);
          setIsStreaming(false);
          setIsTyping(false);
          break;
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      if (isStreaming) {
        setMessages((prev) => [
          ...prev,
          { id: `ai_${Date.now()}`, sender: "ai", text: currentAnswer || "Connection lost", timestamp: Date.now() },
        ]);
        setCurrentAnswer("");
        setIsStreaming(false);
        setIsTyping(false);
      }
    };

    ws.onerror = () => {
      setError("WebSocket connection failed. Make sure the backend is running.");
    };
  }, [currentAnswer, isStreaming]);

  const handleSiteChange = (siteId: number) => {
    setSelectedSiteId(siteId);
    setMessages([
      { id: "welcome", sender: "ai", text: `Connected to site. Ask me anything about it!`, timestamp: Date.now() },
    ]);
    setCurrentAnswer("");
    setError("");
    setTimeout(() => connectWebSocket(siteId), 100);
  };

  const sendMessage = (text: string) => {
    if (!text.trim() || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    setMessages((prev) => [
      ...prev,
      { id: `user_${Date.now()}`, sender: "user", text: text.trim(), timestamp: Date.now() },
    ]);
    setInput("");
    setCurrentAnswer("");
    setIsStreaming(true);
    setIsTyping(true);

    wsRef.current.send(JSON.stringify({ type: "message", content: text.trim() }));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-4">
      <div className="w-72 bg-white rounded-lg shadow p-4 flex flex-col">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Websites</h2>
        {sites.length === 0 ? (
          <p className="text-sm text-gray-400">No websites found. Add one first.</p>
        ) : (
          <div className="space-y-1 flex-1 overflow-y-auto">
            {sites.map((site) => (
              <button
                key={site.id}
                onClick={() => handleSiteChange(site.id)}
                className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-colors ${
                  selectedSiteId === site.id
                    ? "bg-primary-50 text-primary-700 font-medium border border-primary-200"
                    : "hover:bg-gray-100 text-gray-700"
                }`}
              >
                <div className="font-medium truncate">{site.name}</div>
                <div className="text-xs text-gray-400 truncate mt-0.5">{site.url}</div>
              </button>
            ))}
          </div>
        )}
        <div className="mt-3 pt-3 border-t text-xs text-gray-400">
          {isConnected ? (
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 bg-green-500 rounded-full" />
              Connected
            </span>
          ) : (
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 bg-gray-300 rounded-full" />
              {selectedSiteId ? "Disconnected" : "Select a site"}
            </span>
          )}
        </div>
      </div>

      <div className="flex-1 bg-white rounded-lg shadow flex flex-col">
        {!selectedSiteId ? (
          <div className="flex-1 flex items-center justify-center text-gray-400">
            <div className="text-center">
              <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="mx-auto mb-3 text-gray-300">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
              </svg>
              <p className="text-sm">Select a website from the left to start chatting</p>
            </div>
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.map((msg) => (
                <div key={msg.id} className={`flex ${msg.sender === "user" ? "justify-end" : "justify-start"}`}>
                  <div
                    className={`max-w-[75%] px-4 py-2.5 rounded-lg text-sm ${
                      msg.sender === "user"
                        ? "bg-primary-600 text-white rounded-br-none"
                        : "bg-gray-50 text-gray-900 border rounded-bl-none"
                    }`}
                  >
                    <ReactMarkdown>{msg.text}</ReactMarkdown>
                    {msg.sender === "ai" && msg.sources && msg.sources.length > 0 && (
                      <details className="mt-2 pt-2 border-t border-gray-200">
                        <summary className="text-xs text-gray-400 cursor-pointer hover:text-gray-600">
                          Sources ({msg.sources.length})
                        </summary>
                        <div className="mt-1 space-y-1">
                          {msg.sources.map((s, i) => (
                            <div key={i} className="text-xs text-gray-500 p-1.5 bg-gray-100 rounded">
                              <div className="truncate">{s.url || "No URL"}</div>
                              <div className="text-gray-400 mt-0.5 line-clamp-2">{s.snippet}</div>
                            </div>
                          ))}
                        </div>
                      </details>
                    )}
                  </div>
                </div>
              ))}

              {isStreaming && currentAnswer && (
                <div className="flex justify-start">
                  <div className="max-w-[75%] px-4 py-2.5 rounded-lg text-sm bg-gray-50 border">
                    <ReactMarkdown>{currentAnswer}</ReactMarkdown>
                    <span className="inline-block w-2 h-4 bg-primary-600 animate-pulse ml-1" />
                  </div>
                </div>
              )}

              {isTyping && !currentAnswer && (
                <div className="flex justify-start">
                  <div className="px-4 py-3 rounded-lg bg-gray-50 border">
                    <div className="flex gap-1">
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {error && (
              <div className="px-4 py-2 bg-red-50 text-red-600 text-sm">{error}</div>
            )}

            <div className="p-4 border-t flex gap-3">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type your question..."
                disabled={!isConnected || isStreaming}
                className="flex-1 border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50"
              />
              <button
                onClick={() => sendMessage(input)}
                disabled={!input.trim() || !isConnected || isStreaming}
                className="px-4 py-2.5 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 disabled:opacity-50 transition-colors"
              >
                Send
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
