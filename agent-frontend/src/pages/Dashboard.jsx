
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Ticket,
  Clock,
  CheckCircle,
  AlertCircle,
  RefreshCw,
} from "lucide-react";

import { getTickets } from "../services/ticketApi";

function Dashboard() {
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

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

  useEffect(() => {
    fetchTickets();
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
                      <span className={`status ${ticket.status.toLowerCase().replace(" ", "-")}`}>
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
