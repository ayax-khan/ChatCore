"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Message {
  id: string;
  sender: "user" | "ai";
  text: string;
  timestamp: number;
  sources?: { url: string; snippet: string }[];
  confidence?: number;
}

interface ChatWidgetProps {
  siteId: number;
  apiUrl?: string;
  primaryColor?: string;
  position?: "left" | "right";
  welcomeMessage?: string;
  logoUrl?: string;
}

export default function ChatWidget({
  siteId,
  apiUrl = "/api/v1",
  primaryColor = "#3b82f6",
  position = "right",
  welcomeMessage = "Hello! How can I help you today?",
  logoUrl,
}: ChatWidgetProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    { id: "welcome", sender: "ai", text: welcomeMessage, timestamp: Date.now() },
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([]);
  const [currentAnswer, setCurrentAnswer] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, currentAnswer, scrollToBottom]);

  useEffect(() => {
    if (!isOpen) return;
    const token = localStorage.getItem("access_token") || "public";
    const sessionId = localStorage.getItem("chat_session") || `sess_${Math.random().toString(36).substring(2, 15)}`;
    localStorage.setItem("chat_session", sessionId);
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/api/ws/chat?token=${token}&session_id=${sessionId}&site_id=${siteId}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      fetchSuggestedQuestions();
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleWsMessage(data);
    };

    ws.onerror = (err) => {
      console.error("WebSocket error:", err);
    };

    ws.onclose = () => {
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

    return () => {
      ws.close();
    };
  }, [isOpen, siteId]);

  const handleWsMessage = (data: any) => {
    switch (data.type) {
      case "token":
        setCurrentAnswer((prev) => prev + data.content);
        break;
      case "sources":
        break;
      case "confidence":
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

  const fetchSuggestedQuestions = async () => {
    try {
      const res = await fetch(`/api/v1/feedback/suggested-questions?site_id=${siteId}`);
      if (res.ok) {
        const data = await res.json();
        setSuggestedQuestions(data.questions || []);
      }
    } catch {}
  };

  const sendMessage = (text: string) => {
    if (!text.trim() || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    const userMsg: Message = {
      id: `user_${Date.now()}`,
      sender: "user",
      text: text.trim(),
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, userMsg]);
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

  const handleFeedback = async (messageId: string, rating: number) => {
    try {
      await fetch("/api/v1/feedback/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: localStorage.getItem("chat_session"), message_id: messageId, rating }),
      });
    } catch {}
  };

  return (
    <>
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          style={{ backgroundColor: primaryColor, [position]: "20px" }}
          className="fixed bottom-5 w-14 h-14 rounded-full shadow-lg flex items-center justify-center text-white hover:scale-110 transition-transform z-50"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        </button>
      )}

      {isOpen && (
        <div
          style={{ [position]: "20px" }}
          className="fixed bottom-5 w-[380px] max-w-[calc(100vw-40px)] h-[600px] max-h-[calc(100vh-120px)] bg-white rounded-xl shadow-2xl flex flex-col z-50 overflow-hidden border"
        >
          <div
            style={{ backgroundColor: primaryColor }}
            className="px-4 py-3 flex items-center justify-between text-white"
          >
            <div className="flex items-center gap-2">
              {logoUrl ? (
                <img src={logoUrl} alt="Logo" className="w-8 h-8 rounded-full" />
              ) : (
                <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center font-bold">C</div>
              )}
              <span className="font-semibold">ChatCore Assistant</span>
            </div>
            <button onClick={() => setIsOpen(false)} className="text-white/80 hover:text-white">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
            {messages.map((msg) => (
              <div key={msg.id} className={`flex ${msg.sender === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[80%] px-3 py-2 rounded-lg text-sm ${
                    msg.sender === "user"
                      ? "bg-primary-600 text-white rounded-br-none"
                      : "bg-white text-gray-900 shadow-sm rounded-bl-none border"
                  }`}
                >
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.text}</ReactMarkdown>
                  {msg.sender === "ai" && msg.id !== "welcome" && (
                    <div className="flex gap-2 mt-2 pt-2 border-t">
                      <button onClick={() => handleFeedback(msg.id, 1)} className="text-xs text-gray-400 hover:text-green-500" title="Helpful">
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/></svg>
                      </button>
                      <button onClick={() => handleFeedback(msg.id, 0)} className="text-xs text-gray-400 hover:text-red-500" title="Not helpful">
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3H10z"/><line x1="17" y1="2" x2="17" y2="15"/></svg>
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {isStreaming && currentAnswer && (
              <div className="flex justify-start">
                <div className="max-w-[80%] px-3 py-2 rounded-lg text-sm bg-white shadow-sm border">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{currentAnswer}</ReactMarkdown>
                  <span className="inline-block w-2 h-4 bg-primary-600 animate-pulse ml-1" />
                </div>
              </div>
            )}

            {isTyping && !currentAnswer && (
              <div className="flex justify-start">
                <div className="px-4 py-3 rounded-lg bg-white shadow-sm border">
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

          {suggestedQuestions.length > 0 && !isStreaming && messages.length <= 1 && (
            <div className="px-4 py-2 border-t bg-white">
              <p className="text-xs text-gray-500 mb-2">Suggested questions:</p>
              <div className="flex flex-wrap gap-2">
                {suggestedQuestions.slice(0, 3).map((q, i) => (
                  <button key={i} onClick={() => sendMessage(q)} className="text-xs bg-gray-100 hover:bg-gray-200 px-3 py-1.5 rounded-full transition-colors">
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="p-3 border-t bg-white flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your question..."
              disabled={isStreaming}
              className="flex-1 border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 disabled:opacity-50"
              style={{ focusRingColor: primaryColor }}
            />
            <button
              onClick={() => sendMessage(input)}
              disabled={!input.trim() || isStreaming}
              className="px-3 py-2 rounded-lg text-white disabled:opacity-50"
              style={{ backgroundColor: primaryColor }}
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
            </button>
          </div>
        </div>
      )}
    </>
  );
}
