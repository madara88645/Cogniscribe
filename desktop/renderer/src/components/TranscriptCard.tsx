type Props = {
  text: string;
  confidence: number;
  accepted: boolean;
};

export function TranscriptCard({ text, confidence, accepted }: Props) {
  const confidenceText = Number.isFinite(confidence) ? `${Math.round(confidence * 100)}%` : "-";

  return (
    <section className="rounded-2xl border border-[var(--vp-border)] bg-[var(--vp-surface)] p-4 shadow-soft">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--vp-muted)]">Last Transcript</h3>
        <span className={`rounded-full px-2 py-1 text-[10px] font-bold tracking-[0.14em] ${accepted ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>
          {confidenceText}
        </span>
      </div>
      <p className="min-h-20 whitespace-pre-wrap text-sm leading-6 text-[var(--vp-text)]">{text || "-"}</p>
    </section>
  );
}
