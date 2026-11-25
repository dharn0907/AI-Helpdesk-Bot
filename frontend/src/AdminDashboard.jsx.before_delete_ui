
import { useState, useEffect } from "react";

const API = "http://127.0.0.1:8000";

const emptyConfig = {
  bot_name: "Support Assistant",
  what_this_bot_helps_with: "",
  about_business: "",
  how_to_respond: "",
  when_to_handoff: "",
  dos: "",
  donts: "",
  advanced_instructions: ""
};

const fields = [
  ["bot_name", "Bot Name"],
  ["what_this_bot_helps_with", "What this bot helps with"],
  ["about_business", "About your business"],
  ["how_to_respond", "How should the bot respond?"],
  ["when_to_handoff", "When should it hand off to a human?"],
  ["dos", "Do's"],
  ["donts", "Don'ts"],
  ["advanced_instructions", "Advanced instructions"]
];

export default function AdminDashboard({ onBack, session, chatbot }) {
  const [companyId, setCompanyId] = useState(null);
  const [companyName, setCompanyName] = useState("");
  const [newCompanyName, setNewCompanyName] = useState("");
  const [newCompanyEmail, setNewCompanyEmail] = useState("");
  const [config, setConfig] = useState(emptyConfig);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [knowledgeFiles, setKnowledgeFiles] = useState([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [conversations, setConversations] = useState([]);
  const [tickets, setTickets] = useState([]);
  const [agents, setAgents] = useState([]);
  const [agentName, setAgentName] = useState("");
  const [agentEmail, setAgentEmail] = useState("");
  const [agentOtp, setAgentOtp] = useState("");
  const [pendingAgentId, setPendingAgentId] = useState(null);
  const [agentMessage, setAgentMessage] = useState("");
  const [agentError, setAgentError] = useState("");
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [dashboardLoading, setDashboardLoading] = useState(false);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [dashboardError, setDashboardError] = useState("");


  const headers = (extra = {}) => ({
    "Content-Type": "application/json",
    Authorization: `Bearer ${session.token}`,
    "X-Company-ID": String(session.company.id),
    ...extra
  });

  const readResponse = async (response) => {
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Request failed.");
    }

    return data;
  };

  const loadKnowledgeFiles = async () => {
    const response = await fetch(`${API}/knowledge-base/files`, {
      headers: headers()
    });

    const data = await readResponse(response);
    setKnowledgeFiles(data.files || []);
  };

  const loadCompany = async () => {
    const response = await fetch(`${API}/companies/current`, {
      headers: headers()
    });

    const data = await readResponse(response);


    if (data.exists) {
      setCompanyId(data.company_id);
      setCompanyName(data.company_name);
      setConfig({ ...emptyConfig, ...data.configuration });

      await loadKnowledgeFiles();

      setMessage("Company configuration and Knowledge Base loaded.");
    } else {
      setCompanyId(null);
      setCompanyName("");
      setConfig(emptyConfig);
      setKnowledgeFiles([]);
      setMessage("No company found. Create your first company below.");
    }
  };

  const connect = async () => {
    setLoading(true);
    setError("");
    setMessage("");

    try {
      await loadCompany();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setCompanyId(session.company.id);
    setCompanyName(session.company.name);
    connect();
  }, [session.token, session.company.id]);


  const loadBotData = async () => {
    if (!chatbot?.id) return;
    setDashboardLoading(true);
    setDashboardError("");
    try {
      const [conversationResponse, ticketResponse, agentResponse] = await Promise.all([
        fetch(`${API}/conversations/?chatbot_id=${chatbot.id}`, {
          headers: headers()
        }),
        fetch(`${API}/tickets/?chatbot_id=${chatbot.id}`, {
          headers: headers()
        }),
        fetch(`${API}/tickets/agents`, {
          headers: headers()
        })
      ]);

      const [conversationData, ticketData, agentData] = await Promise.all([
        readResponse(conversationResponse),
        readResponse(ticketResponse),
        readResponse(agentResponse)
      ]);

      setConversations(Array.isArray(conversationData) ? conversationData : []);
      setTickets(Array.isArray(ticketData) ? ticketData : []);
      setAgents(Array.isArray(agentData) ? agentData : []);
    } catch (err) {
      setDashboardError(err.message || "Could not load chatbot activity.");
    } finally {
      setDashboardLoading(false);
    }
  };

  const addSupportAgent = async (e) => {
    e.preventDefault();
    setAgentError("");
    setAgentMessage("");

    try {
      const response = await fetch(`${API}/tickets/agents`, {
        method: "POST",
        headers: headers(),
        body: JSON.stringify({
          name: agentName.trim(),
          email: agentEmail.trim().toLowerCase()
        })
      });

      const data = await readResponse(response);

      setAgentMessage("Agent registered and approved successfully.");
      setAgentName("");
      setAgentEmail("");
      setPendingAgentId(null);
      setAgentOtp("");
      await loadBotData();
    } catch (err) {
      setAgentError(err.message);
    }
  };

  const openConversation = async (conversation) => {
    setSelectedConversation(null);
    setDetailsLoading(true);
    setDashboardError("");
    try {
      const response = await fetch(
        `${API}/conversations/${conversation.id}?chatbot_id=${chatbot.id}`,
        { headers: headers() }
      );
      const data = await readResponse(response);
      setSelectedConversation(data);
    } catch (err) {
      setDashboardError(err.message || "Could not load conversation.");
    } finally {
      setDetailsLoading(false);
    }
  };

  useEffect(() => {
    loadBotData();
  }, [chatbot?.id, session.token, session.company.id]);

  const createCompany = async (event) => {
    event.preventDefault();

    if (!newCompanyName.trim()) {
      setError("Enter your company name.");
      return;
    }
    if (!newCompanyEmail.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(newCompanyEmail.trim())) {
      setError("Enter a valid company email address.");
      return;
    }

    setLoading(true);
    setError("");
    setMessage("");

    try {
      const response = await fetch(`${API}/companies/`, {
        method: "POST",
        headers: headers(),
        body: JSON.stringify({
          name: newCompanyName.trim(),
          email: newCompanyEmail.trim()
        })
      });

      await readResponse(response);

      setMessage("Verification email sent. Open the link in your company inbox to activate your account.");
      setNewCompanyName("");
      setNewCompanyEmail("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const saveConfiguration = async (event) => {
    event.preventDefault();

    if (!companyId) return;

    setLoading(true);
    setError("");
    setMessage("");

    try {
      const response = await fetch(
        `${API}/companies/${companyId}/configuration`,
        {
          method: "PATCH",
          headers: headers(),
          body: JSON.stringify(config)
        }
      );

      await readResponse(response);
      setMessage("Bot configuration saved successfully.");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const uploadKnowledgeFile = async () => {
    if (!selectedFile) {
      setError("Select a CSV or XLSX file first.");
      return;
    }

    const extension = selectedFile.name.split(".").pop().toLowerCase();

    if (!["csv", "xlsx"].includes(extension)) {
      setError("Only CSV and XLSX files are supported currently.");
      return;
    }

    setUploading(true);
    setError("");
    setMessage("");

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      const response = await fetch(`${API}/knowledge-base/upload`, {
        method: "POST",
        headers: headers(),
        body: formData
      });

      const data = await readResponse(response);

      setMessage(
        `Successfully uploaded ${data.filename}. ${data.records_saved} records saved.`
      );

      setSelectedFile(null);

      const fileInput = document.getElementById("knowledge-file-input");
      if (fileInput) fileInput.value = "";

      await loadKnowledgeFiles();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const deleteKnowledgeFile = async (fileId, filename) => {
    const confirmed = window.confirm(
      `Are you sure you want to delete "${filename}" and all its extracted records?`
    );

    if (!confirmed) return;

    setError("");
    setMessage("");

    try {
      const response = await fetch(
        `${API}/knowledge-base/files/${fileId}`,
        {
          method: "DELETE",
          headers: headers()
        }
      );

      const data = await readResponse(response);

      setMessage(data.message || "File deleted successfully.");
      await loadKnowledgeFiles();
    } catch (err) {
      setError(err.message);
    }
  };

  const updateField = (name, value) => {
    setConfig((previous) => ({ ...previous, [name]: value }));
  };

  const inputStyle = {
    width: "100%",
    boxSizing: "border-box",
    padding: "11px 12px",
    border: "1px solid #d1d5db",
    borderRadius: 8,
    fontSize: 14,
    background: "#fff",
    color: "#111827"
  };

  const buttonStyle = {
    padding: "11px 18px",
    background: "#2563eb",
    color: "#fff",
    border: 0,
    borderRadius: 8,
    cursor: "pointer",
    fontWeight: 600
  };

  return (
    <main style={{
      minHeight: "100vh",
      background: "#f3f4f6",
      padding: "28px 16px",
      boxSizing: "border-box",
      fontFamily: "Arial, sans-serif",
      color: "#111827"
    }}>
      <div style={{ maxWidth: 850, margin: "0 auto" }}>
        <header style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 12,
          flexWrap: "wrap",
          marginBottom: 24
        }}>
          <div>
            <h1 style={{ fontSize: 27, margin: "0 0 6px" }}>
              Chatbot Admin Dashboard
            </h1>
            <p style={{ color: "#6b7280", margin: 0 }}>
              Configure your chatbot and company knowledge
            </p>
          </div>

          <button
            onClick={onBack}
            style={{
              ...buttonStyle,
              background: "#374151"
            }}
          >
            Back to Customer Chat
          </button>
        </header>

        <section style={{ marginBottom: 26, padding: 20, background: "#fff", border: "1px solid #e5e7eb", borderRadius: 12 }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
            <div>
              <h2 style={{ margin: "0 0 5px", fontSize: 21 }}> {chatbot?.bot_name || "Selected chatbot"} ? Overview</h2>
              <p style={{ margin: 0, color: "#6b7280", fontSize: 13 }}>Activity belonging only to this chatbot</p>
            </div>
            <button type="button" onClick={loadBotData} style={{ padding: "9px 15px", border: 0, borderRadius: 7, background: "#7f1d3f", color: "#fff", cursor: "pointer" }}>Refresh data</button>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(135px,1fr))", gap: 12, marginTop: 18 }}>
            {[
              ["Conversations", conversations.length],
              ["Tickets", tickets.length],
              ["Open tickets", tickets.filter(t => String(t.status || "").toLowerCase() === "open").length],
              ["Resolved tickets", tickets.filter(t => String(t.status || "").toLowerCase() === "resolved").length]
            ].map(([label, value]) => (
              <div key={label} style={{ padding: 15, borderRadius: 9, background: "#f9fafb", border: "1px solid #e5e7eb" }}>
                <div style={{ color: "#6b7280", fontSize: 12 }}>{label}</div>
                <strong style={{ display: "block", fontSize: 25, marginTop: 5 }}>{value}</strong>
              </div>
            ))}
          </div>
          {dashboardLoading && <p style={{ color: "#6b7280" }}>Loading chatbot activity...</p>}
          {dashboardError && <p style={{ color: "#b91c1c" }}>{dashboardError}</p>}
        </section>

        <section style={{ marginBottom: 26, padding: 20, background: "#fff", border: "1px solid #e5e7eb", borderRadius: 12 }}>
          <h2 style={{ marginTop: 0 }}>Customer Conversations</h2>
          {conversations.length === 0 && !dashboardLoading ? (
            <p style={{ color: "#6b7280" }}>No conversations found for this chatbot yet.</p>
          ) : conversations.map(c => (
            <button key={c.id} type="button" onClick={() => openConversation(c)}
              style={{ display: "block", width: "100%", textAlign: "left", padding: 14, marginBottom: 9, border: "1px solid #e5e7eb", borderRadius: 9, background: "#fff", cursor: "pointer", color: "#111827" }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
                <strong>{c.customer_email || c.customer_id || `Customer ? ${c.id}`}</strong>
                <span style={{ color: "#6b7280", fontSize: 12 }}>{c.status || "Conversation"}</span>
              </div>
              <p style={{ margin: "7px 0", color: "#374151", fontSize: 13 }}>{c.last_message || "No messages"}</p>
              <span style={{ color: "#6b7280", fontSize: 11 }}>
                {c.message_count || 0} messages ? {c.last_activity ? new Date(c.last_activity).toLocaleString() : "Date unavailable"} ? ID {c.id}
              </span>
            </button>
          ))}

          {detailsLoading && <p>Loading conversation transcript...</p>}
          {selectedConversation && (
            <div style={{ marginTop: 18, padding: 16, border: "1px solid #cbd5e1", borderRadius: 10, background: "#f8fafc" }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
                <h3 style={{ margin: 0 }}>Conversation #{selectedConversation.id}</h3>
                <button type="button" onClick={() => setSelectedConversation(null)} style={{ padding: "6px 10px", cursor: "pointer" }}>Close transcript</button>
              </div>
              <p style={{ color: "#64748b", fontSize: 12 }}>{selectedConversation.customer_email || selectedConversation.customer_id || "Customer"} ? {selectedConversation.status}</p>
              <div style={{ display: "grid", gap: 9 }}>
                {(selectedConversation.messages || []).map((m, i) => (
                  <div key={m.id || i} style={{ padding: 12, borderRadius: 8, background: String(m.sender).toLowerCase().includes("user") || String(m.sender).toLowerCase().includes("customer") ? "#fff" : "#fce7f3", border: "1px solid #e5e7eb" }}>
                    <strong style={{ fontSize: 12 }}>{m.sender || "Message"}</strong>
                    <p style={{ margin: "5px 0", whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{m.content}</p>
                    <span style={{ color: "#6b7280", fontSize: 10 }}>{m.timestamp ? new Date(m.timestamp).toLocaleString() : ""}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>

        <section style={{ marginBottom: 26, padding: 20, background: "#fff", border: "1px solid #e5e7eb", borderRadius: 12 }}>
          <div style={{ marginBottom: 22, padding: 16, background: "#f9fafb", border: "1px solid #e5e7eb", borderRadius: 9 }}>
            <h3 style={{ marginTop: 0 }}>Support Agents</h3>
            <form onSubmit={addSupportAgent}
              style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 12 }}>
              <input required placeholder="Agent name" value={agentName}
                onChange={e => setAgentName(e.target.value)} />
              <input required type="email" placeholder="Agent email" value={agentEmail}
                onChange={e => setAgentEmail(e.target.value)} />
              <button type="submit">Register Agent</button>
            </form>
            {agentMessage && <p style={{color:"#15803d"}}>{agentMessage}</p>}
            {agentError && <p style={{color:"#b91c1c"}}>{agentError}</p>}
            {agents.length === 0 ? (
              <p style={{ color: "#6b7280" }}>No support agents registered for this company.</p>
            ) : (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 10 }}>
                {agents.map(agent => (
                  <div key={agent.id} style={{ padding: 12, background: "#fff", border: "1px solid #e5e7eb", borderRadius: 8 }}>
                    <strong>{agent.name || "Unnamed agent"}</strong>
                    <div style={{ fontSize: 12, color: "#64748b" }}>{agent.email}</div>
                    <div style={{ marginTop: 7, fontSize: 12 }}>
                      Email: <strong style={{ color: agent.email_verified ? "#15803d" : "#b91c1c" }}>
                        {agent.status === "approved" ? "Registered" : "Not verified"}
                      </strong>
                    </div>
                    <div style={{ fontSize: 12 }}>
                      Approval: <strong>{agent.status === "approved" ? "Approved" : "Pending"}</strong>
                    </div>
                    <div style={{ fontSize: 12, color: "#64748b" }}>Status: {agent.status}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
          <h2 style={{ marginTop: 0 }}>Support Tickets</h2>
          {tickets.length === 0 && !dashboardLoading ? (
            <p style={{ color: "#6b7280" }}>No tickets found for this chatbot yet.</p>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead><tr style={{ textAlign: "left", background: "#f9fafb" }}>
                  {["Ticket ID", "Customer", "Issue", "Category", "Priority", "Status", "Assigned Agent", "Created"].map(x => <th key={x} style={{ padding: 10, borderBottom: "1px solid #e5e7eb" }}>{x}</th>)}
                </tr></thead>
                <tbody>
                  {tickets.map((t, i) => (
                    <tr key={t.ticket_id || t.id || i}>
                      <td style={{ padding: 10, borderBottom: "1px solid #e5e7eb" }}>{t.ticket_id || t.id}</td>
                      <td style={{ padding: 10, borderBottom: "1px solid #e5e7eb" }}>{t.customer_email || "Not provided"}</td>
                      <td style={{ padding: 10, borderBottom: "1px solid #e5e7eb", minWidth: 180 }}>{t.customer_message || t.additional_details || "?"}</td>
                      <td style={{ padding: 10, borderBottom: "1px solid #e5e7eb" }}>{t.category || t.intent || "?"}</td>
                      <td style={{ padding: 10, borderBottom: "1px solid #e5e7eb" }}>{t.priority || "?"}</td>
                      <td style={{ padding: 10, borderBottom: "1px solid #e5e7eb" }}>{t.status || "?"}</td>
                      <td style={{ padding: 10, borderBottom: "1px solid #e5e7eb" }}>{t.assigned_agent?.name || t.assigned_agent?.email || "Unassigned"}</td>
                      <td style={{ padding: 10, borderBottom: "1px solid #e5e7eb", whiteSpace: "nowrap" }}>{t.created_at ? new Date(t.created_at).toLocaleString() : "?"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>



        {error && (
          <p style={{
            color: "#b91c1c",
            background: "#fee2e2",
            padding: 12,
            borderRadius: 8
          }}>
            {error}
          </p>
        )}

        {message && (
          <p style={{
            color: "#166534",
            background: "#dcfce7",
            padding: 12,
            borderRadius: 8
          }}>
            {message}
          </p>
        )}

        {!companyId && (
          <section style={{
            background: "#fff",
            padding: 22,
            borderRadius: 12,
            marginBottom: 18
          }}>
            <h2 style={{ fontSize: 19, marginTop: 0 }}>
              Initial Company Setup
            </h2>

            <p style={{ color: "#6b7280", fontSize: 14 }}>
              Create the single company used by this prototype.
            </p>

            <form onSubmit={createCompany}>
              <label style={{ display: "block", marginBottom: 8 }}>
                Company Name
              </label>

              <input
                value={newCompanyName}
                onChange={(e) => setNewCompanyName(e.target.value)}
                placeholder="Enter your company name"
                style={{ ...inputStyle, marginBottom: 14 }}
              />

              <label style={{ display: "block", marginBottom: 8 }}>
                Company Email
              </label>

              <input
                type="email"
                value={newCompanyEmail}
                onChange={(e) => setNewCompanyEmail(e.target.value)}
                placeholder="Enter your business email"
                required
                style={{ ...inputStyle, marginBottom: 14 }}
              />

              <button disabled={loading} style={buttonStyle}>
                {loading ? "Registering..." : "Register Agent"}
              </button>
            </form>
          </section>
        )}

        {companyId && (
          <>
            <section style={{
              background: "#fff",
              padding: 22,
              borderRadius: 12,
              marginBottom: 18
            }}>
              <h2 style={{ fontSize: 19, marginTop: 0 }}>
                Company: {companyName}
              </h2>

              <p style={{ color: "#6b7280", fontSize: 13 }}>
                Edit your chatbot's identity, purpose, tone and instructions.
              </p>
            </section>

            <form onSubmit={saveConfiguration}>
              <section style={{
                background: "#fff",
                padding: 22,
                borderRadius: 12,
                marginBottom: 18
              }}>
                <h2 style={{ fontSize: 19, marginTop: 0 }}>
                  Bot Configuration
                </h2>

                {fields.map(([name, label]) => (
                  <div key={name} style={{ marginBottom: 18 }}>
                    <label style={{
                      display: "block",
                      fontWeight: 600,
                      fontSize: 14,
                      marginBottom: 7
                    }}>
                      {label}
                    </label>

                    {name === "bot_name" ? (
                      <input
                        value={config[name] || ""}
                        onChange={(e) => updateField(name, e.target.value)}
                        style={inputStyle}
                      />
                    ) : (
                      <textarea
                        rows={3}
                        value={config[name] || ""}
                        onChange={(e) => updateField(name, e.target.value)}
                        placeholder={`Enter ${label.toLowerCase()}...`}
                        style={{
                          ...inputStyle,
                          resize: "vertical",
                          fontFamily: "inherit"
                        }}
                      />
                    )}
                  </div>
                ))}

                <button
                  type="submit"
                  disabled={loading}
                  style={buttonStyle}
                >
                  {loading ? "Saving..." : "Save Bot Configuration"}
                </button>
              </section>
            </form>

            <section style={{
              background: "#fff",
              padding: 22,
              borderRadius: 12,
              marginBottom: 18
            }}>
              <h2 style={{ fontSize: 19, marginTop: 0 }}>
                Company Knowledge Base
              </h2>

              <p style={{ color: "#6b7280", fontSize: 14 }}>
                Upload and manage your company's product information,
                FAQs, services, policies and other business data.
              </p>

              <div style={{
                border: "1px dashed #9ca3af",
                padding: 22,
                borderRadius: 9,
                marginBottom: 20
              }}>
                <h3 style={{ fontSize: 15, marginTop: 0 }}>
                  Upload Company Data
                </h3>

                <p style={{ fontSize: 13, color: "#6b7280" }}>
                  Supported formats: CSV and XLSX. Maximum file size: 10 MB.
                </p>

                <input
                  id="knowledge-file-input"
                  type="file"
                  accept=".csv,.xlsx"
                  onChange={(e) => {
                    setSelectedFile(e.target.files?.[0] || null);
                    setError("");
                  }}
                  style={{
                    ...inputStyle,
                    marginBottom: 14
                  }}
                />

                {selectedFile && (
                  <p style={{
                    fontSize: 13,
                    color: "#374151"
                  }}>
                    Selected: {selectedFile.name}
                  </p>
                )}

                <button
                  type="button"
                  onClick={uploadKnowledgeFile}
                  disabled={uploading || !selectedFile}
                  style={{
                    ...buttonStyle,
                    opacity: uploading || !selectedFile ? 0.6 : 1,
                    cursor: uploading || !selectedFile
                      ? "not-allowed"
                      : "pointer"
                  }}
                >
                  {uploading ? "Uploading..." : "Upload to Knowledge Base"}
                </button>
              </div>

              <div>
                <div style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: 10,
                  flexWrap: "wrap"
                }}>
                  <h3 style={{ fontSize: 16 }}>
                    Uploaded Company Files
                  </h3>

                  <button
                    type="button"
                    onClick={async () => {
                      try {
                        setError("");
                        await loadKnowledgeFiles();
                        setMessage("Knowledge Base list refreshed.");
                      } catch (err) {
                        setError(err.message);
                      }
                    }}
                    style={{
                      ...buttonStyle,
                      background: "#4b5563",
                      padding: "8px 12px"
                    }}
                  >
                    Refresh
                  </button>
                </div>

                {knowledgeFiles.length === 0 ? (
                  <p style={{
                    color: "#6b7280",
                    fontSize: 14,
                    padding: 15,
                    background: "#f9fafb",
                    borderRadius: 8
                  }}>
                    No company files uploaded yet.
                  </p>
                ) : (
                  <div style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: 10
                  }}>
                    {knowledgeFiles.map((file) => (
                      <div
                        key={file.id}
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          gap: 12,
                          flexWrap: "wrap",
                          padding: 14,
                          border: "1px solid #e5e7eb",
                          borderRadius: 9
                        }}
                      >
                        <div style={{ flex: "1 1 200px" }}>
                          <strong style={{
                            display: "block",
                            fontSize: 14,
                            overflowWrap: "anywhere"
                          }}>
                            {file.filename}
                          </strong>

                          <p style={{
                            color: "#6b7280",
                            fontSize: 12,
                            margin: "5px 0"
                          }}>
                            {file.file_type.toUpperCase()} ·{" "}
                            {file.row_count} records · {file.status}
                          </p>

                          {file.created_at && (
                            <p style={{
                              color: "#9ca3af",
                              fontSize: 11,
                              margin: 0
                            }}>
                              Uploaded:{" "}
                              {new Date(file.created_at).toLocaleString()}
                            </p>
                          )}
                        </div>

                        <button
                          type="button"
                          onClick={() =>
                            deleteKnowledgeFile(file.id, file.filename)
                          }
                          style={{
                            ...buttonStyle,
                            background: "#dc2626",
                            padding: "8px 13px"
                          }}
                        >
                          Delete
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </section>
          </>
        )}
      </div>
    </main>
  );
}
