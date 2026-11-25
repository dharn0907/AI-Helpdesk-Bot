
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

export default function AdminDashboard({ onBack }) {
  const [companyId, setCompanyId] = useState(null);
  const [companyName, setCompanyName] = useState("");
  const [newCompanyName, setNewCompanyName] = useState("");
  const [config, setConfig] = useState(emptyConfig);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [knowledgeFiles, setKnowledgeFiles] = useState([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const headers = () => ({
    "Content-Type": "application/json"
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
    connect();
  }, []);

  const createCompany = async (event) => {
    event.preventDefault();

    if (!newCompanyName.trim()) {
      setError("Enter your company name.");
      return;
    }

    setLoading(true);
    setError("");
    setMessage("");

    try {
      const response = await fetch(`${API}/companies/`, {
        method: "POST",
        headers: headers(),
        body: JSON.stringify({ name: newCompanyName.trim() })
      });

      await readResponse(response);

      setMessage("Company created successfully.");
      await loadCompany();
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
        headers: {
        },
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

              <button disabled={loading} style={buttonStyle}>
                {loading ? "Creating..." : "Create Company"}
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
