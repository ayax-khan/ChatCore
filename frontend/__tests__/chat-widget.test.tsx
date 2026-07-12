import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import ChatWidget from "@/components/ChatWidget";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

describe("ChatWidget", () => {
  it("renders chat toggle button", () => {
    render(<ChatWidget siteId={1} />);
    expect(screen.getByRole("button")).toBeDefined();
  });

  it("opens chat on click", () => {
    render(<ChatWidget siteId={1} />);
    const toggle = screen.getByRole("button");
    fireEvent.click(toggle);
    expect(screen.getByPlaceholderText(/type your message/i)).toBeDefined();
  });

  it("shows suggested questions", () => {
    render(<ChatWidget siteId={1} />);
    const toggle = screen.getByRole("button");
    fireEvent.click(toggle);
    expect(screen.getByText(/suggested questions/i)).toBeDefined();
  });
});
