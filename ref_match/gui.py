"""Desktop window: pick a mix and references, see the chart, export matched copies."""
import os
import queue
import threading

from . import APP_NAME, __version__, audio, chart, report
from .analysis import MAX_REFS, compare, export_matched

AUDIO_TYPES = [("Audio", "*.wav *.wave *.aif *.aiff *.aifc *.flac *.mp3 *.ogg"),
               ("All files", "*.*")]
INTRO = (
    "1. Choose your mix.\n"
    "2. Add 1 to %d reference tracks you want to sound like.\n"
    "3. Click Compare.\n\n"
    "Everything is compared at equal loudness, so you see tone, width and dynamics\n"
    "instead of which file is louder. Export matched references to A/B them in your DAW.\n"
    % MAX_REFS)


def main():
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext

    root = tk.Tk()
    root.title("%s %s" % (APP_NAME, __version__))
    root.geometry("960x800")
    state = {"mix": None, "refs": [], "result": None, "busy": False}
    events = queue.Queue()

    tk.Label(root, text=APP_NAME, font=("Helvetica", 18, "bold")).pack(pady=(12, 0))
    tk.Label(root, text="Compare your mix with references at equal loudness").pack(pady=(0, 6))

    top = tk.Frame(root)
    top.pack(fill="x", padx=12)
    mix_label = tk.Label(top, text="Your mix: (none)", anchor="w")
    mix_label.grid(row=0, column=0, sticky="we")
    top.columnconfigure(0, weight=1)
    refs_box = tk.Listbox(top, height=4)
    refs_box.grid(row=1, column=0, sticky="we", pady=4)
    side = tk.Frame(top)
    side.grid(row=0, column=1, rowspan=2, sticky="n", padx=(8, 0))

    status = tk.Label(root, anchor="w", fg="#555")
    canvas = tk.Canvas(root, height=330, bg="white", highlightthickness=0)
    out = scrolledtext.ScrolledText(root, font=("Courier", 11), wrap="none", height=12)
    out.tag_configure("warn", foreground="#a15c00")

    def show(text_value):
        out.configure(state="normal")
        out.delete("1.0", "end")
        for line in text_value.split("\n"):
            out.insert("end", line + "\n", "warn" if line.startswith("  WARN") else None)
        out.configure(state="disabled")

    def choose_mix():
        path = filedialog.askopenfilename(title="Choose your mix", filetypes=AUDIO_TYPES)
        if path:
            state["mix"] = path
            mix_label.configure(text="Your mix: %s" % os.path.basename(path))

    def add_refs():
        paths = filedialog.askopenfilenames(title="Choose reference tracks", filetypes=AUDIO_TYPES)
        for p in paths:
            if len(state["refs"]) < MAX_REFS and p not in state["refs"]:
                state["refs"].append(p)
                refs_box.insert("end", os.path.basename(p))

    def remove_ref():
        for i in reversed(refs_box.curselection()):
            refs_box.delete(i)
            del state["refs"][i]

    def run_compare():
        if state["busy"]:
            return
        if not state["mix"] or not state["refs"]:
            messagebox.showinfo(APP_NAME, "Choose your mix and at least one reference.")
            return
        state["busy"] = True
        status.configure(text="Measuring %d files..." % (1 + len(state["refs"])))
        mix, refs = state["mix"], list(state["refs"])

        def work():
            try:
                events.put(("done", compare(mix, refs)))
            except (audio.AudioError, OSError, ValueError) as e:
                events.put(("error", str(e)))

        threading.Thread(target=work, daemon=True).start()

    def poll():
        try:
            while True:
                kind, value = events.get_nowait()
                state["busy"] = False
                if kind == "error":
                    status.configure(text="")
                    messagebox.showerror(APP_NAME, value)
                else:
                    state["result"] = value
                    status.configure(text="Compared with %d reference(s)." % len(value["refs"]))
                    chart.draw_tk(canvas, value)
                    show(report.text(value))
        except queue.Empty:
            pass
        root.after(150, poll)

    def need_result():
        if not state["result"]:
            messagebox.showinfo(APP_NAME, "Compare first.")
            return False
        return True

    def save(kind):
        if not need_result():
            return
        ext = ".html" if kind == "html" else ".json"
        path = filedialog.asksaveasfilename(defaultextension=ext,
                                            initialfile="ref-match-report" + ext)
        if path:
            body = (report.to_html if kind == "html" else report.to_json)(state["result"])
            with open(path, "w", encoding="utf-8") as f:
                f.write(body)
            status.configure(text="Saved %s" % path)

    def export():
        if not need_result():
            return
        folder = filedialog.askdirectory(title="Where to save the matched references")
        if folder:
            written = export_matched(state["result"], folder)
            status.configure(text="Wrote %d matched reference(s) to %s" % (len(written), folder))

    def redraw(_event=None):
        if state["result"]:
            chart.draw_tk(canvas, state["result"])

    for text_value, cmd in (("Choose mix...", choose_mix), ("Add references...", add_refs),
                            ("Remove reference", remove_ref)):
        tk.Button(side, text=text_value, width=18, command=cmd).pack(pady=2)
    bar = tk.Frame(root)
    tk.Button(bar, text="Compare", width=14, command=run_compare).pack(side="left", padx=4)
    tk.Button(bar, text="Export matched references...", width=26, command=export).pack(
        side="left", padx=4)
    tk.Button(bar, text="Save JSON...", width=12, command=lambda: save("json")).pack(
        side="right", padx=4)
    tk.Button(bar, text="Save HTML report...", width=18, command=lambda: save("html")).pack(
        side="right", padx=4)
    bar.pack(fill="x", padx=12, pady=6)
    status.pack(fill="x", padx=16)
    canvas.pack(fill="x", padx=12, pady=6)
    canvas.bind("<Configure>", redraw)
    out.pack(fill="both", expand=True, padx=12, pady=(0, 12))
    show(INTRO)
    poll()
    root.mainloop()
