import { Scale, User, Loader2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import type { Message } from "@/lib/api";
import Citations from "./Citations";

interface MessageBubbleProps {
  message: Message;
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div style={{
      display      : "flex",
      gap          : "12px",
      padding      : "20px 0",
      borderBottom : "1px solid var(--border)",
      alignItems   : "flex-start",
    }}>

      {/* Avatar */}
      <div style={{
        width       : "30px",
        height      : "30px",
        borderRadius: "6px",
        background  : isUser ? "var(--bg-hover)" : "var(--accent)",
        display     : "flex",
        alignItems  : "center",
        justifyContent: "center",
        flexShrink  : 0,
        border      : `1px solid ${isUser ? "var(--border)" : "transparent"}`,
      }}>
        {isUser
          ? <User size={15} color="var(--text-muted)" />
          : <Scale size={15} color="var(--bg-base)" />
        }
      </div>

      {/* Content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <span style={{
          fontSize   : "12px",
          fontWeight : "600",
          color      : isUser ? "var(--text-muted)" : "var(--accent)",
          display    : "block",
          marginBottom: "8px",
          letterSpacing: "0.04em",
        }}>
          {isUser ? "You" : "Lexis"}
        </span>

        {message.loading ? (
          <div style={{
            display   : "flex",
            alignItems: "center",
            gap       : "8px",
            color     : "var(--text-muted)",
          }}>
            <Loader2
              size={14}
              style={{ animation: "spin 1s linear infinite" }}
            />
            <span style={{ fontSize: "14px" }}>Searching legal context...</span>
          </div>
        ) : (
          <>
            <div
              className="answer-content"
              style={{
                fontSize  : "14px",
                color     : "var(--text-primary)",
                lineHeight: "1.7",
              }}
            >
              {isUser ? (
                <p style={{ margin: 0 }}>{message.content}</p>
              ) : (
                <ReactMarkdown>{message.content}</ReactMarkdown>
              )}
            </div>

            {!isUser && message.citations.length > 0 && (
              <Citations citations={message.citations} />
            )}
          </>
        )}
      </div>
    </div>
  );
}