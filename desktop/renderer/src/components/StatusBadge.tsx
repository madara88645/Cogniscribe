import { StatusName } from "../types/voicePaste";

type Props = {
  status: StatusName;
};

const STATUS_MAP: Record<StatusName, { label: string; className: string }> = {
  loading: { label: "Loading", className: "bg-amber-100 text-amber-800 border-amber-200" },
  ready: { label: "Ready", className: "bg-emerald-100 text-emerald-800 border-emerald-200" },
  listening: { label: "Listening", className: "bg-rose-100 text-rose-800 border-rose-200" },
  transcribing: { label: "Transcribing", className: "bg-orange-100 text-orange-800 border-orange-200" },
  low_conf: { label: "Low Confidence", className: "bg-yellow-100 text-yellow-800 border-yellow-200" },
  error: { label: "Error", className: "bg-red-100 text-red-800 border-red-200" },
};

export function StatusBadge({ status }: Props) {
  const item = STATUS_MAP[status];
  return (
    <span className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold tracking-wide ${item.className}`}>
      {item.label}
    </span>
  );
}
