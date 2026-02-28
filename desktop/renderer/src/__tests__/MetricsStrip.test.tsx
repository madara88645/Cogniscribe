import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { MetricsStrip } from "../components/MetricsStrip";

describe("MetricsStrip", () => {
  it("shows latency formatted as '1.23s'", () => {
    render(
      <MetricsStrip latencySec={1.234} device="GPU" model="base" confidence={0.5} />
    );
    expect(screen.getByText("1.23s")).toBeInTheDocument();
  });

  it("shows '0.00s' when latency is zero", () => {
    render(
      <MetricsStrip latencySec={0} device="GPU" model="base" confidence={0.5} />
    );
    expect(screen.getByText("0.00s")).toBeInTheDocument();
  });

  it("shows confidence as percentage '85%'", () => {
    render(
      <MetricsStrip latencySec={1} device="GPU" model="base" confidence={0.85} />
    );
    expect(screen.getByText("85%")).toBeInTheDocument();
  });

  it("shows device string", () => {
    render(
      <MetricsStrip latencySec={1} device="CPU" model="base" confidence={0.5} />
    );
    expect(screen.getByText("CPU")).toBeInTheDocument();
  });

  it("shows model string", () => {
    render(
      <MetricsStrip latencySec={1} device="GPU" model="small" confidence={0.5} />
    );
    expect(screen.getByText("small")).toBeInTheDocument();
  });

  it("shows '-' when device is empty string", () => {
    render(
      <MetricsStrip latencySec={1} device="" model="base" confidence={0.5} />
    );

    const deviceLabel = screen.getByText("Device");
    const deviceValue = deviceLabel.parentElement?.querySelector("p:last-child");

    expect(deviceValue).toHaveTextContent("-");
  });
});
