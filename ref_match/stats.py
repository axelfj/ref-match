"""
Sample-level statistics shared by the checks: clipping, DC offset, stereo
correlation, silence at the edges and the real bit depth of the audio.
"""
import math

import numpy as np

from .loudness import NEG_INF, db

CLIP_LEVEL = 0.99995
CLIP_RUN = 3          # this many full-scale samples in a row count as a clip
SILENCE_DBFS = -60.0


def clip_runs(samples, level=CLIP_LEVEL, min_run=CLIP_RUN):
    """Number of places where the waveform sits at full scale for min_run samples."""
    total = 0
    for ch in range(samples.shape[1]):
        hot = np.abs(samples[:, ch]) >= level
        if not hot.any():
            continue
        edges = np.diff(np.concatenate([[0], hot.view(np.int8), [0]]))
        starts, ends = np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)
        total += int(np.count_nonzero(ends - starts >= min_run))
    return total


def overs(samples):
    """Samples above 0 dBFS. Only floating point files can hold them."""
    return int(np.count_nonzero(np.abs(samples) > 1.0))


def dc_offset_db(samples):
    """Largest per-channel DC offset in dBFS."""
    if samples.size == 0:
        return NEG_INF
    return db(float(np.max(np.abs(samples.mean(axis=0, dtype=np.float64)))))


def correlation(left, right):
    """Pearson correlation of two channels; 1.0 for silence or identical signals."""
    l = left.astype(np.float64)
    r = right.astype(np.float64)
    l -= l.mean()
    r -= r.mean()
    den = math.sqrt(float(np.dot(l, l)) * float(np.dot(r, r)))
    if den == 0.0:
        return 1.0
    return float(np.dot(l, r) / den)


def is_dual_mono(samples):
    return samples.shape[1] == 2 and np.array_equal(samples[:, 0], samples[:, 1])


def edge_silence(samples, rate, threshold_db=SILENCE_DBFS):
    """Seconds of near-silence at the start and at the end."""
    level = 10.0 ** (threshold_db / 20.0)
    loud = np.flatnonzero(np.max(np.abs(samples), axis=1) > level)
    if loud.size == 0:
        dur = samples.shape[0] / float(rate)
        return dur, dur
    return loud[0] / float(rate), (samples.shape[0] - 1 - loud[-1]) / float(rate)


def edge_rms_db(samples, rate, seconds=0.01):
    """RMS level of the first and the last few milliseconds."""
    n = max(1, int(rate * seconds))
    head = samples[:n].astype(np.float64)
    tail = samples[-n:].astype(np.float64)
    return (db(math.sqrt(float(np.mean(head * head)))),
            db(math.sqrt(float(np.mean(tail * tail)))))


def effective_bits(samples, declared_bits, is_float):
    """
    Smallest bit depth whose grid holds every sample. A 24-bit file that is
    really 16-bit audio (padded with zeros) returns 16.
    """
    x = samples[np.abs(samples) > 0]
    if x.size == 0:
        return 0
    x = x[: 1 << 20].astype(np.float64)
    for bits in (8, 16, 24):
        if bits >= declared_bits and not is_float:
            break
        scaled = x * (2 ** (bits - 1))
        if np.all(scaled == np.round(scaled)):
            return bits
    return 32 if is_float else declared_bits
