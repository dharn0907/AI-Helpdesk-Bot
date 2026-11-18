
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Search, RefreshCw, Eye } from "lucide-react";

import { getTickets } from "../services/ticketApi";

function TicketList() {
  const [tickets, setTickets] = useState([]);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
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

  const filteredTickets = tickets.filter((ticket) => {
    const searchText = search.toLowerCase();

    const matchesSearch =
      ticket.ticket_id?.toLowerCase().includes(searchText) ||
      ticket.customer_message?.toLowerCase().includes(searchText) ||
      ticket.intent?.toLowerCase().includes(searchText);

    const matchesStatus =
      statusFilter === "All" || ticket.status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  return (
    <div className="ticket-list">
      <div className="dashboard-header">
        <div>
          <h1>All Tickets</h1>
          <p>View and manage customer support requests.</p>
        </div>

        <button onClick={fetchTickets} className="refresh-button">
          <RefreshCw size={16} />
          Refresh
        </button>
      </div>

      <div className="ticket-filters">
        <div className="search-box">
          <Search size={18} />
          <input
            type="text"
            placeholder="Search by ticket ID, complaint or category..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="All">All Statuses</option>
          <option value="Open">Open</option>
          <option value="In Progress">In Progress</option>
          <option value="Resolved">Resolved</option>
        </select>
      </div>

      {error && <p className="error-message">{error}</p>}

      <div className="table-container">
        {loading ? (
          <p>Loading tickets...</p>
        ) : filteredTickets.length === 0 ? (
          <p className="empty-message">No matching tickets found.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Ticket ID</th>
                <th>Customer Complaint</th>
                <th>Category</th>
                <th>Priority</th>
                <th>Status</th>
                <th>Created At</th>
                <th>Action</th>
              </tr>
            </thead>

            <tbody>
              {filteredTickets.map((ticket) => (
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
                    {new Date(ticket.created_at).toLocaleString()}
                  </td>
                  <td>
                    <Link
                      to={`/tickets/${ticket.ticket_id}`}
                      className="view-button"
                    >
                      <Eye size={15} />
                      View
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <p className="ticket-count">
        Showing {filteredTickets.length} of {tickets.length} tickets
      </p>
    </div>
  );
}

export default TicketList;
