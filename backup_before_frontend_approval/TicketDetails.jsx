
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Send, RefreshCw } from "lucide-react";

import {
  getTicketById,
  updateTicket,
} from "../services/ticketApi";

function TicketDetails() {
  const { ticketId } = useParams();

  const [ticket, setTicket] = useState(null);
  const [agentReply, setAgentReply] = useState("");
  const [status, setStatus] = useState("Open");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const fetchTicket = async () => {
    try {
      setLoading(true);
      setError("");

      const data = await getTicketById(ticketId);

      setTicket(data);
      setAgentReply(data.agent_reply || "");
      setStatus(data.status || "Open");
    } catch (err) {
      setError(err.message || "Unable to load ticket.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTicket();
  }, [ticketId]);

  const handleUpdate = async (e) => {
    e.preventDefault();

    if (!agentReply.trim()) {
      setError("Please enter a response before submitting.");
      return;
    }

    try {
      setSaving(true);
      setError("");
      setSuccess("");

      await updateTicket(ticketId, {
        agent_reply: agentReply,
        status: status,
      });

      setSuccess("Ticket updated successfully!");

      await fetchTicket();
    } catch (err) {
      setError(err.message || "Unable to update ticket.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="page-loading">Loading ticket...</div>;
  }

  if (!ticket) {
    return (
      <div className="page-loading">
        <p>{error || "Ticket not found."}</p>
        <Link to="/tickets">Back to tickets</Link>
      </div>
    );
  }

  return (
    <div className="ticket-details">
      <Link to="/tickets" className="back-link">
        <ArrowLeft size={17} />
        Back to Tickets
      </Link>

      <div className="dashboard-header">
        <div>
          <h1>Ticket Details</h1>
          <p>Ticket ID: {ticket.ticket_id}</p>
        </div>

        <button onClick={fetchTicket} className="refresh-button">
          <RefreshCw size={16} />
          Refresh
        </button>
      </div>

      <div className="details-grid">
        <section className="details-card">
          <h2>Customer Complaint</h2>

          <p className="complaint-text">
            {ticket.customer_message}
          </p>

          <div className="ticket-metadata">
            <div>
              <span>Category</span>
              <strong>{ticket.intent}</strong>
            </div>

            <div>
              <span>Priority</span>
              <strong>{ticket.priority}</strong>
            </div>

            <div>
              <span>Status</span>
              <strong>{ticket.status}</strong>
            </div>

            <div>
              <span>Created At</span>
              <strong>
                {new Date(ticket.created_at).toLocaleString()}
              </strong>
            </div>

            <div>
              <span>Session ID</span>
              <strong>{ticket.session_id}</strong>
            </div>
          </div>
        </section>

        <section className="details-card response-card">
          <h2>Agent Response</h2>

          {ticket.agent_reply && (
            <div className="previous-reply">
              <span>Previous response</span>
              <p>{ticket.agent_reply}</p>
            </div>
          )}

          <form onSubmit={handleUpdate}>
            <label htmlFor="agentReply">
              Write your response
            </label>

            <textarea
              id="agentReply"
              rows="6"
              placeholder="Type your response to the customer..."
              value={agentReply}
              onChange={(e) => setAgentReply(e.target.value)}
            />

            <label htmlFor="ticketStatus">
              Update ticket status
            </label>

            <select
              id="ticketStatus"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              <option value="Open">Open</option>
              <option value="In Progress">In Progress</option>
              <option value="Resolved">Resolved</option>
            </select>

            {error && <p className="error-message">{error}</p>}
            {success && <p className="success-message">{success}</p>}

            <button
              type="submit"
              className="submit-button"
              disabled={saving}
            >
              <Send size={16} />
              {saving ? "Saving..." : "Save Response"}
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}

export default TicketDetails;
