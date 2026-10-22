"""
Loudness and peak measurement.

  * Loudness: ITU-R BS.1770-5 (K-weighting, 400 ms blocks with 75 % overlap,
    -70 LUFS absolute gate, -10 LU relative gate).
  * Loudness range: EBU Tech 3342 (3 s short-term windows, -70 LUFS absolute
    gate, -20 LU relative gate, 10th to 95th percentile).
  * True peak: BS.1770 Annex 2, oversampled to at least 176.4 kHz.

K-weighting coefficients are derived for any sample rate the same way
libebur128 does, so 48 kHz reproduces the table in BS.1770 exactly.
"""
import math

import numpy as np
from scipy import signal

NEG_INF = float("-inf")
ABS_GATE = -70.0
CHANNEL_WEIGHTS_51 = (1.0, 1.0, 1.0, 0.0, 1.41, 1.41)  # L R C LFE Ls Rs


def db(x):
    return 20.0 * math.log10(x) if x > 0 else NEG_INF


def k_weighting(rate):
    """The two BS.1770 biquads (high shelf, then high pass) as (b, a) pairs."""
    f0, gain, q = 1681.974450955533, 3.999843853973347, 0.7071752369554196
    k = math.tan(math.pi * f0 / rate)
    vh = 10.0 ** (gain / 20.0)
    vb = vh ** 0.4996667741545416
    a0 = 1.0 + k / q + k * k
    shelf = ([(vh + vb * k / q + k * k) / a0, 2.0 * (k * k - vh) / a0,
              (vh - vb * k / q + k * k) / a0],
             [1.0, 2.0 * (k * k - 1.0) / a0, (1.0 - k / q + k * k) / a0])
    f0, q = 38.13547087602444, 0.5003270373238773
    k = math.tan(math.pi * f0 / rate)
    a0 = 1.0 + k / q + k * k
    highpass = ([1.0, -2.0, 1.0],
                [1.0, 2.0 * (k * k - 1.0) / a0, (1.0 - k / q + k * k) / a0])
    return shelf, highpass


def channel_weights(channels):
    if channels == 6:
        return CHANNEL_WEIGHTS_51
    return (1.0,) * channels


def weighted_power(samples, rate):
    """Per-sample K-weighted power summed over channels with BS.1770 weights."""
    (b1, a1), (b2, a2) = k_weighting(rate)
    sos = np.vstack([np.r_[b1, a1], np.r_[b2, a2]])
    total = np.zeros(samples.shape[0])
    for ch, w in enumerate(channel_weights(samples.shape[1])):
        if w == 0.0:
            continue
        y = signal.sosfilt(sos, samples[:, ch].astype(np.float64))
        total += w * y * y
    return total


def block_loudness(power, rate, window_s, hop_s):
    """Loudness (LUFS) of each sliding window over the weighted power signal."""
    win = int(round(window_s * rate))
    hop = int(round(hop_s * rate))
    if len(power) < win:
        return np.array([])
    csum = np.concatenate([[0.0], np.cumsum(power)])
    starts = np.arange(0, len(power) - win + 1, hop)
    mean_sq = (csum[starts + win] - csum[starts]) / win
    with np.errstate(divide="ignore"):
        return -0.691 + 10.0 * np.log10(np.maximum(mean_sq, 0.0))


def _energy(lufs):
    return 10.0 ** ((lufs + 0.691) / 10.0)


def _loudness(energy):
    return -0.691 + 10.0 * math.log10(energy) if energy > 0 else NEG_INF


def integrated(momentary_blocks):
    blocks = momentary_blocks[momentary_blocks > ABS_GATE]
    if blocks.size == 0:
        return NEG_INF
    rel_gate = _loudness(np.mean(_energy(blocks))) - 10.0
    blocks = blocks[blocks > rel_gate]
    return _loudness(np.mean(_energy(blocks)))


def loudness_range(short_term_blocks):
    blocks = short_term_blocks[short_term_blocks > ABS_GATE]
    if blocks.size == 0:
        return 0.0
    rel_gate = _loudness(np.mean(_energy(blocks))) - 20.0
    blocks = blocks[blocks > rel_gate]
    if blocks.size == 0:
        return 0.0
    low, high = np.percentile(blocks, [10, 95])
    return float(high - low)


def true_peak(samples, rate, chunk=1 << 20):
    """Highest absolute value after oversampling, linear scale."""
    factor = 1 if rate >= 176400 else (2 if rate >= 88200 else 4)
    if factor == 1:
        return float(np.max(np.abs(samples))) if samples.size else 0.0
    pad = 64
    peak = 0.0
    n = samples.shape[0]
    for ch in range(samples.shape[1]):
        x = samples[:, ch].astype(np.float64)
        for start in range(0, n, chunk):
            lo, hi = max(0, start - pad), min(n, start + chunk + pad)
            y = signal.resample_poly(x[lo:hi], factor, 1)
            # Drop the padded edges, where the filter sees a cut-off signal.
            y = y[(start - lo) * factor: len(y) - (hi - min(n, start + chunk)) * factor]
            if y.size:
                peak = max(peak, float(np.max(np.abs(y))))
    return max(peak, float(np.max(np.abs(samples))) if samples.size else 0.0)


def measure(samples, rate):
    """All loudness numbers for one file, as a dict of plain floats."""
    power = weighted_power(samples, rate)
    momentary = block_loudness(power, rate, 0.4, 0.1)
    short_term = block_loudness(power, rate, 3.0, 0.1)
    sample_peak = float(np.max(np.abs(samples))) if samples.size else 0.0
    tp = true_peak(samples, rate)
    result = {
        "integrated_lufs": integrated(momentary),
        "momentary_max_lufs": float(momentary.max()) if momentary.size else NEG_INF,
        "short_term_max_lufs": float(short_term.max()) if short_term.size else NEG_INF,
        "lra_lu": loudness_range(short_term),
        "sample_peak_dbfs": db(sample_peak),
        "true_peak_dbtp": db(tp),
    }
    i = result["integrated_lufs"]
    result["plr_db"] = result["true_peak_dbtp"] - i if i != NEG_INF else NEG_INF
    return result
