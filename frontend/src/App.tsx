import { useState, useEffect, useCallback } from "react";
import Navbar from "./components/NavBar";
import Sidebar from "./components/SideBar";
import MessageList, { EmptyState } from "./components/MessageList";
import SearchBox from "./components/SearchBox";
import type { Chat, Message } from "./lib/api";
import {
  askQuestion,
  checkHealth,
  generateId,
  createChat,
  getChats,
  getChat,
  deleteChat,
} from "./lib/api";
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
    total_nodes?: number;
  }>({});
  const [user] = useState<User | null>(() => {
    handleOAuthRedirect();
    return getCurrentUser();
  });

  useEffect(() => {
    checkHealth()
      .then(h => setHealth(h))
      .catch(() => {});
  }, []);

  // Load persisted chats for the authenticated user.
  useEffect(() => {
    if (!user) return;

    getChats()
      .then(serverChats => {
        setChats(serverChats);
        if (serverChats.length > 0) {
          setActiveChatId(serverChats[0].id);
        }
      })
      .catch(() => {});
  }, [user]);

  // Load messages whenever the selected chat changes.
  useEffect(() => {
    if (!activeChatId) return;

    getChat(activeChatId)
      .then(serverChat => {
        setChats(prev => prev.map(chat =>
          chat.id === serverChat.id ? serverChat : chat
        ));
      })
      .catch(() => {});
  }, [activeChatId]);

  const activeChat = chats.find(c => c.id === activeChatId) ?? null;

  async function handleNewChat() {
    if (!user) return;

    try {
      const chat = await createChat();
      setChats(prev => [chat, ...prev]);
      setActiveChatId(chat.id);
    } catch {
      // Keep the UI unchanged if chat creation fails.
    }
  }

  function handleSelectChat(id: string) {
    setActiveChatId(id);
  }

  async function handleDeleteChat(id: string) {
    try {
      await deleteChat(id);
      setChats(prev => prev.filter(c => c.id !== id));
      if (activeChatId === id) {
        const remaining = chats.filter(c => c.id !== id);
        setActiveChatId(remaining[0]?.id ?? null);
      }
    } catch {
      // Do not remove a chat locally if the server rejected deletion.
    }
  }

  const handleSubmit = useCallback(async (question: string) => {
    if (!user) return;

    let chatId = activeChatId;

    try {
      // Create the real server-side chat when the user starts from the empty state.
      if (!chatId) {
        const newChat = await createChat(question.slice(0, 80));
        chatId = newChat.id;
        setChats(prev => [newChat, ...prev]);
        setActiveChatId(chatId);
      }

      const targetChatId = chatId;
      const userMsg: Message = {
        id: generateId(),
        role: "user",
        content: question,
        citations: [],
        timestamp: new Date(),
      };

      const loadingMsg: Message = {
        id: generateId(),
        role: "assistant",
        content: "",
        citations: [],
        timestamp: new Date(),
        loading: true,
      };

      setChats(prev => prev.map(chat =>
        chat.id === targetChatId
          ? {
              ...chat,
              title: chat.messages.length === 0
                ? question.slice(0, 40) + (question.length > 40 ? "..." : "")
                : chat.title,
              messages: [...chat.messages, userMsg, loadingMsg],
            }
          : chat
      ));

      setLoading(true);

      const response = await askQuestion(question, targetChatId);

      const assistantMsg: Message = {
        id: loadingMsg.id,
        role: "assistant",
        content: response.answer,
        citations: response.citations,
        timestamp: new Date(),
        loading: false,
      };

      setChats(prev => prev.map(chat =>
        chat.id === targetChatId
          ? {
              ...chat,
              messages: chat.messages.map(message =>
                message.id === loadingMsg.id ? assistantMsg : message
              ),
            }
          : chat
      ));
    } catch {
      const errorMsg: Message = {
        id: generateId(),
        role: "assistant",
        content: "Something went wrong. Please try again.",
        citations: [],
        timestamp: new Date(),
        loading: false,
      };

      setChats(prev => prev.map(chat => {
        if (chat.id !== chatId) return chat;
        const loadingIndex = [...chat.messages]
          .reverse()
          .findIndex(message => message.loading);
        if (loadingIndex < 0) return chat;

        const index = chat.messages.length - 1 - loadingIndex;
        return {
          ...chat,
          messages: chat.messages.map((message, i) =>
            i === index ? errorMsg : message
          ),
        };
      }));
    } finally {
      setLoading(false);
    }
  }, [activeChatId, user]);

  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      height: "100vh",
      overflow: "hidden",
      background: "var(--bg-base)",
    }}>
      <Navbar
        totalVectors={health.total_vectors}
        totalNodes={health.total_nodes}
        user={user}
      />

      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        <Sidebar
          chats={chats}
          activeChatId={activeChatId}
          onNewChat={handleNewChat}
          onSelectChat={handleSelectChat}
          onDeleteChat={handleDeleteChat}
        />

        <main style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          background: "var(--bg-base)",
        }}>
          {activeChat && activeChat.messages.length > 0 ? (
            <MessageList messages={activeChat.messages} />
          ) : (
            <div style={{ flex: 1, overflow: "hidden" }}>
              <EmptyState onSuggestion={handleSubmit} />
            </div>
          )}

          <SearchBox onSubmit={handleSubmit} loading={loading} />
        </main>
      </div>
    </div>
  );
}
