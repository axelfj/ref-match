"""Text, JSON and HTML reports."""
import html
import json
import math
import time

from . import APP_NAME, __version__, chart
from .analysis import REGIONS

LABEL = {"warn": "WARN", "info": "    "}


def loudness_rows(result):
    m, r = result["mix"]["loudness"], result["reference_loudness"]
    return [
        ("Integrated loudness", "%.1f LUFS" % m["integrated_lufs"],
         "%.1f LUFS" % r["integrated_lufs"]),
        ("Peak to loudness (PLR)", "%.1f dB" % m["plr_db"], "%.1f dB" % r["plr_db"]),
        ("Loudness range (LRA)", "%.1f LU" % m["lra_lu"], "%.1f LU" % r["lra_lu"]),
        ("True peak", "%+.1f dBTP" % m["true_peak_dbtp"], "%+.1f dBTP" % r["true_peak_dbtp"]),
    ]


def region_rows(result):
    rows = []
    for name, lo, hi in REGIONS:
        if name in result["regions"]:
            rows.append(("%s (%g-%g Hz)" % (name, lo, hi), "%+.1f dB" % result["regions"][name],
                         ("n/a" if result["width_diff"][name] is None else "%+.1f dB" % result["width_diff"][name])))
    return rows


def text(result):
    lines = ["Mix:        %s  (%s)" % (result["mix"]["name"], result["mix"]["description"])]
    for r in result["refs"]:
        lines.append("Reference:  %s  (%s)" % (r["name"], r["description"]))
    lines += ["", "   %-26s %12s %14s" % ("", "Your mix", "References")]
    for row in loudness_rows(result):
        lines.append("   %-26s %12s %14s" % row)
    lines += ["", "   At equal loudness       %12s %14s" % ("Tone", "Width")]
    for row in region_rows(result):
        lines.append("   %-26s %12s %14s" % row)
    lines.append("")
    for n in result["notes"]:
        lines.append("  %s  %s" % (LABEL[n["level"]], n["message"]))
    return "\n".join(lines)


def to_json(result):
    def keyed(d):
        return {str(k): v for k, v in d.items()}

    clean = dict(result)
    clean["mix"] = dict(result["mix"], bands=keyed(result["mix"]["bands"]))
    clean["refs"] = [dict(r, bands=keyed(r["bands"])) for r in result["refs"]]
    clean["reference_curve"] = keyed(result["reference_curve"])
    clean["diff"] = keyed(result["diff"])
    def finite(value):
        if isinstance(value, dict):
            return {k: finite(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [finite(v) for v in value]
        return None if isinstance(value, float) and not math.isfinite(value) else value
    return json.dumps(finite({"app": APP_NAME, "version": __version__, "result": clean}),
                      indent=2, allow_nan=False, default=lambda v: None)


CSS = """
body{font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;max-width:900px;
margin:24px auto;padding:0 16px;color:#1d1d1f;background:#fff}
h1{font-size:22px}h2{font-size:17px;margin-top:28px}
table{border-collapse:collapse;margin:8px 0}td,th{border-bottom:1px solid #ddd;
padding:5px 12px;text-align:left}.warn{color:#a15c00;font-weight:600}small{color:#666}
"""


def to_html(result):
    e = html.escape
    out = ["<!doctype html><meta charset=utf-8><title>%s report</title><style>%s</style>"
           % (APP_NAME, CSS),
           "<h1>%s report</h1><small>%s %s, %s</small>"
           % (APP_NAME, APP_NAME, __version__, time.strftime("%Y-%m-%d %H:%M")),
           "<p><b>Mix:</b> %s<br><b>References:</b> %s</p>" % (
               e(result["mix"]["name"]), e(", ".join(r["name"] for r in result["refs"]))),
           chart.to_svg(result),
           "<h2>Notes</h2><ul>"]
    for n in result["notes"]:
        cls = ' class=warn' if n["level"] == "warn" else ""
        out.append("<li%s>%s</li>" % (cls, e(n["message"])))
    out.append("</ul><h2>Tone and width at equal loudness</h2><table><tr><th>Range</th>"
               "<th>Tone vs references</th><th>Width vs references</th></tr>")
    out += ["<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % tuple(map(e, row))
            for row in region_rows(result)]
    out.append("</table><h2>Loudness and dynamics</h2><table><tr><th></th><th>Your mix</th>"
               "<th>References</th></tr>")
    out += ["<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % tuple(map(e, row))
            for row in loudness_rows(result)]
    out.append("</table><p><small>All files compared as if normalized to the same integrated "
               "loudness (ITU-R BS.1770-5). Spectrum: third-octave bands of mid plus side. "
               "Width: side energy relative to mid energy.</small></p>")
    return "\n".join(out)

