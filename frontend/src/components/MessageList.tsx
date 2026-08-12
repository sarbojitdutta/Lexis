import { useEffect, useRef } from "react";
import { Scale } from "lucide-react";
import type{ Message } from "@/lib/api";
import MessageBubble from "./MessageBubble";

interface MessageListProps {
  messages: Message[];
}

const SUGGESTIONS = [
  "Can a minor enter into a contract?",
  "What is free consent in Indian law?",
  "Explain breach of contract and compensation",
  "What makes an agreement void?",
  "What is a contract of indemnity?",
];

interface EmptyStateProps {
  onSuggestion: (q: string) => void;
}

export function EmptyState({ onSuggestion }: EmptyStateProps) {
  return (
    <div style={{
      display        : "flex",
      flexDirection  : "column",
      alignItems     : "center",
      justifyContent : "center",
      height         : "100%",
      gap            : "32px",
      padding        : "40px",
    }}>
      {/* Icon + title */}
      <div style={{ textAlign: "center" }}>
        <div style={{
          width       : "52px",
          height      : "52px",
          borderRadius: "12px",
          background  : "var(--bg-surface)",
          border      : "1px solid var(--border)",
          display     : "flex",
          alignItems  : "center",
          justifyContent: "center",
          margin      : "0 auto 16px",
        }}>
          <Scale size={24} color="var(--accent)" />
        </div>
        <h2 style={{
          fontSize  : "20px",
          fontWeight: "600",
          color     : "var(--text-primary)",
          margin    : "0 0 8px",
        }}>
          Ask anything about Indian law
        </h2>
        <p style={{
          fontSize: "14px",
          color   : "var(--text-muted)",
          maxWidth: "360px",
          margin  : "0 auto",
          lineHeight: "1.6",
        }}>
          Powered by SAT Graph RAG — finds relevant sections
          and their legal relationships for accurate answers
        </p>
      </div>

      {/* Suggestions */}
      <div style={{
        display       : "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
        gap           : "8px",
        width         : "100%",
        maxWidth      : "600px",
      }}>
        {SUGGESTIONS.map((s, i) => (
          <button
            key={i}
            onClick={() => onSuggestion(s)}
            style={{
              padding     : "10px 14px",
              background  : "var(--bg-surface)",
              border      : "1px solid var(--border)",
              borderRadius: "8px",
              color       : "var(--text-muted)",
              fontSize    : "13px",
              cursor      : "pointer",
              textAlign   : "left",
              lineHeight  : "1.4",
              transition  : "all 0.15s ease",
            }}
            onMouseEnter={e => {
              const el = e.currentTarget as HTMLElement;
              el.style.background   = "var(--bg-hover)";
              el.style.color        = "var(--text-primary)";
              el.style.borderColor  = "var(--text-subtle)";
            }}
            onMouseLeave={e => {
              const el = e.currentTarget as HTMLElement;
              el.style.background   = "var(--bg-surface)";
              el.style.color        = "var(--text-muted)";
              el.style.borderColor  = "var(--border)";
            }}
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function MessageList({ messages }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div style={{
      flex     : 1,
      overflowY: "auto",
      padding  : "0 24px",
    }}>
      <div style={{ maxWidth: "720px", margin: "0 auto" }}>
        {messages.map(msg => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}