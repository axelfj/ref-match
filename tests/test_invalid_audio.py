"""Malformed float audio must never become an analysis verdict."""
import json
import numpy as np
import pytest
from ref_match import audio, report

@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize("whole_file", [False, True])
def test_reject_nonfinite_audio(tmp_path, bad, whole_file):
    x = np.full((4410, 2), 0.01, dtype=np.float32)
    if whole_file:
        x[:] = bad
    else:
        x[200, 1] = bad
    path = str(tmp_path / "corrupt.wav")
    audio.write_wav_float(path, x, 44100)
    with pytest.raises(audio.AudioError, match="non-finite"):
        audio.read(path)

def test_width_distinguishes_silent_mono_and_antiphase():
    from ref_match.analysis import width_ratio_db
    assert width_ratio_db(0, 0) is None
    assert width_ratio_db(1, 0) == -60
    assert width_ratio_db(0, 1) == 60
    assert width_ratio_db(1, 1) == 0

def test_antiphase_warns_and_exports_strict_json(tmp_path):
    from ref_match import analysis
    x = .1 * np.sin(2 * np.pi * 1000 * np.arange(44100) / 44100)
    mix, ref = str(tmp_path / "anti.wav"), str(tmp_path / "mono.wav")
    audio.write_wav_float(mix, np.column_stack([x, -x]), 44100)
    audio.write_wav_float(ref, np.column_stack([x, x]), 44100)
    result = analysis.compare(mix, [ref])
    assert result["mix"]["width_db"]["Mids"] == 60
    assert any(n["level"] == "warn" and "mono cancellation" in n["message"] for n in result["notes"])
    json.loads(report.to_json(result), parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))
