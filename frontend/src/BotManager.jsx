import { useEffect, useState } from "react";
import AdminDashboard from "./AdminDashboard";
import TestBot from "./TestBot";
import "./index.css";

const API = "http://127.0.0.1:8000";

export default function BotManager({ session }) {
  const [bots, setBots] = useState([]);
  const [selectedBot, setSelectedBot] = useState(null);
  const [testBotOpen, setTestBotOpen] = useState(false);
  const [botName, setBotName] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const headers = {
    Authorization: `Bearer ${session.token}`,
    "X-Company-ID": String(session.company.id),
    "Content-Type": "application/json",
  };

  async function loadBots() {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API}/companies/current/chatbots`, { headers });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Could not load chatbots");
      setBots(Array.isArray(data) ? data : []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadBots();
  }, [session.token, session.company.id]);

  async function createBot(e) {
    e.preventDefault();
    if (!botName.trim()) return;
    setSaving(true);
    setError("");
    try {
      const res = await fetch(`${API}/companies/current/chatbots`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          bot_name: botName.trim(),
          description: description.trim(),
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Bot creation failed");
      setBotName("");
      setDescription("");
      await loadBots();
      setSelectedBot(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  if (selectedBot) {
    return (
      <div>
        <div style={{ padding: "12px 24px", borderBottom: "1px solid #ddd" }}>
          <button onClick={() => { setSelectedBot(null); setTestBotOpen(false); }}>â† Back to My Chatbots</button>
          <strong style={{ marginLeft: 16 }}>{selectedBot.bot_name}</strong>
          <button style={{ marginLeft: 16 }} onClick={() => setTestBotOpen(v => !v)}>{testBotOpen ? "Close Test Bot" : "Test Bot"}</button>
        </div>
        {testBotOpen && <TestBot key={selectedBot.public_id} chatbot={selectedBot} />}
        <AdminDashboard
          session={session}
          chatbot={selectedBot}
          onBack={() => setSelectedBot(null)}
        />
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", padding: 28 }}>
      <h2>My Chatbots</h2>
      <p>Manage the chatbots created for {session.company.name}.</p>

      <form onSubmit={createBot} style={{
        display: "flex", flexWrap: "wrap", gap: 10,
        padding: 18, margin: "22px 0", border: "1px solid #ddd",
        borderRadius: 12
      }}>
        <input
          value={botName}
          onChange={e => setBotName(e.target.value)}
          placeholder="Enter chatbot name"
          required
          style={{ flex: "1 1 220px", padding: 12 }}
        />
        <input
          value={description}
          onChange={e => setDescription(e.target.value)}
          placeholder="Description (optional)"
          style={{ flex: "2 1 260px", padding: 12 }}
        />
        <button type="submit" disabled={saving} style={{ padding: "12px 22px" }}>
          {saving ? "Creating..." : "+ Create Bot"}
        </button>
      </form>

      {error && <p style={{ color: "red" }}>{error}</p>}
      {loading ? <p>Loading chatbots...</p> : (
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill,minmax(240px,1fr))",
          gap: 16
        }}>
          {bots.map(bot => (
            <button
              key={bot.id}
              onClick={() => setSelectedBot(bot)}
              style={{
                textAlign: "left", padding: 20, border: "1px solid #ddd",
                borderRadius: 12, background: "white", cursor: "pointer"
              }}
            >
              <strong style={{ display: "block", fontSize: 17 }}>
                {bot.bot_name}
              </strong>
              <p>{bot.description || "No description added"}</p>
              <small>Status: {bot.status}</small>
              <p style={{ marginBottom: 0 }}>Open workspace â†’</p>
            </button>
          ))}
          {bots.length === 0 && (
            <p>No chatbots yet. Create your first chatbot above.</p>
          )}
        </div>
      )}
    </div>
  );
}

