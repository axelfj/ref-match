# Ref Match

**Compare your mix with reference tracks at equal loudness.** Louder always sounds
better, so comparing your mix with a finished release by ear is rigged. Ref Match
measures every file as if they were all at the same loudness and shows where your mix
really differs:

- **Tone**: a third-octave spectrum of your mix over the average of up to 5 references,
  and the difference band by band. Anything outside the +/-3 dB zone is highlighted.
- **Notes in plain words**: "Sub & low: clearly more than the references (+4.1 dB)",
  "High mids are narrower than the references".
- **Stereo width** in five ranges, from sub to air.
- **Dynamics**: loudness, peak-to-loudness ratio, LRA and true peak next to the references.
- **Matched references for your DAW**: export each reference turned down (or up) to your
  mix's loudness as a 32-bit float WAV, drop them on a track and A/B fairly.

There is no audio playback in the app: listening happens in your DAW with the matched files.

Free and open source (MIT), made by [ROMMUSER](https://rommuser.com). Part of a set with
[Master Check](https://github.com/axelfj/master-check),
[Mix Ready](https://github.com/axelfj/mix-ready) and
[Stem Organizer](https://github.com/axelfj/stem-organizer).

## Download

Get the latest version from the [Releases page](https://github.com/axelfj/ref-match/releases/latest):

| System | File |
|---|---|
| Windows 10/11 (64-bit) | `RefMatch-Setup.exe` (installer) |
| macOS 12+ on Apple silicon | `RefMatch.dmg` (drag *Ref Match* to Applications) |

The apps are not code-signed yet, so the first launch shows a warning once:

- **Windows**: SmartScreen says "Windows protected your PC". Click *More info*, then *Run anyway*.
- **macOS**: open the app once, then go to *System Settings > Privacy & Security* and
  click *Open Anyway*.

## Using it

1. **Choose mix...** and pick your bounce.
2. **Add references...**: 1 to 5 released tracks in the sound you are going for
   (WAV, AIFF, FLAC or MP3).
3. **Compare**. Read the chart and the notes.
4. **Export matched references...** to get loudness-matched copies for your DAW, and
   **Save HTML report...** to keep the chart.

Pick references in the same genre and with a similar arrangement. A dense peak-time
techno track and a deep house track have very different spectra, and averaging them
hides more than it shows.

### Command line

```
python app.py "My mix.wav" --ref "Ref 1.flac" --ref "Ref 2.mp3" --html report.html --export matched/
```

## How it works

| Number | Method |
|---|---|
| Loudness matching | ITU-R BS.1770-5 integrated loudness; every file is scaled to -14 LUFS before the spectrum is taken |
| Spectrum | Welch average (Hann window, about 5 Hz resolution) of mid plus side, summed into ISO third-octave bands |
| Reference curve | power average of the references in each band |
| Range differences | total mix power over total reference power in 20-120, 120-500, 500-2k, 2k-6k and 6k-20k Hz |
| Width | side energy relative to mid energy in each range, in dB |
| Matched exports | gain = mix loudness minus reference loudness, written as 32-bit float so nothing clips |

The +/-3 dB and +/-6 dB thresholds are the usual tolerance for tonal balance against
references. Treat them as pointers, not rules: your track is allowed to sound different.

## Run from source

```
pip install -r requirements.txt
python app.py
```

Tests: `python -m unittest discover -s tests -v`. See [CONTRIBUTING.md](CONTRIBUTING.md)
and [CHANGELOG.md](CHANGELOG.md).

## En español

**Ref Match** compara tu mezcla con hasta 5 temas de referencia al mismo volumen, para
que el "más fuerte suena mejor" no te engañe. Muestra el espectro por tercios de octava,
la diferencia por rangos (subgraves, medios, agudos), el ancho estéreo y la dinámica, y
exporta las referencias ajustadas a la sonoridad de tu mezcla para comparar en tu DAW.
Descargá el instalador de Windows o el .dmg de Mac en
[Releases](https://github.com/axelfj/ref-match/releases/latest).

## License

MIT. See [LICENSE](LICENSE).
