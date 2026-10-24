"""
Audio file reading.

WAV files are parsed here directly, so the header details that delivery
platforms care about (the raw format code, EXTENSIBLE headers, RF64) are
reported exactly as written. Every other format (AIFF, FLAC, MP3, OGG...) is
decoded with libsndfile through the soundfile package.

Samples come back as float32 in [-1, 1) with shape (frames, channels).
"""
import os
import struct

import numpy as np

WAV_PCM = 0x0001
WAV_FLOAT = 0x0003
WAV_EXTENSIBLE = 0xFFFE

AUDIO_EXTENSIONS = (".wav", ".wave", ".aif", ".aiff", ".aifc", ".flac", ".mp3", ".ogg")


class AudioError(Exception):
    pass


class Audio:
    """Decoded samples plus what the file header says about them."""

    def __init__(self, path, samples, rate, bits, is_float, container, format_tag=None,
                 encoding=None):
        if samples.size == 0:
            raise AudioError("the audio file contains no samples")
        if rate <= 0:
            raise AudioError("invalid sample rate")
        if not np.isfinite(samples).all():
            raise AudioError("audio contains non-finite samples (NaN or infinity)")
        self.path = path
        self.samples = samples
        self.rate = rate
        self.bits = bits
        self.is_float = is_float
        self.container = container
        self.format_tag = format_tag
        self.encoding = encoding

    @property
    def name(self):
        return os.path.basename(self.path)

    @property
    def channels(self):
        return self.samples.shape[1]

    @property
    def frames(self):
        return self.samples.shape[0]

    @property
    def duration(self):
        return self.frames / float(self.rate)

    def describe(self):
        kind = "float" if self.is_float else "int"
        return "%s, %d Hz, %d-bit %s, %d ch, %.1f s" % (
            self.encoding or self.container, self.rate, self.bits, kind, self.channels,
            self.duration)


def is_audio_file(path):
    return path.lower().endswith(AUDIO_EXTENSIONS) and not os.path.basename(path).startswith(".")


def list_audio_files(folder):
    return sorted(os.path.join(folder, n) for n in os.listdir(folder)
                  if is_audio_file(os.path.join(folder, n)))


def read(path):
    with open(path, "rb") as f:
        magic = f.read(12)
    if magic[:4] in (b"RIFF", b"RF64") and magic[8:12] == b"WAVE":
        return _read_wav(path)
    return _read_soundfile(path)


def _read_wav(path):
    with open(path, "rb") as f:
        riff, _size, _wave = struct.unpack("<4sI4s", f.read(12))
        fmt = None
        while True:
            head = f.read(8)
            if len(head) < 8:
                raise AudioError("no audio data in this WAV file")
            cid, size = struct.unpack("<4sI", head)
            if cid == b"fmt ":
                body = f.read(size + (size & 1))
                if len(body) < 16:
                    raise AudioError("broken WAV format chunk")
                tag, ch, rate, _br, _align, bits = struct.unpack("<HHIIHH", body[:16])
                sub = tag
                if tag == WAV_EXTENSIBLE and len(body) >= 26:
                    sub = struct.unpack("<H", body[24:26])[0]
                fmt = {"tag": tag, "sub": sub, "channels": ch, "rate": rate, "bits": bits}
            elif cid == b"data":
                if fmt is None:
                    raise AudioError("WAV data chunk comes before its format chunk")
                # RF64 stores 0xFFFFFFFF here and the real size in ds64; reading
                # to the end of the file gets the same audio.
                raw = f.read() if size == 0xFFFFFFFF else f.read(size)
                break
            else:
                f.seek(size + (size & 1), os.SEEK_CUR)
    ch, bits = fmt["channels"], fmt["bits"]
    if ch < 1 or bits not in (8, 16, 24, 32, 64):
        raise AudioError("unsupported WAV layout (%d channels, %d bits)" % (ch, bits))
    frame_bytes = ch * bits // 8
    raw = raw[: len(raw) - len(raw) % frame_bytes]
    x = _decode_pcm(raw, fmt["sub"], bits).reshape(-1, ch)
    if fmt["tag"] == WAV_EXTENSIBLE:
        encoding = "WAV (EXTENSIBLE)"
    else:
        encoding = "WAV"
    return Audio(path, x, fmt["rate"], bits, fmt["sub"] == WAV_FLOAT,
                 "RF64" if riff == b"RF64" else "WAV", fmt["tag"], encoding)


