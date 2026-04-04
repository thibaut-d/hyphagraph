import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
  Typography,
  CircularProgress,
  Alert,
  Stack,
} from "@mui/material";
import { getCaptcha, submitBugReport, type CaptchaChallenge } from "../api/bugReport";
import { useAuthContext } from "../auth/AuthContext";

interface BugReportDialogProps {
  open: boolean;
  onClose: () => void;
}

export function BugReportDialog({ open, onClose }: BugReportDialogProps) {
  const { t } = useTranslation();
  const { user } = useAuthContext();

  const [message, setMessage] = useState("");
  const [captcha, setCaptcha] = useState<CaptchaChallenge | null>(null);
  const [captchaAnswer, setCaptchaAnswer] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Load captcha for anonymous users when dialog opens
  useEffect(() => {
    if (!open) return;
    setMessage("");
    setCaptchaAnswer("");
    setError(null);
    setSuccess(false);
    setCaptcha(null);
    if (!user) {
      getCaptcha()
        .then(setCaptcha)
        .catch(() => {
          setCaptcha(null);
          setError(t("bug_report.captcha_load_error", "Could not load CAPTCHA. Please try again."));
        });
    }
  }, [open, user]);

  const handleSubmit = async () => {
    if (message.trim().length < 10) {
      setError(t("bug_report.message_too_short", "Please describe the issue in at least 10 characters."));
      return;
    }
    if (!user && (!captcha || !captchaAnswer.trim())) {
      setError(t("bug_report.captcha_required", "Please answer the CAPTCHA."));
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      await submitBugReport({
        message: message.trim(),
        page_url: window.location.href,
        user_agent: navigator.userAgent,
        ...(captcha && { captcha_token: captcha.token, captcha_answer: captchaAnswer.trim() }),
      });
      setSuccess(true);
    } catch {
      setError(t("bug_report.submit_error", "Failed to submit report. Please try again."));
    } finally {
      setSubmitting(false);
    }
  };

  const handleClose = () => {
    if (!submitting) onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>{t("bug_report.title", "Report a Bug")}</DialogTitle>
      <DialogContent>
        {success ? (
          <Alert severity="success" sx={{ mt: 1 }}>
            {t("bug_report.success", "Thank you! Your report has been submitted.")}
          </Alert>
        ) : (
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label={t("bug_report.message_label", "Describe the issue")}
              multiline
              minRows={4}
              fullWidth
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              inputProps={{ maxLength: 4000 }}
              disabled={submitting}
              helperText={`${message.length}/4000`}
            />

            {!user && (
              <>
                {captcha ? (
                  <TextField
                    label={captcha.question}
                    fullWidth
                    value={captchaAnswer}
                    onChange={(e) => setCaptchaAnswer(e.target.value)}
                    disabled={submitting}
                    inputProps={{ inputMode: "numeric" }}
                  />
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    {t("bug_report.loading_captcha", "Loading CAPTCHA…")}
                  </Typography>
                )}
              </>
            )}

            {error && <Alert severity="error">{error}</Alert>}
          </Stack>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={submitting}>
          {success ? t("common.close", "Close") : t("common.cancel", "Cancel")}
        </Button>
        {!success && (
          <Button
            onClick={handleSubmit}
            variant="contained"
            disabled={submitting || (!user && !captcha)}
            startIcon={submitting ? <CircularProgress size={16} color="inherit" /> : null}
          >
            {submitting
              ? t("common.submitting", "Submitting…")
              : t("bug_report.submit", "Submit Report")}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
}
