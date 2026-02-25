import math

import numpy as np


INT16_MAX = 32768.0


def get_rms(audio_data: np.ndarray) -> float:
    if len(audio_data) == 0:
        return 0.0
    x = audio_data.astype(np.float32)
    return float(np.sqrt(np.mean(x * x)))


def bytes_to_int16(audio_bytes: bytes) -> np.ndarray:
    return np.frombuffer(audio_bytes, dtype=np.int16).copy()


def int16_to_bytes(audio_data: np.ndarray) -> bytes:
    clipped = np.clip(audio_data, -32768, 32767).astype(np.int16)
    return clipped.tobytes()


def highpass_filter(
    audio_data: np.ndarray, sample_rate: int, cutoff_hz: float
) -> np.ndarray:
    if cutoff_hz <= 0:
        return audio_data.astype(np.float32)
    x = audio_data.astype(np.float32)
    dt = 1.0 / float(sample_rate)
    rc = 1.0 / (2.0 * math.pi * float(cutoff_hz))
    alpha = rc / (rc + dt)
    y = np.zeros_like(x, dtype=np.float32)
    prev_y = 0.0
    prev_x = x[0] if len(x) > 0 else 0.0
    for i, cur_x in enumerate(x):
        cur_y = alpha * (prev_y + cur_x - prev_x)
        y[i] = cur_y
        prev_y = cur_y
        prev_x = cur_x
    return y


def normalize_to_dbfs(audio_data: np.ndarray, target_dbfs: float) -> np.ndarray:
    x = audio_data.astype(np.float32)
    if len(x) == 0:
        return x
    rms = np.sqrt(np.mean(x * x))
    if rms < 1e-6:
        return x
    current_dbfs = 20.0 * np.log10(rms / INT16_MAX)
    gain = 10.0 ** ((target_dbfs - current_dbfs) / 20.0)
    return x * gain


def suppress_noise(audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
    x = audio_data.astype(np.float32)
    if len(x) == 0:
        return x
    head = x[: max(int(0.25 * sample_rate), 1)]
    floor = np.percentile(np.abs(head), 70)
    threshold = max(40.0, floor * 1.5)
    x[np.abs(x) < threshold] = 0.0
    return x


def preprocess_audio_bytes(
    audio_bytes: bytes,
    sample_rate: int,
    highpass_hz: float,
    normalize_target_dbfs: float,
    noise_suppression: bool,
) -> bytes:
    data = bytes_to_int16(audio_bytes)
    processed = highpass_filter(data, sample_rate, highpass_hz)
    if noise_suppression:
        processed = suppress_noise(processed, sample_rate)
    processed = normalize_to_dbfs(processed, normalize_target_dbfs)
    return int16_to_bytes(processed)


def calibrate_silence_threshold(
    stream,
    sample_rate: int,
    chunk_size: int,
    calibration_seconds: float,
    adaptive_multiplier: float,
    fallback_threshold: int,
    min_threshold: int,
) -> int:
    if calibration_seconds <= 0:
        return int(fallback_threshold)
    total_chunks = max(1, int((calibration_seconds * sample_rate) / chunk_size))
    values = []
    for _ in range(total_chunks):
        try:
            chunk = stream.read(chunk_size, exception_on_overflow=False)
            rms = get_rms(np.frombuffer(chunk, dtype=np.int16))
            values.append(rms)
        except Exception:
            break
    if not values:
        return int(fallback_threshold)
    ambient = float(np.percentile(values, 90))
    adaptive = int(max(min_threshold, ambient * adaptive_multiplier))
    return int(max(fallback_threshold, adaptive))
