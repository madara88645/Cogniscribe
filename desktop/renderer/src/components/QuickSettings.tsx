type Props = {
  model: string;
  profile: string;
  languageMode: string;
  onModelChange: (value: string) => void;
  onProfileChange: (value: string) => void;
  onLanguageModeChange: (value: string) => void;
  disabled?: boolean;
};

const selectClass =
  "w-full rounded-xl border border-[var(--vp-border)] bg-[#0b1327] px-3 py-2 text-sm font-medium text-[var(--vp-text)] shadow-soft outline-none transition focus:border-[var(--vp-accent)] focus:shadow-[0_0_0_3px_rgba(42,168,255,0.16)]";

export function QuickSettings({
  model,
  profile,
  languageMode,
  onModelChange,
  onProfileChange,
  onLanguageModeChange,
  disabled,
}: Props) {
  return (
    <section className="vp-glass vp-glow rounded-2xl border border-[var(--vp-border)] p-4">
      <p className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--vp-muted)]">Quick Settings</p>
      <div className="grid grid-cols-3 gap-2">
        <label className="space-y-1">
          <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--vp-muted)]">Model</span>
          <select className={selectClass} value={model} onChange={(e) => onModelChange(e.target.value)} disabled={disabled}>
            <option value="tiny">tiny</option>
            <option value="base">base</option>
            <option value="small">small</option>
            <option value="medium">medium</option>
            <option value="large-v3">large-v3</option>
          </select>
        </label>

        <label className="space-y-1">
          <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--vp-muted)]">Profile</span>
          <select className={selectClass} value={profile} onChange={(e) => onProfileChange(e.target.value)} disabled={disabled}>
            <option value="fast">fast</option>
            <option value="balanced">balanced</option>
            <option value="quality">quality</option>
          </select>
        </label>

        <label className="space-y-1">
          <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--vp-muted)]">Language</span>
          <select className={selectClass} value={languageMode} onChange={(e) => onLanguageModeChange(e.target.value)} disabled={disabled}>
            <option value="tr_en_mixed">TR + EN</option>
            <option value="multilingual_auto">Auto</option>
          </select>
        </label>
      </div>
    </section>
  );
}
