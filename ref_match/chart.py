"""
Geometry for the spectrum chart, shared by the window (Tk canvas) and the
HTML report (SVG). Top panel: mix and reference curves. Bottom panel: the
difference, mix minus references.
"""
import math

F_LO, F_HI = 20.0, 20000.0
GRID_HZ = [(50, "50"), (100, "100"), (200, "200"), (500, "500"), (1000, "1k"), (2000, "2k"),
           (5000, "5k"), (10000, "10k")]
DIFF_RANGE = 12.0
COLORS = {"mix": "#d9480f", "ref": "#1864ab", "diff": "#495057", "grid": "#dee2e6",
          "zone": "#fff3bf", "text": "#495057"}


class Layout:
    def __init__(self, width, height, pad=40):
        self.w, self.h, self.pad = width, height, pad
        self.split = pad + (height - 2 * pad) * 0.62
        self.gap = 18

    def x(self, f):
        span = math.log10(F_HI) - math.log10(F_LO)
        return self.pad + (self.w - 2 * self.pad) * (math.log10(f) - math.log10(F_LO)) / span

    def y_curve(self, v, lo, hi):
        top, bottom = self.pad, self.split - self.gap / 2
        return bottom - (bottom - top) * (v - lo) / (hi - lo)

    def y_diff(self, d):
        top, bottom = self.split + self.gap / 2, self.h - self.pad
        d = max(-DIFF_RANGE, min(DIFF_RANGE, d))
        return (top + bottom) / 2 - (bottom - top) / 2 * d / DIFF_RANGE


def geometry(result, width=860, height=420):
    """Lines, rectangles and labels in pixel coordinates."""
    lay = Layout(width, height)
    mix = result["mix"]["bands"]
    ref = result["reference_curve"]
    shown = [v for fc, v in list(mix.items()) + list(ref.items()) if F_LO <= fc <= F_HI]
    hi = math.ceil(max(shown) / 6.0) * 6.0
    lo = hi - 48.0

    g = {"lines": [], "rects": [], "labels": []}
    for f, label in GRID_HZ:
        x = lay.x(f)
        g["lines"].append(((x, lay.pad, x, height - lay.pad), COLORS["grid"], 1))
        g["labels"].append((x, height - lay.pad + 14, label, "middle"))
    for d in (-6, -3, 3, 6):
        y = lay.y_diff(d)
        g["lines"].append(((lay.pad, y, width - lay.pad, y), COLORS["grid"], 1))
    g["rects"].append((lay.pad, lay.y_diff(3), width - lay.pad, lay.y_diff(-3), COLORS["zone"]))
    y0 = lay.y_diff(0)
    g["lines"].append(((lay.pad, y0, width - lay.pad, y0), COLORS["diff"], 1))
    g["labels"] += [(lay.pad - 6, lay.y_diff(6) + 4, "+6 dB", "end"),
                    (lay.pad - 6, y0 + 4, "0", "end"),
                    (lay.pad - 6, lay.y_diff(-6) + 4, "-6", "end"),
                    (lay.pad, lay.pad - 10, "Spectrum at equal loudness", "start"),
                    (lay.pad, lay.split + lay.gap / 2 - 4, "Mix minus references (dB)", "start")]

    def curve(points, color, width_px):
        pts = [(lay.x(fc), lay.y_curve(max(lo, v), lo, hi)) for fc, v in sorted(points.items())
               if F_LO <= fc <= F_HI]
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            g["lines"].append(((x1, y1, x2, y2), color, width_px))

    curve(ref, COLORS["ref"], 2)
    curve(mix, COLORS["mix"], 2)
    for fc, d in sorted(result["diff"].items()):
        if not F_LO <= fc <= F_HI:
            continue
        x = lay.x(fc)
        half = max(2.0, (lay.x(fc * 2 ** (1 / 6)) - lay.x(fc * 2 ** (-1 / 6))) / 2 - 1)
        y1, y2 = sorted((lay.y_diff(0), lay.y_diff(d)))
        x1, x2 = max(lay.pad, x - half), min(width - lay.pad, x + half)
        g["rects"].append((x1, y1, x2, y2, COLORS["mix"] if abs(d) >= 3
                           else COLORS["diff"]))
    g["legend"] = [(COLORS["mix"], "Your mix"), (COLORS["ref"], "References (average)")]
    return g


def to_svg(result, width=860, height=420):
    g = geometry(result, width, height)
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="100%%" '
           'font-family="Helvetica,Arial,sans-serif" font-size="11">' % (width, height)]
    for x1, y1, x2, y2, color in g["rects"]:
        out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
                   % (x1, y1, x2 - x1, max(0.5, y2 - y1), color))
    for (x1, y1, x2, y2), color, w in g["lines"]:
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                   'stroke-width="%d"/>' % (x1, y1, x2, y2, color, w))
    for x, y, text, anchor in g["labels"]:
        out.append('<text x="%.1f" y="%.1f" text-anchor="%s" fill="%s">%s</text>'
                   % (x, y, anchor, COLORS["text"], text))
    for n, (color, text) in enumerate(g["legend"]):
        x = width - 300 + n * 140
        out.append('<rect x="%d" y="16" width="12" height="4" fill="%s"/>'
                   '<text x="%d" y="22" fill="%s">%s</text>' % (x, color, x + 16,
                                                              COLORS["text"], text))
    out.append("</svg>")
    return "\n".join(out)


def draw_tk(canvas, result):
    canvas.delete("all")
    width = max(400, canvas.winfo_width())
    height = max(260, canvas.winfo_height())
    g = geometry(result, width, height)
    for x1, y1, x2, y2, color in g["rects"]:
        canvas.create_rectangle(x1, y1, x2, max(y1 + 1, y2), fill=color, outline="")
    for (x1, y1, x2, y2), color, w in g["lines"]:
        canvas.create_line(x1, y1, x2, y2, fill=color, width=w)
    anchors = {"start": "w", "middle": "center", "end": "e"}
    for x, y, text, anchor in g["labels"]:
        canvas.create_text(x, y, text=text, anchor=anchors[anchor], fill=COLORS["text"])
    for n, (color, text) in enumerate(g["legend"]):
        x = width - 300 + n * 140
        canvas.create_rectangle(x, 16, x + 12, 20, fill=color, outline="")
        canvas.create_text(x + 16, 18, text=text, anchor="w", fill=COLORS["text"])
