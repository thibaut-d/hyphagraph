import { render, screen, waitFor, fireEvent, act } from "@testing-library/react";
import { NotificationProvider, useNotification } from "../NotificationContext";
import { describe, test, expect, vi, beforeEach } from "vitest";
import { ErrorCode, ParsedAppError } from "../../utils/errorHandler";

// Mock i18next
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: { defaultValue?: string }) => {
      // Simulate translation: if key exists in mock translations, return it, otherwise return defaultValue or key
      const mockTranslations: Record<string, string> = {
        "notifications.network_error":
          "Network error. Please check your connection.",
        "notifications.session_expired":
          "Your session has expired. Please log in again.",
      };
      return mockTranslations[key] || options?.defaultValue || key;
    },
  }),
  initReactI18next: { type: '3rdParty', init: () => {} },
}));

// Test component that uses the notification hook
function TestComponent() {
  const { showSuccess, showError, showInfo, showWarning, dismiss } =
    useNotification();

  return (
    <div>
      <button onClick={() => showSuccess("Success message")}>
        Show Success
      </button>
      <button onClick={() => showError("Error message")}>Show Error</button>
      <button onClick={() => showInfo("Info message")}>Show Info</button>
      <button onClick={() => showWarning("Warning message")}>
        Show Warning
      </button>
      <button onClick={() => showSuccess("notifications.network_error")}>
        Show i18n Key
      </button>
      <button
        onClick={() =>
          showSuccess("Custom duration", { duration: 1000, autoDismiss: true })
        }
      >
        Show Custom Duration
      </button>
      <button
        onClick={() => showError("Persistent", { autoDismiss: false })}
      >
        Show Persistent
      </button>
      <button
        onClick={() =>
          showError(
            new ParsedAppError({
              userMessage: "Structured extraction failure",
              developerMessage: "Backend stack details",
              code: ErrorCode.INTERNAL_SERVER_ERROR,
              field: "source_url",
              context: { sourceId: "source-123" },
              statusCode: 500,
            }),
            { autoDismiss: false },
          )
        }
      >
        Show Structured Error
      </button>
      <button
        onClick={() =>
          showError(
            new ParsedAppError({
              userMessage: "Timed structured extraction failure",
              developerMessage: "Timed backend stack details",
              code: ErrorCode.INTERNAL_SERVER_ERROR,
            }),
            { duration: 1000, autoDismiss: true },
          )
        }
      >
        Show Timed Structured Error
      </button>
      <button onClick={dismiss}>Dismiss</button>
    </div>
  );
}

function HookOutsideProvider() {
  useNotification();
  return null;
}

