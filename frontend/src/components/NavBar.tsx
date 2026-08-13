// src/components/Navbar.tsx

import { Scale } from "lucide-react";
import { loginWithGoogle } from "@/lib/auth";
import UserMenu from "./UserMenu";
import type { User as UserType } from "@/lib/auth";

interface NavbarProps {
  totalVectors?: number;
  totalNodes?  : number;
  user         : UserType | null;
}

export default function Navbar({
  user,
}: NavbarProps) {
  return (
    <nav style={{
      height        : "52px",
      borderBottom  : "1px solid var(--border)",
      display       : "flex",
      alignItems    : "center",
      justifyContent: "space-between",
      padding       : "0 20px",
      background    : "var(--bg-base)",
      flexShrink    : 0,
    }}>

      {/* Left — brand */}
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <Scale size={18} color="var(--lexis-accent)" />
        <span style={{
          fontSize     : "15px",
          fontWeight   : "600",
          color        : "var(--text-primary)",
          letterSpacing: "0.1em",
        }}>
          LEXIS
        </span>
      </div>


      {/* Right — auth */}
      {user ? (
        <UserMenu user={user} />
      ) : (
        <button
          onClick={loginWithGoogle}
          style={{
            display      : "flex",
            alignItems   : "center",
            gap          : "8px",
            padding      : "6px 14px",
            background   : "transparent",
            border       : "1px solid var(--border)",
            borderRadius : "6px",
            color        : "var(--text-muted)",
            cursor       : "pointer",
            fontSize     : "13px",
            transition   : "all 0.15s ease",
          }}
          onMouseEnter={e => {
            const el = e.currentTarget as HTMLElement;
            el.style.background  = "var(--bg-hover)";
            el.style.borderColor = "var(--text-subtle)";
            el.style.color       = "var(--text-primary)";
          }}
          onMouseLeave={e => {
            const el = e.currentTarget as HTMLElement;
            el.style.background  = "transparent";
            el.style.borderColor = "var(--border)";
            el.style.color       = "var(--text-muted)";
          }}
        >
          <img
            src="https://www.google.com/favicon.ico"
            width="14"
            height="14"
            alt="Google"
          />
          Continue with Google
        </button>
      )}
    </nav>
  );
}