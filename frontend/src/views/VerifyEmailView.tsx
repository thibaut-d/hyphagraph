import React, { useState, useEffect } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { verifyEmail } from "../api/auth";
import { useNotification } from "../notifications/NotificationContext";
import { parseError } from "../utils/errorHandler";

export default function VerifyEmailView() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get("token");
  const { showError } = useNotification();

  const [loading, setLoading] = useState(true);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!token) {
      const message = "Invalid or missing verification token";
      showError(new Error(message));
      setError(message);
      setLoading(false);
      return;
    }

    const verify = async () => {
      try {
        await verifyEmail(token);
        setSuccess(true);
        setLoading(false);

        // Redirect to login after 3 seconds
        setTimeout(() => {
          navigate("/account");
        }, 3000);
      } catch (err: unknown) {
        const parsedError = parseError(
          err,
          "Failed to verify email. The link may have expired.",
        );
        setError(parsedError.userMessage);
        setLoading(false);
      }
    };

    verify();
  }, [token, navigate, showError]);

  if (loading) {
    return (
      <div style={{ maxWidth: "400px", margin: "100px auto", padding: "20px" }}>
        <div
          style={{
            background: "#f0f9ff",
            border: "1px solid #0ea5e9",
            borderRadius: "8px",
            padding: "20px",
            textAlign: "center",
          }}
        >
          <h2 style={{ margin: "0 0 10px 0", color: "#0369a1" }}>
            Verifying Email...
          </h2>
          <p style={{ margin: 0, color: "#0c4a6e" }}>
            Please wait while we verify your email address.
          </p>
        </div>
      </div>
    );
  }

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
            Email Verified!
          </h2>
          <p style={{ margin: 0, color: "#166534" }}>
            Your email address has been successfully verified.
          </p>
          <p
            style={{
              margin: "10px 0 0 0",
              fontSize: "14px",
              color: "#166534",
            }}
          >
            You can now log in to your account.
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
      <div
        style={{
          background: "#fee",
          border: "1px solid #fcc",
          borderRadius: "8px",
          padding: "20px",
          marginBottom: "20px",
        }}
      >
        <h2 style={{ margin: "0 0 10px 0", color: "#c00" }}>
          Verification Failed
        </h2>
        <p style={{ margin: 0, color: "#900" }}>{error}</p>
        <p
          style={{
            margin: "10px 0 0 0",
            fontSize: "14px",
            color: "#900",
          }}
        >
          The verification link may have expired or is invalid.
        </p>
      </div>

      <div style={{ textAlign: "center" }}>
        <Link
          to="/resend-verification"
          style={{
            display: "inline-block",
            marginBottom: "10px",
            color: "#0ea5e9",
            textDecoration: "none",
            fontWeight: "500",
          }}
        >
          Resend Verification Email
        </Link>
        <br />
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
