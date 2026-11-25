import { useState } from "react";

const API = "http://127.0.0.1:8000";

export default function AgentHelpdesk() {
  const [email, setEmail] = useState("");
  const [agent, setAgent] = useState(null);
  const [tickets, setTickets] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function login(e) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const normalizedEmail = email.trim().toLowerCase();

      const response = await fetch(`${API}/tickets/agents/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: normalizedEmail })
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Agent not found");

      const ticketResponse = await fetch(`${API}/tickets/agents/tickets`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: normalizedEmail })
      });

      const ticketData = await ticketResponse.json();
      if (!ticketResponse.ok) {
        throw new Error(ticketData.detail || "Could not load tickets");
      }

      setAgent(data);
      setTickets(ticketData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    setAgent(null);
    setTickets([]);
    setEmail("");
    setError("");
  }

  const card = {
    background: "white",
    padding: 20,
    borderRadius: 12,
    border: "1px solid #e5e7eb"
  };

  return (
    <main style={{
      minHeight: "100vh",
      background: "#f3f4f6",
      fontFamily: "Arial, sans-serif",
      padding: 24,
      boxSizing: "border-box"
    }}>
      {!agent ? (
        <section style={{
          ...card,
          maxWidth: 420,
          margin: "100px auto"
        }}>
          <h2>Agent Helpdesk</h2>
          <p>Login using the email registered by your company admin.</p>

          <form onSubmit={login}>
            <input
              type="email"
              required
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="Registered email"
              style={{
                width: "100%",
                boxSizing: "border-box",
                padding: 13,
                marginBottom: 14,
                border: "1px solid #ccc",
                borderRadius: 7
              }}
            />

            {error && <p style={{ color: "red" }}>{error}</p>}

            <button
              disabled={loading}
              style={{
                width: "100%",
                padding: 13,
                background: "#2563eb",
                color: "white",
                border: 0,
                borderRadius: 7,
                cursor: "pointer"
              }}
            >
              {loading ? "Loading..." : "Continue"}
            </button>
          </form>
        </section>
      ) : (
        <section style={{ maxWidth: 1150, margin: "auto" }}>
          <header style={{
            ...card,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: 12,
            marginBottom: 22
          }}>
            <div>
              <h2 style={{ margin: "0 0 8px" }}>Agent Helpdesk</h2>
              <div>Welcome, {agent.name || "Agent"}</div>
              <small>{agent.email}</small>
            </div>
            <button onClick={logout} style={{
              padding: "10px 18px",
              background: "#dc2626",
              color: "white",
              border: 0,
              borderRadius: 7,
              cursor: "pointer"
            }}>
              Log out
            </button>
          </header>

          <div style={{
            display: "flex",
            gap: 15,
            flexWrap: "wrap",
            marginBottom: 22
          }}>
            <div style={{ ...card, flex: 1, minWidth: 150 }}>
              <small>Total Company Tickets</small>
              <h2>{tickets.length}</h2>
            </div>
            <div style={{ ...card, flex: 1, minWidth: 150 }}>
              <small>Open Tickets</small>
              <h2>{tickets.filter(t => t.status === "Open").length}</h2>
            </div>
            <div style={{ ...card, flex: 1, minWidth: 150 }}>
              <small>Resolved Tickets</small>
              <h2>{tickets.filter(t => t.status === "Resolved").length}</h2>
            </div>
          </div>

          <div style={card}>
            <h2>Company Support Tickets</h2>

            {tickets.length === 0 ? (
              <p>No tickets found for this company.</p>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table style={{
                  width: "100%",
                  borderCollapse: "collapse",
                  textAlign: "left"
                }}>
                  <thead>
                    <tr style={{ background: "#f3f4f6" }}>
                      {["Ticket ID", "Customer", "Message", "Priority", "Status", "Created"].map(h => (
                        <th key={h} style={{
                          padding: 12,
                          borderBottom: "1px solid #ddd"
                        }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {tickets.map((ticket, index) => (
                      <tr key={ticket.id || index}>
                        <td style={{ padding: 12, borderBottom: "1px solid #eee" }}>
                          {ticket.ticket_id}
                        </td>
                        <td style={{ padding: 12, borderBottom: "1px solid #eee" }}>
                          {ticket.customer_email || "Not provided"}
                        </td>
                        <td style={{
                          padding: 12,
                          borderBottom: "1px solid #eee",
                          maxWidth: 300
                        }}>
                          {ticket.customer_message}
                        </td>
                        <td style={{ padding: 12, borderBottom: "1px solid #eee" }}>
                          {ticket.priority}
                        </td>
                        <td style={{ padding: 12, borderBottom: "1px solid #eee" }}>
                          {ticket.status}
                        </td>
                        <td style={{ padding: 12, borderBottom: "1px solid #eee" }}>
                          {ticket.created_at
                            ? new Date(ticket.created_at).toLocaleString()
                            : "-"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>
      )}
    </main>
  );
}
