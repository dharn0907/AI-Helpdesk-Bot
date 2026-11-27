
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
  const [selectedKnowledgeType, setSelectedKnowledgeType] = useState("general");
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
  const [supportEmail, setSupportEmail] = useState("");
  const [supportEmailVerified, setSupportEmailVerified] = useState(false);
  const [supportEmailLoading, setSupportEmailLoading] = useState(false);
  const [supportEmailMessage, setSupportEmailMessage] = useState("");
  const [smtpHost, setSmtpHost] = useState("smtp.gmail.com");
  const [smtpPort, setSmtpPort] = useState("587");
  const [smtpUsername, setSmtpUsername] = useState("");
  const [smtpPassword, setSmtpPassword] = useState("");
  const [smtpSecurity, setSmtpSecurity] = useState("starttls");
  const [smtpConfigured, setSmtpConfigured] = useState(false);
  const [smtpLoading, setSmtpLoading] = useState(false);
  const [smtpMessage, setSmtpMessage] = useState("");
  const [ticketTimeoutEnabled, setTicketTimeoutEnabled] = useState(true);
  const [ticketTimeoutMinutes, setTicketTimeoutMinutes] = useState("2");
  const [ticketTimeoutLoading, setTicketTimeoutLoading] = useState(false);
  const [ticketTimeoutMessage, setTicketTimeoutMessage] = useState("");
  const [ticketIntake, setTicketIntake] = useState({ global_fields: [], categories: [] });
  const [ticketIntakeLoading, setTicketIntakeLoading] = useState(false);
  const [ticketIntakeMessage, setTicketIntakeMessage] = useState("");



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

  const loadSupportEmail = async () => {
    const response = await fetch(`${API}/companies/support-email`, {
      headers: headers()
    });
    const data = await readResponse(response);
    setSupportEmail(data.support_email || "");
    setSupportEmailVerified(Boolean(data.verified));
  };

  const saveSupportEmail = async (event) => {
    event.preventDefault();
    if (!supportEmail.trim()) return;

    setSupportEmailLoading(true);
    setSupportEmailMessage("");

    try {
      const response = await fetch(`${API}/companies/support-email`, {
        method: "POST",
        headers: headers(),
        body: JSON.stringify({ email: supportEmail.trim() })
      });

      const data = await readResponse(response);
      setSupportEmailVerified(false);
      setSupportEmailMessage(
        data.message || "Verification email sent. Check your inbox."
      );
    } catch (err) {
      setSupportEmailMessage(err.message || "Could not save support email.");
    } finally {
      setSupportEmailLoading(false);
    }
  };
  const loadTicketConversationTimeout = async () => {
    const response = await fetch(`${API}/companies/current/ticket-conversation-timeout`, {
      headers: headers()
    });
    const data = await readResponse(response);
    setTicketTimeoutEnabled(data.enabled !== false);
    setTicketTimeoutMinutes(String(data.timeout_minutes || 2));
  };

  const saveTicketConversationTimeout = async () => {
    setTicketTimeoutLoading(true);
    setTicketTimeoutMessage("");
    try {
      const response = await fetch(`${API}/companies/current/ticket-conversation-timeout`, {
        method: "PATCH",
        headers: headers(),
        body: JSON.stringify({
          enabled: ticketTimeoutEnabled,
          timeout_minutes: Number(ticketTimeoutMinutes)
        })
      });
      const data = await readResponse(response);
      setTicketTimeoutMessage(data.message || "Inactivity settings saved.");
    } catch (err) {
      setTicketTimeoutMessage(err.message || "Could not save inactivity settings.");
    } finally {
      setTicketTimeoutLoading(false);
    }
  };

  const loadTicketIntake = async () => {
    const response = await fetch(`${API}/companies/current/ticket-intake`, { headers: headers() });
    const data = await readResponse(response);
    const normalizeField = (field) => {
      if (field?.key === "email" && field?.type === "phone") {
        return {
          ...field,
          key: "phone",
          prompt: /email address/i.test(field.prompt || "")
            ? "What phone number can our support team use to contact you?"
            : field.prompt,
          required: true,
        };
      }
      return field;
    };
    setTicketIntake({
      global_fields: (Array.isArray(data.global_fields) ? data.global_fields : []).map(normalizeField),
      categories: (Array.isArray(data.categories) ? data.categories : []).map(category => ({
        ...category,
        fields: (Array.isArray(category.fields) ? category.fields : []).map(normalizeField),
      })),
    });
  };

  const saveTicketIntake = async () => {
    setTicketIntakeLoading(true);
    setTicketIntakeMessage("");
    try {
      const response = await fetch(`${API}/companies/current/ticket-intake`, { method: "PUT", headers: headers(), body: JSON.stringify(ticketIntake) });
      const data = await readResponse(response);
      setTicketIntake(data.configuration || ticketIntake);
      setTicketIntakeMessage(data.message || "Ticket information settings saved.");
    } catch (err) {
      setTicketIntakeMessage(err.message || "Could not save ticket information settings.");
    } finally { setTicketIntakeLoading(false); }
  };

  const addIntakeField = (scope, categoryIndex = -1) => {
    const field = { key: `custom_field_${Date.now().toString(36)}`, label: "New information", type: "text", required: true, prompt: "Could you provide this information?" };
    setTicketIntake(current => {
      if (scope === "global") return { ...current, global_fields: [...current.global_fields, field] };
      const categories = [...current.categories];
      categories[categoryIndex] = { ...categories[categoryIndex], fields: [...(categories[categoryIndex].fields || []), field] };
      return { ...current, categories };
    });
  };

  const updateIntakeField = (scope, index, property, value, categoryIndex = -1) => {
    setTicketIntake(current => {
      const updateField = (field) => {
        const next = { ...field, [property]: value };
        // Changing a field's data type must also change its internal key and
        // default customer-facing question. Otherwise a phone field can still
        // be treated as the legacy "email" field by the ticket workflow.
        if (property === "type") {
          if (field.key === "email" || field.key === "phone" || field.key?.startsWith("custom_field_")) {
            next.key = value === "email" ? "email" : value === "phone" ? "phone" : `custom_field_${Date.now().toString(36)}`;
          }
          if (!field.prompt || /email address|phone number|provide this information/i.test(field.prompt)) {
            next.prompt = value === "email"
              ? "What email address should our support team use to send you updates?"
              : value === "phone"
                ? "What phone number can our support team use to contact you?"
                : "Could you provide this information?";
          }
          if (value === "email" || value === "phone") next.required = true;
        }
        return next;
      };
      if (scope === "global") {
        const global_fields = [...current.global_fields]; global_fields[index] = updateField(global_fields[index]);
        return { ...current, global_fields };
      }
      const categories = [...current.categories]; const fields = [...(categories[categoryIndex].fields || [])];
      fields[index] = updateField(fields[index]); categories[categoryIndex] = { ...categories[categoryIndex], fields };
      return { ...current, categories };
    });
  };

  const removeIntakeField = (scope, index, categoryIndex = -1) => {
    setTicketIntake(current => {
      if (scope === "global") return { ...current, global_fields: current.global_fields.filter((_, i) => i !== index) };
      const categories = [...current.categories]; categories[categoryIndex] = { ...categories[categoryIndex], fields: (categories[categoryIndex].fields || []).filter((_, i) => i !== index) };
      return { ...current, categories };
    });
  };

  const addIntakeCategory = () => {
    const key = `category_${Date.now().toString(36)}`;
    setTicketIntake(current => ({ ...current, categories: [...current.categories, { key, label: "New ticket category", fields: [] }] }));
  };

  const updateIntakeCategory = (index, property, value) => {
    setTicketIntake(current => { const categories = [...current.categories]; categories[index] = { ...categories[index], [property]: value }; return { ...current, categories }; });
  };

  const removeIntakeCategory = (index) => setTicketIntake(current => ({ ...current, categories: current.categories.filter((_, i) => i !== index) }));

  const renderIntakeFieldEditor = (field, index, scope, categoryIndex = -1) => (
    <div key={field.key || index} style={{ display: "grid", gridTemplateColumns: "1fr 1fr 130px auto", gap: 8, alignItems: "center", padding: 10, border: "1px solid #e5e7eb", borderRadius: 8, marginTop: 8 }}>
      <input value={field.label || ""} onChange={e => updateIntakeField(scope, index, "label", e.target.value, categoryIndex)} placeholder="Field label" style={{ ...inputStyle, margin: 0 }} />
      <input value={field.prompt || ""} onChange={e => updateIntakeField(scope, index, "prompt", e.target.value, categoryIndex)} placeholder="Question the bot asks" style={{ ...inputStyle, margin: 0 }} />
      <select value={field.type || "text"} onChange={e => updateIntakeField(scope, index, "type", e.target.value, categoryIndex)} style={{ ...inputStyle, margin: 0 }}>
        {["text", "textarea", "email", "phone", "number", "date", "select"].map(type => <option key={type} value={type}>{type}</option>)}
      </select>
      <button type="button" onClick={() => removeIntakeField(scope, index, categoryIndex)} style={{ border: "1px solid #dc2626", color: "#dc2626", background: "white", borderRadius: 6, padding: "8px 10px" }}>Remove</button>
      <label style={{ gridColumn: "1 / -1", display: "flex", gap: 8, alignItems: "center", fontSize: 13 }}>
        <input type="checkbox" checked={Boolean(field.required)} onChange={e => updateIntakeField(scope, index, "required", e.target.checked, categoryIndex)} /> Required <span style={{ color: "#6b7280" }}>Field key: {field.key} · Changing the type updates its key and suggested question.</span>
      </label>
      {field.type === "select" && <input value={(field.options || []).join(", ")} onChange={e => updateIntakeField(scope, index, "options", e.target.value.split(",").map(v => v.trim()).filter(Boolean), categoryIndex)} placeholder="Dropdown options, comma separated" style={{ ...inputStyle, gridColumn: "1 / -1", margin: 0 }} />}
    </div>
  );

  const loadSmtpSettings = async () => {
    const response = await fetch(`${API}/companies/smtp-settings`, {
      headers: headers()
    });
    const data = await readResponse(response);

    setSmtpHost(data.host || "");
    setSmtpPort(String(data.port || 587));
    setSmtpUsername(data.username || "");
    setSmtpSecurity(data.security || "starttls");
    setSmtpConfigured(Boolean(data.configured));
  };

  const saveSmtpSettings = async () => {
    setSmtpLoading(true);
    setSmtpMessage("");

    try {
      const response = await fetch(`${API}/companies/smtp-settings`, {
        method: "POST",
        headers: headers(),
        body: JSON.stringify({
          host: smtpHost,
          port: Number(smtpPort),
          username: smtpUsername,
          password: smtpPassword,
          security: smtpSecurity
        })
      });

      const data = await readResponse(response);
      setSmtpConfigured(true);
      setSmtpPassword("");
      setSmtpMessage(data.message || "SMTP settings saved.");
    } catch (error) {
      setSmtpMessage(error.message);
    } finally {
      setSmtpLoading(false);
    }
  };

  const testSmtpConnection = async () => {
    setSmtpLoading(true);
    setSmtpMessage("");

    try {
      const response = await fetch(`${API}/companies/smtp-settings/test`, {
        method: "POST",
        headers: headers()
      });

      const data = await readResponse(response);
      setSmtpMessage(data.message);
    } catch (error) {
      setSmtpMessage(error.message);
    } finally {
      setSmtpLoading(false);
    }
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
      await loadSupportEmail();
      await loadTicketConversationTimeout();
      await loadSmtpSettings();

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
    loadTicketIntake().catch(err => setTicketIntakeMessage(err.message));
  }, [session.token, session.company.id]);

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


  const deleteSupportAgent = async (agent) => {
    if (!window.confirm(`Revoke access for ${agent.name || agent.email}? Their ticket history will be kept.`)) return;
    setAgentError("");
    setAgentMessage("");
    try {
      const response = await fetch(`${API}/tickets/agents/${agent.id}`, {
        method: "DELETE",
        headers: headers(),
      });
      const data = await readResponse(response);
      setAgentMessage(data.message || "Agent access revoked.");
      await loadBotData();
    } catch (err) {
      setAgentError(err.message);
    }
  };

  const deleteSelectedChatbot = async () => {
    if (!chatbot?.id || !window.confirm(`Deactivate chatbot "${chatbot.bot_name || "this chatbot"}"?`)) return;
    try {
      const response = await fetch(`${API}/companies/current/chatbots/${chatbot.id}`, {
        method: "DELETE",
        headers: headers(),
      });
      const data = await readResponse(response);
      window.alert(data.message || "Chatbot deactivated.");
      onBack();
    } catch (err) {
      window.alert(err.message);
    }
  };

  const deleteCompanyAccount = async () => {
    if (!window.confirm("Deactivate this entire company account? All bots and agent access will stop. Existing records and audit history will be retained.")) return;
    if (!window.confirm("Final confirmation: are you sure you want to deactivate this company?")) return;
    try {
      const response = await fetch(`${API}/companies/current`, {
        method: "DELETE",
        headers: headers(),
      });
      const data = await readResponse(response);
      window.alert(data.message || "Company deactivated.");
      onBack();
    } catch (err) {
      window.alert(err.message);
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
      formData.append("knowledge_type", selectedKnowledgeType);

      const response = await fetch(`${API}/knowledge-base/upload`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session.token}`,
          "X-Company-ID": String(session.company.id)
        },
        body: formData
      });

      const data = await readResponse(response);

      setMessage(
        `Successfully uploaded ${data.filename}. ${data.records_saved} records saved.`
      );

      setSelectedFile(null);
      setSelectedKnowledgeType("general");

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
          <button type="button" onClick={deleteSelectedChatbot}
            style={{ marginLeft: 8, background: "#dc2626", color: "#fff", border: 0, borderRadius: 6, padding: "9px 13px", cursor: "pointer" }}>
            Delete Chatbot
          </button>
          <button type="button" onClick={deleteCompanyAccount}
            style={{ marginLeft: 8, background: "#991b1b", color: "#fff", border: 0, borderRadius: 6, padding: "9px 13px", cursor: "pointer" }}>
            Delete Company
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
                    {agent.status !== "revoked" && (
                      <button type="button" onClick={() => deleteSupportAgent(agent)}
                        style={{ marginTop: 10, background: "#dc2626", color: "#fff", border: 0, borderRadius: 6, padding: "7px 11px", cursor: "pointer" }}>
                        Delete Agent
                      </button>
                    )}
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

            <section style={{
              background: "#fff",
              padding: 22,
              borderRadius: 12,
              marginBottom: 18
            }}>
              <h2 style={{ fontSize: 19, marginTop: 0 }}>
                Company Support Email
              </h2>

              <p style={{ color: "#6b7280", fontSize: 13 }}>
                Customers can reply to ticket emails using this verified company support address.
              </p>

              <form onSubmit={saveSupportEmail}>
                <label style={{
                  display: "block",
                  fontWeight: 600,
                  fontSize: 14,
                  marginBottom: 7
                }}>
                  Support Email Address
                </label>

                <input
                  type="email"
                  value={supportEmail}
                  onChange={(e) => {
                    setSupportEmail(e.target.value);
                    setSupportEmailVerified(false);
                    setSupportEmailMessage("");
                  }}
                  placeholder="support@yourcompany.com"
                  required
                  style={{ ...inputStyle, marginBottom: 12 }}
                />

                <div style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  flexWrap: "wrap"
                }}>
                  <button type="submit" disabled={supportEmailLoading}
                    style={buttonStyle}>
                    {supportEmailLoading ? "Sending..." : "Save & Send Verification"}
                  </button>

                  <span style={{
                    fontSize: 13,
                    fontWeight: 600,
                    color: supportEmailVerified ? "#15803d" : "#b45309"
                  }}>
                    {supportEmailVerified ? "Verified" : "Not verified"}
                  </span>
                </div>

                {supportEmailMessage && (
                  <p style={{ fontSize: 13, color: "#2563eb", marginBottom: 0 }}>
                    {supportEmailMessage}
                  </p>
                )}
              </form>
            </section>
            <section style={{ background: "#ffffff", border: "1px solid #e5e7eb", borderRadius: 10, padding: 20, marginBottom: 18 }}>
              <h2 style={{ fontSize: 19, marginTop: 0 }}>Ticket Information Builder</h2>
              <p style={{ color: "#6b7280", fontSize: 13 }}>Choose what this company's chatbot collects for every ticket and for individual categories. Required fields must be provided. Optional fields are asked conversationally but customers can reply SKIP. Email is not mandatory unless you add it as a required field.</p>
              <h3>Information for every ticket</h3>
              {ticketIntake.global_fields.map((field, index) => renderIntakeFieldEditor(field, index, "global"))}
              <button type="button" onClick={() => addIntakeField("global")} style={{ ...buttonStyle, marginTop: 10 }}>+ Add global field</button>
              <div style={{ borderTop: "1px solid #e5e7eb", margin: "20px 0" }} />
              <h3>Ticket categories and their fields</h3>
              <p style={{ color: "#6b7280", fontSize: 12 }}>Use standard category names such as Payment / Billing, Delivery / Shipping, Login / Authentication, Refunds / Returns, Technical Issues, Account Management, Product / Service Questions or Feature Requests. For a custom intent, set its key to the intent name used by your chatbot.</p>
              {ticketIntake.categories.map((category, categoryIndex) => (
                <div key={category.key || categoryIndex} style={{ border: "1px solid #d1d5db", borderRadius: 8, padding: 14, marginTop: 12 }}>
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <input value={category.label || ""} onChange={e => updateIntakeCategory(categoryIndex, "label", e.target.value)} placeholder="Category name" style={{ ...inputStyle, margin: 0 }} />
                    <input value={category.key || ""} onChange={e => updateIntakeCategory(categoryIndex, "key", e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, "_"))} placeholder="Intent key (e.g. payment_issue)" style={{ ...inputStyle, margin: 0 }} />
                    <button type="button" onClick={() => removeIntakeCategory(categoryIndex)} style={{ border: "1px solid #dc2626", color: "#dc2626", background: "white", borderRadius: 6, padding: "8px 10px" }}>Delete category</button>
                  </div>
                  <p style={{ color: "#6b7280", fontSize: 12 }}>Category key: {category.key}</p>
                  {(category.fields || []).map((field, index) => renderIntakeFieldEditor(field, index, "category", categoryIndex))}
                  <button type="button" onClick={() => addIntakeField("category", categoryIndex)} style={{ ...buttonStyle, marginTop: 10 }}>+ Add category field</button>
                </div>
              ))}
              <button type="button" onClick={addIntakeCategory} style={{ ...buttonStyle, marginTop: 12 }}>+ Generate ticket category</button>
              <div style={{ marginTop: 14 }}>
                <button type="button" onClick={saveTicketIntake} disabled={ticketIntakeLoading} style={buttonStyle}>{ticketIntakeLoading ? "Saving..." : "Save Ticket Information Settings"}</button>
                {ticketIntakeMessage && <p style={{ color: "#2563eb", fontSize: 13 }}>{ticketIntakeMessage}</p>}
              </div>
            </section>

            <section style={{
              background: "#ffffff",
              border: "1px solid #e5e7eb",
              borderRadius: 10,
              padding: 20,
              marginBottom: 18
            }}>
              <h2 style={{ fontSize: 19, marginTop: 0 }}>
                Ticket Conversation Inactivity
              </h2>
              <p style={{ color: "#6b7280", fontSize: 13 }}>
                If a customer stops replying while a support ticket is being prepared, the bot submits the ticket after this period only when all required information configured in Ticket Information Builder has been collected. New customer messages reset the timer. The default is 2 minutes.
              </p>
              <label style={{ display: "flex", alignItems: "center", gap: 9, marginBottom: 12 }}>
                <input
                  type="checkbox"
                  checked={ticketTimeoutEnabled}
                  onChange={(e) => setTicketTimeoutEnabled(e.target.checked)}
                />
                Enable automatic ticket submission after inactivity
              </label>
              <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                <label htmlFor="ticket-timeout-minutes">Inactivity period (minutes)</label>
                <input
                  id="ticket-timeout-minutes"
                  type="number"
                  min="1"
                  max="30"
                  value={ticketTimeoutMinutes}
                  onChange={(e) => setTicketTimeoutMinutes(e.target.value)}
                  style={{ ...inputStyle, width: 110, marginBottom: 0 }}
                />
                <button
                  type="button"
                  disabled={ticketTimeoutLoading}
                  onClick={saveTicketConversationTimeout}
                  style={{
                    padding: "10px 18px",
                    background: "#2563eb",
                    color: "#ffffff",
                    border: "none",
                    borderRadius: 6,
                    cursor: "pointer"
                  }}
                >
                  {ticketTimeoutLoading ? "Saving..." : "Save Inactivity Settings"}
                </button>
              </div>
              {ticketTimeoutMessage && (
                <p style={{ color: "#6b7280", fontSize: 13, marginBottom: 0 }}>
                  {ticketTimeoutMessage}
                </p>
              )}
            </section>

            <section style={{
              background: "#ffffff",
              border: "1px solid #e5e7eb",
              borderRadius: 10,
              padding: 20,
              marginBottom: 18
            }}>
              <h2 style={{ fontSize: 19, marginTop: 0 }}>
                Company SMTP Settings
              </h2>

              <p style={{ color: "#6b7280", fontSize: 13 }}>
                Configure your company's email server. Ticket replies will be sent using these credentials.
              </p>

              <input
                value={smtpHost}
                onChange={(e) => setSmtpHost(e.target.value)}
                placeholder="SMTP Host (example: smtp.gmail.com)"
                style={{ ...inputStyle, marginBottom: 12 }}
              />

              <input
                type="number"
                value={smtpPort}
                onChange={(e) => setSmtpPort(e.target.value)}
                placeholder="SMTP Port (587)"
                style={{ ...inputStyle, marginBottom: 12 }}
              />

              <input
                value={smtpUsername}
                onChange={(e) => setSmtpUsername(e.target.value)}
                placeholder="SMTP Username / Email"
                style={{ ...inputStyle, marginBottom: 12 }}
              />

              <input
                type="password"
                value={smtpPassword}
                onChange={(e) => setSmtpPassword(e.target.value)}
                placeholder={smtpConfigured ? "Password saved (leave blank to keep it)" : "SMTP Password / App Password"}
                style={{ ...inputStyle, marginBottom: 12 }}
              />

              <select
                value={smtpSecurity}
                onChange={(e) => setSmtpSecurity(e.target.value)}
                style={{ ...inputStyle, marginBottom: 12 }}
              >
                <option value="starttls">STARTTLS (usually port 587)</option>
                <option value="ssl">SSL (usually port 465)</option>
              </select>

              <p style={{ fontSize: 12, color: "#6b7280" }}>
                {smtpConfigured ? "SMTP credentials are saved. Enter a new password only if you want to change it." : "SMTP credentials have not been configured yet."}
              </p>

              <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                <button
                  type="button"
                  disabled={smtpLoading}
                  onClick={saveSmtpSettings}
                  style={{
                    padding: "10px 18px",
                    background: "#2563eb",
                    color: "#ffffff",
                    border: "none",
                    borderRadius: 6,
                    cursor: "pointer"
                  }}
                >
                  {smtpLoading ? "Please wait..." : "Save SMTP Settings"}
                </button>

                <button
                  type="button"
                  disabled={smtpLoading || !smtpConfigured}
                  onClick={testSmtpConnection}
                  style={{
                    padding: "10px 18px",
                    background: "#059669",
                    color: "#ffffff",
                    border: "none",
                    borderRadius: 6,
                    cursor: "pointer"
                  }}
                >
                  Test SMTP Connection
                </button>
              </div>

              {smtpMessage && (
                <p style={{ fontSize: 13, marginTop: 12, color: "#2563eb" }}>
                  {smtpMessage}
                </p>
              )}
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
                  Upload Knowledge Base Data
                </h3>

                <p style={{ fontSize: 13, color: "#6b7280" }}>
                  Choose which knowledge collection this file belongs to. The chatbot retrieves only the matching collection for each intent. Existing uploaded files remain in General Knowledge.
                </p>

                <label style={{ display: "block", fontWeight: 600, fontSize: 13, marginBottom: 7 }}>
                  Knowledge Base Type
                </label>
                <select
                  value={selectedKnowledgeType}
                  onChange={(e) => setSelectedKnowledgeType(e.target.value)}
                  style={{ ...inputStyle, marginBottom: 14 }}
                >
                  <option value="general">General Knowledge — FAQs, products, services and business information</option>
                  <option value="ticket">Ticket Knowledge — troubleshooting, complaints and support procedures</option>
                </select>

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
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                    gap: 16,
                    marginTop: 12
                  }}>
                    {[
                      {
                        type: "general",
                        title: "General Knowledge Files",
                        description: "Company information, products, services and FAQs."
                      },
                      {
                        type: "ticket",
                        title: "Ticket Knowledge Files",
                        description: "Support procedures, troubleshooting and ticket policies."
                      }
                    ].map((group) => {
                      const groupFiles = knowledgeFiles.filter(
                        (file) => (file.knowledge_type || "general") === group.type
                      );

                      return (
                        <div
                          key={group.type}
                          style={{
                            border: "1px solid #e5e7eb",
                            borderRadius: 10,
                            padding: 14,
                            background: "#fafafa",
                            minWidth: 0
                          }}
                        >
                          <h4 style={{ fontSize: 15, margin: "0 0 5px" }}>
                            {group.title}
                          </h4>
                          <p style={{
                            color: "#6b7280",
                            fontSize: 12,
                            margin: "0 0 12px"
                          }}>
                            {group.description}
                          </p>

                          {groupFiles.length === 0 ? (
                            <p style={{
                              color: "#9ca3af",
                              fontSize: 13,
                              padding: 12,
                              background: "#fff",
                              borderRadius: 8,
                              margin: 0
                            }}>
                              No {group.type === "ticket" ? "ticket" : "general"} knowledge files uploaded.
                            </p>
                          ) : (
                            <div style={{
                              display: "flex",
                              flexDirection: "column",
                              gap: 10
                            }}>
                              {groupFiles.map((file) => (
                                <div
                                  key={file.id}
                                  style={{
                                    display: "flex",
                                    justifyContent: "space-between",
                                    alignItems: "center",
                                    gap: 12,
                                    flexWrap: "wrap",
                                    padding: 12,
                                    border: "1px solid #e5e7eb",
                                    borderRadius: 9,
                                    background: "#fff"
                                  }}
                                >
                                  <div style={{ flex: "1 1 150px", minWidth: 0 }}>
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
                                      {file.file_type.toUpperCase()} · {file.row_count} records · {file.status}
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
                      );
                    })}
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
