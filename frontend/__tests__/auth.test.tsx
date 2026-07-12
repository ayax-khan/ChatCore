import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import LoginPage from "@/app/login/page";
import RegisterPage from "@/app/register/page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/lib/api", () => ({
  api: {
    post: vi.fn(),
  },
}));

describe("Login Page", () => {
  it("renders login form", () => {
    render(<LoginPage />);
    expect(screen.getByPlaceholderText(/email/i)).toBeDefined();
    expect(screen.getByPlaceholderText(/password/i)).toBeDefined();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeDefined();
  });

  it("shows validation errors for empty fields", async () => {
    render(<LoginPage />);
    const button = screen.getByRole("button", { name: /sign in/i });
    fireEvent.click(button);
    await waitFor(() => {
      expect(screen.getByText(/email is required/i)).toBeDefined();
    });
  });
});

describe("Register Page", () => {
  it("renders registration form", () => {
    render(<RegisterPage />);
    expect(screen.getByPlaceholderText(/email/i)).toBeDefined();
    expect(screen.getByPlaceholderText(/password/i)).toBeDefined();
    expect(screen.getByPlaceholderText(/business name/i)).toBeDefined();
  });
});
