import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { StatusBadge } from "../components/StatusBadge";

describe("StatusBadge", () => {
  it('renders "Loading" badge when status is loading', () => {
    render(<StatusBadge status="loading" />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading");
  });

  it('renders "Ready" badge with emerald class when status is ready', () => {
    render(<StatusBadge status="ready" />);
    const badge = screen.getByRole("status");
    expect(badge).toHaveTextContent("Ready");
    expect(badge.className).toContain("emerald");
  });

  it('renders "Listening" badge when status is listening', () => {
    render(<StatusBadge status="listening" />);
    expect(screen.getByRole("status")).toHaveTextContent("Listening");
  });

  it('renders "Transcribing" badge when status is transcribing', () => {
    render(<StatusBadge status="transcribing" />);
    expect(screen.getByRole("status")).toHaveTextContent("Transcribing");
  });

  it('renders "Error" badge when status is error', () => {
    render(<StatusBadge status="error" />);
    expect(screen.getByRole("status")).toHaveTextContent("Error");
  });

  it('renders "Low Confidence" badge when status is low_conf', () => {
    render(<StatusBadge status="low_conf" />);
    expect(screen.getByRole("status")).toHaveTextContent("Low Confidence");
  });

  it('has role="status" and aria-live="polite"', () => {
    render(<StatusBadge status="ready" />);
    const badge = screen.getByRole("status");
    expect(badge).toHaveAttribute("aria-live", "polite");
  });
});
