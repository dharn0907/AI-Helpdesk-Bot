
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Ticket,
  Clock,
  CheckCircle,
  AlertCircle,
  RefreshCw,
  Settings,
} from "lucide-react";

import { getTickets } from "../services/ticketApi";

const API = "http://127.0.0.1:8000";

function Dashboard() {
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [timeoutEnabled, setTimeoutEnabled] = useState(true);
  const [timeoutHours, setTimeoutHours] = useState(24);
  const [settingsLoading, setSettingsLoading] = useState(true);
  const [settingsSaving, setSettingsSaving] = useState(false);
  const [settingsMessage, setSettingsMessage] = useState("");

  const fetchTickets = async () => {
    try {
      setLoading(true);
      setError("");

      const data = await getTickets();
      setTickets(data);
    } catch (err) {
      setError(err.message || "Unable to load tickets.");
    } finally {
      setLoading(false);
    }
  };

  const fetchTimeoutSettings = async () => {
    try {
      setSettingsLoading(true);

      const response = await fetch(`${API}/companies/current`);

      if (!response.ok) {
        throw new Error("Unable to load timeout settings.");
      }

      const data = await response.json();

      if (data.exists && data.historical_solution_timeout) {
        setTimeoutEnabled(
          data.historical_solution_timeout.enabled
        );

        setTimeoutHours(
          data.historical_solution_timeout.timeout_hours
        );
      }
    } catch (err) {
      setSettingsMessage(err.message);
    } finally {
      setSettingsLoading(false);
    }
  };

  const saveTimeoutSettings = async () => {
    if (
      !Number.isInteger(Number(timeoutHours)) ||
      Number(timeoutHours) < 1 ||
      Number(timeoutHours) > 168
    ) {
      setSettingsMessage("Timeout must be between 1 and 168 hours.");
      return;
    }

    try {
      setSettingsSaving(true);
      setSettingsMessage("");

      const response = await fetch(
        `${API}/companies/current/historical-solution-timeout`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            enabled: timeoutEnabled,
            timeout_hours: Number(timeoutHours),
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to save settings.");
      }

      setSettingsMessage("Settings saved successfully.");
    } catch (err) {
      setSettingsMessage(err.message);
    } finally {
      setSettingsSaving(false);
    }
  };

  useEffect(() => {
    fetchTickets();
    fetchTimeoutSettings();
  }, []);

  const openTickets = tickets.filter(
    (ticket) => ticket.status === "Open"
  ).length;

  const inProgressTickets = tickets.filter(
    (ticket) => ticket.status === "In Progress"
  ).length;

  const resolvedTickets = tickets.filter(
    (ticket) => ticket.status === "Resolved"
  ).length;

  const stats = [
    {
      title: "Total Tickets",
      value: tickets.length,
      icon: Ticket,
    },
    {
      title: "Open Tickets",
      value: openTickets,
      icon: AlertCircle,
    },
    {
      title: "In Progress",
      value: inProgressTickets,
      icon: Clock,
    },
    {
      title: "Resolved",
      value: resolvedTickets,
      icon: CheckCircle,
    },
  ];

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div>
          <h1>Dashboard</h1>
          <p>Welcome to your human support workspace.</p>
        </div>

        <button onClick={fetchTickets} className="refresh-button">
          <RefreshCw size={16} />
          Refresh
        </button>
      </div>

      {error && <p className="error-message">{error}</p>}

      <div className="stats-grid">
        {stats.map((stat) => {
          const Icon = stat.icon;

          return (
            <div className="stat-card" key={stat.title}>
              <div className="stat-icon">
                <Icon size={24} />
              </div>

              <div>
                <p>{stat.title}</p>
                <h2>{loading ? "..." : stat.value}</h2>
              </div>
            </div>
          );
        })}
      </div>

      {/* Historical Solution Timeout Settings */}
      <div
        style={{
          background: "var(--card-bg, #ffffff)",
          border: "1px solid var(--border-color, #e5e7eb)",
          borderRadius: "12px",
          padding: "24px",
          marginBottom: "24px",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
            marginBottom: "8px",
          }}
        >
          <Settings size={21} />
          <h2 style={{ margin: 0 }}>
            Historical Solution Timeout Settings
          </h2>
        </div>

        <p style={{ color: "#6b7280", marginBottom: "20px" }}>
          Automatically mark unanswered historical solution attempts
          as abandoned when the customer does not confirm resolution.
        </p>

        {settingsLoading ? (
          <p>Loading settings...</p>
        ) : (
          <>
            <label
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                marginBottom: "20px",
                cursor: "pointer",
              }}
            >
              <input
                type="checkbox"
                checked={timeoutEnabled}
                onChange={(e) => {
                  setTimeoutEnabled(e.target.checked);
                  setSettingsMessage("");
                }}
              />

              <span>
                Enable automatic abandonment
              </span>
            </label>

            <div style={{ marginBottom: "20px" }}>
              <label
                htmlFor="timeout-hours"
                style={{
                  display: "block",
                  marginBottom: "8px",
                  fontWeight: 600,
                }}
              >
                Abandonment timeout (hours)
              </label>

              <input
                id="timeout-hours"
                type="number"
                min="1"
                max="168"
                value={timeoutHours}
                disabled={!timeoutEnabled}
                onChange={(e) => {
                  setTimeoutHours(e.target.value);
                  setSettingsMessage("");
                }}
                style={{
                  width: "150px",
                  padding: "10px",
                  border: "1px solid #d1d5db",
                  borderRadius: "8px",
                  opacity: timeoutEnabled ? 1 : 0.5,
                }}
              />

              <p style={{ color: "#6b7280", fontSize: "13px" }}>
                Choose between 1 hour and 7 days (168 hours).
                Default: 24 hours.
              </p>
            </div>

            <button
              onClick={saveTimeoutSettings}
              disabled={settingsSaving}
              style={{
                padding: "10px 18px",
                borderRadius: "8px",
                border: "none",
                background: "#2563eb",
                color: "#ffffff",
                cursor: settingsSaving ? "wait" : "pointer",
                opacity: settingsSaving ? 0.7 : 1,
              }}
            >
              {settingsSaving ? "Saving..." : "Save Settings"}
            </button>

            {settingsMessage && (
              <p
                style={{
                  marginTop: "14px",
                  color: settingsMessage.includes("successfully")
                    ? "#16a34a"
                    : "#dc2626",
                }}
              >
                {settingsMessage}
              </p>
            )}
          </>
        )}
      </div>

      <div className="recent-tickets">
        <div className="section-header">
          <h2>Recent Tickets</h2>
          <Link to="/tickets">View All</Link>
        </div>

        {loading ? (
          <p>Loading tickets...</p>
        ) : tickets.length === 0 ? (
          <p>No tickets available.</p>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Ticket ID</th>
                  <th>Customer Complaint</th>
                  <th>Category</th>
                  <th>Priority</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>

              <tbody>
                {tickets.slice(0, 5).map((ticket) => (
                  <tr key={ticket.id}>
                    <td>{ticket.ticket_id}</td>
                    <td>{ticket.customer_message}</td>
                    <td>{ticket.intent}</td>
                    <td>{ticket.priority}</td>
                    <td>
                      <span
                        className={`status ${ticket.status
                          .toLowerCase()
                          .replace(" ", "-")}`}
                      >
                        {ticket.status}
                      </span>
                    </td>
                    <td>
                      <Link to={`/tickets/${ticket.ticket_id}`}>
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default Dashboard;
