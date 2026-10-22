"""Command line: ref-match MIX --ref REF [--ref REF...] [--html out.html] [--export DIR]"""
import argparse
import sys

from . import APP_NAME, __version__, audio, report
from .analysis import MAX_REFS, compare, export_matched


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ref-match", description="%s %s: compare a mix with "
                                 "reference tracks at equal loudness." % (APP_NAME, __version__))
    ap.add_argument("mix", help="your mix")
    ap.add_argument("--ref", action="append", required=True,
                    help="a reference track (repeat up to %d times)" % MAX_REFS)
    ap.add_argument("--json", metavar="FILE", help="also write a JSON report")
    ap.add_argument("--html", metavar="FILE", help="also write an HTML report with the chart")
    ap.add_argument("--export", metavar="DIR",
                    help="write the references turned to your mix's loudness, for A/B in the DAW")
    ap.add_argument("--version", action="version", version=__version__)
    args = ap.parse_args(argv)
    try:
        result = compare(args.mix, args.ref)
    except (audio.AudioError, OSError, ValueError) as e:
        print("Error: %s" % e, file=sys.stderr)
        return 2
    print(report.text(result))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            f.write(report.to_json(result))
    if args.html:
        with open(args.html, "w", encoding="utf-8") as f:
            f.write(report.to_html(result))
    if args.export:
        for path in export_matched(result, args.export):
            print("Wrote %s" % path)
    return 0
