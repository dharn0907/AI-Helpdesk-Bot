import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Ticket,
  Headset,
  MessageSquare,
  Database,
  Activity,
} from "lucide-react";

function Sidebar() {
  const navClass = ({ isActive }) =>
    isActive ? "nav-item active" : "nav-item";

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-icon">
          <Headset size={25} />
        </div>

        <div>
          <h2>HelpDesk AI</h2>
          <span>Agent Workspace</span>
        </div>
      </div>

      <div className="sidebar-menu">
        <p className="menu-heading">WORKSPACE</p>

        <NavLink to="/" end className={navClass}>
          <LayoutDashboard size={19} />
          <span>Dashboard</span>
        </NavLink>

        <NavLink to="/tickets" className={navClass}>
          <Ticket size={19} />
          <span>All Tickets</span>
        </NavLink>

        <NavLink to="/conversations" className={navClass}>
          <MessageSquare size={19} />
          <span>Conversations</span>
        </NavLink>

        <NavLink to="/historical-solutions" className={navClass}>
          <Database size={19} />
          <span>Historical Solutions</span>
        </NavLink>

        <NavLink
          to="/historical-solution-attempts"
          className={navClass}
        >
          <Activity size={19} />
          <span>Historical Solution Attempts</span>
        </NavLink>
      </div>

      <div className="sidebar-footer">
        <div className="agent-profile">
          <div className="agent-avatar">A</div>

          <div>
            <strong>Support Agent</strong>
            <span>Human Support Team</span>
          </div>
        </div>
      </div>
    </aside>
  );
}

export default Sidebar;