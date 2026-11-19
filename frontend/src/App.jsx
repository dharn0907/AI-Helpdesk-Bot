
import { useEffect, useRef, useState } from "react";
import AdminDashboard from "./AdminDashboard.jsx";

function App() {
  const [activeView, setActiveView] = useState("chat");
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [emailAddress, setEmailAddress] = useState("");
  const [emailError, setEmailError] = useState("");

  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [uploading, setUploading] = useState(false);

  const fileInputRef = useRef(null);
  const sessionIdRef = useRef(crypto.randomUUID());
  const customerIdRef = useRef(
    localStorage.getItem("helpdesk_customer_id") || crypto.randomUUID()
  );

  useEffect(() => {
    localStorage.setItem(
      "helpdesk_customer_id",
      customerIdRef.current
    );
  }, []);
  const requestInProgressRef = useRef(false);

  // Clean up image preview URL
  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  // Send text messages and interactive confirmation choices.
  const sendChatMessage = async (
    requestText,
    displayText = requestText
  ) => {
    if (
      !requestText.trim() ||
      loading ||
      uploading ||
      requestInProgressRef.current
    ) return;

    requestInProgressRef.current = true;

    setMessages((prev) => [
      ...prev,
      { sender: "user", text: displayText }
    ]);

    setLoading(true);

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/chat",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            message: requestText,
            session_id: sessionIdRef.current,
            customer_id: customerIdRef.current
          })
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Backend request failed."
        );
      }

      setMessages((prev) => [
        ...prev,
        {
          sender: "bot",
          text: data.reply || "No reply received.",
          actions: data.awaiting_summary_confirmation
            ? "summary_confirmation"
            : data.awaiting_email
              ? "email_collection"
              : null
        }
      ]);

    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          sender: "bot",
          text: `Unable to connect to the backend: ${error.message}`
        }
      ]);
    } finally {
      requestInProgressRef.current = false;
      setLoading(false);
    }
  };

  // Send a normal customer message.
  const sendMessage = async () => {
    if (!message.trim() || loading || uploading) return;

    const userMessage = message.trim();
    setMessage("");

    await sendChatMessage(userMessage, userMessage);
  };

  // Handle summary confirmation buttons.
  const handleSummaryChoice = async (confirmed) => {
    if (loading || uploading || requestInProgressRef.current) return;

    if (confirmed) {
      await sendChatMessage("yes", "Yes, that's correct");
    } else {
      await sendChatMessage("no", "No, make changes");
    }
  };

  // Validate and submit the customer's email address.
  const handleEmailSubmit = async (event) => {
    event.preventDefault();

    if (loading || uploading || requestInProgressRef.current) return;

    const email = emailAddress.trim();
    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!email) {
      setEmailError("Please enter your email address.");
      return;
    }

    if (!emailPattern.test(email)) {
      setEmailError("Please enter a valid email address, such as name@example.com.");
      return;
    }

    setEmailError("");
    await sendChatMessage(email, email);
    setEmailAddress("");
  };

  // Select an image
  const handleFileChange = (event) => {
    const file = event.target.files?.[0];

    if (!file) return;

    if (!file.type.startsWith("image/")) {
      alert("Please select an image file.");
      event.target.value = "";
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      alert("Image size must not exceed 10 MB.");
      event.target.value = "";
      return;
    }

    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
  };

  // Upload image, extract text using OCR, and process the complaint
  const uploadImage = async () => {
    if (!selectedFile || uploading || loading) return;

    setUploading(true);

    const file = selectedFile;

    setMessages((prev) => [
      ...prev,
      {
        sender: "user",
        text: `Uploaded complaint image: ${file.name}`
      }
    ]);

    const formData = new FormData();
    formData.append("file", file);

    try {
      // STEP 1: Send image to OCR API
      const response = await fetch(
        "http://127.0.0.1:8000/image/extract-text",
        {
          method: "POST",
          body: formData
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Image processing failed."
        );
      }

      const extractedText = data.extracted_text || "";

      // STEP 2: Display extracted text
      setMessages((prev) => [
        ...prev,
        {
          sender: "bot",
          text: extractedText.trim()
            ? `Text extracted successfully:\n\n${extractedText}`
            : "The image was uploaded, but no readable text was detected."
        }
      ]);

      // STEP 3: Send OCR text to chatbot backend
      if (extractedText.trim()) {
        const chatResponse = await fetch(
          "http://127.0.0.1:8000/chat",
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json"
            },
            body: JSON.stringify({
              message: extractedText,
              session_id: sessionIdRef.current,
            customer_id: customerIdRef.current
            })
          }
        );

        const chatData = await chatResponse.json();

        if (!chatResponse.ok) {
          throw new Error(
            chatData.detail || "Complaint processing failed."
          );
        }

        // STEP 4: Display the chatbot response
        setMessages((prev) => [
          ...prev,
          {
            sender: "bot",
            text: chatData.reply || "Complaint analyzed successfully."
          }
        ]);
      }

    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          sender: "bot",
          text: `Unable to process complaint: ${error.message}`
        }
      ]);
    } finally {
      setUploading(false);
      setSelectedFile(null);
      setPreviewUrl(null);

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  if (activeView === "admin") {
    return <AdminDashboard onBack={() => setActiveView("chat")} />;
  }

  return (
    <div style={styles.container}>
      <div style={styles.chatWindow}>

        {/* Header */}
        <header style={styles.header}>
          <div>
            <h2>AI Helpdesk Bot</h2>
            <p>Your personal customer support assistant</p>
          </div>

          <button
            onClick={() => setActiveView("admin")}
            style={{ padding: "8px 12px", border: 0, borderRadius: 7, cursor: "pointer" }}
          >Admin Dashboard</button>

          <span style={styles.status}>â— Online</span>
        </header>

        {/* Chat messages */}
        <div style={styles.messages}>

          {messages.length === 0 && (
            <div style={styles.welcome}>
              <h2>Hello! ðŸ‘‹</h2>
              <p>How can I help you today?</p>
              <p>You can also upload a screenshot of your complaint.</p>
            </div>
          )}

          {messages.map((msg, index) => (
            <div
              key={index}
              style={{
                ...styles.message,
                alignSelf:
                  msg.sender === "user" ? "flex-end" : "flex-start",
                background:
                  msg.sender === "user" ? "#2563eb" : "#e5e7eb",
                color:
                  msg.sender === "user" ? "white" : "#111827"
              }}
            >
              <div style={{ whiteSpace: "pre-wrap" }}>
                {msg.text}
              </div>

              {msg.sender === "bot" &&
                msg.actions === "summary_confirmation" && (
                  <div
                    style={{
                      display: "flex",
                      flexWrap: "wrap",
                      gap: "10px",
                      marginTop: "14px"
                    }}
                  >
                    <button
                      type="button"
                      disabled={loading || uploading}
                      onClick={() => handleSummaryChoice(true)}
                      style={{
                        background: "#15803d",
                        color: "white",
                        border: "none",
                        borderRadius: "8px",
                        padding: "10px 16px",
                        cursor: loading ? "not-allowed" : "pointer",
                        opacity: loading ? 0.6 : 1
                      }}
                    >
                      Yes, that's correct
                    </button>

                    <button
                      type="button"
                      disabled={loading || uploading}
                      onClick={() => handleSummaryChoice(false)}
                      style={{
                        background: "white",
                        color: "#374151",
                        border: "1px solid #9ca3af",
                        borderRadius: "8px",
                        padding: "10px 16px",
                        cursor: loading ? "not-allowed" : "pointer",
                        opacity: loading ? 0.6 : 1
                      }}
                    >
                      No, make changes
                    </button>
                  </div>
                )}

              {msg.sender === "bot" &&
                msg.actions === "email_collection" && (
                  <form
                    onSubmit={handleEmailSubmit}
                    style={{
                      marginTop: "16px",
                      padding: "16px",
                      background: "white",
                      border: "1px solid #dbe3ef",
                      borderRadius: "12px",
                      width: "min(100%, 340px)",
                      boxSizing: "border-box"
                    }}
                  >
                    <div style={{ marginBottom: "12px" }}>
                      <div style={{
                        fontSize: "15px",
                        fontWeight: "700",
                        color: "#111827",
                        marginBottom: "5px"
                      }}>
                        <span role="img" aria-label="email">??</span>
                        {" "}Where should we send your updates?
                      </div>

                      <div style={{
                        fontSize: "13px",
                        color: "#6b7280",
                        lineHeight: "1.5"
                      }}>
                        Enter your email address so our support team
                        can contact you about this ticket.
                      </div>
                    </div>

                    <label
                      htmlFor={`customer-email-${index}`}
                      style={{
                        display: "block",
                        fontSize: "13px",
                        fontWeight: "600",
                        color: "#374151",
                        marginBottom: "6px"
                      }}
                    >
                      Email address
                    </label>

                    <input
                      id={`customer-email-${index}`}
                      type="email"
                      autoComplete="email"
                      required
                      value={emailAddress}
                      onChange={(event) => {
                        setEmailAddress(event.target.value);
                        setEmailError("");
                      }}
                      placeholder="name@example.com"
                      disabled={loading || uploading}
                      style={{
                        width: "100%",
                        boxSizing: "border-box",
                        padding: "12px",
                        border: emailError
                          ? "1px solid #dc2626"
                          : "1px solid #cbd5e1",
                        borderRadius: "8px",
                        fontSize: "14px",
                        outline: "none",
                        marginBottom: "8px"
                      }}
                    />

                    {emailError && (
                      <div
                        role="alert"
                        style={{
                          color: "#dc2626",
                          fontSize: "12px",
                          marginBottom: "10px"
                        }}
                      >
                        {emailError}
                      </div>
                    )}

                    <button
                      type="submit"
                      disabled={loading || uploading}
                      style={{
                        width: "100%",
                        padding: "11px",
                        background: loading ? "#93c5fd" : "#2563eb",
                        color: "white",
                        border: "none",
                        borderRadius: "8px",
                        fontSize: "14px",
                        fontWeight: "600",
                        cursor: loading ? "not-allowed" : "pointer"
                      }}
                    >
                      {loading ? "Submitting..." : "Submit email"}
                    </button>

                    <div style={{
                      fontSize: "11px",
                      color: "#6b7280",
                      marginTop: "9px",
                      textAlign: "center"
                    }}>
                      Your email will be used for support ticket updates.
                    </div>
                  </form>
                )}
            </div>
          ))}

          {loading && <p>Bot is typing...</p>}

          {uploading && (
            <p>Analyzing your image...</p>
          )}

        </div>

        {/* Image preview */}
        {previewUrl && (
          <div style={styles.previewArea}>
            <img
              src={previewUrl}
              alt="Selected complaint"
              style={styles.previewImage}
            />

            <div style={styles.previewInfo}>
              <p>{selectedFile?.name}</p>

              <button
                onClick={() => {
                  setSelectedFile(null);
                  setPreviewUrl(null);

                  if (fileInputRef.current) {
                    fileInputRef.current.value = "";
                  }
                }}
                style={styles.removeButton}
              >
                Remove
              </button>
            </div>

            <button
              onClick={uploadImage}
              disabled={uploading || loading}
              style={styles.uploadButton}
            >
              {uploading ? "Processing..." : "Upload & Analyze Complaint"}
            </button>
          </div>
        )}

        {/* Input area */}
        <div style={styles.inputArea}>

          <input
            ref={fileInputRef}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            onChange={handleFileChange}
            style={{ display: "none" }}
          />

          <button
            style={styles.attachButton}
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading || loading}
            title="Attach complaint image"
          >
            ðŸ“Ž
          </button>

          <input
            style={styles.input}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") sendMessage();
            }}
            placeholder="Type your message..."
            disabled={uploading || loading}
          />

          <button
            style={styles.button}
            onClick={sendMessage}
            disabled={loading || uploading}
          >
            Send
          </button>

        </div>
      </div>
    </div>
  );
}

