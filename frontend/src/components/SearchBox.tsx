// src/components/SearchBox.tsx

import { useState, useRef, useEffect } from "react";
import type { KeyboardEvent } from "react";
import { ArrowUp, Loader2 } from "lucide-react";

interface SearchBoxProps {
  onSubmit : (question: string) => void;
  loading  : boolean;
  disabled?: boolean;
}

export default function SearchBox({
  onSubmit,
  loading,
  disabled,
}: SearchBoxProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 160) + "px";
  }, [value]);

  function handleSubmit() {
    const q = value.trim();
    if (!q || loading || disabled) return;
    setValue("");
    onSubmit(q);
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }

  return (
    <div style={{
      padding    : "16px 24px 24px",
      background : "var(--bg-base)",
      flexShrink : 0,
    }}>
      <div style={{ maxWidth: "720px", margin: "0 auto" }}>

        {/* Input wrapper */}
        <div style={{
          display      : "flex",
          alignItems   : "flex-end",
          gap          : "10px",
          background   : "var(--bg-surface)",
          border       : "1px solid var(--border)",
          borderRadius : "12px",
          padding      : "12px 12px 12px 16px",
          transition   : "border-color 0.15s ease",
        }}
          onFocus={() => {}}
        >
          <textarea
            ref={textareaRef}
            value={value}
            onChange={e => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about Indian law..."
            disabled={loading || disabled}
            rows={1}
            style={{
              flex       : 1,
              background : "transparent",
              border     : "none",
              outline    : "none",
              color      : "var(--text-primary)",
              fontSize   : "14px",
              lineHeight : "1.6",
              resize     : "none",
              fontFamily : "inherit",
              maxHeight  : "160px",
              overflowY  : "auto",
            }}
          />

          {/* Submit button */}
          <button
            onClick={handleSubmit}
            disabled={!value.trim() || loading || disabled}
            style={{
              width       : "32px",
              height      : "32px",
              borderRadius: "8px",
              background  : value.trim() && !loading
                              ? "var(--accent)"
                              : "var(--bg-hover)",
              border      : "none",
              cursor      : value.trim() && !loading
                              ? "pointer"
                              : "not-allowed",
              display     : "flex",
              alignItems  : "center",
              justifyContent: "center",
              flexShrink  : 0,
              transition  : "all 0.15s ease",
            }}
          >
            {loading
              ? <Loader2 size={15} color="var(--text-muted)"
                  style={{ animation: "spin 1s linear infinite" }} />
              : <ArrowUp size={15}
                  color={value.trim() ? "var(--bg-base)" : "var(--text-subtle)"} />
            }
          </button>
        </div>

        {/* Footer note */}
        <p style={{
          fontSize  : "11px",
          color     : "var(--text-subtle)",
          textAlign : "center",
          marginTop : "10px",
        }}>
          Lexis searches Indian legal texts using SAT Graph RAG.
          Always consult a lawyer for specific legal advice.
        </p>
      </div>
    </div>
  );
}