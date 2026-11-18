
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Headset, Mail, Lock, ArrowRight } from "lucide-react";

function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const navigate = useNavigate();

  const handleLogin = (e) => {
    e.preventDefault();

    // Temporary demo navigation.
    // Real authentication will be connected later.
    navigate("/");
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-logo">
          <Headset size={30} />
        </div>

        <h1>Welcome Back</h1>
        <p>Sign in to your HelpDesk AI workspace</p>

        <form onSubmit={handleLogin}>
          <label>Email Address</label>
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

          <label>Password</label>
          <div className="login-input">
            <Lock size={18} />
            <input
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <button type="submit" className="login-button">
            Sign In <ArrowRight size={18} />
          </button>
        </form>

        <span className="login-note">
          Human Support Agent Portal
        </span>
      </div>
    </div>
  );
}

export default Login;
