import { useState } from "react";

const API = "http://127.0.0.1:8000";

export default function CompanyAccess({ onComplete }) {
  const [step, setStep] = useState("email");
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [token, setToken] = useState("");
  const [companies, setCompanies] = useState([]);
  const [companyName, setCompanyName] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const request = async (path, options = {}, authToken = "") => {
    const response = await fetch(API + path, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        ...(options.headers || {})
      }
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || "Something went wrong.");
    }
    return data;
  };

  const sendOtp = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setNotice("");

    try {
      const result = await request("/companies/auth/request-otp", {
        method: "POST",
        body: JSON.stringify({ email })
      });
      setEmail(result.email || email.trim().toLowerCase());
      setStep("otp");
      setNotice("OTP sent. Check your email.");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const verifyOtp = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setNotice("");

    try {
      const result = await request("/companies/auth/verify-otp", {
        method: "POST",
        body: JSON.stringify({ email, otp })
      });

      setToken(result.access_token);

      const companyResult = await request(
        "/companies/auth/companies",
        {},
        result.access_token
      );

      setCompanies(companyResult.companies || []);
      setStep("companies");
      setNotice("Email verified successfully.");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const createCompany = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      await request(
        "/companies/auth/companies",
        {
          method: "POST",
          body: JSON.stringify({ name: companyName })
        },
        token
      );

      const result = await request(
        "/companies/auth/companies",
        {},
        token
      );

      setCompanies(result.companies || []);
      setCompanyName("");
      setShowCreate(false);
      setNotice("Company created successfully. Select it to continue.");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const selectCompany = (company) => {
    onComplete({
      token,
      company,
      email
    });
  };

  const styles = {
    page: {
      minHeight: "100vh",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      background: "#f3f4f6",
      padding: "24px",
      fontFamily: "Arial, sans-serif"
    },
    panel: {
      width: "100%",
      maxWidth: "440px",
      background: "#ffffff",
      borderRadius: "16px",
      padding: "32px",
      boxShadow: "0 12px 40px rgba(0,0,0,0.08)"
    },
    heading: {
      fontSize: "25px",
      fontWeight: "700",
      color: "#111827",
      marginBottom: "8px"
    },
    subtitle: {
      color: "#6b7280",
      fontSize: "14px",
      lineHeight: 1.6,
      marginBottom: "25px"
    },
    input: {
      width: "100%",
      boxSizing: "border-box",
      padding: "13px",
      border: "1px solid #d1d5db",
      borderRadius: "8px",
      fontSize: "15px",
      marginBottom: "15px"
    },
    button: {
      width: "100%",
      padding: "13px",
      border: "none",
      borderRadius: "8px",
      background: "#2563eb",
      color: "white",
      fontSize: "15px",
      fontWeight: "600",
      cursor: "pointer"
    },
    secondary: {
      width: "100%",
      padding: "12px",
      border: "1px solid #d1d5db",
      borderRadius: "8px",
      background: "white",
      color: "#374151",
      fontSize: "14px",
      cursor: "pointer",
      marginTop: "12px"
    },
    company: {
      width: "100%",
      textAlign: "left",
      padding: "16px",
      border: "1px solid #e5e7eb",
      borderRadius: "9px",
      background: "#fff",
      cursor: "pointer",
      marginBottom: "10px"
    },
    error: {
      color: "#dc2626",
      background: "#fef2f2",
      padding: "10px",
      borderRadius: "7px",
      fontSize: "13px",
      marginBottom: "14px"
    },
    notice: {
      color: "#166534",
      background: "#f0fdf4",
      padding: "10px",
      borderRadius: "7px",
      fontSize: "13px",
      marginBottom: "14px"
    }
  };

  return (
    <div style={styles.page}>
      <div style={styles.panel}>
        <div style={{ color: "#2563eb", fontWeight: "700", marginBottom: "18px" }}>
          AI HELPDESK
        </div>

        {step === "email" && (
          <>
            <div style={styles.heading}>Welcome back</div>
            <div style={styles.subtitle}>
              Enter your email address. We will send you a one-time verification code.
            </div>

            {error && <div style={styles.error}>{error}</div>}

            <form onSubmit={sendOtp}>
              <input
                style={styles.input}
                type="email"
                placeholder="Enter your email address"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoFocus
              />
              <button style={styles.button} disabled={loading}>
                {loading ? "Sending OTP..." : "Get OTP"}
              </button>
            </form>
          </>
        )}

        {step === "otp" && (
          <>
            <div style={styles.heading}>Verify your email</div>
            <div style={styles.subtitle}>
              Enter the 6-digit code sent to <b>{email}</b>.
            </div>

            {notice && <div style={styles.notice}>{notice}</div>}
            {error && <div style={styles.error}>{error}</div>}

            <form onSubmit={verifyOtp}>
              <input
                style={styles.input}
                type="text"
                inputMode="numeric"
                maxLength={6}
                placeholder="Enter 6-digit OTP"
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
                required
                autoFocus
              />
              <button style={styles.button} disabled={loading}>
                {loading ? "Verifying..." : "Verify OTP"}
              </button>
            </form>

            <button
              style={styles.secondary}
              onClick={() => {
                setStep("email");
                setOtp("");
                setError("");
                setNotice("");
              }}
            >
              Change email address
            </button>
          </>
        )}

        {step === "companies" && (
          <>
            <div style={styles.heading}>Choose your company</div>
            <div style={styles.subtitle}>
              Verified as <b>{email}</b>. Select the company workspace you want to access.
            </div>

            {notice && <div style={styles.notice}>{notice}</div>}
            {error && <div style={styles.error}>{error}</div>}

            {companies.length > 0 ? (
              companies.map((company) => (
                <button
                  key={company.id}
                  style={styles.company}
                  onClick={() => selectCompany(company)}
                >
                  <div style={{ fontWeight: "700", color: "#111827" }}>
                    {company.name}
                  </div>
                  <div style={{ fontSize: "12px", color: "#6b7280", marginTop: "5px" }}>
                    Open company workspace →
                  </div>
                </button>
              ))
            ) : (
              <div style={styles.subtitle}>
                No company is connected to this email yet. Create your first company to continue.
              </div>
            )}

            {showCreate ? (
              <form onSubmit={createCompany}>
                <input
                  style={styles.input}
                  placeholder="Enter company name"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  required
                  autoFocus
                />
                <button style={styles.button} disabled={loading}>
                  {loading ? "Creating..." : "Create company"}
                </button>
                <button
                  type="button"
                  style={styles.secondary}
                  onClick={() => setShowCreate(false)}
                >
                  Cancel
                </button>
              </form>
            ) : (
              <button
                style={styles.secondary}
                onClick={() => {
                  setShowCreate(true);
                  setError("");
                  setNotice("");
                }}
              >
                + Create a new company
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}
