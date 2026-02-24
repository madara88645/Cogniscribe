import { useEffect, useMemo, useState } from "react";

import { MetricsStrip } from "./components/MetricsStrip";
import { QuickSettings } from "./components/QuickSettings";
import { RecordButton } from "./components/RecordButton";
import { StatusBadge } from "./components/StatusBadge";
import { TranscriptCard } from "./components/TranscriptCard";
import type { ErrorPayload, MetricsPayload, StatusName, StatusPayload, TranscriptPayload } from "./types/voicePaste";


type AppConfig = {
  hotkey: string;
  exit_hotkey: string;
  stt: {
    model_cpu: string;
    quality_profile: string;
    language_mode: string;
  };
};

const DEFAULT_CONFIG: AppConfig = {
  hotkey: "ctrl+shift+space",
  exit_hotkey: "ctrl+shift+q",
  stt: {
    model_cpu: "small",
    quality_profile: "balanced",
    language_mode: "tr_en_mixed",
  },
};

export default function App() {
  const [config, setConfig] = useState<AppConfig>(DEFAULT_CONFIG);
  const [status, setStatus] = useState<StatusName>("loading");
  const [transcript, setTranscript] = useState<TranscriptPayload>({ text: "", confidence: 0, accepted: false, pasted: false });
  const [metrics, setMetrics] = useState<MetricsPayload>({
    latency_sec: 0,
    duration_audio_sec: 0,
    device: "-",
    model: "-",
    avg_logprob: 0,
    no_speech_prob: 0,
    confidence: 0,
    accepted: false,
  });
  const [error, setError] = useState<string>("");

  useEffect(() => {
    let mounted = true;

    const setup = async () => {
      try {
        const cfg = await window.voicePaste.getConfig();
        if (mounted) {
          setConfig(cfg);
          setStatus("ready");
        }
      } catch (err) {
        if (mounted) {
          setError(String(err));
          setStatus("error");
        }
      }
    };

    void setup();

    const unsubStatus = window.voicePaste.onStatus((payload: StatusPayload) => {
      setStatus(payload.status);
    });
    const unsubTranscript = window.voicePaste.onTranscript((payload: TranscriptPayload) => {
      setTranscript(payload);
      if (payload.warning) setError(payload.warning);
    });
    const unsubMetrics = window.voicePaste.onMetrics((payload: MetricsPayload) => {
      setMetrics(payload);
    });
    const unsubError = window.voicePaste.onError((payload: ErrorPayload) => {
      setError(payload.message);
    });

    return () => {
      mounted = false;
      unsubStatus();
      unsubTranscript();
      unsubMetrics();
      unsubError();
    };
  }, []);

  const isListening = status === "listening";
  const isTranscribing = status === "transcribing";
  const isBusy = isListening || isTranscribing || status === "loading";

  const hotkeysText = useMemo(() => {
    const record = config.hotkey?.split("+").join(" + ").toUpperCase() || "CTRL + SHIFT + SPACE";
    const exit = config.exit_hotkey?.split("+").join(" + ").toUpperCase() || "CTRL + SHIFT + Q";
    return { record, exit };
  }, [config.hotkey, config.exit_hotkey]);

  const toggleListening = async () => {
    try {
      if (isListening) {
        await window.voicePaste.stopListening();
      } else {
        await window.voicePaste.startListening();
      }
    } catch (err) {
      setError(String(err));
      setStatus("error");
    }
  };

  const patchConfig = async (patch: Record<string, unknown>) => {
    try {
      const updated = await window.voicePaste.updateConfig(patch);
      setConfig(updated);
    } catch (err) {
      setError(String(err));
      setStatus("error");
    }
  };

  return (
    <main className="mx-auto flex h-full w-full max-w-[420px] flex-col gap-3 p-4">
      <header className="rounded-2xl border border-[var(--vp-border)] bg-[var(--vp-surface)]/95 px-4 py-4 shadow-soft">
        <div className="mb-2 flex items-center justify-between">
          <h1 className="font-display text-2xl tracking-tight text-[var(--vp-text)]">Voice Paste Studio</h1>
          <StatusBadge status={status} />
        </div>
        <p className="text-xs text-[var(--vp-muted)]">Refined local dictation workspace with compact desktop flow.</p>
      </header>

      <section className="rounded-2xl border border-[var(--vp-border)] bg-[var(--vp-surface)]/95 px-4 py-4 text-center shadow-soft">
        <RecordButton isListening={isListening} isTranscribing={isTranscribing} disabled={status === "loading"} onClick={() => void toggleListening()} />
        <p className="mt-3 text-xs font-semibold uppercase tracking-[0.14em] text-[var(--vp-muted)]">{hotkeysText.record} to record</p>
      </section>

      <QuickSettings
        model={config.stt?.model_cpu || "small"}
        profile={config.stt?.quality_profile || "balanced"}
        languageMode={config.stt?.language_mode || "tr_en_mixed"}
        onModelChange={(value) => void patchConfig({ stt: { model_cpu: value } })}
        onProfileChange={(value) => void patchConfig({ stt: { quality_profile: value } })}
        onLanguageModeChange={(value) => void patchConfig({ stt: { language_mode: value } })}
        disabled={isBusy}
      />

      <TranscriptCard text={transcript.text} confidence={transcript.confidence} accepted={Boolean(transcript.accepted)} />

      <MetricsStrip latencySec={metrics.latency_sec} device={metrics.device} model={metrics.model} confidence={metrics.confidence} />

      <footer className="mt-auto rounded-2xl border border-[var(--vp-border)] bg-[var(--vp-surface)]/90 px-4 py-3 text-[11px] text-[var(--vp-muted)] shadow-soft">
        <p className="font-semibold uppercase tracking-[0.12em]">Hotkeys</p>
        <p>Record: {hotkeysText.record}</p>
        <p>Exit: {hotkeysText.exit}</p>
        <p className="mt-1">Tray Mode: Active</p>
        {error ? <p className="mt-2 rounded-lg bg-red-100 px-2 py-1 text-red-700">{error}</p> : null}
      </footer>
    </main>
  );
}
