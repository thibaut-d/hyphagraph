import React, { useState, useEffect } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { verifyEmail } from "../api/auth";
import { parseError } from "../utils/errorHandler";

export default function VerifyEmailView() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get("token");

  const [loading, setLoading] = useState(true);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      setError(t("verify_email.invalid_token"));
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
          t("verify_email.error_hint"),
        );
        setError(parsedError.userMessage);
        setLoading(false);
      }
    };

    void verify();
  }, [token, navigate, t]);

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
            {t("verify_email.loading_title")}
          </h2>
          <p style={{ margin: 0, color: "#0c4a6e" }}>
            {t("verify_email.loading_message")}
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
            {t("verify_email.success_title")}
          </h2>
          <p style={{ margin: 0, color: "#166534" }}>
            {t("verify_email.success_message")}
          </p>
          <p
            style={{
              margin: "10px 0 0 0",
              fontSize: "14px",
              color: "#166534",
            }}
          >
            {t("verify_email.success_hint")}
          </p>
          <p
            style={{
              margin: "10px 0 0 0",
              fontSize: "14px",
              color: "#166534",
            }}
          >
            {t("verify_email.success_redirect")}
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
          {t("verify_email.go_to_login")}
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
          {t("verify_email.error_title")}
        </h2>
        <p style={{ margin: 0, color: "#900" }}>{error}</p>
        <p
          style={{
            margin: "10px 0 0 0",
            fontSize: "14px",
            color: "#900",
          }}
        >
          {t("verify_email.error_hint")}
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
          {t("verify_email.resend_link")}
        </Link>
        <br />
        <Link
          to="/account"
          style={{
            color: "#0ea5e9",
            textDecoration: "none",
          }}
        >
          {t("verify_email.back_to_login")}
        </Link>
      </div>
    </div>
  );
}
