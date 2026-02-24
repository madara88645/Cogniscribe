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
      <span className={`absolute -inset-2 rounded-full bg-[var(--vp-accent)]/20 blur-md transition ${ringClass}`} />
      <span
        className={`relative flex h-28 w-28 items-center justify-center rounded-full border border-white/60 text-sm font-bold tracking-[0.16em] text-white shadow-luxe transition duration-200 ${
          isListening
            ? "bg-[var(--vp-danger)]"
            : isTranscribing
            ? "bg-[var(--vp-warn)]"
            : "bg-[var(--vp-accent)] group-hover:bg-[#7f5522]"
        }`}
      >
        {label}
      </span>
    </button>
  );
}
