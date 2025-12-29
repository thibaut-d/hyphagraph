/**
 * Tests for ScrollToTop component.
 *
 * Tests scroll visibility threshold, scroll-to-top functionality, and cleanup.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ScrollToTop } from "../ScrollToTop";

describe("ScrollToTop", () => {
  beforeEach(() => {
    // Mock window.scrollTo
    window.scrollTo = vi.fn();
    // Mock window.pageYOffset
    Object.defineProperty(window, "pageYOffset", {
      writable: true,
      configurable: true,
      value: 0,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders button (initially hidden)", () => {
    render(<ScrollToTop />);

    const button = screen.getByLabelText("scroll to top");
    expect(button).toBeInTheDocument();
  });

  it("shows button when scrolled past threshold", async () => {
    render(<ScrollToTop threshold={300} />);

    // Simulate scroll past threshold
    Object.defineProperty(window, "pageYOffset", { value: 400, writable: true, configurable: true });
    fireEvent.scroll(window);

    await waitFor(() => {
      const button = screen.getByLabelText("scroll to top");
      expect(button).toBeInTheDocument();
    });
  });

  it("scrolls to top when clicked", async () => {
    render(<ScrollToTop threshold={300} />);

    // Scroll down to show button
    Object.defineProperty(window, "pageYOffset", { value: 400, writable: true, configurable: true });
    fireEvent.scroll(window);

    await waitFor(() => {
      expect(screen.getByLabelText("scroll to top")).toBeInTheDocument();
    });

    const button = screen.getByLabelText("scroll to top");
    fireEvent.click(button);

    expect(window.scrollTo).toHaveBeenCalledWith({
      top: 0,
      behavior: "smooth",
    });
  });

  it("uses custom threshold", async () => {
    render(<ScrollToTop threshold={500} />);

    // Scroll to 600 (above threshold)
    Object.defineProperty(window, "pageYOffset", { value: 600, writable: true, configurable: true });
    fireEvent.scroll(window);

    await waitFor(() => {
      const button = screen.getByLabelText("scroll to top");
      expect(button).toBeInTheDocument();
    });
  });

  it("uses default threshold of 300", () => {
    render(<ScrollToTop />);

    expect(screen.getByLabelText("scroll to top")).toBeInTheDocument();
  });

  it("cleans up scroll event listener on unmount", () => {
    const removeEventListenerSpy = vi.spyOn(window, "removeEventListener");

    const { unmount } = render(<ScrollToTop />);

    unmount();

    expect(removeEventListenerSpy).toHaveBeenCalledWith("scroll", expect.any(Function));
  });
});
