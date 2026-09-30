"""
Ritaglio & raddrizzamento fogli - versione GUI
"""

import threading
import traceback
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import os
import sys
import subprocess

import cv2
import numpy as np


# ===========================================================================
# CORE
# ===========================================================================
def find_sheet_angle(img_bgr):
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255,
                              cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kernel = np.ones((5, 5), np.uint8)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return 0.0

    c = max(contours, key=cv2.contourArea)
    peri = cv2.arcLength(c, True)
    approx = cv2.approxPolyDP(c, 0.02 * peri, True)

    if len(approx) == 4:
        pts = approx.reshape(4, 2).astype(np.float32)
        s = pts.sum(axis=1)
        d = np.diff(pts, axis=1).ravel()
        rect = np.zeros((4, 2), dtype=np.float32)
        rect[0] = pts[np.argmin(s)]
        rect[1] = pts[np.argmin(d)]
        rect[2] = pts[np.argmax(s)]
        rect[3] = pts[np.argmax(d)]
        dx = rect[1][0] - rect[0][0]
        dy = rect[1][1] - rect[0][1]
        return float(np.degrees(np.arctan2(dy, dx)))
    else:
        rect = cv2.minAreaRect(c)
        angle = rect[-1]
        if angle < -45:
            angle = 90 + angle
        if angle > 45:
            angle = angle - 90
        return float(angle)


def rotate_image(img_bgr, angle):
    if abs(angle) < 0.1:
        return img_bgr
    h, w = img_bgr.shape[:2]
    cx, cy = w / 2, h / 2
    M = cv2.getRotationMatrix2D((cx, cy), angle, 1.0)
    cos = abs(M[0, 0])
    sin = abs(M[0, 1])
    new_w = int(h * sin + w * cos)
    new_h = int(h * cos + w * sin)
    M[0, 2] += new_w / 2 - cx
    M[1, 2] += new_h / 2 - cy
    return cv2.warpAffine(
        img_bgr, M, (new_w, new_h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0)
    )


def trim_black(img_bgr, threshold=25, min_ratio=0.03, padding=5):
    h, w = img_bgr.shape[:2]
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    mask = (gray > threshold).astype(np.uint8)
    righe_ok = mask.sum(axis=1) >= max(1, int(min_ratio * w))
    colonne_ok = mask.sum(axis=0) >= max(1, int(min_ratio * h))
    if not righe_ok.any() or not colonne_ok.any():
        return None
    y1 = int(np.argmax(righe_ok))
    y2 = int(len(righe_ok) - np.argmax(righe_ok[::-1]) - 1)
    x1 = int(np.argmax(colonne_ok))
    x2 = int(len(colonne_ok) - np.argmax(colonne_ok[::-1]) - 1)
    x1 = max(0, x1 - padding)
    y1 = max(0, y1 - padding)
    x2 = min(w - 1, x2 + padding)
    y2 = min(h - 1, y2 + padding)
    return img_bgr[y1:y2 + 1, x1:x2 + 1]


def process_one(image_path, output_path, max_angle=20,
                threshold=25, min_ratio=0.03, padding=5, log=print):
    img = cv2.imread(str(image_path))
    if img is None:
        log(f"  [ERR] impossibile leggere {Path(image_path).name}")
        return False
    log(f"  origine: {img.shape[1]}x{img.shape[0]}")
    angle = find_sheet_angle(img)
    if abs(angle) > max_angle:
        log(f"  angolo {angle:.2f} troppo grande, non ruoto")
        angle = 0.0
    rotated = rotate_image(img, angle)
    if abs(angle) >= 0.1:
        log(f"  ruotata di {angle:.2f} gradi")
    trimmed = trim_black(rotated, threshold, min_ratio, padding)
    if trimmed is None:
        log("  [SKIP] nessun contenuto dopo il trim")
        return False
    log(f"  finale: {trimmed.shape[1]}x{trimmed.shape[0]}")
    cv2.imwrite(str(output_path), trimmed)
    return True


