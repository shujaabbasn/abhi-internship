import { useState, useRef, useEffect, useCallback } from "react";
import Sidebar from "./components/Sidebar";
import ChatBubble from "./components/ChatBubble";
import TypingIndicator from "./components/TypingIndicator";
import { sendMessage } from "./api";
import "./App.css";

const WELCOME_MESSAGE = {
  id: "welcome",
  role: "assistant",
  content:
    "👋 **Welcome to the ABHI Banking Assistant!**\n\nI can help you with:\n- 🏦 **Check your account balance**\n- 💸 **Send money**\n- 🌤 **Check the weather**\n- 💱 **Currency conversion**\n- 📚 **Learn about ABHI products**\n\nHow can I assist you today?",
  intent: null,
  timestamp: Date.now(),
};

function createConversation(firstMessage = null) {
  return {
    id: crypto.randomUUID(),
    title: firstMessage ? firstMessage.slice(0, 36) + (firstMessage.length > 36 ? "…" : "") : "New Conversation",
    messages: [WELCOME_MESSAGE],
    sessionId: null,
  };
}

export default function App() {
  const [conversations, setConversations] = useState([createConversation()]);
  const [activeId, setActiveId] = useState(conversations[0].id);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [backendOnline, setBackendOnline] = useState(true);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const activeConv = conversations.find((c) => c.id === activeId);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeConv?.messages, isLoading]);

  // Focus input on mount / conversation switch
  useEffect(() => {
    inputRef.current?.focus();
  }, [activeId]);

  const updateConversation = useCallback((id, updater) => {
    setConversations((prev) => prev.map((c) => (c.id === id ? updater(c) : c)));
  }, []);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || isLoading) return;

    setInput("");
    setIsLoading(true);

    // Append user message
    const userMsg = { id: crypto.randomUUID(), role: "user", content: text, timestamp: Date.now() };
    updateConversation(activeId, (c) => {
      const isFirst = c.messages.length === 1; // only welcome
      return {
        ...c,
        title: isFirst ? text.slice(0, 36) + (text.length > 36 ? "…" : "") : c.title,
        messages: [...c.messages, userMsg],
      };
    });

    try {
      const currentSessionId = activeConv.sessionId;
      const data = await sendMessage(text, currentSessionId);

      const assistantMsg = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: data.reply,
        intent: data.intent,
        data: data.data,
        timestamp: Date.now(),
      };

      updateConversation(activeId, (c) => ({
        ...c,
        sessionId: data.session_id,
        messages: [...c.messages, assistantMsg],
      }));

      setBackendOnline(true);
    } catch (err) {
      setBackendOnline(false);
      const errorMsg = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "❌ **Could not reach the backend.** Make sure the FastAPI server is running on port 8000.",
        intent: null,
        timestamp: Date.now(),
      };
      updateConversation(activeId, (c) => ({ ...c, messages: [...c.messages, errorMsg] }));
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleNewChat = () => {
    const conv = createConversation();
    setConversations((prev) => [conv, ...prev]);
    setActiveId(conv.id);
    setInput("");
  };

  const handleDeleteChat = (idToDelete) => {
    setConversations((prev) => {
      const filtered = prev.filter((c) => c.id !== idToDelete);
      if (filtered.length === 0) {
        const newConv = createConversation();
        setActiveId(newConv.id);
        return [newConv];
      }
      if (idToDelete === activeId) {
        setActiveId(filtered[0].id);
      }
      return filtered;
    });
  };

  return (
    <div className="app">
      {/* Background decorative blobs */}
      <div className="bg-blob bg-blob-1" />
      <div className="bg-blob bg-blob-2" />

      <Sidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={(id) => { setActiveId(id); setInput(""); }}
        onNew={handleNewChat}
        onDelete={handleDeleteChat}
      />

      <main className="chat-area">
        {/* Header */}
        <header className="chat-header">
          <div className="chat-header-left">
            <h1 className="header-title">Chat Interface</h1>
            <div className="header-status">
              <span className={`status-dot ${backendOnline ? "status-online" : "status-offline"}`} />
              <span className="status-label">{backendOnline ? "Backend: Online" : "Backend: Offline"}</span>
            </div>
          </div>
          <div className="chat-header-right">
            <div className="header-actions">
              <svg onClick={() => alert("Connecting to Cloud Server...")} width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/></svg>
              <svg onClick={() => alert("Opening Documents...")} width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
              <svg onClick={() => alert("No new notifications")} width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
            </div>
          </div>
        </header>

        {/* Messages */}
        <div className="messages-container">
          {activeConv?.messages.map((msg) => (
            <ChatBubble key={msg.id} message={msg} />
          ))}
          {isLoading && <TypingIndicator />}
          <div ref={messagesEndRef} />
        </div>

        {/* Input bar */}
        <div className="input-area">
          <div className="input-bar">
            <textarea
              ref={inputRef}
              id="chat-input"
              className="input-field"
              placeholder="Ask about your account, weather, currency, or ABHI products…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
              disabled={isLoading}
            />
            <button
              id="send-button"
              className={`send-btn ${input.trim() && !isLoading ? "send-btn-active" : ""}`}
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              aria-label="Send message"
            >
              {isLoading ? (
                <span className="spinner" />
              ) : (
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <path d="M3 10L17 10M11 4L17 10L11 16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              )}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
