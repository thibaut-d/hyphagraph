import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { resendVerificationEmail } from "../api/auth";
import { useAsyncAction } from "../hooks/useAsyncAction";

export default function ResendVerificationView() {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const { isRunning: loading, run } = useAsyncAction((message) =>
    setSubmitError(message ?? null),
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError(null);
    await run(async () => {
      await resendVerificationEmail(email);
      setSubmitted(true);
    }, t("resend_verification.error"));
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
            {t("resend_verification.success_title")}
          </h2>
          <p style={{ margin: 0, color: "#0c4a6e" }}>
            {t("resend_verification.success_message", { email })}
          </p>
          <p
            style={{
              margin: "10px 0 0 0",
              fontSize: "14px",
              color: "#0c4a6e",
            }}
          >
            {t("resend_verification.success_hint")}
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
          {t("resend_verification.back_to_login")}
        </Link>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: "400px", margin: "100px auto", padding: "20px" }}>
      <h1 style={{ marginBottom: "10px" }}>
        {t("resend_verification.title")}
      </h1>
      <p style={{ color: "#666", marginBottom: "30px" }}>
        {t("resend_verification.subtitle")}
      </p>

      <form onSubmit={(e) => { void handleSubmit(e); }}>
        <div style={{ marginBottom: "20px" }}>
          <label
            style={{
              display: "block",
              marginBottom: "5px",
              fontWeight: "500",
            }}
          >
            {t("resend_verification.email_label")}
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            disabled={loading}
            placeholder={t("resend_verification.email_placeholder")}
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
          {loading
            ? t("resend_verification.sending")
            : t("resend_verification.submit")}
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
          {t("resend_verification.back_to_login")}
        </Link>
      </div>
    </div>
  );
}
