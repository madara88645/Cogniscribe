import json
import math
import os
import re
import tempfile
import time
import wave
from dataclasses import dataclass
from typing import Any, Optional

import ctranslate2
from faster_whisper import WhisperModel

from config_manager import get_profile_decode_options


@dataclass
class TranscriptionResult:
    text: str
    accepted: bool
    confidence: float
    avg_logprob: float
    no_speech_prob: float
    latency_sec: float
    duration_audio_sec: float
    model: str
    device: str
    warning: str = ""


class STTService:
    def __init__(self, config: dict[str, Any], sample_rate: int, channels: int):
        self.sample_rate = sample_rate
        self.channels = channels
        self._model: Optional[WhisperModel] = None
        self._loaded_signature: Optional[tuple[str, str, str]] = None
        self._cuda_disabled = False
        self.reload(config)

    def reload(self, config: dict[str, Any]) -> None:
        stt = config["stt"]
        device = self._resolve_device(stt)
        model_name = stt["model_gpu"] if device == "cuda" else stt["model_cpu"]
        compute_type = (
            stt["compute_type_gpu"] if device == "cuda" else stt["compute_type_cpu"]
        )
        signature = (model_name, device, compute_type)

        if signature == self._loaded_signature and self._model is not None:
            return

        print(
            f"[STT] Loading model={model_name} device={device} "
            f"compute_type={compute_type}"
        )
        try:
            self._model = WhisperModel(
                model_name, device=device, compute_type=compute_type
            )
            self._loaded_signature = signature
            return
        except Exception as exc:
            if device != "cuda":
                raise
            print(f"[STT] CUDA load failed ({exc}). Falling back to CPU.")
            self._cuda_disabled = True

        fallback_model = stt["model_cpu"]
        fallback_compute = stt["compute_type_cpu"]
        fallback_sig = (fallback_model, "cpu", fallback_compute)
        self._model = WhisperModel(
            fallback_model, device="cpu", compute_type=fallback_compute
        )
        self._loaded_signature = fallback_sig

    def _resolve_device(self, stt_cfg: dict[str, Any]) -> str:
        forced = stt_cfg.get("device", "auto")
        if forced in ("cpu", "cuda"):
            return forced
        if self._cuda_disabled:
            return "cpu"

        try:
            import torch  # type: ignore

            if torch.cuda.is_available():
                return "cuda"
        except Exception:
            pass

        try:
            if ctranslate2.get_cuda_device_count() > 0:
                return "cuda"
        except Exception:
            pass
        return "cpu"

    def transcribe_audio_bytes(
        self, audio_bytes: bytes, config: dict[str, Any]
    ) -> TranscriptionResult:
        self.reload(config)
        if self._model is None or self._loaded_signature is None:
            raise RuntimeError("STT model failed to load")
        duration_audio_sec = len(audio_bytes) / float(
            self.sample_rate * self.channels * 2
        )
        start = time.time()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            path = tmp.name

        try:
            with wave.open(path, "wb") as wav_file:
                wav_file.setnchannels(self.channels)
                wav_file.setsampwidth(2)
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(audio_bytes)

            language_mode = config["stt"].get("language_mode", "tr_en_mixed")
            primary_language = config["stt"].get("primary_language", "tr")
            language = (
                None if language_mode == "multilingual_auto" else primary_language
            )
            hints = config["stt"].get("term_hints", [])

            prompt = (
                "Bu konusma cogunlukla Turkce. "
                "Ingilizce teknik terimler, marka ve urun adlarini aynen koru."
                if language == "tr"
                else None
            )
            if language == "tr" and hints:
                prompt = f"{prompt} Terim ipuclari: {', '.join(hints[:12])}."

            first_decode = get_profile_decode_options(config)
            best = self._run_decode_pass(path, language, prompt, first_decode)
            min_conf = float(config["stt"].get("min_confidence_for_accept", 0.35))
            retry_enabled = bool(config["stt"].get("retry_on_low_confidence", True))
            needs_retry = (
                not best["text"]
                or best["confidence"] < min_conf
                or _looks_fragmented(best["text"])
            )

            if retry_enabled and needs_retry:
                retry_decode = {
                    "beam_size": max(5, int(first_decode["beam_size"])),
                    "best_of": max(5, int(first_decode["best_of"])),
                    "temperature": [0.0, 0.2, 0.4],
                    "vad_filter": True,
                }
                retry = self._run_decode_pass(path, language, prompt, retry_decode)
                best_score = _decode_quality_score(best)
                retry_score = _decode_quality_score(retry)
                if retry_score >= best_score or (not best["text"] and retry["text"]):
                    best = retry

            text = best["text"]
            avg_logprob = best["avg_logprob"]
            no_speech_prob = best["no_speech_prob"]
            confidence = best["confidence"]
            accepted = bool(text) and confidence >= min_conf
            warning = "" if accepted else "Dusuk guvenli sonuc, lutfen tekrar deneyin."
            latency = time.time() - start

            result = TranscriptionResult(
                text=text,
                accepted=accepted,
                confidence=confidence,
                avg_logprob=avg_logprob,
                no_speech_prob=no_speech_prob,
                latency_sec=latency,
                duration_audio_sec=duration_audio_sec,
                model=self._loaded_signature[0],
                device=self._loaded_signature[1],
                warning=warning,
            )
            self._write_telemetry(config, result)
            return result
        finally:
            try:
                os.remove(path)
            except Exception:
                pass

    def _run_decode_pass(
        self,
        path: str,
        language: str | None,
        prompt: str | None,
        decode: dict[str, Any],
    ) -> dict[str, Any]:
        if self._model is None:
            raise RuntimeError("STT model is not loaded")
        segments, _ = self._model.transcribe(
            path,
            language=language,
            initial_prompt=prompt,
            beam_size=int(decode["beam_size"]),
            best_of=int(decode["best_of"]),
            vad_filter=bool(decode["vad_filter"]),
            temperature=decode["temperature"],
            vad_parameters={"min_silence_duration_ms": 400, "speech_pad_ms": 350},
        )
        segment_list = list(segments)
        text = " ".join(seg.text.strip() for seg in segment_list).strip()
        avg_logprob = _mean(
            [getattr(seg, "avg_logprob", None) for seg in segment_list], -2.0
        )
        no_speech_prob = _mean(
            [getattr(seg, "no_speech_prob", None) for seg in segment_list], 0.35
        )
        confidence = _confidence_score(avg_logprob, no_speech_prob)
        return {
            "text": text,
            "avg_logprob": avg_logprob,
            "no_speech_prob": no_speech_prob,
            "confidence": confidence,
        }

    def _write_telemetry(
        self, config: dict[str, Any], result: TranscriptionResult
    ) -> None:
        telemetry = config.get("telemetry", {})
        if not telemetry.get("enabled", True):
            return
        output_path = telemetry.get("log_path", "logs/transcribe_metrics.jsonl")
        abs_path = output_path
        if not os.path.isabs(output_path):
            root = os.path.dirname(os.path.abspath(__file__))
            abs_path = os.path.join(root, output_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        line = {
            "ts": int(time.time()),
            "duration_audio_sec": round(result.duration_audio_sec, 3),
            "latency_sec": round(result.latency_sec, 3),
            "device": result.device,
            "model": result.model,
            "avg_logprob": round(result.avg_logprob, 4),
            "no_speech_prob": round(result.no_speech_prob, 4),
            "confidence": round(result.confidence, 4),
            "accepted": result.accepted,
        }
        with open(abs_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")


def _mean(values: list[Any], default: float) -> float:
    clean = [float(v) for v in values if v is not None]
    if not clean:
        return default
    return float(sum(clean) / len(clean))


def _confidence_score(avg_logprob: float, no_speech_prob: float) -> float:
    lp_conf = math.exp(min(0.0, avg_logprob))
    speech_conf = 1.0 - max(0.0, min(1.0, no_speech_prob))
    score = 0.6 * lp_conf + 0.4 * speech_conf
    return max(0.0, min(1.0, score))


_TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9çğıöşüÇĞİÖŞÜ]+")
_SPLIT_HINT_PATTERN = re.compile(r"\b[iı]p\s+le\s+mantasyon\b")


def _looks_fragmented(text: str) -> bool:
    if not text:
        return True
    lower_text = text.lower()
    tokens = _TOKEN_PATTERN.findall(lower_text)
    if len(tokens) < 4:
        return False
    short_tokens = sum(1 for token in tokens if len(token) <= 2)
    short_ratio = short_tokens / max(1, len(tokens))
    if short_ratio >= 0.35:
        return True
    return bool(_SPLIT_HINT_PATTERN.search(lower_text))


def _fragment_ratio(text: str) -> float:
    tokens = _TOKEN_PATTERN.findall((text or "").lower())
    if not tokens:
        return 1.0
    short_tokens = sum(1 for token in tokens if len(token) <= 2)
    return short_tokens / max(1, len(tokens))


def _decode_quality_score(decoded: dict[str, Any]) -> float:
    text = decoded.get("text", "")
    conf = float(decoded.get("confidence", 0.0))
    score = conf
    if _looks_fragmented(text):
        score -= 0.20
    score -= 0.10 * _fragment_ratio(text)
    return score
