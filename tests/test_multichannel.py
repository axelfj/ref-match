import os
import tempfile
import unittest
import numpy as np
from ref_match import audio
from ref_match.analysis import profile

class ChannelValidation(unittest.TestCase):
    def test_reject_multichannel_instead_of_silently_ignoring_channels(self):
        with tempfile.TemporaryDirectory() as folder:
            for count in (3, 6, 8):
                path = os.path.join(folder, str(count) + '.wav')
                x = np.zeros((44100, count))
                x[:, -1] = .1 * np.sin(2*np.pi*1000*np.arange(44100)/44100)
                audio.write_wav_float(path, x, 44100)
                with self.assertRaisesRegex(audio.AudioError, 'mono or stereo'):
                    profile(path)
