import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { RecordButton } from "../components/RecordButton";

describe("RecordButton", () => {
  it('shows "RECORD" label when not listening and not transcribing', () => {
    render(
      <RecordButton
        isListening={false}
        isTranscribing={false}
        onClick={vi.fn()}
      />
    );
    expect(screen.getByRole("button")).toHaveTextContent("RECORD");
  });

  it('shows "STOP" label when isListening is true', () => {
    render(
      <RecordButton
        isListening={true}
        isTranscribing={false}
        onClick={vi.fn()}
      />
    );
    expect(screen.getByRole("button")).toHaveTextContent("STOP");
  });

  it('shows "TRANSCRIBING" label when isTranscribing is true', () => {
    render(
      <RecordButton
        isListening={false}
        isTranscribing={true}
        onClick={vi.fn()}
      />
    );
    expect(screen.getByRole("button")).toHaveTextContent("TRANSCRIBING");
  });

  it("button is disabled when disabled=true", () => {
    render(
      <RecordButton
        isListening={false}
        isTranscribing={false}
        disabled={true}
        onClick={vi.fn()}
      />
    );
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("calls onClick when clicked", async () => {
    const user = userEvent.setup();
    const handleClick = vi.fn();
    render(
      <RecordButton
        isListening={false}
        isTranscribing={false}
        onClick={handleClick}
      />
    );
    await user.click(screen.getByRole("button"));
    expect(handleClick).toHaveBeenCalledOnce();
  });
});
