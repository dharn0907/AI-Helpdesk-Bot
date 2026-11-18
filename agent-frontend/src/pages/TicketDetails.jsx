import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  Send,
  RefreshCw,
  CheckCircle,
  XCircle,
  BookOpen,
} from "lucide-react";

import {
  getTicketById,
  updateTicket,
  reviewTicketResolution,
  getTicketResolutionReview,
} from "../services/ticketApi";

function TicketDetails() {
  const { ticketId } = useParams();

  const [ticket, setTicket] = useState(null);
  const [agentReply, setAgentReply] = useState("");
  const [status, setStatus] = useState("Open");
  const [reusableSolution, setReusableSolution] = useState("");
  const [approvalStatus, setApprovalStatus] = useState(null);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [reviewSaving, setReviewSaving] = useState(false);

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [reviewError, setReviewError] = useState("");
  const [reviewSuccess, setReviewSuccess] = useState("");

  const fetchTicket = async () => {
    try {
      setLoading(true);
      setError("");

      const data = await getTicketById(ticketId);
      const review = await getTicketResolutionReview(ticketId);

      setTicket(data);
      setAgentReply(data.agent_reply || "");
      setStatus(data.status || "Open");
      setApprovalStatus(review.approval_status);

      setReusableSolution(
        review.approval_status
          ? review.approved_solution || ""
          : data.agent_reply || ""
      );
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

  const handleResolutionReview = async (decision) => {
    if (
      decision === "yes" &&
      !reusableSolution.trim()
    ) {
      setReviewError(
        "Please enter a reusable solution before approving."
      );
      return;
    }

    const confirmation =
      decision === "yes"
        ? "Add this solution to the chatbot's approved knowledge base?"
        : "Reject this solution for future chatbot use?";

    if (!window.confirm(confirmation)) {
      return;
    }

    try {
      setReviewSaving(true);
      setReviewError("");
      setReviewSuccess("");

      const result = await reviewTicketResolution(ticketId, {
        decision: decision,
        approved_solution:
          decision === "yes" ? reusableSolution.trim() : "",
      });

      setApprovalStatus(result.approval_status);
      setReusableSolution(result.approved_solution || "");
      setReviewSuccess(result.message);
    } catch (err) {
      setReviewError(
        err.message || "Unable to save resolution review."
      );
    } finally {
      setReviewSaving(false);
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

  const canReview =
    ["Resolved", "Closed"].includes(ticket.status) &&
    Boolean(ticket.agent_reply?.trim());

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

<div className="ticket-additional-details">
  <h3>Additional Customer Information</h3>

  <p>
    <strong>Customer Email:</strong>{" "}
    {ticket.customer_email || "Not provided"}
  </p>

  
</div>

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
              <option value="Closed">Closed</option>
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

      <section className="details-card" style={{ marginTop: "24px" }}>
        <h2>
          <BookOpen
            size={20}
            style={{ verticalAlign: "middle", marginRight: "8px" }}
          />
          Reusable Solution for Chatbot
        </h2>

        <p>
          Review and edit the solution below. Only an explicitly
          approved solution will become eligible for future chatbot use.
        </p>

        {approvalStatus && (
          <div style={{ margin: "16px 0", fontWeight: 600 }}>
            {approvalStatus === "approved" ? (
              <span style={{ color: "green" }}>
                <CheckCircle size={17} style={{ verticalAlign: "middle" }} />
                {" "}Approved for chatbot use
              </span>
            ) : (
              <span style={{ color: "red" }}>
                <XCircle size={17} style={{ verticalAlign: "middle" }} />
                {" "}Rejected — excluded from chatbot knowledge
              </span>
            )}
          </div>
        )}

        <label htmlFor="reusableSolution">
          Edit reusable solution
        </label>

        <textarea
          id="reusableSolution"
          rows="7"
          value={reusableSolution}
          onChange={(e) => setReusableSolution(e.target.value)}
          placeholder="Write a reusable solution that can help other customers..."
          disabled={!canReview || reviewSaving}
        />

        {!canReview && (
          <p>
            Save an agent response and resolve or close this ticket
            before reviewing its solution.
          </p>
        )}

        {reviewError && (
          <p className="error-message">{reviewError}</p>
        )}

        {reviewSuccess && (
          <p className="success-message">{reviewSuccess}</p>
        )}

        <div
          style={{
            display: "flex",
            gap: "12px",
            flexWrap: "wrap",
            marginTop: "16px",
          }}
        >
          <button
            type="button"
            className="submit-button"
            disabled={!canReview || reviewSaving}
            onClick={() => handleResolutionReview("yes")}
          >
            <CheckCircle size={16} />
            {reviewSaving ? "Saving..." : "YES — Add to Knowledge Base"}
          </button>

          <button
            type="button"
            disabled={!canReview || reviewSaving}
            onClick={() => handleResolutionReview("no")}
            style={{
              padding: "10px 16px",
              border: "1px solid #dc2626",
              borderRadius: "6px",
              background: "white",
              color: "#dc2626",
              cursor: "pointer",
            }}
          >
            <XCircle size={16} />
            {" "}NO — Don't Add
          </button>
        </div>
      </section>
    </div>
  );
}

export default TicketDetails;
