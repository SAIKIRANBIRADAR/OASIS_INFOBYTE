import tkinter as tk
from tkinter import ttk, messagebox
import secrets
import string
import math
import time

# ---------------- SETTINGS ----------------
MIN_LEN, MAX_LEN = 8, 64
AMBIGUOUS = "0O1lI"
DEFAULT_SYMBOLS = "!@#$%^&*()-_=+[]{}|;:,.<>?/~"

CATEGORY_COLORS = {
    "Very Weak": "#ef4444",
    "Weak": "#f59e0b",
    "Strong": "#10b981",
    "Excellent": "#3b82f6",
}

# ------------------------------------------
def entropy_bits(length, pool):
    if not pool:
        return 0
    return length * math.log2(len(pool))

def password_strength_label(bits):
    if bits < 28:
        return "Very Weak"
    if bits < 36:
        return "Weak"
    if bits < 60:
        return "Strong"
    return "Excellent"

def generate_password(length, pool):
    return "".join(secrets.choice(pool) for _ in range(length))

# ------------------------------------------
class PasswordGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Password Generator Pro")
        self.geometry("580x460")
        self.resizable(False, False)

        self.length = tk.IntVar(value=16)
        self.use_upper = tk.BooleanVar(value=True)
        self.use_lower = tk.BooleanVar(value=True)
        self.use_digits = tk.BooleanVar(value=True)
        self.use_symbols = tk.BooleanVar(value=True)
        self.exclude_amb = tk.BooleanVar(value=False)

        self.generated_pw = tk.StringVar()
        self.strength_label = tk.StringVar(value="Strength: —")

        self.history = []

        self.build_ui()
        self.update_strength_preview()

    # ---------------- UI ------------------
    def build_ui(self):
        pad = 10
        frame = ttk.Frame(self, padding=pad)
        frame.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(frame, text="Password Generator Pro", font=(None, 18, "bold"))
        title.grid(row=0, column=0, columnspan=4, pady=(0, 12))
        ttk.Label(frame, text="Length:").grid(row=1, column=0, sticky="w")
        slider = ttk.Scale(frame, from_=MIN_LEN, to=MAX_LEN, orient=tk.HORIZONTAL,
                           variable=self.length, command=lambda _ : self.update_strength_preview())
        slider.grid(row=1, column=1, sticky="ew", padx=6)
        self.length_label = ttk.Label(frame, text="16")
        self.length_label.grid(row=1, column=2, sticky="w")

        frame.columnconfigure(1, weight=1)

        self.add_check(frame, self.use_upper, "A-Z Uppercase", 2)
        self.add_check(frame, self.use_lower, "a-z Lowercase", 3)
        self.add_check(frame, self.use_digits, "0-9 Numbers", 4)
        self.add_check(frame, self.use_symbols, "!@# Symbols", 5)

        excl = ttk.Checkbutton(frame, text="Exclude ambiguous chars (0 O 1 l I)",
                               variable=self.exclude_amb, command=self.update_strength_preview)
        excl.grid(row=6, column=0, columnspan=3, sticky="w", pady=(4,8))

        # PASSWORD DISPLAY BOX
        box = ttk.LabelFrame(frame, text="Generated Password", padding=8)
        box.grid(row=7, column=0, columnspan=4, sticky="ew", pady=(4,8))
        self.output_entry = ttk.Entry(box, textvariable=self.generated_pw, font=(None, 13))
        self.output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(box, text="Copy", command=self.copy_pw).pack(side=tk.LEFT, padx=6)

        # STRENGTH METER
        self.str_label = ttk.Label(frame, textvariable=self.strength_label, font=(None, 11, "bold"))
        self.str_label.grid(row=8, column=0, sticky="w")

        self.meter = tk.Canvas(frame, height=16, width=220, bg="#e5e7eb", highlightthickness=0)
        self.meter.grid(row=8, column=1, columnspan=2, sticky="w")

        # BUTTONS
        ttk.Button(frame, text="Generate", command=self.generate).grid(row=9, column=0, pady=10, sticky="w")
        ttk.Button(frame, text="Generate & Copy", command=lambda: (self.generate(), self.copy_pw())).grid(row=9, column=1, pady=10, sticky="w")

        # HISTORY
        hist = ttk.LabelFrame(frame, text="Recent Passwords", padding=6)
        hist.grid(row=10, column=0, columnspan=4, sticky="nsew")
        self.hist_list = tk.Listbox(hist, height=5)
        self.hist_list.pack(fill=tk.BOTH, expand=True)
        self.hist_list.bind("<<ListboxSelect>>", self.select_history)

    def add_check(self, frame, var, text, row):
        ttk.Checkbutton(frame, text=text, variable=var, command=self.update_strength_preview).grid(row=row, column=0, columnspan=3, sticky="w")

    # ---------------- LOGIC ----------------
    def current_pool(self):
        pool = ""
        if self.use_upper.get(): pool += string.ascii_uppercase
        if self.use_lower.get(): pool += string.ascii_lowercase
        if self.use_digits.get(): pool += string.digits
        if self.use_symbols.get(): pool += DEFAULT_SYMBOLS
        if self.exclude_amb.get():
            pool = ''.join(c for c in pool if c not in AMBIGUOUS)
        return pool

    def update_strength_preview(self):
        length = int(self.length.get())
        self.length_label.config(text=str(length))
        pool = self.current_pool()
        bits = entropy_bits(length, pool)
        label = password_strength_label(bits)
        self.strength_label.set(f"Strength: {label}")
        self.draw_meter(label)

    def draw_meter(self, label):
        self.meter.delete("all")
        color = CATEGORY_COLORS.get(label, "#6b7280")
        w = int(self.meter.winfo_width())
        self.meter.create_rectangle(0, 0, w, 16, fill=color, outline="")

    def generate(self):
        pool = self.current_pool()
        if not pool:
            messagebox.showerror("Error", "Select at least one character set.")
            return
        length = int(self.length.get())
        pw = generate_password(length, pool)
        self.generated_pw.set(pw)
        self.add_history(pw)
        self.update_strength_preview()

    def copy_pw(self):
        pw = self.generated_pw.get()
        if not pw:
            return
        try:
            self.clipboard_clear()
            self.clipboard_append(pw)
            messagebox.showinfo("Copied", "Password copied to clipboard.")
        except Exception:
            messagebox.showerror("Error", "Failed to copy to clipboard.")

    def add_history(self, pw):
        self.history.insert(0, pw)
        self.history = self.history[:10]
        self.refresh_history()

    def refresh_history(self):
        self.hist_list.delete(0, tk.END)
        for pw in self.history:
            self.hist_list.insert(tk.END, pw)

    def select_history(self, event):
        idxs = self.hist_list.curselection()
        if not idxs:
            return
        pw = self.hist_list.get(idxs[0])
        self.generated_pw.set(pw)
        self.update_strength_preview()

# ---------------- RUN --------------------
if __name__ == "__main__":
    app = PasswordGUI()
    app.mainloop()
