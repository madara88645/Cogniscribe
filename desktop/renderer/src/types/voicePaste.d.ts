export type StatusName = "loading" | "ready" | "listening" | "transcribing" | "low_conf" | "error";

export type StatusPayload = {
  status: StatusName;
  trace_id?: string;
};

export type TranscriptPayload = {
  text: string;
  confidence: number;
  accepted: boolean;
  pasted: boolean;
  warning?: string;
  trace_id?: string;
};

export type MetricsPayload = {
  latency_sec: number;
  duration_audio_sec: number;
  device: string;
  model: string;
  avg_logprob: number;
  no_speech_prob: number;
  confidence: number;
  accepted: boolean;
  trace_id?: string;
};

export type ErrorPayload = {
  message: string;
  trace_id?: string;
  traceback?: string;
};

declare global {
  interface Window {
    voicePaste: {
      startListening: () => Promise<void>;
      stopListening: () => Promise<void>;
      getConfig: () => Promise<any>;
      updateConfig: (patch: Record<string, unknown>) => Promise<any>;
      onStatus: (cb: (payload: StatusPayload) => void) => () => void;
      onTranscript: (cb: (payload: TranscriptPayload) => void) => () => void;
      onMetrics: (cb: (payload: MetricsPayload) => void) => () => void;
      onError: (cb: (payload: ErrorPayload) => void) => () => void;
    };
  }
}

export {};
