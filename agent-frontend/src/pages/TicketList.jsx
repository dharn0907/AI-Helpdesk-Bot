
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Search, RefreshCw, Eye } from "lucide-react";

import { getTickets } from "../services/ticketApi";

const CATEGORIES = [
  "Login / Authentication",
  "Delivery / Shipping",
  "Payment / Billing",
  "Refunds / Returns",
  "Technical Issues",
  "Account Management",
  "Product / Service Questions",
  "Feature Requests",
  "Other",
];

function getCategory(ticket) {
  if (ticket.category) return ticket.category;

  const intent = (ticket.intent || "").toLowerCase().trim();

  const mapping = {
    login_issue: "Login / Authentication",
    authentication: "Login / Authentication",
    delivery_tracking: "Delivery / Shipping",
    delivery_issue: "Delivery / Shipping",
    duplicate_payment: "Payment / Billing",
    payment_issue: "Payment / Billing",
    refund_request: "Refunds / Returns",
    return_request: "Refunds / Returns",
    technical_issue: "Technical Issues",
    bug_report: "Technical Issues",
    account_issue: "Account Management",
    account_management: "Account Management",
    product_question: "Product / Service Questions",
    feature_request: "Feature Requests",
  };

  return mapping[intent] || "Other";
}

function TicketList() {
  const [tickets, setTickets] = useState([]);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  const [categoryFilter, setCategoryFilter] = useState("All");
  const [priorityFilter, setPriorityFilter] = useState("All");
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
    const searchText = search.toLowerCase().trim();
    const category = getCategory(ticket);

    const matchesSearch =
      ticket.ticket_id?.toLowerCase().includes(searchText) ||
      ticket.customer_message?.toLowerCase().includes(searchText) ||
      ticket.intent?.toLowerCase().includes(searchText) ||
      ticket.customer_email?.toLowerCase().includes(searchText) ||
      category.toLowerCase().includes(searchText);

    const matchesStatus =
      statusFilter === "All" || ticket.status === statusFilter;

    const matchesCategory =
      categoryFilter === "All" || category === categoryFilter;

    const matchesPriority =
      priorityFilter === "All" || ticket.priority === priorityFilter;

    return (
      matchesSearch &&
      matchesStatus &&
      matchesCategory &&
      matchesPriority
    );
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
            placeholder="Search ID, complaint, email, category..."
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
          <option value="Pending">Pending</option>
          <option value="Resolved">Resolved</option>
          <option value="Closed">Closed</option>
        </select>

        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
        >
          <option value="All">All Categories</option>

          {CATEGORIES.map((category) => (
            <option key={category} value={category}>
              {category}
            </option>
          ))}
        </select>

        <select
          value={priorityFilter}
          onChange={(e) => setPriorityFilter(e.target.value)}
        >
          <option value="All">All Priorities</option>
          <option value="High">High</option>
          <option value="Medium">Medium</option>
          <option value="Low">Low</option>
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

                  <td>{getCategory(ticket)}</td>

                  <td>{ticket.priority || "Medium"}</td>

                  <td>
                    <span
                      className={`status ${
                        (ticket.status || "Open")
                          .toLowerCase()
                          .replace(/\s+/g, "-")
                      }`}
                    >
                      {ticket.status || "Open"}
                    </span>
                  </td>

                  <td>
                    {ticket.created_at
                      ? new Date(ticket.created_at).toLocaleString()
                      : "—"}
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
