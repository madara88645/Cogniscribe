type Props = {
  text: string;
  confidence: number;
  accepted: boolean;
};

export function TranscriptCard({ text, confidence, accepted }: Props) {
  const confidenceText = Number.isFinite(confidence) ? `${Math.round(confidence * 100)}%` : "-";

  return (
    <section className="vp-glass vp-glow rounded-2xl border border-[var(--vp-border)] p-4">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--vp-muted)]">Last Transcript</h3>
        <span className={`rounded-full border px-2 py-1 text-[10px] font-bold tracking-[0.14em] ${accepted ? "border-emerald-400/40 bg-emerald-500/15 text-emerald-200" : "border-amber-400/40 bg-amber-500/15 text-amber-200"}`}>
          {confidenceText}
        </span>
      </div>
      <p className="min-h-20 whitespace-pre-wrap text-sm leading-6 text-[var(--vp-text)]">{text || "-"}</p>
    </section>
  );
}
