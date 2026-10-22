"""
Compares a mix with reference tracks at equal loudness.

Every file is measured as if it were normalized to the same integrated
loudness, so the comparison shows tone, width and dynamics rather than
"theirs is louder".
"""
import math
import os

import numpy as np
from scipy import signal

from . import audio, loudness

ANCHOR_LUFS = -14.0
LOWEST, HIGHEST = 20.0, 20000.0
# ISO 266 third-octave centre frequencies, 20 Hz to 20 kHz.
BAND_CENTRES = [20, 25, 31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800,
                1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500, 16000,
                20000]
REGIONS = [("Sub & low", 20, 120), ("Low mids", 120, 500), ("Mids", 500, 2000),
           ("High mids", 2000, 6000), ("Highs & air", 6000, 20000)]
MAX_REFS = 5


def band_edges(fc):
    return fc * 2 ** (-1 / 6), fc * 2 ** (1 / 6)


def _psd(x, rate):
    nper = 1 << int(round(math.log2(rate / 5.0)))   # about 0.2 s, 5 Hz resolution
    nper = min(nper, len(x)) if len(x) else nper
    return signal.welch(x, rate, window="hann", nperseg=nper, noverlap=nper // 2,
                        scaling="spectrum")


def _bands_db(freqs, power, centres):
    out = []
    for fc in centres:
        lo, hi = band_edges(fc)
        sel = (freqs >= lo) & (freqs < hi)
        p = float(power[sel].sum()) if sel.any() else 0.0
        out.append(10 * math.log10(p) if p > 0 else -150.0)
    return out


def _region_power(freqs, power, lo, hi):
    sel = (freqs >= lo) & (freqs < hi)
    return float(power[sel].sum())


def profile(path):
    """Loudness, third-octave spectrum and width of one file at ANCHOR_LUFS."""
    a = audio.read(path)
    x = a.samples.astype(np.float64)
    m = loudness.measure(a.samples, a.rate)
    i = m["integrated_lufs"]
    if i == loudness.NEG_INF:
        raise audio.AudioError("the file is silent")
    gain = 10 ** ((ANCHOR_LUFS - i) / 20.0)
    if x.shape[1] >= 2:
        mid = (x[:, 0] + x[:, 1]) / 2 * gain
        side = (x[:, 0] - x[:, 1]) / 2 * gain
    else:
        mid = x[:, 0] * gain
        side = np.zeros_like(mid)
    freqs, p_mid = _psd(mid, a.rate)
    _, p_side = _psd(side, a.rate)
    centres = [fc for fc in BAND_CENTRES if band_edges(fc)[1] <= a.rate / 2]
    bands = _bands_db(freqs, p_mid + p_side, centres)
    width = {}
    for name, lo, hi in REGIONS:
        pm, ps = _region_power(freqs, p_mid, lo, hi), _region_power(freqs, p_side, lo, hi)
        width[name] = 10 * math.log10(ps / pm) if pm > 0 and ps > 0 else -60.0
    return {
        "file": path,
        "name": os.path.basename(path),
        "rate": a.rate,
        "description": a.describe(),
        "loudness": m,
        "bands": dict(zip(centres, bands)),
        "width_db": width,
    }


def _mean_db(values):
    return 10 * math.log10(sum(10 ** (v / 10) for v in values) / len(values))


def reference_curve(refs):
    """Power average of the references, band by band (bands every ref has)."""
    common = [fc for fc in BAND_CENTRES if all(fc in r["bands"] for r in refs)]
    return {fc: _mean_db([r["bands"][fc] for r in refs]) for fc in common}


def region_of(fc):
    for name, lo, hi in REGIONS:
        if lo <= fc < hi or (hi == HIGHEST and fc == HIGHEST):
            return name
    return None


def describe_diff(region, d):
    size = abs(d)
    if size < 1.5:
        return "info", "%s match the references (%+.1f dB)." % (region, d)
    more = "more" if d > 0 else "less"
    if size < 3:
        return "info", "%s: slightly %s than the references (%+.1f dB)." % (region, more, d)
    if size < 6:
        return "warn", "%s: clearly %s than the references (%+.1f dB)." % (region, more, d)
    return "warn", "%s: much %s than the references (%+.1f dB)." % (region, more, d)


def compare(mix_path, ref_paths):
    if not ref_paths:
        raise ValueError("add at least one reference track")
    if len(ref_paths) > MAX_REFS:
        raise ValueError("use at most %d references" % MAX_REFS)
    mix = profile(mix_path)
    refs = [profile(p) for p in ref_paths]
    curve = reference_curve(refs)
    diff = {fc: mix["bands"][fc] - curve[fc] for fc in curve if fc in mix["bands"]}

    notes = []
    regions = {}
    for name, _lo, _hi in REGIONS:
        fcs = [fc for fc in diff if region_of(fc) == name]
        if not fcs:
            continue
        # Region difference = total mix power over total reference power in it.
        d = (_mean_db([mix["bands"][fc] for fc in fcs])
             - _mean_db([curve[fc] for fc in fcs]))
        regions[name] = d
        level, text = describe_diff(name, d)
        notes.append({"level": level, "message": text})

    ref_l = {k: sum(r["loudness"][k] for r in refs) / len(refs)
             for k in ("integrated_lufs", "lra_lu", "plr_db", "true_peak_dbtp")}
    mix_l = mix["loudness"]
    louder = mix_l["integrated_lufs"] - ref_l["integrated_lufs"]
    if abs(louder) >= 1.0:
        notes.insert(0, {"level": "info", "message": "Your mix is %.1f LU %s than the "
                         "references (%.1f vs %.1f LUFS)." % (abs(louder),
                                                             "louder" if louder > 0 else "quieter",
                                                             mix_l["integrated_lufs"],
                                                             ref_l["integrated_lufs"])})
    dyn = mix_l["plr_db"] - ref_l["plr_db"]
    if abs(dyn) >= 2.0:
        notes.append({"level": "info", "message": "Peak-to-loudness ratio is %.1f dB %s than "
                      "the references: your mix is %s." % (
                          abs(dyn), "higher" if dyn > 0 else "lower",
                          "more dynamic (less limited)" if dyn > 0 else "more squashed")})

    width = {}
    for name, _lo, _hi in REGIONS:
        ref_w = _mean_db([r["width_db"][name] for r in refs])
        width[name] = mix["width_db"][name] - ref_w
        if abs(width[name]) >= 3.0 and max(mix["width_db"][name], ref_w) > -30:
            notes.append({"level": "info", "message": "%s are %s than the references "
                          "(side/mid %+.1f dB)." % (name, "wider" if width[name] > 0
                                                    else "narrower", width[name])})

    return {"mix": mix, "refs": refs, "reference_curve": curve, "diff": diff,
            "regions": regions, "width_diff": width, "reference_loudness": ref_l,
            "notes": notes}


def export_matched(result, folder):
    """Writes each reference turned to the mix's integrated loudness, as 32-bit float WAV."""
    target = result["mix"]["loudness"]["integrated_lufs"]
    written = []
    for r in result["refs"]:
        a = audio.read(r["file"])
        gain_db = target - r["loudness"]["integrated_lufs"]
        stem = os.path.splitext(r["name"])[0]
        out = os.path.join(folder, "%s (matched %+.1f dB).wav" % (stem, gain_db))
        audio.write_wav_float(out, a.samples * np.float32(10 ** (gain_db / 20)), a.rate)
        written.append(out)
    return written
