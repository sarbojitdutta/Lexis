import { useState, useEffect, useCallback } from "react";
import Navbar from "./components/NavBar";
import Sidebar from "./components/SideBar";
import MessageList, { EmptyState } from "./components/MessageList";
import SearchBox   from "./components/SearchBox";
import type { Chat, Message } from "./lib/api";
import { askQuestion, checkHealth, generateId, createChat } from "./lib/api";
import {
  getCurrentUser,
  handleOAuthRedirect,
  type User,
} from "./lib/auth";



export default function App() {
  const [chats, setChats] = useState<Chat[]>([]);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [health, setHealth] = useState<{
    total_vectors?: number;
    total_nodes?  : number;
  }>({});
  const [user, setUser] = useState<User | null>(() => getCurrentUser());
  
  const wasRedirect = handleOAuthRedirect()
  if(wasRedirect){
    setUser(getCurrentUser());
  }

  // Load health stats on mount
  useEffect(() => {
    checkHealth()
      .then(h => setHealth(h))
      .catch(() => {});
  }, []);

  // Get currently active chat
  const activeChat = chats.find(c => c.id === activeChatId) ?? null;

  // ── New chat ──
  function handleNewChat() {
    const chat = createChat();
    setChats(prev => [chat, ...prev]);
    setActiveChatId(chat.id);
  }

  // ── Select chat from sidebar ──
  function handleSelectChat(id: string) {
    setActiveChatId(id);
  }

  // ── Delete chat from sidebar ──
  function handleDeleteChat(id: string) {
    setChats(prev => prev.filter(c => c.id !== id));
    if (activeChatId === id) {
      setActiveChatId(
        chats.find(c => c.id !== id)?.id ?? null
      );
    }
  }

  // ── Submit question ──
  const handleSubmit = useCallback(async (question: string) => {

    // Create new chat if none is active
    let chatId = activeChatId;
    if (!chatId) {
      const newChat = createChat(question);
      setChats(prev => [newChat, ...prev]);
      setActiveChatId(newChat.id);
      chatId = newChat.id;
    }

    // Set chat title from first question
    setChats(prev => prev.map(c => {
      if (c.id !== chatId) return c;
      const isFirst = c.messages.length === 0;
      return {
        ...c,
        title: isFirst
          ? question.slice(0, 40) + (question.length > 40 ? "..." : "")
          : c.title,
      };
    }));

    // Add user message
    const userMsg: Message = {
      id       : generateId(),
      role     : "user",
      content  : question,
      citations: [],
      timestamp: new Date(),
    };

    // Add loading placeholder
    const loadingMsg: Message = {
      id       : generateId(),
      role     : "assistant",
      content  : "",
      citations: [],
      timestamp: new Date(),
      loading  : true,
    };

    setChats(prev => prev.map(c =>
      c.id === chatId
        ? { ...c, messages: [...c.messages, userMsg, loadingMsg] }
        : c
    ));

    setLoading(true);

    try {
      const response = await askQuestion(question);

      // Replace loading message with real answer
      const assistantMsg: Message = {
        id       : loadingMsg.id,
        role     : "assistant",
        content  : response.answer,
        citations: response.citations,
        timestamp: new Date(),
        loading  : false,
      };

      setChats(prev => prev.map(c =>
        c.id === chatId
          ? {
              ...c,
              messages: c.messages.map(m =>
                m.id === loadingMsg.id ? assistantMsg : m
              ),
            }
          : c
      ));

    } catch (err) {
      // Replace loading with error message
      const errorMsg: Message = {
        id       : loadingMsg.id,
        role     : "assistant",
        content  : "Something went wrong.",
        citations: [],
        timestamp: new Date(),
        loading  : false,
      };

      setChats(prev => prev.map(c =>
        c.id === chatId
          ? {
              ...c,
              messages: c.messages.map(m =>
                m.id === loadingMsg.id ? errorMsg : m
              ),
            }
          : c
      ));

    } finally {
      setLoading(false);
    }

  }, [activeChatId]);

  return (
    <div style={{
      display      : "flex",
      flexDirection: "column",
      height       : "100vh",
      overflow     : "hidden",
      background   : "var(--bg-base)",
    }}>

      {/* Top navbar */}
      <Navbar
        totalVectors={health.total_vectors}
        totalNodes={health.total_nodes}
        user = {user}
      />

      {/* Body — sidebar + main */}
      <div style={{
        display : "flex",
        flex    : 1,
        overflow: "hidden",
      }}>

        {/* Left sidebar */}
        <Sidebar
          chats        = {chats}
          activeChatId = {activeChatId}
          onNewChat    = {handleNewChat}
          onSelectChat = {handleSelectChat}
          onDeleteChat = {handleDeleteChat}
        />

        {/* Main area */}
        <main style={{
          flex         : 1,
          display      : "flex",
          flexDirection: "column",
          overflow     : "hidden",
          background   : "var(--bg-base)",
        }}>

          {/* Messages or empty state */}
          {activeChat && activeChat.messages.length > 0 ? (
            <MessageList messages={activeChat.messages} />
          ) : (
            <div style={{ flex: 1, overflow: "hidden" }}>
              <EmptyState onSuggestion={handleSubmit} />
            </div>
          )}

          {/* Search box always at bottom */}
          <SearchBox
            onSubmit={handleSubmit}
            loading={loading}
          />

        </main>
      </div>
    </div>
  );
}