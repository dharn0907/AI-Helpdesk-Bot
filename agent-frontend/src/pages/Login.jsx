import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Headset, Mail, ArrowRight } from "lucide-react";

const API_BASE_URL = "http://127.0.0.1:8000";

function Login() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/tickets/agents/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim().toLowerCase() }),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || "This email is not registered as an approved agent.");
      }

      sessionStorage.setItem("agent", JSON.stringify(result));
      navigate("/", { replace: true });
    } catch (err) {
      setError(err.message || "Unable to log in. Check your backend connection.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-logo"><Headset size={30} /></div>
        <h1>Welcome Back</h1>
        <p>Sign in to your HelpDesk AI workspace</p>
        <form onSubmit={handleLogin}>
          <label>Registered Email Address</label>
          <div className="login-input">
            <Mail size={18} />
            <input
              type="email"
              placeholder="agent@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          {error && <p style={{ color: "#dc2626" }}>{error}</p>}
          <button type="submit" className="login-button" disabled={loading}>
            {loading ? "Verifying..." : "Sign In"} <ArrowRight size={18} />
          </button>
        </form>
        <span className="login-note">Human Support Agent Portal</span>
      </div>
    </div>
  );
}

export default Login;
