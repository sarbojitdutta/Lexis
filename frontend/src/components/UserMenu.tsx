import { LogOut, User as UserIcon } from "lucide-react";
import  { logout } from "@/lib/auth";
import type {User} from "@/lib/auth"

interface UserMenuProps {
  user: User;
}

export default function UserMenu({ user }: UserMenuProps) {
  return (
    <div style={{
      display    : "flex",
      alignItems : "center",
      gap        : "8px",
    }}>
      {/* Avatar */}
      {user.picture ? (
        <img
          src={user.picture}
          alt={user.name}
          style={{
            width       : "28px",
            height      : "28px",
            borderRadius: "50%",
            border      : "1px solid var(--border)",
          }}
        />
      ) : (
        <div style={{
          width          : "28px",
          height         : "28px",
          borderRadius   : "50%",
          background     : "var(--bg-hover)",
          border         : "1px solid var(--border)",
          display        : "flex",
          alignItems     : "center",
          justifyContent : "center",
        }}>
          <UserIcon size={14} color="var(--text-muted)" />
        </div>
      )}

      {/* Name */}
      <span style={{
        fontSize: "13px",
        color   : "var(--text-muted)",
      }}>
        {user.name || user.email}
      </span>

      {/* Logout button */}
      <button
        onClick={logout}
        style={{
          display      : "flex",
          alignItems   : "center",
          gap          : "5px",
          padding      : "5px 10px",
          background   : "transparent",
          border       : "1px solid var(--border)",
          borderRadius : "6px",
          color        : "var(--text-muted)",
          cursor       : "pointer",
          fontSize     : "12px",
          transition   : "all 0.15s ease",
        }}
        onMouseEnter={e => {
          const el = e.currentTarget as HTMLElement;
          el.style.background   = "var(--bg-hover)";
          el.style.borderColor  = "var(--text-subtle)";
          el.style.color        = "var(--text-primary)";
        }}
        onMouseLeave={e => {
          const el = e.currentTarget as HTMLElement;
          el.style.background   = "transparent";
          el.style.borderColor  = "var(--border)";
          el.style.color        = "var(--text-muted)";
        }}
      >
        <LogOut size={12} />
        Logout
      </button>
    </div>
  );
}