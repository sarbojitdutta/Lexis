import { useState } from "react";
import { Plus, MessageSquare, Trash2 } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import type { Chat } from "@/lib/api";

interface SidebarProps {
  chats       : Chat[];
  activeChatId: string | null;
  onNewChat   : () => void;
  onSelectChat: (id: string) => void;
  onDeleteChat: (id: string) => void;
}

export default function Sidebar({
  chats,
  activeChatId,
  onNewChat,
  onSelectChat,
  onDeleteChat,
}: SidebarProps) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  return (
    <aside
      style={{
        width        : "240px",
        minWidth     : "240px",
        height       : "100%",
        background   : "var(--bg-surface)",
        borderRight  : "1px solid var(--border)",
        display      : "flex",
        flexDirection: "column",
        padding      : "12px 8px",
      }}
    >
      {/* New Chat button */}
      <button
        onClick={onNewChat}
        style={{
          display      : "flex",
          alignItems   : "center",
          gap          : "8px",
          padding      : "9px 12px",
          background   : "transparent",
          border       : "1px solid var(--border)",
          borderRadius : "8px",
          color        : "var(--text-primary)",
          cursor       : "pointer",
          fontSize     : "13px",
          marginBottom : "16px",
          width        : "100%",
          transition   : "all 0.15s ease",
        }}
        onMouseEnter={e => {
          (e.currentTarget as HTMLElement).style.background    = "var(--bg-hover)";
          (e.currentTarget as HTMLElement).style.borderColor   = "var(--text-subtle)";
        }}
        onMouseLeave={e => {
          (e.currentTarget as HTMLElement).style.background    = "transparent";
          (e.currentTarget as HTMLElement).style.borderColor   = "var(--border)";
        }}
      >
        <Plus size={15} />
        New chat
      </button>

      <Separator style={{ background: "var(--border)", marginBottom: "12px" }} />

      {/* History label */}
      <span style={{
        fontSize     : "10px",
        fontWeight   : "600",
        color        : "var(--text-muted)",
        padding      : "0 8px",
        marginBottom : "8px",
        letterSpacing: "0.08em",
        textTransform: "uppercase",
      }}>
        Recent
      </span>

      {/* Chat list */}
      <ScrollArea style={{ flex: 1 }}>
        {chats.length === 0 ? (
          <div style={{
            display      : "flex",
            flexDirection: "column",
            alignItems   : "center",
            gap          : "8px",
            padding      : "32px 16px",
            color        : "var(--text-subtle)",
          }}>
            <MessageSquare size={20} />
            <span style={{ fontSize: "12px", textAlign: "center" }}>
              Your conversations will appear here
            </span>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "1px" }}>
            {chats.map(chat => (
              <div
                key={chat.id}
                onMouseEnter={() => setHoveredId(chat.id)}
                onMouseLeave={() => setHoveredId(null)}
                onClick={() => onSelectChat(chat.id)}
                style={{
                  display     : "flex",
                  alignItems  : "center",
                  gap         : "8px",
                  padding     : "8px 10px",
                  borderRadius: "6px",
                  cursor      : "pointer",
                  background  : activeChatId === chat.id
                                  ? "var(--bg-hover)"
                                  : "transparent",
                  transition  : "background 0.12s ease",
                }}
              >
                <MessageSquare
                  size={13}
                  color="var(--text-muted)"
                  style={{ flexShrink: 0 }}
                />
                <span style={{
                  fontSize    : "13px",
                  color       : activeChatId === chat.id
                                  ? "var(--text-primary)"
                                  : "var(--text-muted)",
                  flex        : 1,
                  overflow    : "hidden",
                  whiteSpace  : "nowrap",
                  textOverflow: "ellipsis",
                }}>
                  {chat.title}
                </span>

                {hoveredId === chat.id && (
                  <button
                    onClick={e => {
                      e.stopPropagation();
                      onDeleteChat(chat.id);
                    }}
                    style={{
                      background  : "transparent",
                      border      : "none",
                      cursor      : "pointer",
                      padding     : "2px 3px",
                      borderRadius: "4px",
                      flexShrink  : 0,
                      display     : "flex",
                      alignItems  : "center",
                    }}
                  >
                    <Trash2 size={12} color="var(--text-muted)" />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </ScrollArea>
    </aside>
  );
}