describe("NotificationContext", () => {
  beforeEach(() => {
    vi.useRealTimers();
    window.history.pushState({}, "", "/");
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  test("throws error when hook used outside provider", () => {
    // Suppress console.error for this test
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    expect(() => {
      render(<HookOutsideProvider />);
    }).toThrow("useNotification must be used within NotificationProvider");

    consoleSpy.mockRestore();
  });

  test("shows success notification", async () => {
    render(
      <NotificationProvider>
        <TestComponent />
      </NotificationProvider>,
    );

    fireEvent.click(screen.getByText("Show Success"));

    await waitFor(() => {
      expect(screen.getByText("Success message")).toBeInTheDocument();
    });
  });

  test("shows error notification", async () => {
    render(
      <NotificationProvider>
        <TestComponent />
      </NotificationProvider>,
    );

    fireEvent.click(screen.getByText("Show Error"));

    await waitFor(() => {
      expect(screen.getByText("Error message")).toBeInTheDocument();
    });
  });

  test("shows info notification", async () => {
    render(
      <NotificationProvider>
        <TestComponent />
      </NotificationProvider>,
    );

    fireEvent.click(screen.getByText("Show Info"));

    await waitFor(() => {
      expect(screen.getByText("Info message")).toBeInTheDocument();
    });
  });

  test("shows warning notification", async () => {
    render(
      <NotificationProvider>
        <TestComponent />
      </NotificationProvider>,
    );

    fireEvent.click(screen.getByText("Show Warning"));

    await waitFor(() => {
      expect(screen.getByText("Warning message")).toBeInTheDocument();
    });
  });

  test("translates i18n keys", async () => {
    render(
      <NotificationProvider>
        <TestComponent />
      </NotificationProvider>,
    );

    fireEvent.click(screen.getByText("Show i18n Key"));

    await waitFor(() => {
      expect(
        screen.getByText("Network error. Please check your connection."),
      ).toBeInTheDocument();
    });
  });

  test("auto-dismisses after default timeout for success", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    render(
      <NotificationProvider>
        <TestComponent />
      </NotificationProvider>,
    );

    fireEvent.click(screen.getByText("Show Success"));

    await waitFor(() => {
      expect(screen.getByText("Success message")).toBeInTheDocument();
    });

    // Fast-forward time by 4000ms (default success duration)
    act(() => {
      vi.advanceTimersByTime(4000);
    });

    await waitFor(() => {
      expect(screen.queryByText("Success message")).not.toBeInTheDocument();
    });
  });

  test("auto-dismisses after custom duration", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    render(
      <NotificationProvider>
        <TestComponent />
      </NotificationProvider>,
    );

    fireEvent.click(screen.getByText("Show Custom Duration"));

    await waitFor(() => {
      expect(screen.getByText("Custom duration")).toBeInTheDocument();
    });

    // Fast-forward time by 1000ms (custom duration)
    act(() => {
      vi.advanceTimersByTime(1000);
    });

    await waitFor(() => {
      expect(screen.queryByText("Custom duration")).not.toBeInTheDocument();
    });
  });

  test("does not auto-dismiss when autoDismiss is false", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    render(
      <NotificationProvider>
        <TestComponent />
      </NotificationProvider>,
    );

    fireEvent.click(screen.getByText("Show Persistent"));

    await waitFor(() => {
      expect(screen.getByText("Persistent")).toBeInTheDocument();
    });

    // Fast-forward time by 10000ms (error default duration)
    act(() => {
      vi.advanceTimersByTime(10000);
    });

    // Should still be visible
    expect(screen.getByText("Persistent")).toBeInTheDocument();
  });

  test("manual dismiss works", async () => {
    render(
      <NotificationProvider>
        <TestComponent />
      </NotificationProvider>,
    );

    fireEvent.click(screen.getByText("Show Success"));

    await waitFor(() => {
      expect(screen.getByText("Success message")).toBeInTheDocument();
    });

    // Click the dismiss button in the test component
    fireEvent.click(screen.getByText("Dismiss"));

    await waitFor(() => {
      expect(screen.queryByText("Success message")).not.toBeInTheDocument();
    });
  });

  test("close button dismisses notification", async () => {
    render(
      <NotificationProvider>
        <TestComponent />
      </NotificationProvider>,
    );

    fireEvent.click(screen.getByText("Show Success"));

    await waitFor(() => {
      expect(screen.getByText("Success message")).toBeInTheDocument();
    });

    // Find and click the close button (IconButton with aria-label="close")
    const closeButton = screen.getByLabelText("close");
    fireEvent.click(closeButton);

    await waitFor(() => {
      expect(screen.queryByText("Success message")).not.toBeInTheDocument();
    });
  });

  test("clicking notification content does not dismiss a persistent structured error", async () => {
    render(
      <NotificationProvider>
        <TestComponent />
      </NotificationProvider>,
    );

    fireEvent.click(screen.getByText("Show Structured Error"));

    await waitFor(() => {
      expect(screen.getByText("Structured extraction failure")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Structured extraction failure"));

    expect(screen.getByText("Structured extraction failure")).toBeInTheDocument();
  });

  test("copy debug details includes page and structured error context", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date("2026-04-09T12:34:56.000Z"));
    window.history.pushState({}, "", "/sources/abc?tab=review#errors");

    render(
      <NotificationProvider>
        <TestComponent />
      </NotificationProvider>,
    );

    fireEvent.click(screen.getByText("Show Structured Error"));

    await waitFor(() => {
      expect(screen.getByText("Structured extraction failure")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Dev details/i }));
    await act(async () => {
      fireEvent.click(screen.getByLabelText("Copy debug details"));
      await Promise.resolve();
    });

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      JSON.stringify(
        {
          timestamp: "2026-04-09T12:34:56.000Z",
          severity: "error",
          page: "/sources/abc?tab=review#errors",
          userMessage: "Structured extraction failure",
          code: ErrorCode.INTERNAL_SERVER_ERROR,
          developerMessage: "Backend stack details",
          statusCode: 500,
          field: "source_url",
          context: { sourceId: "source-123" },
        },
        null,
        2,
      ),
    );

    expect(screen.getByText("Structured extraction failure")).toBeInTheDocument();
  });

  test("hovering an auto-dismissing structured error keeps it open while reading details", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    render(
      <NotificationProvider>
        <TestComponent />
      </NotificationProvider>,
    );

    fireEvent.click(screen.getByText("Show Timed Structured Error"));

    await waitFor(() => {
      expect(screen.getByText("Timed structured extraction failure")).toBeInTheDocument();
    });

    const alert = screen.getByRole("alert");
    fireEvent.mouseEnter(alert);
    fireEvent.click(screen.getByRole("button", { name: /Dev details/i }));

    expect(screen.getByText(/Timed backend stack details/)).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(1000);
    });

    expect(screen.getByText("Timed structured extraction failure")).toBeInTheDocument();

    fireEvent.mouseLeave(alert);

    act(() => {
      vi.advanceTimersByTime(1000);
    });

    await waitFor(() => {
      expect(
        screen.queryByText("Timed structured extraction failure"),
      ).not.toBeInTheDocument();
    });
  });

  test("queue management: shows notifications one at a time", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    render(
      <NotificationProvider>
        <TestComponent />
      </NotificationProvider>,
    );

    // Trigger multiple notifications rapidly
    fireEvent.click(screen.getByText("Show Success"));
    fireEvent.click(screen.getByText("Show Error"));
    fireEvent.click(screen.getByText("Show Info"));

    // First notification should be visible
    await waitFor(() => {
      expect(screen.getByText("Success message")).toBeInTheDocument();
    });

    // Other notifications should not be visible yet
    expect(screen.queryByText("Error message")).not.toBeInTheDocument();
    expect(screen.queryByText("Info message")).not.toBeInTheDocument();

    // Dismiss first notification
    act(() => {
      vi.advanceTimersByTime(4000);
    });

    // Second notification should now be visible
    await waitFor(() => {
      expect(screen.getByText("Error message")).toBeInTheDocument();
    });

    expect(screen.queryByText("Success message")).not.toBeInTheDocument();
    expect(screen.queryByText("Info message")).not.toBeInTheDocument();

    // Dismiss second notification
    act(() => {
      vi.advanceTimersByTime(10000);
    });

    // Third notification should now be visible
    await waitFor(() => {
      expect(screen.getByText("Info message")).toBeInTheDocument();
    });

    expect(screen.queryByText("Success message")).not.toBeInTheDocument();
    expect(screen.queryByText("Error message")).not.toBeInTheDocument();
  });

  test("shows raw message when translation key not found", async () => {
    render(
      <NotificationProvider>
        <TestComponent />
      </NotificationProvider>,
    );

    fireEvent.click(screen.getByText("Show Success"));

    await waitFor(() => {
      // Should show the raw message since "Success message" is not a translation key
      expect(screen.getByText("Success message")).toBeInTheDocument();
    });
  });
});
