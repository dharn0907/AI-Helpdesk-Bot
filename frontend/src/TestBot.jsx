import { useState } from "react";

const API = "http://127.0.0.1:8000";

export default function TestBot({ chatbot }) {
  const [messages, setMessages] = useState([
    { role: "bot", text: `Hello! Welcome to ${chatbot.bot_name}. I'm here to help. What can I assist you with today?` }
  ]);
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [sessionId] = useState(() => `test-${chatbot.public_id}-${crypto.randomUUID()}`);

  async function sendMessage(e) {
    e.preventDefault();
    const text = message.trim();
    if (!text || sending) return;

    setMessages(prev => [...prev, { role: "user", text }]);
    setMessage("");
    setSending(true);

    try {
      const res = await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          session_id: sessionId,
          bot_public_id: chatbot.public_id
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Chat request failed");
      setMessages(prev => [...prev, {
        role: "bot",
        text: data.reply || "The chatbot returned an empty response."
      }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: "error", text: err.message }]);
    } finally {
      setSending(false);
    }
  }

  return (
    <section style={{
      maxWidth: 920, margin: "28px auto", padding: 0,
      overflow: "hidden", borderRadius: 20,
      background: "#120d10", border: "1px solid #48202e",
      boxShadow: "0 25px 80px #0009"
    }}>
      <div style={{
        padding: "22px 26px", display: "flex",
        justifyContent: "space-between", alignItems: "center",
        gap: 15, flexWrap: "wrap",
        background: "linear-gradient(110deg,#35101e,#1a1015)",
        borderBottom: "1px solid #542033"
      }}>
        <div style={{display:"flex",alignItems:"center",gap:14}}>
          <div style={{
            width:48,height:48,borderRadius:15,
            display:"grid",placeItems:"center",fontSize:22,
            background:"linear-gradient(135deg,#a51036,#f43f5e)",
            boxShadow:"0 7px 25px #e11d4840"
          }}>✦</div>
          <div>
            <h2 style={{margin:0,fontSize:19}}>{chatbot.bot_name}</h2>
            <p style={{margin:"5px 0 0",fontSize:12,color:"#d6aab8"}}>LIVE BOT PREVIEW · REAL AI RESPONSE</p>
          </div>
        </div>
        <span style={{
          fontSize:11,letterSpacing:1.1,color:"#ff9db1",
          border:"1px solid #87334c",background:"#541426",
          borderRadius:30,padding:"7px 12px"
        }}>● CONNECTED</span>
      </div>

      <div style={{
        padding:"18px 24px",display:"flex",alignItems:"center",
        gap:9,borderBottom:"1px solid #302027",
        color:"#a9959d",fontSize:12
      }}>
        <span style={{color:"#f43f5e"}}>✦</span>
        Preview your chatbot by sending a message below.
      </div>

      <div style={{
        height:390,overflowY:"auto",padding:"25px 22px",
        display:"flex",flexDirection:"column",gap:18,
        background:"radial-gradient(ellipse at 50% 0%,#27121b,#100c0f 70%)"
      }}>
        {messages.map((m,i) => (
          <div key={i} style={{
            display:"flex",gap:10,
            justifyContent:m.role==="user"?"flex-end":"flex-start",
            alignItems:"flex-end"
          }}>
            {m.role!=="user" && <div style={{
              width:30,height:30,flexShrink:0,borderRadius:10,
              display:"grid",placeItems:"center",
              background:"#64152d",color:"#ff9db1",fontSize:14
            }}>{m.role==="error"?"!":"✦"}</div>}
            <div style={{
              maxWidth:"78%",padding:"13px 16px",
              borderRadius:m.role==="user"?"16px 16px 4px 16px":"16px 16px 16px 4px",
              background:m.role==="user"
                ?"linear-gradient(135deg,#9f1239,#e11d48)"
                :m.role==="error"?"#421522":"#21171d",
              border:m.role==="user"?"1px solid #ed4268":"1px solid #49303a",
              color:m.role==="error"?"#ff9bad":"#f8eaf0",
              fontSize:14,lineHeight:1.65,whiteSpace:"pre-wrap",
              boxShadow:"0 5px 18px #0003"
            }}>{m.text}</div>
          </div>
        ))}
        {sending && <div style={{color:"#d9a8b8",fontSize:13,paddingLeft:42}}>✦ Thinking...</div>}
      </div>

      <form onSubmit={sendMessage} style={{
        display:"flex",gap:11,padding:"18px 20px",
        borderTop:"1px solid #39232c",background:"#171014"
      }}>
        <input
          value={message}
          onChange={e=>setMessage(e.target.value)}
          placeholder="Type your message here..."
          disabled={sending}
          style={{
            flex:1,minWidth:0,padding:"14px 16px",
            borderRadius:12,background:"#0d090c",
            border:"1px solid #49313a",color:"#fff",fontSize:14
          }}
        />
        <button type="submit" disabled={sending||!message.trim()} style={{
          minWidth:105,borderRadius:12,
          background:"linear-gradient(135deg,#a51036,#f02d57)",
          border:0,color:"#fff",fontWeight:700
        }}>{sending?"Sending...":"Send  ➤"}</button>
      </form>
      <div style={{
        padding:"0 20px 15px",background:"#171014",
        color:"#76616b",fontSize:11,textAlign:"center"
      }}>Powered by your configured chatbot · Messages use the actual chat API</div>
    </section>
  );
}
