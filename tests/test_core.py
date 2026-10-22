"""Tests for the shared reader and meter, with synthesized signals."""
import os
import tempfile
import unittest

import numpy as np
import soundfile

from ref_match import audio, loudness, stats


def sine(freq, seconds, rate, dbfs, phase=0.0):
    t = np.arange(int(seconds * rate)) / rate
    return 10 ** (dbfs / 20) * np.sin(2 * np.pi * freq * t + phase)


def stereo(x):
    return np.stack([x, x], 1).astype(np.float32)


class LoudnessTest(unittest.TestCase):
    def test_ebu_3341_reference_tone_reads_minus_23(self):
        for rate in (44100, 48000, 96000):
            m = loudness.measure(stereo(sine(1000, 20, rate, -23)), rate)
            self.assertAlmostEqual(m["integrated_lufs"], -23.0, delta=0.1, msg=rate)
            self.assertAlmostEqual(m["momentary_max_lufs"], -23.0, delta=0.1)
            self.assertAlmostEqual(m["short_term_max_lufs"], -23.0, delta=0.1)

    def test_48k_coefficients_match_bs1770_table(self):
        (b1, a1), (b2, a2) = loudness.k_weighting(48000)
        np.testing.assert_allclose(b1, [1.53512485958697, -2.69169618940638,
                                        1.19839281085285], atol=1e-6)
        np.testing.assert_allclose(a1[1:], [-1.69065929318241, 0.73248077421585], atol=1e-6)
        np.testing.assert_allclose(a2[1:], [-1.99004745483398, 0.99007225036621], atol=1e-6)

    def test_relative_gate_ignores_quiet_part(self):
        rate = 48000
        x = np.concatenate([sine(1000, 10, rate, -20), sine(1000, 10, rate, -50)])
        self.assertAlmostEqual(loudness.measure(stereo(x), rate)["integrated_lufs"], -20.0,
                               delta=0.1)

    def test_silence_is_minus_infinity(self):
        m = loudness.measure(np.zeros((48000 * 2, 2), np.float32), 48000)
        self.assertEqual(m["integrated_lufs"], loudness.NEG_INF)

    def test_ebu_3342_loudness_range(self):
        rate = 48000
        for a, b, lra in ((-20, -30, 10), (-20, -15, 5), (-40, -20, 20)):
            x = np.concatenate([sine(1000, 20, rate, a), sine(1000, 20, rate, b)])
            self.assertAlmostEqual(loudness.measure(stereo(x), rate)["lra_lu"], lra, delta=1.0)

    def test_true_peak_finds_intersample_peak(self):
        rate = 48000
        x = stereo(sine(rate / 4, 2, rate, -6, phase=np.pi / 4))
        m = loudness.measure(x, rate)
        self.assertAlmostEqual(m["sample_peak_dbfs"], -9.0, delta=0.1)
        self.assertAlmostEqual(m["true_peak_dbtp"], -6.0, delta=0.3)


class AudioTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.x = stereo(sine(440, 1, 44100, -6))

    def test_pcm_round_trips(self):
        for bits in (16, 24, 32):
            p = os.path.join(self.dir, "t%d.wav" % bits)
            audio.write_wav_pcm(p, self.x, 44100, bits)
            a = audio.read(p)
            self.assertEqual((a.rate, a.bits, a.channels, a.is_float), (44100, bits, 2, False))
            self.assertEqual(a.format_tag, audio.WAV_PCM)
            np.testing.assert_allclose(a.samples, self.x, atol=2.0 ** -(bits - 2))

    def test_float_round_trips(self):
        p = os.path.join(self.dir, "f.wav")
        audio.write_wav_float(p, self.x * 2, 48000)
        a = audio.read(p)
        self.assertTrue(a.is_float)
        np.testing.assert_array_equal(a.samples, self.x * 2)

    def test_extensible_header_is_reported(self):
        p = os.path.join(self.dir, "x.wav")
        audio.write_wav_pcm(p, self.x, 44100, 24, extensible=True)
        a = audio.read(p)
        self.assertEqual(a.format_tag, audio.WAV_EXTENSIBLE)
        self.assertEqual(a.bits, 24)
        self.assertFalse(a.is_float)
        self.assertEqual(soundfile.info(p).subtype, "PCM_24")

    def test_reads_flac_and_aiff(self):
        for ext, sub in (("flac", "PCM_16"), ("aiff", "PCM_24")):
            p = os.path.join(self.dir, "s." + ext)
            soundfile.write(p, self.x, 44100, subtype=sub)
            a = audio.read(p)
            self.assertEqual(a.frames, len(self.x))
            np.testing.assert_allclose(a.samples, self.x, atol=1e-4)

    def test_garbage_raises_audio_error(self):
        p = os.path.join(self.dir, "bad.wav")
        with open(p, "wb") as f:
            f.write(b"not audio at all")
        with self.assertRaises(audio.AudioError):
            audio.read(p)


class StatsTest(unittest.TestCase):
    def test_clip_runs(self):
        x = np.zeros((1000, 1), np.float32)
        x[10:15] = 1.0
        x[100:102] = -1.0     # 2 samples: not a clip
        x[500:510] = -1.0
        self.assertEqual(stats.clip_runs(x), 2)

    def test_effective_bits_spots_padded_16_bit(self):
        rng = np.random.default_rng(1)
        x16 = (np.round(rng.normal(0, 0.1, (4800, 2)) * 32768) / 32768).astype(np.float32)
        self.assertEqual(stats.effective_bits(x16, 24, False), 16)
        x24 = (np.round(rng.normal(0, 0.1, (4800, 2)) * 2 ** 23) / 2 ** 23).astype(np.float32)
        self.assertEqual(stats.effective_bits(x24, 24, False), 24)

    def test_correlation_and_edges(self):
        x = sine(100, 1, 48000, -6)
        self.assertAlmostEqual(stats.correlation(x, -x), -1.0, places=6)
        pad = np.zeros(48000)
        y = np.concatenate([pad, x, pad, pad])[:, None]
        head, tail = stats.edge_silence(y, 48000)
        self.assertAlmostEqual(head, 1.0, delta=0.01)
        self.assertAlmostEqual(tail, 2.0, delta=0.01)


if __name__ == "__main__":
    unittest.main()
