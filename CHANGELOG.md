# Changelog

## Unreleased: V2 preparation

- Distinguir bandas sin energía, mono y contrafase; advertir cancelación mono; rechazar audio vacío/no finito y emitir JSON estricto.
- Todavía no constituye una versión V2 publicada ni valida binarios nativos.

All notable changes to Ref Match are listed here. Versions follow
[Semantic Versioning](https://semver.org).

## [0.1.0] - 2026-10-22

First release.

- Compares a mix with 1 to 5 reference tracks as if all were normalized to the same
  integrated loudness (ITU-R BS.1770-5).
- Third-octave spectrum chart (20 Hz to 20 kHz) of the mix against the average of the
  references, and the difference, with a +/-3 dB zone.
- Tone and stereo width (side relative to mid) in five ranges, from sub to air, with
  plain-language notes.
- Loudness, peak-to-loudness ratio, LRA and true peak side by side.
- Exports each reference turned to the mix's loudness as 32-bit float WAV, for a fair
  A/B in the DAW.
- Reads WAV (including RF64 and 32-bit float), AIFF, FLAC, MP3 and OGG.
- Window app plus command line, with HTML (chart included) and JSON reports.
- Windows installer and macOS (Apple silicon) disk image.

