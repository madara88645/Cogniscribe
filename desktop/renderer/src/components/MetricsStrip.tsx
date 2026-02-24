type Props = {
  latencySec: number;
  device: string;
  model: string;
  confidence: number;
};

export function MetricsStrip({ latencySec, device, model, confidence }: Props) {
  const latency = Number.isFinite(latencySec) ? `${latencySec.toFixed(2)}s` : "-";
  const conf = Number.isFinite(confidence) ? `${Math.round(confidence * 100)}%` : "-";

  return (
    <section className="rounded-2xl border border-[var(--vp-border)] bg-[var(--vp-surface-soft)] px-4 py-3 shadow-soft">
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="space-y-0.5">
          <p className="font-semibold uppercase tracking-[0.12em] text-[var(--vp-muted)]">Latency</p>
          <p className="font-bold text-[var(--vp-text)]">{latency}</p>
        </div>
        <div className="space-y-0.5">
          <p className="font-semibold uppercase tracking-[0.12em] text-[var(--vp-muted)]">Confidence</p>
          <p className="font-bold text-[var(--vp-text)]">{conf}</p>
        </div>
        <div className="space-y-0.5">
          <p className="font-semibold uppercase tracking-[0.12em] text-[var(--vp-muted)]">Device</p>
          <p className="font-bold text-[var(--vp-text)]">{device || "-"}</p>
        </div>
        <div className="space-y-0.5">
          <p className="font-semibold uppercase tracking-[0.12em] text-[var(--vp-muted)]">Model</p>
          <p className="font-bold text-[var(--vp-text)]">{model || "-"}</p>
        </div>
      </div>
    </section>
  );
}
