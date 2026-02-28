import { fireEvent, render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { QuickSettings } from "../components/QuickSettings";

describe("QuickSettings", () => {
  const setup = (
    overrides?: Partial<{
      model: string;
      profile: string;
      languageMode: string;
      disabled?: boolean;
    }>
  ) => {
    const onModelChange = vi.fn();
    const onProfileChange = vi.fn();
    const onLanguageModeChange = vi.fn();

    render(
      <QuickSettings
        model="small"
        profile="balanced"
        languageMode="tr_en_mixed"
        onModelChange={onModelChange}
        onProfileChange={onProfileChange}
        onLanguageModeChange={onLanguageModeChange}
        {...overrides}
      />
    );

    return { onModelChange, onProfileChange, onLanguageModeChange };
  };

  it("renders Model, Profile, Language labels", () => {
    setup();
    expect(screen.getByText("Model")).toBeInTheDocument();
    expect(screen.getByText("Profile")).toBeInTheDocument();
    expect(screen.getByText("Language")).toBeInTheDocument();
  });

  it("calls onModelChange when model select changes", () => {
    const { onModelChange } = setup();
    fireEvent.change(screen.getByDisplayValue("small"), {
      target: { value: "tiny" },
    });
    expect(onModelChange).toHaveBeenCalledWith("tiny");
  });

  it("calls onProfileChange when profile select changes", () => {
    const { onProfileChange } = setup();
    fireEvent.change(screen.getByDisplayValue("balanced"), {
      target: { value: "fast" },
    });
    expect(onProfileChange).toHaveBeenCalledWith("fast");
  });

  it("calls onLanguageModeChange when language select changes", () => {
    const { onLanguageModeChange } = setup();
    fireEvent.change(screen.getByDisplayValue("TR + EN"), {
      target: { value: "multilingual_auto" },
    });
    expect(onLanguageModeChange).toHaveBeenCalledWith("multilingual_auto");
  });

  it("all selects are disabled when disabled=true", () => {
    setup({ disabled: true });
    expect(screen.getByDisplayValue("small")).toBeDisabled();
    expect(screen.getByDisplayValue("balanced")).toBeDisabled();
    expect(screen.getByDisplayValue("TR + EN")).toBeDisabled();
  });

  it("model select contains options: tiny, base, small, medium, large-v3", () => {
    setup();
    const modelSelect = screen.getByDisplayValue("small");
    const optionValues = Array.from(modelSelect.querySelectorAll("option")).map(
      (option) => option.getAttribute("value")
    );

    expect(optionValues).toEqual(["tiny", "base", "small", "medium", "large-v3"]);
  });
});
