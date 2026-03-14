import React, { useState } from "react";
import { requestPasswordReset } from "../api/auth";
import { Link } from "react-router-dom";
import { useAsyncAction } from "../hooks/useAsyncAction";
import { useValidationMessage } from "../hooks/useValidationMessage";

type ValidationField = "email";

export default function RequestPasswordResetView() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const {
    setValidationMessage,
    clearValidationMessage: clearError,
    getFieldError,
    hasFieldError,
  } = useValidationMessage<ValidationField>();
  const [submitError, setSubmitError] = useState<string | null>(null);
  const { isRunning: loading, run } = useAsyncAction((message) => setSubmitError(message ?? ""));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    setSubmitError(null);
    if (!email.trim()) {
      setValidationMessage("Email address is required", "email");
      return;
    }
    const result = await run(async () => {
      await requestPasswordReset(email.trim());
      setSubmitted(true);
    }, "Failed to request password reset");

    if (!result.ok) {
      return;
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
            Check Your Email
          </h2>
          <p style={{ margin: 0, color: "#0c4a6e" }}>
            If an account exists for <strong>{email}</strong>, you will receive
            a password reset link shortly.
          </p>
          <p
            style={{
              margin: "10px 0 0 0",
              fontSize: "14px",
              color: "#0c4a6e",
            }}
          >
            Please check your inbox and spam folder.
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
      <h1 style={{ marginBottom: "10px" }}>Reset Password</h1>
      <p style={{ color: "#666", marginBottom: "30px" }}>
        Enter your email address and we'll send you a link to reset your
        password.
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
            onChange={(e) => {
              setEmail(e.target.value);
              clearError("email");
            }}
            required
            disabled={loading}
            placeholder="your-email@example.com"
            style={{
              width: "100%",
              padding: "10px",
              fontSize: "16px",
              border: `1px solid ${hasFieldError("email") ? "#c00" : "#ddd"}`,
              borderRadius: "4px",
              boxSizing: "border-box",
            }}
          />
          {getFieldError("email") && (
            <div style={{ marginTop: "5px", color: "#c00", fontSize: "14px" }}>
              {getFieldError("email")}
            </div>
          )}
        </div>

        {submitError && (
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
            {submitError}
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
          {loading ? "Sending..." : "Send Reset Link"}
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
