import { contextBridge, ipcRenderer } from "electron";

type Unsubscribe = () => void;

type StatusPayload = {
  status: "loading" | "ready" | "listening" | "transcribing" | "low_conf" | "error";
  trace_id?: string;
};

type TranscriptPayload = {
  text: string;
  confidence: number;
  accepted: boolean;
  pasted: boolean;
  warning?: string;
  trace_id?: string;
};

type MetricsPayload = {
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

type ErrorPayload = {
  message: string;
  trace_id?: string;
  traceback?: string;
};

function subscribe<T>(eventName: string, cb: (payload: T) => void): Unsubscribe {
  const handler = (_event: unknown, payload: { event: string; data: T }) => {
    if (payload?.event === eventName) {
      cb(payload.data);
    }
  };
  ipcRenderer.on("voicepaste:event", handler);
  return () => ipcRenderer.removeListener("voicepaste:event", handler);
}

const api = {
  startListening: () => ipcRenderer.invoke("voicepaste:startListening"),
  stopListening: () => ipcRenderer.invoke("voicepaste:stopListening"),
  getConfig: () => ipcRenderer.invoke("voicepaste:getConfig"),
  updateConfig: (patch: Record<string, unknown>) => ipcRenderer.invoke("voicepaste:updateConfig", patch),
  onStatus: (cb: (payload: StatusPayload) => void) => subscribe<StatusPayload>("status_changed", cb),
  onTranscript: (cb: (payload: TranscriptPayload) => void) => subscribe<TranscriptPayload>("transcript_ready", cb),
  onMetrics: (cb: (payload: MetricsPayload) => void) => subscribe<MetricsPayload>("metrics", cb),
  onError: (cb: (payload: ErrorPayload) => void) => subscribe<ErrorPayload>("runtime_error", cb),
};

contextBridge.exposeInMainWorld("voicePaste", api);