// UI styles
const styles = {
  container: {
    minHeight: "100vh",
    background: "#f3f4f6",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    padding: "20px",
    fontFamily: "Arial, sans-serif"
  },

  chatWindow: {
    width: "100%",
    maxWidth: "700px",
    height: "650px",
    background: "white",
    borderRadius: "15px",
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
    boxShadow: "0 5px 25px rgba(0,0,0,0.1)"
  },

  header: {
    background: "#1e40af",
    color: "white",
    padding: "20px",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center"
  },

  status: {
    fontSize: "13px",
    color: "#86efac"
  },

  messages: {
    flex: 1,
    padding: "20px",
    display: "flex",
    flexDirection: "column",
    gap: "15px",
    overflowY: "auto"
  },

  welcome: {
    textAlign: "center",
    margin: "auto",
    color: "#374151"
  },

  message: {
    maxWidth: "75%",
    padding: "12px 16px",
    borderRadius: "12px",
    lineHeight: "1.5",
    overflowWrap: "anywhere"
  },

  inputArea: {
    display: "flex",
    gap: "10px",
    padding: "15px",
    borderTop: "1px solid #e5e7eb"
  },

  input: {
    flex: 1,
    minWidth: 0,
    padding: "13px",
    border: "1px solid #d1d5db",
    borderRadius: "8px",
    outline: "none",
    fontSize: "15px"
  },

  button: {
    background: "#2563eb",
    color: "white",
    border: "none",
    borderRadius: "8px",
    padding: "0 22px",
    cursor: "pointer"
  },

  attachButton: {
    background: "#e5e7eb",
    border: "none",
    borderRadius: "8px",
    padding: "0 15px",
    fontSize: "20px",
    cursor: "pointer"
  },

  previewArea: {
    padding: "12px 15px",
    borderTop: "1px solid #e5e7eb",
    background: "#f9fafb"
  },

  previewImage: {
    maxWidth: "150px",
    maxHeight: "100px",
    objectFit: "contain",
    borderRadius: "8px"
  },

  previewInfo: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: "10px",
    fontSize: "13px"
  },

  removeButton: {
    border: "none",
    background: "transparent",
    color: "#dc2626",
    cursor: "pointer"
  },

  uploadButton: {
    background: "#16a34a",
    color: "white",
    border: "none",
    borderRadius: "8px",
    padding: "10px 15px",
    cursor: "pointer"
  }
};

export default App;

