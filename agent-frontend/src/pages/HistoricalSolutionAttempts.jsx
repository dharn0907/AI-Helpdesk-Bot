import { useEffect, useMemo, useState } from "react";

const API = "http://127.0.0.1:8000";

function getAgentHeaders() {
  const agent = JSON.parse(sessionStorage.getItem("agent") || "null");
  if (!agent?.email || !agent?.company_id) {
    throw new Error("Agent session or company not found. Please log in again.");
  }
  return {
    "X-Agent-Email": agent.email,
    "X-Company-ID": String(agent.company_id),
  };
}


export default function HistoricalSolutionAttempts() {
  const [attempts, setAttempts] = useState([]);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadAttempts() {
    setLoading(true);
    setError("");

    try {
      const response = await fetch(
        `${API}/historical-solution-attempts/`,
        { headers: getAgentHeaders() }
      );

      if (!response.ok) {
        throw new Error("Failed to load historical solution attempts.");
      }

      const data = await response.json();
      setAttempts(data.attempts || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAttempts();
  }, []);

  const stats = useMemo(() => {
    return {
      total: attempts.length,
      resolved: attempts.filter(
        (a) => a.attempt_status === "resolved"
      ).length,
      failed: attempts.filter(
        (a) => a.attempt_status === "failed"
      ).length,
      ticketCreated: attempts.filter(
        (a) => a.attempt_status === "ticket_created"
      ).length,
      pending: attempts.filter(
        (a) => a.attempt_status === "pending"
      ).length,
      abandoned: attempts.filter(
        (a) => a.attempt_status === "abandoned"
      ).length,
    };
  }, [attempts]);

  const filteredAttempts = attempts.filter((attempt) => {
    const searchText = search.toLowerCase();

    const matchesSearch =
      String(attempt.customer_complaint || "")
        .toLowerCase()
        .includes(searchText) ||
      String(attempt.matched_ticket_id || "")
        .toLowerCase()
        .includes(searchText) ||
      String(attempt.created_ticket_id || "")
        .toLowerCase()
        .includes(searchText) ||
      String(attempt.customer_email || "")
        .toLowerCase()
        .includes(searchText) ||
      String(attempt.retrieved_solution || "")
        .toLowerCase()
        .includes(searchText) ||
      String(attempt.response_delivered || "")
        .toLowerCase()
        .includes(searchText) ||
      String(attempt.session_id || "")
        .toLowerCase()
        .includes(searchText);

    const matchesStatus =
      statusFilter === "all" ||
      attempt.attempt_status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  function formatDate(date) {
    if (!date) return "Unknown";

    const parsed = new Date(date);

    if (isNaN(parsed.getTime())) return "Unknown";

    return parsed.toLocaleString();
  }

  function formatSimilarity(score) {
    if (score === null || score === undefined) {
      return "Not available";
    }

    const numericScore = Number(score);

    if (isNaN(numericScore)) {
      return "Not available";
    }

    const percentage =
      numericScore <= 1
        ? numericScore * 100
        : numericScore;

    return `${percentage.toFixed(1)}%`;
  }

  function getStatusStyle(status) {
    const styles = {
      resolved: {
        background: "#dcfce7",
        color: "#166534",
      },
      failed: {
        background: "#fee2e2",
        color: "#991b1b",
      },
      ticket_created: {
        background: "#dbeafe",
        color: "#1d4ed8",
      },
      pending: {
        background: "#fef3c7",
        color: "#92400e",
      },
      abandoned: {
        background: "#e5e7eb",
        color: "#374151",
      },
    };

    return styles[status] || {
      background: "#e5e7eb",
      color: "#374151",
    };
  }

  function formatStatus(status) {
    return String(status || "unknown")
      .replace(/_/g, " ")
      .replace(/\b\w/g, (char) => char.toUpperCase());
  }

  const styles = {
    page: {
      padding: "24px",
      maxWidth: "1500px",
      margin: "0 auto",
      color: "#1f2937",
    },

    header: {
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      flexWrap: "wrap",
      gap: "16px",
      marginBottom: "24px",
    },

    title: {
      margin: 0,
      fontSize: "27px",
      fontWeight: 700,
    },

    subtitle: {
      margin: "8px 0 0",
      color: "#6b7280",
    },

    button: {
      padding: "10px 16px",
      borderRadius: "8px",
      border: "1px solid #d1d5db",
      background: "#fff",
      cursor: "pointer",
      fontWeight: 600,
    },

    statsGrid: {
      display: "grid",
      gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
      gap: "14px",
      marginBottom: "24px",
    },

    statCard: {
      background: "#fff",
      border: "1px solid #e5e7eb",
      borderRadius: "12px",
      padding: "18px",
    },

    statNumber: {
      fontSize: "28px",
      fontWeight: 700,
      marginTop: "8px",
    },

    statLabel: {
      color: "#6b7280",
      fontSize: "13px",
    },

    filters: {
      display: "flex",
      flexWrap: "wrap",
      gap: "12px",
      marginBottom: "22px",
    },

    input: {
      padding: "11px 14px",
      border: "1px solid #d1d5db",
      borderRadius: "8px",
      fontSize: "14px",
      flex: "1",
      minWidth: "220px",
      background: "#fff",
    },

    select: {
      padding: "11px 14px",
      border: "1px solid #d1d5db",
      borderRadius: "8px",
      fontSize: "14px",
      background: "#fff",
      minWidth: "180px",
    },

    card: {
      background: "#fff",
      border: "1px solid #e5e7eb",
      borderRadius: "12px",
      padding: "22px",
      marginBottom: "16px",
      boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
    },

    cardHeader: {
      display: "flex",
      justifyContent: "space-between",
      alignItems: "flex-start",
      gap: "15px",
      flexWrap: "wrap",
      marginBottom: "18px",
    },

    badge: {
      display: "inline-block",
      padding: "6px 11px",
      borderRadius: "20px",
      fontSize: "12px",
      fontWeight: 600,
      textTransform: "capitalize",
    },

    sectionLabel: {
      fontSize: "13px",
      fontWeight: 700,
      color: "#6b7280",
      marginBottom: "8px",
    },

    contentBox: {
      background: "#f9fafb",
      borderRadius: "8px",
      padding: "14px",
      marginBottom: "18px",
      lineHeight: 1.7,
      whiteSpace: "pre-wrap",
      overflowWrap: "anywhere",
    },

    solutionBox: {
      background: "#f0fdf4",
      border: "1px solid #bbf7d0",
      borderRadius: "8px",
      padding: "14px",
      marginBottom: "18px",
      lineHeight: 1.7,
      whiteSpace: "pre-wrap",
      overflowWrap: "anywhere",
    },

    responseBox: {
      background: "#eef2ff",
      border: "1px solid #c7d2fe",
      borderRadius: "8px",
      padding: "14px",
      marginBottom: "18px",
      lineHeight: 1.7,
      whiteSpace: "pre-wrap",
      overflowWrap: "anywhere",
    },

    meta: {
      display: "flex",
      flexWrap: "wrap",
      gap: "18px",
      color: "#6b7280",
      fontSize: "13px",
      marginTop: "16px",
    },

    message: {
      padding: "14px",
      borderRadius: "8px",
      marginBottom: "16px",
    },

    ticketLink: {
      fontWeight: 700,
      color: "#4f46e5",
    },
  };

  const statCards = [
    {
      label: "Abandoned",
      value: stats.abandoned,
      filter: "abandoned",
    },
    {
      label: "All Attempts",
      value: stats.total,
      filter: "all",
    },
    {
      label: "Resolved",
      value: stats.resolved,
      filter: "resolved",
    },
    {
      label: "Failed",
      value: stats.failed,
      filter: "failed",
    },
    {
      label: "Ticket Created",
      value: stats.ticketCreated,
      filter: "ticket_created",
    },
    {
      label: "Pending",
      value: stats.pending,
      filter: "pending",
    },
  ];

  return (
    <div style={styles.page}>
      <div style={styles.header}>
        <div>
          <h1 style={styles.title}>
            Historical Solution Attempts
          </h1>

          <p style={styles.subtitle}>
            Track chatbot attempts to resolve customer issues
            using previously approved solutions.
          </p>
        </div>

        <button
          style={styles.button}
          onClick={loadAttempts}
          disabled={loading}
        >
          ↻ Refresh
        </button>
      </div>

      <div style={styles.statsGrid}>
        {statCards.map((stat) => (
          <div
            key={stat.filter}
            style={{
              ...styles.statCard,
              cursor: "pointer",
              border:
                statusFilter === stat.filter
                  ? "1px solid #6366f1"
                  : "1px solid #e5e7eb",
            }}
            onClick={() => setStatusFilter(stat.filter)}
          >
            <div style={styles.statLabel}>
              {stat.label}
            </div>

            <div style={styles.statNumber}>
              {stat.value}
            </div>
          </div>
        ))}
      </div>

      {error && (
        <div
          style={{
            ...styles.message,
            background: "#fee2e2",
            color: "#991b1b",
          }}
        >
          {error}
        </div>
      )}

      <div style={styles.filters}>
        <input
          style={styles.input}
          placeholder="Search complaint, ticket, customer, solution..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />

        <select
          style={styles.select}
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="all">All attempts</option>
          <option value="resolved">Resolved</option>
          <option value="failed">Failed</option>
          <option value="ticket_created">Ticket Created</option>
          <option value="pending">Pending</option>
          <option value="abandoned">Abandoned</option>
        </select>
      </div>

      {loading ? (
        <p>Loading historical solution attempts...</p>
      ) : filteredAttempts.length === 0 ? (
        <div style={styles.card}>
          <p style={{ color: "#6b7280", margin: 0 }}>
            No historical solution attempts found.
          </p>
        </div>
      ) : (
        filteredAttempts.map((attempt) => (
          <div key={attempt.id} style={styles.card}>
            <div style={styles.cardHeader}>
              <div>
                <div style={{ fontWeight: 700, fontSize: "16px" }}>
                  Attempt #{attempt.id}
                </div>

                <div style={{ marginTop: "7px", color: "#6b7280", fontSize: "13px" }}>
                  {formatDate(attempt.created_at)}
                </div>
              </div>

              <span
                style={{
                  ...styles.badge,
                  ...getStatusStyle(attempt.attempt_status),
                }}
              >
                {formatStatus(attempt.attempt_status)}
              </span>
            </div>

            <div style={styles.sectionLabel}>
              CUSTOMER COMPLAINT
            </div>

            <div style={styles.contentBox}>
              {attempt.customer_complaint || "No complaint recorded."}
            </div>

            <div style={styles.sectionLabel}>
              MATCHED HISTORICAL TICKET
            </div>

            <div style={{ ...styles.contentBox, marginBottom: "18px" }}>
              {attempt.matched_ticket_id || "No ticket matched"}
              {"  •  "}
              Similarity: {formatSimilarity(attempt.similarity_score)}
            </div>

            <div style={styles.sectionLabel}>
              RETRIEVED HISTORICAL SOLUTION
            </div>

            <div style={styles.solutionBox}>
              {attempt.retrieved_solution || "No solution recorded."}
            </div>

            <div style={styles.sectionLabel}>
              EXACT RESPONSE DELIVERED TO CUSTOMER
            </div>

            <div style={styles.responseBox}>
              {attempt.response_delivered || "No response recorded."}
            </div>

            <div style={styles.meta}>
              <span>
                Customer: {attempt.customer_email || "Unknown"}
              </span>

              <span>
                Confirmation:{" "}
                {formatStatus(attempt.resolution_confirmation || "pending")}
              </span>

              <span>
                Session: {attempt.session_id || "Unknown"}
              </span>

              <span>
                Attempt ID: {attempt.id}
              </span>
            </div>

            {attempt.created_ticket_id && (
              <div
                style={{
                  marginTop: "16px",
                  padding: "12px",
                  background: "#eff6ff",
                  borderRadius: "8px",
                }}
              >
                <span style={styles.ticketLink}>
                  Created Support Ticket: {attempt.created_ticket_id}
                </span>
              </div>
            )}
          </div>
        ))
      )}
    </div>
  );
}