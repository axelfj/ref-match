"""
Entry point for the packaged app and for running from source.

  python app.py                       opens the window
  python app.py MIX --ref REF ...     command line report (see --help)
  python app.py --selftest            checks a packaged build without opening a window
"""
import sys


def selftest():
    import os
    import tempfile

    import numpy as np
    import soundfile
    import tkinter  # noqa: F401  (the window needs it in the bundle)

    from ref_match import audio, report
    from ref_match.analysis import compare

    rate = 48000
    rng = np.random.default_rng(0)
    folder = tempfile.mkdtemp()
    mix = os.path.join(folder, "mix.wav")
    ref = os.path.join(folder, "ref.flac")
    audio.write_wav_pcm(mix, rng.normal(0, 0.05, (rate * 5, 2)), rate, 24)
    soundfile.write(ref, rng.normal(0, 0.2, (rate * 5, 2)), rate, subtype="PCM_24")
    r = compare(mix, [ref])
    assert abs(r["regions"]["Mids"]) < 1.0, r["regions"]
    assert "<svg" in report.to_html(r)
    print("selftest OK")


def main():
    if "--selftest" in sys.argv:
        selftest()
        return 0
    args = [a for a in sys.argv[1:] if not a.startswith("-psn_")]  # old macOS Finder arg
    if args:
        from ref_match.cli import main as cli_main
        return cli_main(args)
    from ref_match.gui import main as gui_main
    gui_main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
