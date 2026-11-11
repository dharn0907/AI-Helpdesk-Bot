
import { useEffect, useRef, useState } from "react";

function App() {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [uploading, setUploading] = useState(false);

  const fileInputRef = useRef(null);
  const sessionIdRef = useRef(crypto.randomUUID());

  // Clean up image preview URL
  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  // Send normal text messages to BERT
  const sendMessage = async () => {
    if (!message.trim() || loading || uploading) return;

    const userMessage = message.trim();

    setMessages((prev) => [
      ...prev,
      { sender: "user", text: userMessage }
    ]);

    setMessage("");
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
  message: userMessage,
  session_id: sessionIdRef.current
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
          intent: data.intent,
          confidence: data.confidence
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
      setLoading(false);
    }
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

  // Upload image, extract text using OCR, and classify using BERT
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

      // STEP 3: Send OCR text to BERT
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
  session_id: sessionIdRef.current
})
          }
        );

        const chatData = await chatResponse.json();

        if (!chatResponse.ok) {
          throw new Error(
            chatData.detail || "Complaint classification failed."
          );
        }

        // STEP 4: Display BERT classification
        setMessages((prev) => [
          ...prev,
          {
            sender: "bot",
            text: chatData.reply || "Complaint analyzed successfully.",
            intent: chatData.intent,
            confidence: chatData.confidence
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

  return (
    <div style={styles.container}>
      <div style={styles.chatWindow}>

        {/* Header */}
        <header style={styles.header}>
          <div>
            <h2>AI Helpdesk Bot</h2>
            <p>Your personal customer support assistant</p>
          </div>

          <span style={styles.status}>● Online</span>
        </header>

        {/* Chat messages */}
        <div style={styles.messages}>

          {messages.length === 0 && (
            <div style={styles.welcome}>
              <h2>Hello! 👋</h2>
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

              {/* Display BERT prediction */}
              {msg.sender === "bot" && msg.intent && (
                <div style={styles.prediction}>
                  <div>
                    <strong>Detected category:</strong> {msg.intent}
                  </div>

                  {typeof msg.confidence === "number" && (
                    <div>
                      <strong>Confidence:</strong>{" "}
                      {(msg.confidence * 100).toFixed(2)}%
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}

          {loading && <p>Bot is typing...</p>}

          {uploading && (
            <p>Analyzing your image with OCR and BERT...</p>
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
            📎
          </button>

          <input
            style={styles.input}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") sendMessage();
            }}
            placeholder="Type your complaint..."
            disabled={uploading}
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

  prediction: {
    marginTop: "10px",
    padding: "8px",
    background: "#dbeafe",
    color: "#1e40af",
    borderRadius: "6px",
    fontSize: "12px",
    lineHeight: "1.6"
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
