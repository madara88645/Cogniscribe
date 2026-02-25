type Props = {
  isListening: boolean;
  isTranscribing: boolean;
  disabled?: boolean;
  onClick: () => void;
};

export function RecordButton({ isListening, isTranscribing, disabled, onClick }: Props) {
  const label = isTranscribing ? "TRANSCRIBING" : isListening ? "STOP" : "RECORD";
  const ringClass = isListening ? "animate-pulseSoft" : "";

  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className="group relative mx-auto block rounded-full focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--vp-accent)] disabled:cursor-not-allowed disabled:opacity-60"
    >
      <span className={`absolute -inset-3 rounded-full bg-[var(--vp-accent)]/30 blur-xl transition ${ringClass}`} />
      <span
        className={`relative flex h-28 w-28 items-center justify-center rounded-full border text-sm font-bold tracking-[0.16em] text-white shadow-luxe transition duration-200 ${
          isListening
            ? "border-rose-200/50 bg-[var(--vp-danger)]"
            : isTranscribing
            ? "border-amber-200/50 bg-[var(--vp-warn)]"
            : "border-sky-200/60 bg-[var(--vp-accent)] group-hover:bg-[#1e86da]"
        }`}
      >
        {label}
      </span>
    </button>
  );
}
