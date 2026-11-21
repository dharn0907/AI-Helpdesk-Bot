import { useEffect, useMemo, useState } from "react";

const API = "http://127.0.0.1:8000";

export default function HistoricalSolutions() {
  const [solutions, setSolutions] = useState([]);
  const [search, setSearch] = useState("");
  const [intentFilter, setIntentFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editingId, setEditingId] = useState(null);
  const [draft, setDraft] = useState("");
  const [savingId, setSavingId] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [notice, setNotice] = useState("");

  async function loadSolutions() {
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API}/historical-solutions/`);

      if (!response.ok) {
        throw new Error("Failed to load historical solutions.");
      }

      const data = await response.json();
      setSolutions(data.solutions || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadSolutions();
  }, []);

  const intents = useMemo(() => {
    return [
      ...new Set(
        solutions
          .map((solution) => solution.intent)
          .filter(Boolean)
      ),
    ].sort();
  }, [solutions]);

  const filteredSolutions = solutions.filter((solution) => {
    const searchText = search.toLowerCase();

    const matchesSearch =
      String(solution.ticket_id || "")
        .toLowerCase()
        .includes(searchText) ||
      String(solution.complaint || "")
        .toLowerCase()
        .includes(searchText) ||
      String(solution.approved_solution || "")
        .toLowerCase()
        .includes(searchText) ||
      String(solution.customer_email || "")
        .toLowerCase()
        .includes(searchText);

    const matchesIntent =
      intentFilter === "all" ||
      solution.intent === intentFilter;

    return matchesSearch && matchesIntent;
  });

  function startEditing(solution) {
    setEditingId(solution.ticket_id);
    setDraft(solution.approved_solution || "");
    setNotice("");
  }

  function cancelEditing() {
    setEditingId(null);
    setDraft("");
  }

  async function saveSolution(ticketId) {
    if (!draft.trim()) {
      setError("Solution cannot be empty.");
      return;
    }

    setSavingId(ticketId);
    setError("");
    setNotice("");

    try {
      const response = await fetch(
        `${API}/historical-solutions/${encodeURIComponent(ticketId)}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            approved_solution: draft.trim(),
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Failed to update solution."
        );
      }

      setSolutions((previous) =>
        previous.map((solution) =>
          solution.ticket_id === ticketId
            ? {
                ...solution,
                approved_solution: data.approved_solution,
              }
            : solution
        )
      );

      setEditingId(null);
      setDraft("");
      setNotice(`Solution ${ticketId} updated successfully.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingId(null);
    }
  }

  async function deleteSolution(ticketId) {
    const confirmed = window.confirm(
      `Delete the approved historical solution for ${ticketId}?\n\nThis will remove it from the chatbot's reusable historical solutions. The original ticket will not be deleted.`
    );

    if (!confirmed) return;

    setDeletingId(ticketId);
    setError("");
    setNotice("");

    try {
      const response = await fetch(
        `${API}/historical-solutions/${encodeURIComponent(ticketId)}`,
        {
          method: "DELETE",
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Failed to delete solution."
        );
      }

      setSolutions((previous) =>
        previous.filter(
          (solution) => solution.ticket_id !== ticketId
        )
      );

      if (editingId === ticketId) {
        cancelEditing();
      }

      setNotice(`Solution ${ticketId} deleted successfully.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setDeletingId(null);
    }
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
    stats: {
      background: "#fff",
      border: "1px solid #e5e7eb",
      borderRadius: "12px",
      padding: "20px",
      marginBottom: "22px",
      width: "220px",
    },
    statNumber: {
      fontSize: "30px",
      fontWeight: 700,
      margin: "8px 0",
      color: "#4f46e5",
    },
    statLabel: {
      color: "#6b7280",
      fontSize: "14px",
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
    ticket: {
      fontWeight: 700,
      fontSize: "15px",
      color: "#4f46e5",
    },
    badge: {
      display: "inline-block",
      padding: "5px 10px",
      background: "#dcfce7",
      color: "#166534",
      borderRadius: "20px",
      fontSize: "12px",
      fontWeight: 600,
    },
    sectionLabel: {
      fontSize: "13px",
      fontWeight: 700,
      color: "#6b7280",
      marginBottom: "8px",
    },
    complaint: {
      background: "#f9fafb",
      borderRadius: "8px",
      padding: "14px",
      marginBottom: "18px",
      lineHeight: 1.6,
      whiteSpace: "pre-wrap",
    },
    solution: {
      background: "#f0fdf4",
      border: "1px solid #bbf7d0",
      borderRadius: "8px",
      padding: "14px",
      lineHeight: 1.7,
      whiteSpace: "pre-wrap",
      overflowWrap: "anywhere",
    },
    textarea: {
      width: "100%",
      minHeight: "140px",
      padding: "13px",
      border: "1px solid #a5b4fc",
      borderRadius: "8px",
      fontSize: "14px",
      lineHeight: 1.6,
      resize: "vertical",
      boxSizing: "border-box",
    },
    meta: {
      display: "flex",
      flexWrap: "wrap",
      gap: "18px",
      color: "#6b7280",
      fontSize: "13px",
      marginTop: "16px",
    },
    actions: {
      display: "flex",
      flexWrap: "wrap",
      gap: "9px",
      marginTop: "18px",
    },
    editButton: {
      padding: "9px 14px",
      borderRadius: "7px",
      border: "none",
      background: "#4f46e5",
      color: "#fff",
      cursor: "pointer",
      fontWeight: 600,
    },
    saveButton: {
      padding: "9px 14px",
      borderRadius: "7px",
      border: "none",
      background: "#16a34a",
      color: "#fff",
      cursor: "pointer",
      fontWeight: 600,
    },
    cancelButton: {
      padding: "9px 14px",
      borderRadius: "7px",
      border: "1px solid #d1d5db",
      background: "#fff",
      cursor: "pointer",
      fontWeight: 600,
    },
    deleteButton: {
      padding: "9px 14px",
      borderRadius: "7px",
      border: "none",
      background: "#dc2626",
      color: "#fff",
      cursor: "pointer",
      fontWeight: 600,
    },
    message: {
      padding: "12px 15px",
      borderRadius: "8px",
      marginBottom: "16px",
    },
  };

  return (
    <div style={styles.page}>
      <div style={styles.header}>
        <div>
          <h1 style={styles.title}>Historical Solutions</h1>
          <p style={styles.subtitle}>
            Manage approved solutions reused by your AI chatbot.
          </p>
        </div>

        <button
          style={styles.button}
          onClick={loadSolutions}
          disabled={loading}
        >
          ↻ Refresh
        </button>
      </div>

      <div style={styles.stats}>
        <div style={styles.statLabel}>
          Approved Historical Solutions
        </div>

        <div style={styles.statNumber}>
          {solutions.length}
        </div>

        <div style={styles.statLabel}>
          Available for chatbot retrieval
        </div>
      </div>

      {notice && (
        <div
          style={{
            ...styles.message,
            background: "#dcfce7",
            color: "#166534",
          }}
        >
          {notice}
        </div>
      )}

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
          placeholder="Search ticket, complaint, solution, customer..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />

        <select
          style={styles.select}
          value={intentFilter}
          onChange={(e) => setIntentFilter(e.target.value)}
        >
          <option value="all">All intents</option>

          {intents.map((intent) => (
            <option key={intent} value={intent}>
              {intent.replace(/_/g, " ")}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <p>Loading historical solutions...</p>
      ) : filteredSolutions.length === 0 ? (
        <div style={styles.card}>
          <p style={{ color: "#6b7280", margin: 0 }}>
            No historical solutions match your search.
          </p>
        </div>
      ) : (
        filteredSolutions.map((solution) => (
          <div key={solution.ticket_id} style={styles.card}>
            <div style={styles.cardHeader}>
              <div>
                <div style={styles.ticket}>
                  {solution.ticket_id}
                </div>

                <div style={{ marginTop: "7px", fontSize: "13px" }}>
                  {solution.intent || "Uncategorized"}
                </div>
              </div>

              <span style={styles.badge}>Approved</span>
            </div>

            <div style={styles.sectionLabel}>
              ORIGINAL CUSTOMER COMPLAINT
            </div>

            <div style={styles.complaint}>
              {solution.complaint || "No complaint recorded."}
            </div>

            <div style={styles.sectionLabel}>
              APPROVED REUSABLE SOLUTION
            </div>

            {editingId === solution.ticket_id ? (
              <>
                <textarea
                  style={styles.textarea}
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  placeholder="Enter the reusable solution..."
                />

                <div style={styles.actions}>
                  <button
                    style={styles.saveButton}
                    onClick={() => saveSolution(solution.ticket_id)}
                    disabled={savingId === solution.ticket_id}
                  >
                    {savingId === solution.ticket_id
                      ? "Saving..."
                      : "Save Changes"}
                  </button>

                  <button
                    style={styles.cancelButton}
                    onClick={cancelEditing}
                    disabled={savingId === solution.ticket_id}
                  >
                    Cancel
                  </button>
                </div>
              </>
            ) : (
              <div style={styles.solution}>
                {solution.approved_solution}
              </div>
            )}

            <div style={styles.meta}>
              <span>
                Customer: {solution.customer_email || "Unknown"}
              </span>

              <span>
                Ticket status: {solution.ticket_status || "Unknown"}
              </span>

              <span>
                Approved:{" "}
                {solution.approved_at
                  ? new Date(solution.approved_at).toLocaleString()
                  : "Unknown"}
              </span>
            </div>

            {editingId !== solution.ticket_id && (
              <div style={styles.actions}>
                <button
                  style={styles.editButton}
                  onClick={() => startEditing(solution)}
                >
                  ✎ Edit Solution
                </button>

                <button
                  style={styles.deleteButton}
                  onClick={() => deleteSolution(solution.ticket_id)}
                  disabled={deletingId === solution.ticket_id}
                >
                  {deletingId === solution.ticket_id
                    ? "Deleting..."
                    : "Delete Solution"}
                </button>
              </div>
            )}
          </div>
        ))
      )}
    </div>
  );
}