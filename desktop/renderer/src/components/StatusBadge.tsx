import { StatusName } from "../types/voicePaste";

type Props = {
  status: StatusName;
};

const STATUS_MAP: Record<StatusName, { label: string; className: string }> = {
  loading: { label: "Loading", className: "bg-sky-500/15 text-sky-200 border-sky-400/40" },
  ready: { label: "Ready", className: "bg-emerald-500/15 text-emerald-200 border-emerald-400/40" },
  listening: { label: "Listening", className: "bg-cyan-500/15 text-cyan-200 border-cyan-400/50" },
  transcribing: { label: "Transcribing", className: "bg-blue-500/15 text-blue-200 border-blue-400/40" },
  low_conf: { label: "Low Confidence", className: "bg-amber-500/15 text-amber-200 border-amber-400/40" },
  error: { label: "Error", className: "bg-rose-500/15 text-rose-200 border-rose-400/45" },
};

export function StatusBadge({ status }: Props) {
  const item = STATUS_MAP[status];
  return (
    <span className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold tracking-[0.12em] shadow-[0_0_18px_rgba(42,168,255,0.12)] ${item.className}`}>
      {item.label}
    </span>
  );
}
