import { useEffect, useState } from "react";
import "./Conversations.css";

const API = "http://127.0.0.1:8000";

function formatDate(date) {
  if (!date) return "—";

  try {
    return new Date(date).toLocaleString();
  } catch {
    return "—";
  }
}

export default function Conversations() {
  const [conversations, setConversations] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [historicalSolutions, setHistoricalSolutions] = useState([]);

  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);

  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  // Solution editing states
  const [editingTicketId, setEditingTicketId] = useState(null);
  const [editedSolution, setEditedSolution] = useState("");
  const [savingTicketId, setSavingTicketId] = useState(null);
  const [deletingTicketId, setDeletingTicketId] = useState(null);

  useEffect(() => {
    loadConversations();
  }, []);

  async function loadConversations() {
    try {
      setLoading(true);
      setError("");
      setSuccessMessage("");

      const response = await fetch(`${API}/conversations/`);

      if (!response.ok) {
        throw new Error("Failed to load conversations");
      }

      const data = await response.json();
      setConversations(data);

      if (data.length > 0) {
        await loadConversation(data[0].id);
      } else {
        setSelectedId(null);
        setMessages([]);
        setHistoricalSolutions([]);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadConversation(id) {
    setSelectedId(id);
    setMessages([]);
    setHistoricalSolutions([]);
    setEditingTicketId(null);
    setEditedSolution("");
    setError("");
    setSuccessMessage("");
    setDetailLoading(true);

    try {
      const response = await fetch(`${API}/conversations/${id}`);

      if (!response.ok) {
        throw new Error("Failed to load conversation details");
      }

      const data = await response.json();

      setMessages(data.messages || []);
      setHistoricalSolutions(data.historical_solutions || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setDetailLoading(false);
    }
  }

  function startEditing(solution) {
    setEditingTicketId(solution.ticket_id);
    setEditedSolution(solution.approved_solution || "");
    setError("");
    setSuccessMessage("");
  }

  function cancelEditing() {
    setEditingTicketId(null);
    setEditedSolution("");
  }

  async function saveSolution(ticketId) {
    const trimmedSolution = editedSolution.trim();

    if (!trimmedSolution) {
      setError("Solution cannot be empty.");
      return;
    }

    try {
      setSavingTicketId(ticketId);
      setError("");
      setSuccessMessage("");

      const response = await fetch(
        `${API}/conversations/${selectedId}/historical-solutions/${encodeURIComponent(
          ticketId
        )}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            approved_solution: trimmedSolution,
          }),
        }
      );

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          data.detail || "Failed to save historical solution"
        );
      }

      setHistoricalSolutions((previous) =>
        previous.map((solution) =>
          String(solution.ticket_id) === String(ticketId)
            ? {
                ...solution,
                approved_solution: trimmedSolution,
              }
            : solution
        )
      );

      setEditingTicketId(null);
      setEditedSolution("");

      setSuccessMessage(
        `Solution for ${ticketId} updated successfully.`
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingTicketId(null);
    }
  }

  async function deleteSolution(ticketId) {
    const confirmed = window.confirm(
      `Are you sure you want to delete the approved solution for ${ticketId}?\n\n` +
        "This will remove it from the reusable historical solutions database. " +
        "The chatbot will no longer be able to retrieve this approved solution."
    );

    if (!confirmed) return;

    try {
      setDeletingTicketId(ticketId);
      setError("");
      setSuccessMessage("");

      const response = await fetch(
        `${API}/conversations/${selectedId}/historical-solutions/${encodeURIComponent(
          ticketId
        )}`,
        {
          method: "DELETE",
        }
      );

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          data.detail || "Failed to delete historical solution"
        );
      }

      setHistoricalSolutions((previous) =>
        previous.filter(
          (solution) =>
            String(solution.ticket_id) !== String(ticketId)
        )
      );

      if (String(editingTicketId) === String(ticketId)) {
        cancelEditing();
      }

      setSuccessMessage(
        `Approved solution ${ticketId} deleted successfully.`
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setDeletingTicketId(null);
    }
  }

  const filteredConversations = conversations.filter(
    (conversation) => {
      const searchText = search.toLowerCase();

      return (
        String(conversation.customer_id || "")
          .toLowerCase()
          .includes(searchText) ||
        String(conversation.customer_email || "")
          .toLowerCase()
          .includes(searchText) ||
        String(conversation.session_id || "")
          .toLowerCase()
          .includes(searchText) ||
        String(conversation.last_message || "")
          .toLowerCase()
          .includes(searchText)
      );
    }
  );

  return (
    <div className="conversations-page">
      <div className="conversations-heading">
        <div>
          <h1>Conversations</h1>
          <p>Monitor customer conversations with your AI assistant.</p>
        </div>

        <button
          className="conversation-refresh"
          onClick={loadConversations}
          disabled={loading}
        >
          ↻ Refresh
        </button>
      </div>

      {error && (
        <div className="conversation-error">
          {error}
          <button
            onClick={() => setError("")}
            style={{
              marginLeft: "12px",
              border: "none",
              background: "transparent",
              cursor: "pointer",
              color: "inherit",
            }}
          >
            ✕
          </button>
        </div>
      )}

      {successMessage && (
        <div
          style={{
            background: "#e8f7ed",
            color: "#18763a",
            padding: "12px 16px",
            borderRadius: "8px",
            marginBottom: "16px",
            fontSize: "14px",
          }}
        >
          {successMessage}
        </div>
      )}

      <div className="conversation-workspace">
        {/* LEFT PANEL */}
        <div className="conversation-list-panel">
          <div className="conversation-list-header">
            <h3>All Conversations</h3>

            <span className="conversation-count">
              {conversations.length}
            </span>
          </div>

          <input
            className="conversation-search"
            type="text"
            placeholder="Search conversations..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />

          <div className="conversation-list">
            {loading ? (
              <p className="conversation-empty">
                Loading conversations...
              </p>
            ) : filteredConversations.length === 0 ? (
              <p className="conversation-empty">
                No conversations found.
              </p>
            ) : (
              filteredConversations.map((conversation) => (
                <div
                  key={conversation.id}
                  className={`conversation-item ${
                    selectedId === conversation.id ? "selected" : ""
                  }`}
                  onClick={() => loadConversation(conversation.id)}
                >
                  <div className="conversation-avatar">
                    {(conversation.customer_email || "C")
                      .charAt(0)
                      .toUpperCase()}
                  </div>

                  <div className="conversation-item-content">
                    <div className="conversation-item-top">
                      <strong>
                        {conversation.customer_email ||
                          `Customer ${conversation.id}`}
                      </strong>

                      <span className="conversation-date">
                        {conversation.last_activity
                          ? new Date(
                              conversation.last_activity
                            ).toLocaleDateString()
                          : ""}
                      </span>
                    </div>

                    <p className="conversation-preview">
                      {conversation.last_message || "No messages yet"}
                    </p>

                    <span className="conversation-status">
                      {conversation.status}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* RIGHT PANEL */}
        <div className="conversation-chat-panel">
          {!selectedId ? (
            <div className="conversation-empty-detail">
              <h3>Select a conversation</h3>
              <p>
                Select a customer conversation to view its transcript.
              </p>
            </div>
          ) : (
            <>
              <div className="conversation-chat-header">
                <div>
                  <h3>Conversation #{selectedId}</h3>

                  <p>
                    Session:{" "}
                    {
                      conversations.find(
                        (c) => c.id === selectedId
                      )?.session_id
                    }
                  </p>
                </div>

                <span className="conversation-status">
                  {
                    conversations.find(
                      (c) => c.id === selectedId
                    )?.status || "Unknown"
                  }
                </span>
              </div>

              {/* CONVERSATION TRANSCRIPT */}
              <div className="conversation-messages">
                {detailLoading ? (
                  <p className="conversation-empty">
                    Loading messages...
                  </p>
                ) : messages.length === 0 ? (
                  <p className="conversation-empty">
                    No messages available.
                  </p>
                ) : (
                  messages.map((message) => (
                    <div
                      key={message.id}
                      className={`message-row ${
                        message.sender === "customer"
                          ? "customer-message-row"
                          : "bot-message-row"
                      }`}
                    >
                      <div className="message-content">
                        <span className="message-sender">
                          {message.sender === "customer"
                            ? "Customer"
                            : "AI Assistant"}
                        </span>

                        <div
                          className={`message-bubble ${
                            message.sender === "customer"
                              ? "customer-bubble"
                              : "bot-bubble"
                          }`}
                        >
                          {message.content}
                        </div>

                        <span className="message-time">
                          {formatDate(message.timestamp)}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>

              {/* HISTORICAL APPROVED SOLUTIONS */}
              {!detailLoading && (
                <div
                  style={{
                    padding: "20px",
                    borderTop: "1px solid #e5e7eb",
                    background: "#f9fafb",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      flexWrap: "wrap",
                      gap: "10px",
                      marginBottom: "16px",
                    }}
                  >
                    <div>
                      <h3
                        style={{
                          margin: 0,
                          fontSize: "17px",
                          fontWeight: 700,
                        }}
                      >
                        Approved Historical Solutions
                      </h3>

                      <p
                        style={{
                          margin: "5px 0 0",
                          fontSize: "13px",
                          color: "#6b7280",
                        }}
                      >
                        Manage solutions that the chatbot can reuse.
                      </p>
                    </div>

                    <span
                      style={{
                        padding: "5px 10px",
                        borderRadius: "20px",
                        background: "#e5e7eb",
                        color: "#374151",
                        fontSize: "13px",
                        fontWeight: 600,
                      }}
                    >
                      {historicalSolutions.length} solution
                      {historicalSolutions.length !== 1 ? "s" : ""}
                    </span>
                  </div>

                  {historicalSolutions.length === 0 ? (
                    <div
                      style={{
                        padding: "20px",
                        textAlign: "center",
                        background: "#ffffff",
                        border: "1px solid #e5e7eb",
                        borderRadius: "10px",
                        color: "#6b7280",
                        fontSize: "14px",
                      }}
                    >
                      No approved historical solutions are linked to
                      this conversation.
                    </div>
                  ) : (
                    <div
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        gap: "14px",
                      }}
                    >
                      {historicalSolutions.map((solution) => {
                        const ticketId = solution.ticket_id;
                        const isEditing =
                          String(editingTicketId) ===
                          String(ticketId);
                        const isSaving =
                          String(savingTicketId) ===
                          String(ticketId);
                        const isDeleting =
                          String(deletingTicketId) ===
                          String(ticketId);

                        return (
                          <div
                            key={ticketId}
                            style={{
                              background: "#ffffff",
                              border: "1px solid #e5e7eb",
                              borderRadius: "10px",
                              padding: "16px",
                              boxShadow:
                                "0 1px 2px rgba(0,0,0,0.04)",
                            }}
                          >
                            {/* CARD HEADER */}
                            <div
                              style={{
                                display: "flex",
                                justifyContent: "space-between",
                                alignItems: "flex-start",
                                flexWrap: "wrap",
                                gap: "10px",
                                marginBottom: "12px",
                              }}
                            >
                              <div>
                                <div
                                  style={{
                                    display: "flex",
                                    gap: "8px",
                                    alignItems: "center",
                                    flexWrap: "wrap",
                                  }}
                                >
                                  <strong
                                    style={{
                                      fontSize: "14px",
                                      color: "#111827",
                                    }}
                                  >
                                    {ticketId}
                                  </strong>

                                  <span
                                    style={{
                                      background: "#dcfce7",
                                      color: "#166534",
                                      borderRadius: "20px",
                                      padding: "3px 8px",
                                      fontSize: "11px",
                                      fontWeight: 600,
                                    }}
                                  >
                                    APPROVED
                                  </span>
                                </div>

                                {solution.intent && (
                                  <span
                                    style={{
                                      display: "inline-block",
                                      marginTop: "6px",
                                      fontSize: "12px",
                                      color: "#6b7280",
                                    }}
                                  >
                                    Intent: {solution.intent}
                                  </span>
                                )}
                              </div>

                              {!isEditing && (
                                <div
                                  style={{
                                    display: "flex",
                                    gap: "8px",
                                  }}
                                >
                                  <button
                                    onClick={() =>
                                      startEditing(solution)
                                    }
                                    disabled={isDeleting}
                                    style={{
                                      padding: "7px 12px",
                                      border: "1px solid #d1d5db",
                                      background: "#ffffff",
                                      color: "#374151",
                                      borderRadius: "6px",
                                      cursor: isDeleting
                                        ? "not-allowed"
                                        : "pointer",
                                      fontSize: "13px",
                                      fontWeight: 500,
                                    }}
                                  >
                                    ✎ Edit
                                  </button>

                                  <button
                                    onClick={() =>
                                      deleteSolution(ticketId)
                                    }
                                    disabled={
                                      isDeleting || isSaving
                                    }
                                    style={{
                                      padding: "7px 12px",
                                      border: "1px solid #fecaca",
                                      background: "#fff1f2",
                                      color: "#dc2626",
                                      borderRadius: "6px",
                                      cursor:
                                        isDeleting || isSaving
                                          ? "not-allowed"
                                          : "pointer",
                                      fontSize: "13px",
                                      fontWeight: 500,
                                    }}
                                  >
                                    {isDeleting
                                      ? "Deleting..."
                                      : "🗑 Delete"}
                                  </button>
                                </div>
                              )}
                            </div>

                            {/* ORIGINAL COMPLAINT */}
                            <div style={{ marginBottom: "12px" }}>
                              <label
                                style={{
                                  display: "block",
                                  fontSize: "12px",
                                  fontWeight: 600,
                                  color: "#6b7280",
                                  marginBottom: "5px",
                                }}
                              >
                                Original Customer Complaint
                              </label>

                              <div
                                style={{
                                  padding: "10px",
                                  borderRadius: "7px",
                                  background: "#f3f4f6",
                                  color: "#374151",
                                  fontSize: "13px",
                                  lineHeight: 1.6,
                                  whiteSpace: "pre-wrap",
                                }}
                              >
                                {solution.complaint ||
                                  "Complaint not available."}
                              </div>
                            </div>

                            {/* APPROVED SOLUTION */}
                            <div>
                              <label
                                style={{
                                  display: "block",
                                  fontSize: "12px",
                                  fontWeight: 600,
                                  color: "#6b7280",
                                  marginBottom: "5px",
                                }}
                              >
                                Approved Solution
                              </label>

                              {isEditing ? (
                                <>
                                  <textarea
                                    value={editedSolution}
                                    onChange={(e) =>
                                      setEditedSolution(
                                        e.target.value
                                      )
                                    }
                                    rows={5}
                                    disabled={isSaving}
                                    style={{
                                      width: "100%",
                                      boxSizing: "border-box",
                                      padding: "12px",
                                      border: "1px solid #93c5fd",
                                      borderRadius: "8px",
                                      fontSize: "14px",
                                      lineHeight: 1.6,
                                      resize: "vertical",
                                      outline: "none",
                                      fontFamily: "inherit",
                                      background: "#ffffff",
                                    }}
                                  />

                                  <div
                                    style={{
                                      display: "flex",
                                      justifyContent: "flex-end",
                                      gap: "8px",
                                      marginTop: "10px",
                                    }}
                                  >
                                    <button
                                      onClick={cancelEditing}
                                      disabled={isSaving}
                                      style={{
                                        padding: "8px 14px",
                                        border: "1px solid #d1d5db",
                                        borderRadius: "6px",
                                        background: "#ffffff",
                                        cursor: "pointer",
                                        fontSize: "13px",
                                      }}
                                    >
                                      Cancel
                                    </button>

                                    <button
                                      onClick={() =>
                                        saveSolution(ticketId)
                                      }
                                      disabled={
                                        isSaving ||
                                        !editedSolution.trim()
                                      }
                                      style={{
                                        padding: "8px 14px",
                                        border: "none",
                                        borderRadius: "6px",
                                        background: isSaving
                                          ? "#93c5fd"
                                          : "#2563eb",
                                        color: "#ffffff",
                                        cursor: isSaving
                                          ? "not-allowed"
                                          : "pointer",
                                        fontSize: "13px",
                                        fontWeight: 600,
                                      }}
                                    >
                                      {isSaving
                                        ? "Saving..."
                                        : "Save Changes"}
                                    </button>
                                  </div>
                                </>
                              ) : (
                                <div
                                  style={{
                                    padding: "12px",
                                    borderRadius: "7px",
                                    background: "#f0fdf4",
                                    border: "1px solid #dcfce7",
                                    color: "#166534",
                                    fontSize: "14px",
                                    lineHeight: 1.7,
                                    whiteSpace: "pre-wrap",
                                    overflowWrap: "anywhere",
                                  }}
                                >
                                  {solution.approved_solution ||
                                    "No solution content."}
                                </div>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}

              <div className="conversation-footer">
                Conversation transcript is read-only. Approved
                historical solutions can be edited or deleted above.
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}