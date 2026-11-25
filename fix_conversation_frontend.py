from pathlib import Path

p = Path("agent-frontend/src/pages/Conversations.jsx")
s = p.read_text(encoding="utf-8")

if "function getAgentHeaders" not in s:
    s = s.replace(
        'const API = "http://127.0.0.1:8000";',
        '''const API = "http://127.0.0.1:8000";

function getAgentHeaders() {
  const agent = JSON.parse(sessionStorage.getItem("agent") || "null");
  if (!agent?.email) {
    throw new Error("Agent session not found. Please log in again.");
  }
  return { "X-Agent-Email": agent.email };
}'''
    )

s = s.replace(
    'fetch(`${API}/conversations/`)',
    'fetch(`${API}/conversations/`, { headers: getAgentHeaders() })'
)
s = s.replace(
    'fetch(`${API}/conversations/${id}`)',
    'fetch(`${API}/conversations/${id}`, { headers: getAgentHeaders() })'
)

s = s.replace(
    'headers: { "Content-Type": "application/json" },',
    'headers: { "Content-Type": "application/json", ...getAgentHeaders() },'
)

# DELETE request needs agent identity too
s = s.replace(
    'method: "DELETE",',
    'method: "DELETE",\n          headers: getAgentHeaders(),'
)

p.write_text(s, encoding="utf-8")
print("Frontend conversation requests updated.")
