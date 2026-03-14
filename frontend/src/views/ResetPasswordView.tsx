import React, { useState, useEffect } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { resetPassword } from "../api/auth";
import { useNotification } from "../notifications/NotificationContext";
import { useAsyncAction } from "../hooks/useAsyncAction";
import { useValidationMessage } from "../hooks/useValidationMessage";

type ValidationField = "newPassword" | "confirmPassword";

export default function ResetPasswordView() {
  const { showError } = useNotification();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get("token");

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [success, setSuccess] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const {
    clearValidationMessage,
    setValidationMessage,
    getFieldError,
    hasFieldError,
  } = useValidationMessage<ValidationField>();
  const { isRunning, run } = useAsyncAction((message) => setSubmitError(message ?? ""));

  useEffect(() => {
    if (!token) {
      showError(new Error("Invalid or missing reset token"));
    }
  }, [token, showError]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError("");
    clearValidationMessage();

    // Validation
    if (newPassword.length < 8) {
      setValidationMessage("Password must be at least 8 characters long", "newPassword");
      return;
    }

    if (newPassword !== confirmPassword) {
      setValidationMessage("Passwords do not match", "confirmPassword");
      return;
    }

    if (!token) {
      showError(new Error("Invalid or missing reset token"));
      return;
    }

    const result = await run(async () => {
      await resetPassword(token, newPassword);
      setSuccess(true);

      // Redirect to login after 3 seconds
      setTimeout(() => {
        navigate("/account");
      }, 3000);
    }, "Failed to reset password. The link may have expired.");

    if (!result.ok) {
      return;
    }
  };

  if (success) {
    return (
      <div style={{ maxWidth: "400px", margin: "100px auto", padding: "20px" }}>
        <div
          style={{
            background: "#f0fdf4",
            border: "1px solid #22c55e",
            borderRadius: "8px",
            padding: "20px",
            marginBottom: "20px",
          }}
        >
          <h2 style={{ margin: "0 0 10px 0", color: "#15803d" }}>
            Password Reset Successful!
          </h2>
          <p style={{ margin: 0, color: "#166534" }}>
            Your password has been successfully reset.
          </p>
          <p
            style={{
              margin: "10px 0 0 0",
              fontSize: "14px",
              color: "#166534",
            }}
          >
            Redirecting to login...
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
          Go to Login Now
        </Link>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: "400px", margin: "100px auto", padding: "20px" }}>
      <h1 style={{ marginBottom: "10px" }}>Set New Password</h1>
      <p style={{ color: "#666", marginBottom: "30px" }}>
        Enter your new password below.
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
            New Password
          </label>
          <input
            type="password"
            value={newPassword}
            onChange={(e) => {
              setNewPassword(e.target.value);
              clearValidationMessage("newPassword");
            }}
            required
            disabled={isRunning || !token}
            placeholder="Enter new password (min 8 characters)"
            style={{
              width: "100%",
              padding: "10px",
              fontSize: "16px",
              border: `1px solid ${hasFieldError("newPassword") ? "#c00" : "#ddd"}`,
              borderRadius: "4px",
              boxSizing: "border-box",
            }}
          />
          {getFieldError("newPassword") && (
            <div style={{ marginTop: "5px", color: "#c00", fontSize: "14px" }}>
              {getFieldError("newPassword")}
            </div>
          )}
        </div>

        <div style={{ marginBottom: "20px" }}>
          <label
            style={{
              display: "block",
              marginBottom: "5px",
              fontWeight: "500",
            }}
          >
            Confirm Password
          </label>
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => {
              setConfirmPassword(e.target.value);
              clearValidationMessage("confirmPassword");
            }}
            required
            disabled={isRunning || !token}
            placeholder="Confirm new password"
            style={{
              width: "100%",
              padding: "10px",
              fontSize: "16px",
              border: `1px solid ${hasFieldError("confirmPassword") ? "#c00" : "#ddd"}`,
              borderRadius: "4px",
              boxSizing: "border-box",
            }}
          />
          {getFieldError("confirmPassword") && (
            <div style={{ marginTop: "5px", color: "#c00", fontSize: "14px" }}>
              {getFieldError("confirmPassword")}
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
          disabled={isRunning || !token}
          style={{
            width: "100%",
            padding: "12px",
            fontSize: "16px",
            fontWeight: "600",
            color: "white",
            background: isRunning || !token ? "#ccc" : "#0ea5e9",
            border: "none",
            borderRadius: "4px",
            cursor: isRunning || !token ? "not-allowed" : "pointer",
          }}
        >
          {isRunning ? "Resetting..." : "Reset Password"}
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