def _decode_pcm(raw, tag, bits):
    if tag == WAV_FLOAT:
        if bits == 32:
            return np.frombuffer(raw, "<f4").astype(np.float32)
        if bits == 64:
            return np.frombuffer(raw, "<f8").astype(np.float32)
    if tag != WAV_PCM:
        raise AudioError("unsupported WAV encoding (format code 0x%04X)" % tag)
    if bits == 8:
        return ((np.frombuffer(raw, np.uint8).astype(np.float32) - 128.0) / 128.0)
    if bits == 16:
        return np.frombuffer(raw, "<i2").astype(np.float32) / np.float32(32768.0)
    if bits == 24:
        b = np.frombuffer(raw, np.uint8).reshape(-1, 3)
        v = (b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8)
             | (b[:, 2].astype(np.int8).astype(np.int32) << 16))
        return v.astype(np.float32) / np.float32(8388608.0)
    if bits == 32:
        return (np.frombuffer(raw, "<i4").astype(np.float64) / 2147483648.0).astype(np.float32)
    raise AudioError("unsupported PCM bit depth %d" % bits)


SUBTYPE_BITS = {"PCM_S8": 8, "PCM_U8": 8, "PCM_16": 16, "PCM_24": 24, "PCM_32": 32,
                "FLOAT": 32, "DOUBLE": 64}


def _read_soundfile(path):
    try:
        import soundfile
    except ImportError:  # pragma: no cover
        raise AudioError("this build can only read WAV files")
    try:
        info = soundfile.info(path)
        x, rate = soundfile.read(path, dtype="float32", always_2d=True)
    except Exception as e:  # libsndfile raises its own error types
        raise AudioError("could not decode this file (%s)" % e)
    bits = SUBTYPE_BITS.get(info.subtype, 16)
    is_float = info.subtype in ("FLOAT", "DOUBLE")
    return Audio(path, np.ascontiguousarray(x), rate, bits, is_float, info.format,
                 None, "%s %s" % (info.format, info.subtype))


def write_wav_float(path, samples, rate):
    """Writes 32-bit float WAV (format code 3), so no clipping and no dither."""
    x = np.asarray(samples, dtype="<f4")
    if x.ndim == 1:
        x = x[:, None]
    ch = x.shape[1]
    data = x.tobytes()
    with open(path, "wb") as f:
        f.write(struct.pack("<4sI4s", b"RIFF", 4 + 26 + 12 + 8 + len(data), b"WAVE"))
        f.write(struct.pack("<4sIHHIIHHH", b"fmt ", 18, WAV_FLOAT, ch, rate, rate * ch * 4,
                            ch * 4, 32, 0))
        f.write(struct.pack("<4sII", b"fact", 4, x.shape[0]))
        f.write(struct.pack("<4sI", b"data", len(data)))
        f.write(data)


def write_wav_pcm(path, samples, rate, bits=24, extensible=False):
    """Writes integer PCM WAV. Used by the tests to build fixtures."""
    x = np.clip(np.asarray(samples, dtype=np.float64), -1.0, 1.0 - 2.0 ** -(bits - 1))
    if x.ndim == 1:
        x = x[:, None]
    ch = x.shape[1]
    q = np.round(x * 2 ** (bits - 1)).astype(np.int64)
    if bits == 16:
        data = q.astype("<i2").tobytes()
    elif bits == 24:
        q = q.astype("<i4").reshape(-1)
        data = q.view(np.uint8).reshape(-1, 4)[:, :3].tobytes()
    elif bits == 32:
        data = q.astype("<i4").tobytes()
    else:
        raise ValueError(bits)
    block = ch * bits // 8
    if extensible:
        guid = struct.pack("<HHI8s", WAV_PCM, 0, 0x00100000, b"\x80\x00\x00\xaa\x00\x38\x9b\x71")
        fmt = struct.pack("<HHIIHHHHI", WAV_EXTENSIBLE, ch, rate, rate * block, block, bits,
                          22, bits, 3 if ch == 2 else 4) + guid[:16]
    else:
        fmt = struct.pack("<HHIIHH", WAV_PCM, ch, rate, rate * block, block, bits)
    with open(path, "wb") as f:
        f.write(struct.pack("<4sI4s", b"RIFF", 4 + 8 + len(fmt) + 8 + len(data), b"WAVE"))
        f.write(struct.pack("<4sI", b"fmt ", len(fmt)) + fmt)
        f.write(struct.pack("<4sI", b"data", len(data)))
        f.write(data)

