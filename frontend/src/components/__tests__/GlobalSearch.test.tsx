import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BrowserRouter } from "react-router-dom";
import { GlobalSearch } from "../GlobalSearch";
import * as searchApi from "../../api/search";

// Mock the search API
vi.mock("../../api/search");

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe("GlobalSearch", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllTimers();
  });

  const renderComponent = () => {
    return render(
      <BrowserRouter>
        <GlobalSearch />
      </BrowserRouter>
    );
  };

  it("renders search input field", () => {
    renderComponent();
    const input = screen.getByPlaceholderText(/search entities, sources/i);
    expect(input).toBeInTheDocument();
  });

  it("shows search icon", () => {
    renderComponent();
    const searchIcon = document.querySelector('[data-testid="SearchIcon"]');
    expect(searchIcon).toBeInTheDocument();
  });

  it("does not fetch suggestions for queries shorter than 2 characters", async () => {
    const getSuggestionsSpy = vi
      .spyOn(searchApi, "getSuggestions")
      .mockResolvedValue({ query: "a", suggestions: [] });

    renderComponent();
    const input = screen.getByPlaceholderText(/search entities, sources/i);

    await userEvent.type(input, "a");

    // Wait for debounce
    await waitFor(() => {
      expect(getSuggestionsSpy).not.toHaveBeenCalled();
    });
  });

  it("fetches suggestions for queries with 2+ characters", async () => {
    const mockSuggestions = [
      {
        id: "1",
        type: "entity" as const,
        label: "Paracetamol",
        secondary: undefined,
      },
      {
        id: "2",
        type: "entity" as const,
        label: "Tylenol",
        secondary: "→ paracetamol",
      },
    ];

    const getSuggestionsSpy = vi
      .spyOn(searchApi, "getSuggestions")
      .mockResolvedValue({ query: "par", suggestions: mockSuggestions });

    renderComponent();
    const input = screen.getByPlaceholderText(/search entities, sources/i);

    await userEvent.type(input, "par");

    // Wait for debounce and API call
    await waitFor(() => {
      expect(getSuggestionsSpy).toHaveBeenCalledWith("par", undefined, 10);
    });
  });

  it("displays suggestions in dropdown", async () => {
    const mockSuggestions = [
      {
        id: "1",
        type: "entity" as const,
        label: "Paracetamol",
        secondary: undefined,
      },
      {
        id: "2",
        type: "source" as const,
        label: "Paracetamol Study",
        secondary: "article (2023)",
      },
    ];

    vi.spyOn(searchApi, "getSuggestions").mockResolvedValue({
      query: "para",
      suggestions: mockSuggestions,
    });

    renderComponent();
    const input = screen.getByPlaceholderText(/search entities, sources/i);

    await userEvent.type(input, "para");

    // Wait for suggestions to appear
    await waitFor(() => {
      expect(screen.getByText("Paracetamol")).toBeInTheDocument();
    });

    expect(screen.getByText("Paracetamol Study")).toBeInTheDocument();
  });

  it("navigates to entity detail when entity suggestion is selected", async () => {
    const mockSuggestions = [
      {
        id: "entity-123",
        type: "entity" as const,
        label: "Paracetamol",
        secondary: undefined,
      },
    ];

    vi.spyOn(searchApi, "getSuggestions").mockResolvedValue({
      query: "para",
      suggestions: mockSuggestions,
    });

    renderComponent();
    const input = screen.getByPlaceholderText(/search entities, sources/i);

    await userEvent.type(input, "para");

    // Wait for suggestions
    await waitFor(() => {
      expect(screen.getByText("Paracetamol")).toBeInTheDocument();
    });

    // Click the suggestion
    await userEvent.click(screen.getByText("Paracetamol"));

    // Verify navigation
    expect(mockNavigate).toHaveBeenCalledWith("/entities/entity-123");
  });

  it("navigates to source detail when source suggestion is selected", async () => {
    const mockSuggestions = [
      {
        id: "source-456",
        type: "source" as const,
        label: "Research Paper",
        secondary: "study (2023)",
      },
    ];

    vi.spyOn(searchApi, "getSuggestions").mockResolvedValue({
      query: "research",
      suggestions: mockSuggestions,
    });

    renderComponent();
    const input = screen.getByPlaceholderText(/search entities, sources/i);

    await userEvent.type(input, "research");

    // Wait for suggestions
    await waitFor(() => {
      expect(screen.getByText("Research Paper")).toBeInTheDocument();
    });

    // Click the suggestion
    await userEvent.click(screen.getByText("Research Paper"));

    // Verify navigation
    expect(mockNavigate).toHaveBeenCalledWith("/sources/source-456");
  });

  it("navigates to search page when Enter is pressed without selecting", async () => {
    vi.spyOn(searchApi, "getSuggestions").mockResolvedValue({
      query: "test",
      suggestions: [],
    });

    renderComponent();
    const input = screen.getByPlaceholderText(/search entities, sources/i);

    await userEvent.type(input, "test query{Enter}");

    // Verify navigation to search page with query
    expect(mockNavigate).toHaveBeenCalledWith("/search?q=test%20query");
  });

  it("clears input after selecting a suggestion", async () => {
    const mockSuggestions = [
      {
        id: "1",
        type: "entity" as const,
        label: "Test Entity",
        secondary: undefined,
      },
    ];

    vi.spyOn(searchApi, "getSuggestions").mockResolvedValue({
      query: "test",
      suggestions: mockSuggestions,
    });

    renderComponent();
    const input = screen.getByPlaceholderText(
      /search entities, sources/i
    ) as HTMLInputElement;

    await userEvent.type(input, "test");

    await waitFor(() => {
      expect(screen.getByText("Test Entity")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Test Entity"));

    // Input should be cleared
    await waitFor(() => {
      expect(input.value).toBe("");
    });
  });

  it("shows loading indicator while fetching suggestions", async () => {
    let resolvePromise: (value: any) => void;
    const promise = new Promise((resolve) => {
      resolvePromise = resolve;
    });

    vi.spyOn(searchApi, "getSuggestions").mockReturnValue(promise as any);

    renderComponent();
    const input = screen.getByPlaceholderText(/search entities, sources/i);

    await userEvent.type(input, "test");

    // Wait for debounce to trigger API call
    await waitFor(() => {
      const spinner = screen.queryByRole("progressbar");
      expect(spinner).toBeInTheDocument();
    });

    // Resolve the promise
    resolvePromise!({ query: "test", suggestions: [] });
  });

  it("handles API errors gracefully", async () => {
    const consoleErrorSpy = vi
      .spyOn(console, "error")
      .mockImplementation(() => {});

    vi.spyOn(searchApi, "getSuggestions").mockRejectedValue(
      new Error("API Error")
    );

    renderComponent();
    const input = screen.getByPlaceholderText(/search entities, sources/i);

    await userEvent.type(input, "test");

    // Wait for error handling
    await waitFor(() => {
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        "Failed to fetch suggestions:",
        expect.any(Error)
      );
    });

    // Component should not crash
    expect(input).toBeInTheDocument();

    consoleErrorSpy.mockRestore();
  });

  it("displays entity type chip for entity suggestions", async () => {
    const mockSuggestions = [
      {
        id: "1",
        type: "entity" as const,
        label: "Test Entity",
        secondary: undefined,
      },
    ];

    vi.spyOn(searchApi, "getSuggestions").mockResolvedValue({
      query: "test",
      suggestions: mockSuggestions,
    });

    renderComponent();
    const input = screen.getByPlaceholderText(/search entities, sources/i);

    await userEvent.type(input, "test");

    await waitFor(() => {
      expect(screen.getByText("entity")).toBeInTheDocument();
    });
  });

  it("displays source type chip for source suggestions", async () => {
    const mockSuggestions = [
      {
        id: "1",
        type: "source" as const,
        label: "Test Source",
        secondary: "article (2023)",
      },
    ];

    vi.spyOn(searchApi, "getSuggestions").mockResolvedValue({
      query: "test",
      suggestions: mockSuggestions,
    });

    renderComponent();
    const input = screen.getByPlaceholderText(/search entities, sources/i);

    await userEvent.type(input, "test");

    await waitFor(() => {
      expect(screen.getByText("source")).toBeInTheDocument();
    });
  });

  it("displays secondary text for suggestions with metadata", async () => {
    const mockSuggestions = [
      {
        id: "1",
        type: "entity" as const,
        label: "Tylenol",
        secondary: "→ paracetamol",
      },
    ];

    vi.spyOn(searchApi, "getSuggestions").mockResolvedValue({
      query: "tyl",
      suggestions: mockSuggestions,
    });

    renderComponent();
    const input = screen.getByPlaceholderText(/search entities, sources/i);

    await userEvent.type(input, "tyl");

    await waitFor(() => {
      expect(screen.getByText("Tylenol")).toBeInTheDocument();
      expect(screen.getByText("→ paracetamol")).toBeInTheDocument();
    });
  });
});
