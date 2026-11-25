from pathlib import Path

p = Path("frontend/src/BotManager.jsx")
s = p.read_text(encoding="utf-8-sig")

if 'import TestBot from "./TestBot";' not in s:
    s = s.replace(
        'import AdminDashboard from "./AdminDashboard";',
        'import AdminDashboard from "./AdminDashboard";\nimport TestBot from "./TestBot";'
    )

if "const [testBotOpen, setTestBotOpen]" not in s:
    s = s.replace(
        'const [selectedBot, setSelectedBot] = useState(null);',
        'const [selectedBot, setSelectedBot] = useState(null);\n  const [testBotOpen, setTestBotOpen] = useState(false);'
    )

s = s.replace(
    '<button onClick={() => setSelectedBot(null)}>← Back to My Chatbots</button>',
    '<button onClick={() => { setSelectedBot(null); setTestBotOpen(false); }}>← Back to My Chatbots</button>'
)

if 'testBotOpen ? "Close Test Bot"' not in s:
    s = s.replace(
        '<strong style={{ marginLeft: 16 }}>{selectedBot.bot_name}</strong>',
        '<strong style={{ marginLeft: 16 }}>{selectedBot.bot_name}</strong>\n          <button style={{ marginLeft: 16 }} onClick={() => setTestBotOpen(v => !v)}>{testBotOpen ? "Close Test Bot" : "Test Bot"}</button>'
    )

if 'testBotOpen && <TestBot' not in s:
    s = s.replace(
        '<AdminDashboard\n          session={session}',
        '{testBotOpen && <TestBot key={selectedBot.public_id} chatbot={selectedBot} />}\n        <AdminDashboard\n          session={session}'
    )

if 'testBotOpen && <TestBot' not in s:
    raise SystemExit("Patch failed; BotManager unchanged.")

p.write_text(s, encoding="utf-8")
print("BotManager updated successfully.")
