
import { Bell, CircleUserRound } from "lucide-react";

function Header() {
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
      </div>
    </header>
  );
}

export default Header;
