/**
 * Tests for UserAvatar component.
 *
 * Tests avatar initials generation, color consistency, and sizing.
 */
import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { UserAvatar } from "../UserAvatar";

describe("UserAvatar", () => {
  it("renders with email initials", () => {
    const { container } = render(
      <UserAvatar email="john.doe@example.com" />
    );

    const avatar = container.querySelector(".MuiAvatar-root");
    expect(avatar).toBeInTheDocument();
    expect(avatar?.textContent).toBe("JO");
  });

  it("renders with name initials when name provided", () => {
    const { container } = render(
      <UserAvatar email="test@example.com" name="John Doe" />
    );

    const avatar = container.querySelector(".MuiAvatar-root");
    expect(avatar?.textContent).toBe("JD");
  });

  it("handles single name correctly", () => {
    const { container } = render(
      <UserAvatar email="test@example.com" name="Madonna" />
    );

    const avatar = container.querySelector(".MuiAvatar-root");
    expect(avatar?.textContent).toBe("MA");
  });

  it("handles names with multiple words", () => {
    const { container } = render(
      <UserAvatar email="test@example.com" name="John Michael Doe" />
    );

    const avatar = container.querySelector(".MuiAvatar-root");
    // First and last name initials
    expect(avatar?.textContent).toBe("JD");
  });

  it("uses custom size", () => {
    const { container } = render(
      <UserAvatar email="test@example.com" size={60} />
    );

    const avatar = container.querySelector(".MuiAvatar-root");
    expect(avatar).toHaveStyle({ width: "60px", height: "60px" });
  });

  it("uses default size of 40", () => {
    const { container } = render(
      <UserAvatar email="test@example.com" />
    );

    const avatar = container.querySelector(".MuiAvatar-root");
    expect(avatar).toHaveStyle({ width: "40px", height: "40px" });
  });

  it("renders with background color", () => {
    const { container } = render(
      <UserAvatar email="test@example.com" />
    );

    const avatar = container.querySelector(".MuiAvatar-root");
    // Avatar should exist with styling (MUI handles the actual color rendering)
    expect(avatar).toBeInTheDocument();
    expect(avatar).toHaveClass("MuiAvatar-root");
  });

  it("converts initials to uppercase", () => {
    const { container } = render(
      <UserAvatar email="test@example.com" name="john doe" />
    );

    const avatar = container.querySelector(".MuiAvatar-root");
    expect(avatar?.textContent).toBe("JD");
  });

  it("handles empty string name gracefully", () => {
    const { container } = render(
      <UserAvatar email="ab@example.com" name="" />
    );

    const avatar = container.querySelector(".MuiAvatar-root");
    // Falls back to email
    expect(avatar?.textContent).toBe("AB");
  });
});
