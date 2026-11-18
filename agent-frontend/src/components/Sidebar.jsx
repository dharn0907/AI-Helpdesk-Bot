
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Ticket,
  Headset,
  LogOut,
} from "lucide-react";

function Sidebar() {
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

        <NavLink
          to="/"
          end
          className={({ isActive }) =>
            isActive ? "nav-item active" : "nav-item"
          }
        >
          <LayoutDashboard size={19} />
          <span>Dashboard</span>
        </NavLink>

        <NavLink
          to="/tickets"
          className={({ isActive }) =>
            isActive ? "nav-item active" : "nav-item"
          }
        >
          <Ticket size={19} />
          <span>All Tickets</span>
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