# ===========================================================================
# GUI
# ===========================================================================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ritaglio e raddrizzamento fogli")
        self.geometry("700x560")
        self.minsize(600, 480)

        self.input_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.threshold = tk.IntVar(value=25)
        self.min_ratio = tk.DoubleVar(value=0.03)
        self.padding = tk.IntVar(value=5)
        self.max_angle = tk.IntVar(value=20)

        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        frame_dir = ttk.LabelFrame(self, text="Cartelle")
        frame_dir.pack(fill="x", **pad)

        ttk.Label(frame_dir, text="Cartella input:").grid(
            row=0, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(frame_dir, textvariable=self.input_dir,
                  width=55).grid(row=0, column=1, padx=6, pady=4)
        ttk.Button(frame_dir, text="Sfoglia...",
                   command=self._choose_input).grid(row=0, column=2,
                                                    padx=6, pady=4)

        ttk.Label(frame_dir, text="Cartella output:").grid(
            row=1, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(frame_dir, textvariable=self.output_dir,
                  width=55).grid(row=1, column=1, padx=6, pady=4)
        ttk.Button(frame_dir, text="Sfoglia...",
                   command=self._choose_output).grid(row=1, column=2,
                                                     padx=6, pady=4)

        frame_par = ttk.LabelFrame(self, text="Parametri (di solito vanno bene cosi)")
        frame_par.pack(fill="x", **pad)

        ttk.Label(frame_par, text="Soglia nero (0-255):").grid(
            row=0, column=0, sticky="w", padx=6, pady=4)
        ttk.Spinbox(frame_par, from_=0, to=255,
                    textvariable=self.threshold, width=8).grid(
            row=0, column=1, sticky="w", padx=6, pady=4)
        ttk.Label(frame_par, text="(alza se resta bordo grigio)").grid(
            row=0, column=2, sticky="w", padx=6)

        ttk.Label(frame_par, text="Filtro rumore (0.01-0.20):").grid(
            row=1, column=0, sticky="w", padx=6, pady=4)
        ttk.Spinbox(frame_par, from_=0.01, to=0.20, increment=0.01,
                    textvariable=self.min_ratio, width=8).grid(
            row=1, column=1, sticky="w", padx=6, pady=4)
        ttk.Label(frame_par, text="(alza se restano puntini)").grid(
            row=1, column=2, sticky="w", padx=6)

        ttk.Label(frame_par, text="Margine finale (px):").grid(
            row=2, column=0, sticky="w", padx=6, pady=4)
        ttk.Spinbox(frame_par, from_=0, to=100,
                    textvariable=self.padding, width=8).grid(
            row=2, column=1, sticky="w", padx=6, pady=4)

        ttk.Label(frame_par, text="Rotazione max (gradi):").grid(
            row=3, column=0, sticky="w", padx=6, pady=4)
        ttk.Spinbox(frame_par, from_=0, to=90,
                    textvariable=self.max_angle, width=8).grid(
            row=3, column=1, sticky="w", padx=6, pady=4)

        frame_btn = ttk.Frame(self)
        frame_btn.pack(fill="x", **pad)
        self.btn_start = ttk.Button(frame_btn, text="Avvia",
                                    command=self._start)
        self.btn_start.pack(side="left", padx=6)
        ttk.Button(frame_btn, text="Apri cartella output",
                   command=self._open_output).pack(side="left", padx=6)

        self.progress = ttk.Progressbar(frame_btn, mode="determinate")
        self.progress.pack(side="right", fill="x", expand=True, padx=6)

        frame_log = ttk.LabelFrame(self, text="Attivita")
        frame_log.pack(fill="both", expand=True, **pad)
        self.log_text = tk.Text(frame_log, height=12, wrap="word")
        self.log_text.pack(side="left", fill="both", expand=True,
                           padx=6, pady=6)
        scroll = ttk.Scrollbar(frame_log, command=self.log_text.yview)
        scroll.pack(side="right", fill="y", pady=6)
        self.log_text.config(yscrollcommand=scroll.set)

    def _choose_input(self):
        d = filedialog.askdirectory(
            title="Scegli la cartella con le immagini")
        if d:
            self.input_dir.set(d)
            if not self.output_dir.get():
                self.output_dir.set(
                    str(Path(d).parent / (Path(d).name + "_elaborate")))

    def _choose_output(self):
        d = filedialog.askdirectory(
            title="Scegli dove salvare i risultati")
        if d:
            self.output_dir.set(d)

    def _log(self, msg):
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.update_idletasks()

    def _open_output(self):
        d = self.output_dir.get()
        if d and Path(d).exists():
            if sys.platform.startswith("win"):
                os.startfile(d)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", d])
            else:
                subprocess.Popen(["xdg-open", d])
        else:
            messagebox.showinfo("Info", "La cartella output non esiste ancora.")

    def _start(self):
        inp = self.input_dir.get().strip()
        out = self.output_dir.get().strip()
        if not inp or not Path(inp).is_dir():
            messagebox.showerror("Errore",
                                 "Seleziona una cartella input valida.")
            return
        if not out:
            messagebox.showerror("Errore", "Seleziona una cartella output.")
            return

        self.btn_start.config(state="disabled")
        self.log_text.delete("1.0", "end")
        self.progress["value"] = 0
        threading.Thread(target=self._run, args=(inp, out),
                         daemon=True).start()

    def _run(self, inp, out):
        try:
            in_dir = Path(inp)
            out_dir = Path(out)
            out_dir.mkdir(parents=True, exist_ok=True)

            exts = {".jpg", ".jpeg", ".png", ".bmp", ".tif",
                    ".tiff", ".webp"}
            files = [f for f in in_dir.iterdir()
                     if f.suffix.lower() in exts]
            if not files:
                self._log("Nessuna immagine trovata nella cartella input.")
                return

            self._log(f"Trovate {len(files)} immagini.\n")
            self.progress["maximum"] = len(files)

            ok = 0
            for i, f in enumerate(files, 1):
                self._log(f"[{i}/{len(files)}] {f.name}")
                try:
                    if process_one(
                        f, out_dir / f.name,
                        max_angle=self.max_angle.get(),
                        threshold=self.threshold.get(),
                        min_ratio=self.min_ratio.get(),
                        padding=self.padding.get(),
                        log=self._log,
                    ):
                        ok += 1
                except Exception:
                    self._log("  [ERR] " +
                              traceback.format_exc().splitlines()[-1])
                self.progress["value"] = i

            self._log(f"\nFatto! {ok}/{len(files)} immagini elaborate.")
            self._log(f"Risultati in: {out_dir}")
        except Exception:
            self._log("ERRORE GENERALE:\n" + traceback.format_exc())
        finally:
            self.btn_start.config(state="normal")


if __name__ == "__main__":
    App().mainloop()