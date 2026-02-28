import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { TranscriptCard } from "../components/TranscriptCard";

describe("TranscriptCard", () => {
  it("shows placeholder text when text is empty", () => {
    render(<TranscriptCard text="" confidence={0.9} accepted={true} />);
    expect(
      screen.getByText("No transcript yet. Press record to start dictating.")
    ).toBeInTheDocument();
  });

  it("shows the transcript text when text is provided", () => {
    render(
      <TranscriptCard
        text="Hello, world!"
        confidence={0.95}
        accepted={true}
      />
    );
    expect(screen.getByText("Hello, world!")).toBeInTheDocument();
  });

  it("shows confidence percentage badge when text is provided", () => {
    render(
      <TranscriptCard text="Hello" confidence={0.85} accepted={true} />
    );
    expect(screen.getByText("85%")).toBeInTheDocument();
  });

  it("badge has emerald class when accepted=true", () => {
    render(
      <TranscriptCard text="Hello" confidence={0.9} accepted={true} />
    );
    const badge = screen.getByText("90%");
    expect(badge.className).toContain("emerald");
  });

  it("badge has amber class when accepted=false", () => {
    render(
      <TranscriptCard text="Hello" confidence={0.6} accepted={false} />
    );
    const badge = screen.getByText("60%");
    expect(badge.className).toContain("amber");
  });

  it("does not show confidence badge when text is empty", () => {
    render(<TranscriptCard text="" confidence={0.9} accepted={true} />);
    expect(screen.queryByText("90%")).not.toBeInTheDocument();
  });
});
