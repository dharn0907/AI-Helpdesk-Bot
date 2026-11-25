import { Bell, CircleUserRound, LogOut } from "lucide-react";
import { useNavigate } from "react-router-dom";

function Header() {
  const navigate = useNavigate();

  const handleLogout = () => {
    sessionStorage.removeItem("agent");
    navigate("/login", { replace: true });
  };

  return (
    <header className="top-header">
      <div className="header-title">
        <span className="header-eyebrow">SUPPORT CENTER</span>
        <h2>Agent Workspace</h2>
      </div>

      <div className="header-user">
        <button className="notification-button" aria-label="Notifications">
          <Bell size={20} />
        </button>

        <div className="header-avatar">
          <CircleUserRound size={24} />
        </div>

        <div className="header-user-info">
          <strong>Support Agent</strong>
          <span>Human Support</span>
        </div>

        <button
          type="button"
          onClick={handleLogout}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            padding: "10px 16px",
            marginLeft: "16px",
            background: "#dc2626",
            color: "#ffffff",
            border: "none",
            borderRadius: "8px",
            cursor: "pointer",
            fontWeight: 600
          }}
        >
          <LogOut size={18} />
          Logout
        </button>
      </div>
    </header>
  );
}

export default Header;
