import os
import tempfile
import unittest

import numpy as np
from scipy import signal

from ref_match import audio, chart, loudness, report
from ref_match.analysis import compare, export_matched, profile
from ref_match.cli import main as cli_main

RATE = 44100


def music(seconds=15, seed=0, width=0.3, bass_db=0.0, gain_db=-10.0, rate=RATE):
    """Pink-ish stereo noise; bass_db boosts everything below 120 Hz."""
    rng = np.random.default_rng(seed)
    n = int(seconds * rate)
    white = rng.normal(0, 1, (n, 2))
    b, a = signal.butter(1, 200, "lowpass", fs=rate)
    pinkish = white + 3 * signal.lfilter(b, a, white, axis=0)
    mid = pinkish[:, 0]
    side = pinkish[:, 1] * width
    x = np.stack([mid + side, mid - side], 1)
    if bass_db:
        sos = signal.butter(4, 120, "lowpass", fs=rate, output="sos")
        low = signal.sosfilt(sos, x, axis=0)
        x = x + (10 ** (bass_db / 20) - 1) * low
    return x / np.max(np.abs(x)) * 10 ** (gain_db / 20)


class RefMatchTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def write(self, name, x, rate=RATE):
        p = os.path.join(self.dir, name)
        audio.write_wav_pcm(p, x, rate, 24)
        return p

    def test_same_track_at_other_level_matches(self):
        mix = self.write("mix.wav", music(gain_db=-12))
        ref = self.write("ref.wav", music(gain_db=-2))
        r = compare(mix, [ref])
        for d in r["regions"].values():
            self.assertLess(abs(d), 0.2)
        self.assertIn("quieter", r["notes"][0]["message"])

    def test_bass_heavy_mix_is_reported(self):
        mix = self.write("mix.wav", music(bass_db=8))
        refs = [self.write("r%d.wav" % i, music(seed=i + 1)) for i in range(2)]
        r = compare(mix, refs)
        self.assertGreater(r["regions"]["Sub & low"], 3.0)
        self.assertTrue(any(n["level"] == "warn" and n["message"].startswith("Sub & low")
                            for n in r["notes"]))
        # Normalization turns the rest of the mix down to make room for the bass.
        self.assertLess(r["regions"]["Highs & air"], 0.0)

    def test_width(self):
        mix = self.write("mix.wav", music(width=1.0))
        ref = self.write("ref.wav", music(width=0.1, seed=3))
        r = compare(mix, [ref])
        self.assertGreater(r["width_diff"]["Mids"], 10)
        mono = profile(self.write("mono.wav", music()[:, :1]))
        self.assertEqual(mono["width_db"]["Mids"], -60.0)

    def test_mixed_sample_rates(self):
        mix = self.write("mix.wav", music())
        ref = self.write("ref48.wav", music(rate=48000, seed=4), rate=48000)
        r = compare(mix, [ref])
        self.assertNotIn(20000, r["diff"])
        self.assertLess(abs(r["regions"]["Mids"]), 1.5)

    def test_export_matched_references(self):
        mix = self.write("mix.wav", music(gain_db=-14))
        ref = self.write("ref.wav", music(gain_db=-1, seed=5))
        r = compare(mix, [ref])
        out = export_matched(r, self.dir)
        a = audio.read(out[0])
        self.assertTrue(a.is_float)
        got = loudness.measure(a.samples, a.rate)["integrated_lufs"]
        self.assertAlmostEqual(got, r["mix"]["loudness"]["integrated_lufs"], delta=0.05)

    def test_limits(self):
        mix = self.write("mix.wav", music())
        with self.assertRaises(ValueError):
            compare(mix, [])
        with self.assertRaises(audio.AudioError):
            compare(mix, [self.write("silent.wav", np.zeros((RATE * 2, 2)))])

    def test_reports_chart_and_cli(self):
        mix = self.write("mix.wav", music(bass_db=6))
        ref = self.write("ref.wav", music(seed=7))
        r = compare(mix, [ref])
        svg = chart.to_svg(r)
        self.assertEqual(svg.count("<svg"), 1)
        self.assertIn("Sub & low", report.text(r))
        self.assertIn("ref.wav", report.to_json(r))
        html_out = os.path.join(self.dir, "r.html")
        code = cli_main([mix, "--ref", ref, "--html", html_out, "--export", self.dir])
        self.assertEqual(code, 0)
        self.assertTrue(any(n.startswith("ref (matched") for n in os.listdir(self.dir)))
        self.assertEqual(cli_main([mix, "--ref", os.path.join(self.dir, "missing.wav")]), 2)


if __name__ == "__main__":
    unittest.main()
