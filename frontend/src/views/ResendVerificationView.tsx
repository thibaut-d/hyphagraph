import React, { useState } from "react";
import { resendVerificationEmail } from "../api/auth";
import { Link } from "react-router-dom";
import { useNotification } from "../notifications/NotificationContext";
import { parseError } from "../utils/errorHandler";

export default function ResendVerificationView() {
  const { showError } = useNotification();
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await resendVerificationEmail(email);
      setSubmitted(true);
    } catch (err: unknown) {
      const parsedError = parseError(
        err,
        "Failed to resend verification email.",
      );

      // Handle specific errors
      if (parsedError.userMessage.includes("already verified")) {
        const message = "This email address is already verified. You can log in now.";
        setError(message);
        showError(new Error(message));
      } else if (parsedError.userMessage.includes("not found")) {
        const message = "No account found with this email address.";
        setError(message);
        showError(new Error(message));
      } else {
        setError(parsedError.userMessage);
        showError(err);
      }
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <div style={{ maxWidth: "400px", margin: "100px auto", padding: "20px" }}>
        <div
          style={{
            background: "#f0f9ff",
            border: "1px solid #0ea5e9",
            borderRadius: "8px",
            padding: "20px",
            marginBottom: "20px",
          }}
        >
          <h2 style={{ margin: "0 0 10px 0", color: "#0369a1" }}>
            Verification Email Sent
          </h2>
          <p style={{ margin: 0, color: "#0c4a6e" }}>
            A new verification email has been sent to <strong>{email}</strong>.
          </p>
          <p
            style={{
              margin: "10px 0 0 0",
              fontSize: "14px",
              color: "#0c4a6e",
            }}
          >
            Please check your inbox and spam folder for the verification link.
          </p>
        </div>

        <Link
          to="/account"
          style={{
            display: "block",
            textAlign: "center",
            color: "#0ea5e9",
            textDecoration: "none",
          }}
        >
          Back to Login
        </Link>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: "400px", margin: "100px auto", padding: "20px" }}>
      <h1 style={{ marginBottom: "10px" }}>Resend Verification Email</h1>
      <p style={{ color: "#666", marginBottom: "30px" }}>
        Enter your email address and we'll send you a new verification link.
      </p>

      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: "20px" }}>
          <label
            style={{
              display: "block",
              marginBottom: "5px",
              fontWeight: "500",
            }}
          >
            Email Address
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            disabled={loading}
            placeholder="your-email@example.com"
            style={{
              width: "100%",
              padding: "10px",
              fontSize: "16px",
              border: "1px solid #ddd",
              borderRadius: "4px",
              boxSizing: "border-box",
            }}
          />
        </div>

        {error && (
          <div
            style={{
              background: "#fee",
              border: "1px solid #fcc",
              borderRadius: "4px",
              padding: "10px",
              marginBottom: "20px",
              color: "#c00",
            }}
          >
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          style={{
            width: "100%",
            padding: "12px",
            fontSize: "16px",
            fontWeight: "600",
            color: "white",
            background: loading ? "#ccc" : "#0ea5e9",
            border: "none",
            borderRadius: "4px",
            cursor: loading ? "not-allowed" : "pointer",
          }}
        >
          {loading ? "Sending..." : "Resend Verification Email"}
        </button>
      </form>

      <div
        style={{
          marginTop: "20px",
          textAlign: "center",
          fontSize: "14px",
        }}
      >
        <Link
          to="/account"
          style={{
            color: "#0ea5e9",
            textDecoration: "none",
          }}
        >
          Back to Login
        </Link>
      </div>
    </div>
  );
}
