"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import { useParams } from "next/navigation";

interface Message {
  id: string;
  sender: "user" | "ai";
  text: string;
  timestamp: number;
  sources?: { url: string; snippet: string; score: number }[];
}

export default function WidgetChatPage() {
  const params = useParams();
  const siteId = Number(params.siteId);

  const [messages, setMessages] = useState<Message[]>([
    { id: "welcome", sender: "ai", text: "Hello! How can I help you today?", timestamp: Date.now() },
  ]);
  const [input, setInput] = useState("");
  const [isConnected, setIsConnected] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentAnswer, setCurrentAnswer] = useState("");
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => { scrollToBottom(); }, [messages, currentAnswer, scrollToBottom]);

  useEffect(() => {
    const token = localStorage.getItem("access_token") || "public";
    const sessionId = `widget_${Math.random().toString(36).substring(2, 15)}`;
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/api/ws/chat?token=${token}&session_id=${sessionId}&site_id=${siteId}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => setIsConnected(true);
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
          setMessages((prev) => [...prev, { id: `ai_${Date.now()}`, sender: "ai", text: currentAnswer || data.answer || "", timestamp: Date.now(), sources: data.sources }]);
          setCurrentAnswer("");
          setIsStreaming(false);
          setIsTyping(false);
          break;
        case "error":
          setMessages((prev) => [...prev, { id: `err_${Date.now()}`, sender: "ai", text: `Error: ${data.content}`, timestamp: Date.now() }]);
          setIsStreaming(false);
          setIsTyping(false);
          break;
      }
    };
    ws.onclose = () => setIsConnected(false);

    return () => ws.close();
  }, [siteId]);

  const sendMessage = (text: string) => {
    if (!text.trim() || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    setMessages((prev) => [...prev, { id: `user_${Date.now()}`, sender: "user", text: text.trim(), timestamp: Date.now() }]);
    setInput("");
    setCurrentAnswer("");
    setIsStreaming(true);
    setIsTyping(true);
    wsRef.current.send(JSON.stringify({ type: "message", content: text.trim() }));
  };

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column", background: "#f9fafb", fontFamily: "system-ui, sans-serif" }}>
      <div style={{ padding: "14px 20px", background: "#3b82f6", color: "white", display: "flex", alignItems: "center", gap: "10px" }}>
        <div style={{ width: "32px", height: "32px", borderRadius: "50%", background: "rgba(255,255,255,0.2)", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: "bold", fontSize: "16px" }}>C</div>
        <div>
          <div style={{ fontWeight: 600, fontSize: "15px" }}>ChatCore Assistant</div>
          <div style={{ fontSize: "12px", opacity: 0.8 }}>{isConnected ? "Online" : "Connecting..."}</div>
        </div>
      </div>
      <div style={{ flex: 1, overflowY: "auto", padding: "16px", display: "flex", flexDirection: "column", gap: "12px" }}>
        {messages.map((msg) => (
          <div key={msg.id} style={{ display: "flex", justifyContent: msg.sender === "user" ? "flex-end" : "flex-start" }}>
            <div style={{ maxWidth: "80%", padding: "10px 14px", borderRadius: "12px", fontSize: "14px", lineHeight: "1.5", background: msg.sender === "user" ? "#3b82f6" : "white", color: msg.sender === "user" ? "white" : "#111", border: msg.sender === "user" ? "none" : "1px solid #e5e7eb" }}>
              <ReactMarkdown>{msg.text}</ReactMarkdown>
            </div>
          </div>
        ))}
        {isStreaming && currentAnswer && (
          <div style={{ display: "flex", justifyContent: "flex-start" }}>
            <div style={{ maxWidth: "80%", padding: "10px 14px", borderRadius: "12px", fontSize: "14px", background: "white", border: "1px solid #e5e7eb" }}>
              <ReactMarkdown>{currentAnswer}</ReactMarkdown>
              <span style={{ display: "inline-block", width: "6px", height: "14px", background: "#3b82f6", animation: "pulse 1s infinite", marginLeft: "2px" }} />
            </div>
          </div>
        )}
        {isTyping && !currentAnswer && (
          <div style={{ display: "flex", justifyContent: "flex-start" }}>
            <div style={{ padding: "12px 16px", borderRadius: "12px", background: "white", border: "1px solid #e5e7eb", display: "flex", gap: "4px" }}>
              {[0, 150, 300].map((d, i) => (
                <span key={i} style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#9ca3af", animation: `bounce 1.4s infinite`, animationDelay: `${d}ms` }} />
              ))}
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <div style={{ padding: "12px 16px", borderTop: "1px solid #e5e7eb", background: "white", display: "flex", gap: "8px" }}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(input); } }}
          placeholder="Type your question..."
          disabled={!isConnected || isStreaming}
          style={{ flex: 1, padding: "10px 14px", borderRadius: "8px", border: "1px solid #d1d5db", fontSize: "14px", outline: "none" }}
        />
        <button
          onClick={() => sendMessage(input)}
          disabled={!input.trim() || !isConnected || isStreaming}
          style={{ padding: "10px 20px", borderRadius: "8px", border: "none", background: "#3b82f6", color: "white", fontSize: "14px", fontWeight: 500, cursor: "pointer", opacity: (!input.trim() || !isConnected || isStreaming) ? 0.5 : 1 }}
        >
          Send
        </button>
      </div>
      <style>{`
        @keyframes pulse { 0%,100% { opacity:1 } 50% { opacity:0.3 } }
        @keyframes bounce { 0%,60%,100% { transform: translateY(0) } 30% { transform: translateY(-6px) } }
      `}</style>
    </div>
  );
}
