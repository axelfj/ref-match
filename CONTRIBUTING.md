# Contributing

Thanks for helping. Bug reports with an example file are the most useful thing
you can send: open an issue and say which file format, sample rate and bit depth
it was, what Ref Match showed and what you expected.

## Running from source

```
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py                    # the window
python app.py --help             # the command line
python -m unittest discover -s tests -v
```

On Linux the window also needs Tk (`sudo apt install python3-tk`).

## Pull requests

- Keep each pull request to one change, with a test that fails without it.
- Tests use synthesized signals only. Do not commit audio files.
- `audio.py`, `loudness.py` and `stats.py` are shared with the other ROMMUSER
  tools ([master-check](https://github.com/axelfj/master-check),
  [mix-ready](https://github.com/axelfj/mix-ready),
  [ref-match](https://github.com/axelfj/ref-match)). A fix there should go to all three.

## Releasing

1. Bump `__version__` in `ref_match/__init__.py` and add a section to `CHANGELOG.md`.
2. Merge to `main`, then tag it: `git tag v0.2.0 && git push origin v0.2.0`.
3. GitHub Actions builds the Windows installer and the macOS disk image, checks
   that the tag matches `__version__`, and publishes the GitHub Release.

Versions follow [Semantic Versioning](https://semver.org).
