
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  Send,
  RefreshCw,
  CheckCircle,
  XCircle,
  BookOpen,
  Sparkles,
  FileText,
} from "lucide-react";

import {
  getTicketById,
  updateTicket,
  reviewTicketResolution,
  getTicketResolutionReview,
  summarizeTicket,
  getSimilarTickets,
} from "../services/ticketApi";

function TicketDetails() {
  const { ticketId } = useParams();

  const [ticket, setTicket] = useState(null);
  const [similarTickets, setSimilarTickets] = useState([]);
  const [similarLoading, setSimilarLoading] = useState(false);
  const [similarError, setSimilarError] = useState("");
  const [agentReply, setAgentReply] = useState("");
  const [status, setStatus] = useState("Open");
  const [reusableSolution, setReusableSolution] = useState("");
  const [approvalStatus, setApprovalStatus] = useState(null);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [reviewSaving, setReviewSaving] = useState(false);

  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryResult, setSummaryResult] = useState(null);
  const [summaryError, setSummaryError] = useState("");

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

      // Fetch similar tickets
      try {
        setSimilarLoading(true);
        setSimilarError("");

        const similarData = await getSimilarTickets(ticketId);

        setSimilarTickets(
          similarData.similar_tickets || []
        );
      } catch (similarErr) {
        setSimilarError(
          similarErr.message || "Unable to load similar tickets."
        );
      } finally {
        setSimilarLoading(false);
      }

    } catch (err) {
      setError(err.message || "Unable to load ticket.");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    fetchTicket();
  }, [ticketId]);

  const handleSummarize = async (mode) => {
    try {
      setSummaryLoading(true);
      setSummaryError("");
      setSummaryResult(null);

      const result = await summarizeTicket(ticketId, mode);
      setSummaryResult(result);
    } catch (err) {
      setSummaryError(
        err.message || "Unable to summarize this ticket."
      );
    } finally {
      setSummaryLoading(false);
    }
  };

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
          {/* Customer Complaint */}
          <h2>Customer Complaint</h2>

          <p className="complaint-text">
            {ticket.customer_message}
          </p>
          

          {/* Additional Customer Information */}
          <div className="ticket-additional-details">
            <h3>Additional Customer Information</h3>

            <p>
              <strong>Customer Email:</strong>{" "}
              {ticket.customer_email || "Not provided"}
            </p>

            {ticket.additional_details?.trim() && (
              <div style={{ marginTop: "12px" }}>
                <strong>
                  Details provided during conversation:
                </strong>

                <p
                  style={{
                    whiteSpace: "pre-wrap",
                    lineHeight: "1.7",
                    marginTop: "8px",
                  }}
                >
                  {ticket.additional_details}
                </p>
              </div>
            )}
          </div>
          {/* Similar Tickets */}
          <div
            style={{
              marginTop: "24px",
              padding: "18px",
              background: "#f8fafc",
              border: "1px solid #e2e8f0",
              borderRadius: "10px",
            }}
          >
            <h3 style={{ marginTop: 0 }}>
              🔗 Similar Tickets ({similarTickets.length})
            </h3>

            <p style={{ color: "#64748b", fontSize: "14px" }}>
              Tickets reporting similar issues that may be handled together.
            </p>

            {similarLoading && <p>Searching for similar tickets...</p>}

            {similarError && (
              <p style={{ color: "#dc2626" }}>{similarError}</p>
            )}

            {!similarLoading &&
              !similarError &&
              similarTickets.length === 0 && (
                <p>No similar tickets found.</p>
              )}

            {similarTickets.map((similar) => (
              <div
                key={similar.ticket_id}
                style={{
                  padding: "12px",
                  marginTop: "10px",
                  background: "white",
                  border: "1px solid #e2e8f0",
                  borderRadius: "8px",
                }}
              >
                <strong>{similar.ticket_id}</strong>

                <span
                  style={{
                    marginLeft: "10px",
                    color: "#4f46e5",
                    fontWeight: "600",
                  }}
                >
                  {similar.similarity_percent}% similar
                </span>

                <p style={{ margin: "8px 0" }}>
                  {similar.customer_message}
                </p>

                {similar.agent_reply && (
                  <div
                    style={{
                      marginTop: "10px",
                      padding: "12px",
                      background: "#f0fdf4",
                      border: "1px solid #bbf7d0",
                      borderRadius: "8px",
                    }}
                  >
                    <strong style={{ color: "#166534" }}>
                      💡 Agent's Previous Solution
                    </strong>

                    <p
                      style={{
                        margin: "8px 0 0",
                        whiteSpace: "pre-wrap",
                      }}
                    >
                      {similar.agent_reply}
                    </p>
                  </div>
                )}

                <Link to={`/tickets/${similar.ticket_id}`}>
                  View ticket →
                </Link>
              </div>
            ))}
          </div>

          {/* AI Ticket Summarization */}
          <div
            style={{
              marginTop: "24px",
              padding: "18px",
              background: "#f8fafc",
              border: "1px solid #e2e8f0",
              borderRadius: "10px",
            }}
          >
            <h3
              style={{
                marginTop: 0,
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              <Sparkles size={19} />
              AI Ticket Summarization
            </h3>

            <p style={{ color: "#64748b", fontSize: "14px" }}>
              Generate an AI summary to quickly understand the
              customer's issue. The original complaint will not
              be modified.
            </p>

            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: "10px",
                marginTop: "14px",
              }}
            >
              <button
                type="button"
                onClick={() => handleSummarize("normal")}
                disabled={summaryLoading}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  padding: "10px 15px",
                  border: "none",
                  borderRadius: "7px",
                  background: "#4f46e5",
                  color: "white",
                  cursor: summaryLoading
                    ? "not-allowed"
                    : "pointer",
                  opacity: summaryLoading ? 0.6 : 1,
                }}
              >
                <FileText size={16} />
                Normal Summary
              </button>

              <button
                type="button"
                onClick={() => handleSummarize("fields")}
                disabled={summaryLoading}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  padding: "10px 15px",
                  border: "1px solid #4f46e5",
                  borderRadius: "7px",
                  background: "white",
                  color: "#4f46e5",
                  cursor: summaryLoading
                    ? "not-allowed"
                    : "pointer",
                  opacity: summaryLoading ? 0.6 : 1,
                }}
              >
                <Sparkles size={16} />
                Summarize into Fields
              </button>
            </div>

            {summaryLoading && (
              <p
                style={{
                  marginTop: "16px",
                  color: "#4f46e5",
                }}
              >
                AI is analyzing the ticket...
              </p>
            )}

            {summaryError && (
              <p
                style={{
                  marginTop: "16px",
                  color: "#dc2626",
                }}
              >
                {summaryError}
              </p>
            )}

            {summaryResult && (
              <div
                style={{
                  marginTop: "18px",
                  padding: "16px",
                  background: "white",
                  border: "1px solid #cbd5e1",
                  borderRadius: "8px",
                }}
              >
                <h4 style={{ marginTop: 0 }}>
                  {summaryResult.mode === "normal"
                    ? "Ticket Summary"
                    : "Extracted Information"}
                </h4>

                {summaryResult.mode === "normal" && (
                  <p
                    style={{
                      lineHeight: 1.7,
                      whiteSpace: "pre-wrap",
                      marginBottom: 0,
                    }}
                  >
                    {summaryResult.summary}
                  </p>
                )}

                {summaryResult.mode === "fields" && (
                  <>
                    {Object.keys(
                      summaryResult.fields || {}
                    ).length === 0 ? (
                      <p>
                        No structured information could be
                        extracted.
                      </p>
                    ) : (
                      <div>
                        {Object.entries(
                          summaryResult.fields || {}
                        ).map(([field, value]) => (
                          <div
                            key={field}
                            style={{
                              padding: "10px 0",
                              borderBottom:
                                "1px solid #e5e7eb",
                            }}
                          >
                            <strong
                              style={{
                                display: "block",
                                marginBottom: "5px",
                                color: "#374151",
                              }}
                            >
                              {field}
                            </strong>

                            <span style={{ lineHeight: 1.6 }}>
                              {typeof value === "object"
                                ? JSON.stringify(value, null, 2)
                                : String(value)}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </div>
            )}
          </div>

          {/* Ticket Metadata */}
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
                {new Date(
                  ticket.created_at
                ).toLocaleString()}
              </strong>
            </div>

            <div>
              <span>Session ID</span>
              <strong>{ticket.session_id}</strong>
            </div>
          </div>
        </section>

        {/* Agent Response */}
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
              onChange={(e) =>
                setAgentReply(e.target.value)
              }
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

            {error && (
              <p className="error-message">{error}</p>
            )}

            {success && (
              <p className="success-message">{success}</p>
            )}

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

      {/* Reusable Solution for Chatbot */}
      <section
        className="details-card"
        style={{ marginTop: "24px" }}
      >
        <h2>
          <BookOpen
            size={20}
            style={{
              verticalAlign: "middle",
              marginRight: "8px",
            }}
          />
          Reusable Solution for Chatbot
        </h2>

        <p>
          Review and edit the solution below. Only an explicitly
          approved solution will become eligible for future
          chatbot use.
        </p>

        {approvalStatus && (
          <div style={{ margin: "16px 0", fontWeight: 600 }}>
            {approvalStatus === "approved" ? (
              <span style={{ color: "green" }}>
                <CheckCircle
                  size={17}
                  style={{ verticalAlign: "middle" }}
                />
                {" "}Approved for chatbot use
              </span>
            ) : (
              <span style={{ color: "red" }}>
                <XCircle
                  size={17}
                  style={{ verticalAlign: "middle" }}
                />
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
          onChange={(e) =>
            setReusableSolution(e.target.value)
          }
          placeholder="Write a reusable solution that can help other customers..."
          disabled={!canReview || reviewSaving}
        />

        {!canReview && (
          <p>
            Save an agent response and resolve or close this
            ticket before reviewing its solution.
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
            onClick={() =>
              handleResolutionReview("yes")
            }
          >
            <CheckCircle size={16} />
            {reviewSaving
              ? "Saving..."
              : "YES — Add to Knowledge Base"}
          </button>

          <button
            type="button"
            disabled={!canReview || reviewSaving}
            onClick={() =>
              handleResolutionReview("no")
            }
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
