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

    # Use existing float32 array if provided, or copy/cast
    if audio_data.dtype == np.float32:
        x = audio_data
    else:
        x = audio_data.astype(np.float32)

    dt = 1.0 / float(sample_rate)
    rc = 1.0 / (2.0 * math.pi * float(cutoff_hz))
    alpha = rc / (rc + dt)

    # Use python list for slightly faster scalar iteration in pure python
    # This avoids numpy overhead for scalar assignment in loop
    x_list = x.tolist()
    y_list = [0.0] * len(x_list)

    prev_y = 0.0
    prev_x = x_list[0] if len(x_list) > 0 else 0.0

    for i, cur_x in enumerate(x_list):
        cur_y = alpha * (prev_y + cur_x - prev_x)
        y_list[i] = cur_y
        prev_y = cur_y
        prev_x = cur_x

    return np.array(y_list, dtype=np.float32)

def normalize_to_dbfs(audio_data: np.ndarray, target_dbfs: float) -> np.ndarray:
    if audio_data.dtype == np.float32:
        x = audio_data
    else:
        x = audio_data.astype(np.float32)

    if len(x) == 0:
        return x

    rms = np.sqrt(np.mean(x * x))
    if rms < 1e-6:
        return x

    current_dbfs = 20.0 * np.log10(rms / INT16_MAX)
    gain = 10.0 ** ((target_dbfs - current_dbfs) / 20.0)

    # In-place modification if possible
    # Note: If x was a view or shared, this modifies it.
    # In our pipeline we create a fresh float32 array so it's safe.
    x *= gain
    return x

def suppress_noise(audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
    if audio_data.dtype == np.float32:
        x = audio_data
    else:
        x = audio_data.astype(np.float32)

    if len(x) == 0:
        return x

    head = x[: max(int(0.25 * sample_rate), 1)]
    floor = np.percentile(np.abs(head), 70)
    threshold = max(40.0, floor * 1.5)

    # In-place modification
    x[np.abs(x) < threshold] = 0.0
    return x

def preprocess_audio_bytes(
    audio_bytes: bytes,
    sample_rate: int,
    highpass_hz: float,
    normalize_target_dbfs: float,
    noise_suppression: bool,
) -> bytes:
    # 1. Convert to int16
    int16_data = bytes_to_int16(audio_bytes)

    # 2. Convert to float32 immediately
    float_data = int16_data.astype(np.float32)

    # 3. Process in float32 domain
    # highpass_filter returns a NEW float32 array
    processed = highpass_filter(float_data, sample_rate, highpass_hz)

    if noise_suppression:
        # suppress_noise modifies in-place or returns reference
        processed = suppress_noise(processed, sample_rate)

    # normalize_to_dbfs modifies in-place or returns reference
    processed = normalize_to_dbfs(processed, normalize_target_dbfs)

    # 4. Convert back to int16 bytes
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
