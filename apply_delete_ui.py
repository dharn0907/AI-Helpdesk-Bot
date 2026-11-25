from pathlib import Path
import shutil

# Backups
for name in [
    "frontend/src/AdminDashboard.jsx",
    "backend/routes/company_routes.py",
]:
    p = Path(name)
    shutil.copy2(p, p.with_suffix(p.suffix + ".before_delete_ui"))

# Frontend changes
p = Path("frontend/src/AdminDashboard.jsx")
s = p.read_text(encoding="utf-8")

agent_anchor = '  const openConversation = async (conversation) => {'
agent_handler = '''
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

'''
if agent_anchor not in s:
    raise SystemExit("Could not find agent handler insertion point; no frontend changes made.")
if "const deleteSupportAgent" not in s:
    s = s.replace(agent_anchor, agent_handler + agent_anchor, 1)

agent_card_anchor = '                    <div style={{ fontSize: 12, color: "#64748b" }}>Status: {agent.status}</div>'
agent_card_add = agent_card_anchor + '''
                    {agent.status !== "revoked" && (
                      <button type="button" onClick={() => deleteSupportAgent(agent)}
                        style={{ marginTop: 10, background: "#dc2626", color: "#fff", border: 0, borderRadius: 6, padding: "7px 11px", cursor: "pointer" }}>
                        Delete Agent
                      </button>
                    )}'''
if agent_card_anchor not in s:
    raise SystemExit("Could not find agent card status line; no frontend changes made.")
if "Delete Agent" not in s:
    s = s.replace(agent_card_anchor, agent_card_add, 1)

back_anchor = '            Back to Customer Chat\n          </button>'
back_add = back_anchor + '''
          <button type="button" onClick={deleteSelectedChatbot}
            style={{ marginLeft: 8, background: "#dc2626", color: "#fff", border: 0, borderRadius: 6, padding: "9px 13px", cursor: "pointer" }}>
            Delete Chatbot
          </button>
          <button type="button" onClick={deleteCompanyAccount}
            style={{ marginLeft: 8, background: "#991b1b", color: "#fff", border: 0, borderRadius: 6, padding: "9px 13px", cursor: "pointer" }}>
            Delete Company
          </button>'''
if back_anchor not in s:
    raise SystemExit("Could not find Back to Customer Chat button; no frontend changes made.")
if "Delete Company" not in s:
    s = s.replace(back_anchor, back_add, 1)

p.write_text(s, encoding="utf-8")

# Chatbot deletion audit
p = Path("backend/routes/company_routes.py")
s = p.read_text(encoding="utf-8")
if "record_deletion" not in s.split("from services.workspace_auth import", 1)[-1].splitlines()[0]:
    s = s.replace(
        "from services.workspace_auth import get_workspace_company, get_deletion_actor, record_deletion",
        "from services.workspace_auth import get_workspace_company, get_deletion_actor, record_deletion"
    )
    if "from services.workspace_auth import get_workspace_company" in s and "get_deletion_actor" not in s:
        s = s.replace(
            "from services.workspace_auth import get_workspace_company",
            "from services.workspace_auth import get_workspace_company, get_deletion_actor, record_deletion"
        )

audit_anchor = '''    bot.status = "inactive"
    db.commit()
    return {"success": True, "message": "Chatbot deactivated"}'''
audit_replacement = '''    if bot.status != "inactive":
        actor_id = get_deletion_actor(authorization)
        record_deletion(
            db, "chatbot", bot.id, bot.bot_name,
            company["id"], actor_id, "deactivated"
        )
        bot.status = "inactive"
        db.commit()
    return {"success": True, "message": "Chatbot deactivated and recorded"}'''
if audit_anchor not in s:
    raise SystemExit("Could not find chatbot delete implementation; frontend changes saved, chatbot audit not added.")
s = s.replace(audit_anchor, audit_replacement, 1)
p.write_text(s, encoding="utf-8")

print("Dashboard buttons added; chatbot deletion audit added.")
