// src/components/Citations.tsx

import { BookOpen } from "lucide-react";
import type { Citation } from "@/lib/api";
import { Badge } from "@/components/ui/badge";

interface CitationsProps {
  citations: Citation[];
}

export default function Citations({ citations }: CitationsProps) {
  if (!citations || citations.length === 0) return null;

  return (
    <div style={{
      marginTop   : "12px",
      paddingTop  : "12px",
      borderTop   : "1px solid var(--border)",
    }}>
      <div style={{
        display    : "flex",
        alignItems : "center",
        gap        : "6px",
        marginBottom: "8px",
      }}>
        <BookOpen size={12} color="var(--text-muted)" />
        <span style={{
          fontSize : "11px",
          color    : "var(--text-muted)",
          fontWeight: "500",
          letterSpacing: "0.05em",
          textTransform: "uppercase",
        }}>
          Sources
        </span>
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
        {citations.map((c, i) => (
          <div
            key={i}
            style={{
              display     : "flex",
              alignItems  : "center",
              gap         : "5px",
              padding     : "4px 8px",
              background  : "var(--bg-hover)",
              border      : "1px solid var(--border)",
              borderRadius: "5px",
              cursor      : "default",
            }}
          >
            <span style={{
              fontSize : "12px",
              color    : "var(--accent)",
              fontWeight: "500",
            }}>
              §{c.section_id}
            </span>
            {c.title && (
              <span style={{
                fontSize : "12px",
                color    : "var(--text-muted)",
                maxWidth : "180px",
                overflow : "hidden",
                whiteSpace: "nowrap",
                textOverflow: "ellipsis",
              }}>
                {c.title}
              </span>
            )}
            <Badge
              variant="outline"
              style={{
                fontSize    : "9px",
                padding     : "0 4px",
                height      : "14px",
                borderColor : "var(--border)",
                color       : "var(--text-subtle)",
                background  : "transparent",
              }}
            >
              {(c.score * 100).toFixed(0)}%
            </Badge>
          </div>
        ))}
      </div>
    </div>
  );
}