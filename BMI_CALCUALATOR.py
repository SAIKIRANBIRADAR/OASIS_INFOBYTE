import tkinter as tk
from tkinter import ttk, messagebox
import math
import sys

# ----------------------- Styling / Constants -------------------------
APP_TITLE = "Health BMI Calculator"
WIDTH = 520
HEIGHT = 420

CATEGORY_COLORS = {
    "Underweight": "#3b82f6",  # blue
    "Normal": "#10b981",       # green
    "Overweight": "#f59e0b",   # orange
    "Obesity": "#ef4444",      # red
}

THRESHOLDS = [18.5, 25.0, 30.0]

# ----------------------- Helper functions ---------------------------

def calculate_bmi_metric(weight_kg: float, height_m: float) -> float:
    return round(weight_kg / (height_m ** 2), 1)


def kg_from_lb(lb: float) -> float:
    return lb * 0.45359237


def m_from_ft_inches(ft: float, inches: float = 0.0) -> float:
    total_inches = ft * 12 + inches
    return total_inches * 0.0254


def classify_bmi(bmi: float) -> str:
    if bmi < THRESHOLDS[0]:
        return "Underweight"
    if bmi < THRESHOLDS[1]:
        return "Normal"
    if bmi < THRESHOLDS[2]:
        return "Overweight"
    return "Obesity"


# ----------------------- Tooltip -----------------------------------
class Tooltip:

    def __init__(self, widget, text: str):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _event=None):
        if self.tip or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + 20
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tip, text=self.text, background="#ffffe0", relief="solid", borderwidth=1,
                         font=(None, 9))
        label.pack()

    def hide(self, _event=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


# ----------------------- Main App ----------------------------------
class BMICalculatorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry(f"{WIDTH}x{HEIGHT}")
        self.resizable(False, False)
        
        self.unit_var = tk.StringVar(value="metric")  
        self.weight_var = tk.StringVar()
        self.height_m_var = tk.StringVar()
        self.height_ft_var = tk.StringVar()
        self.height_in_var = tk.StringVar()

        # Results
        self.result_bmi_var = tk.StringVar(value="BMI: —")
        self.result_category_var = tk.StringVar(value="Category: —")

        # History
        self.history = [] 
        self.create_widgets()
        self.setup_validation()

    def create_widgets(self):
        pad = 12
        frame = ttk.Frame(self, padding=pad)
        frame.pack(fill=tk.BOTH, expand=True)

        # Header
        header = ttk.Label(frame, text=APP_TITLE, font=(None, 16, "bold"))
        header.grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))

        # Unit toggle
        unit_frame = ttk.Frame(frame)
        unit_frame.grid(row=1, column=0, columnspan=4, sticky="w")
        ttk.Radiobutton(unit_frame, text="Metric (kg, m)", value="metric", variable=self.unit_var,
                        command=self.on_unit_change).pack(side=tk.LEFT)
        ttk.Radiobutton(unit_frame, text="Imperial (lb, ft/in)", value="imperial", variable=self.unit_var,
                        command=self.on_unit_change).pack(side=tk.LEFT, padx=(8, 0))

        # Weight input
        ttk.Label(frame, text="Weight:").grid(row=2, column=0, sticky="e")
        self.weight_entry = ttk.Entry(frame, textvariable=self.weight_var, width=18)
        self.weight_entry.grid(row=2, column=1, sticky="w")
        self.weight_unit_label = ttk.Label(frame, text="kg")
        self.weight_unit_label.grid(row=2, column=2, sticky="w")
        Tooltip(self.weight_entry, "Enter weight. For imperial, enter total pounds (e.g., 150).")

        # Height inputs
        ttk.Label(frame, text="Height:").grid(row=3, column=0, sticky="e")
        self.height_m_entry = ttk.Entry(frame, textvariable=self.height_m_var, width=18)
        self.height_m_entry.grid(row=3, column=1, sticky="w")
        self.height_m_unit_label = ttk.Label(frame, text="m")
        self.height_m_unit_label.grid(row=3, column=2, sticky="w")

        # Imperial split inputs (ft, in)
        self.height_ft_entry = ttk.Entry(frame, textvariable=self.height_ft_var, width=6)
        self.height_in_entry = ttk.Entry(frame, textvariable=self.height_in_var, width=6)
        self.height_ft_label = ttk.Label(frame, text="ft")
        self.height_in_label = ttk.Label(frame, text="in")

        Tooltip(self.height_m_entry, "Enter height in meters like 1.75")
        Tooltip(self.height_ft_entry, "Feet (e.g., 5)")
        Tooltip(self.height_in_entry, "Inches (e.g., 9)")

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=4, column=0, columnspan=4, pady=(10, 6), sticky="w")
        calc_btn = ttk.Button(btn_frame, text="Calculate", command=self.on_calculate)
        calc_btn.pack(side=tk.LEFT)
        clear_btn = ttk.Button(btn_frame, text="Clear", command=self.on_clear)
        clear_btn.pack(side=tk.LEFT, padx=(8, 0))
        copy_btn = ttk.Button(btn_frame, text="Copy Result", command=self.on_copy)
        copy_btn.pack(side=tk.LEFT, padx=(8, 0))

        # Results
        res_frame = ttk.LabelFrame(frame, text="Result", padding=8)
        res_frame.grid(row=5, column=0, columnspan=2, sticky="nsew", pady=(6, 0))
        self.bmi_label = ttk.Label(res_frame, textvariable=self.result_bmi_var, font=(None, 12, "bold"))
        self.bmi_label.pack(anchor="w")
        self.cat_label = ttk.Label(res_frame, textvariable=self.result_category_var, font=(None, 11))
        self.cat_label.pack(anchor="w", pady=(4, 0))

        # Visual scale
        scale_frame = ttk.Frame(frame)
        scale_frame.grid(row=5, column=2, columnspan=2, sticky="nsew", padx=(12, 0))
        ttk.Label(scale_frame, text="BMI Scale").pack(anchor="w")
        self.scale_canvas = tk.Canvas(scale_frame, width=200, height=40, bg="#f3f4f6", highlightthickness=0)
        self.scale_canvas.pack(pady=(6, 0))
        self._draw_scale_background()

        # History
        history_frame = ttk.LabelFrame(frame, text="Recent Calculations", padding=6)
        history_frame.grid(row=6, column=0, columnspan=4, pady=(10, 0), sticky="nsew")
        self.history_listbox = tk.Listbox(history_frame, height=5, activestyle="none")
        self.history_listbox.pack(fill=tk.BOTH, expand=True)
        Tooltip(self.history_listbox, "Click an item to copy it into the input fields.")
        self.history_listbox.bind("<<ListboxSelect>>", self.on_history_select)

        # Layout tweak: grid weights
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(3, weight=1)

        # Initialize UI state
        self.on_unit_change()

    def _draw_scale_background(self):
        c = self.scale_canvas
        c.delete("all")
        width = int(c.winfo_reqwidth())
        # segments: underweight (0-18.5), normal (18.5-25), overweight (25-30), obesity (30-40+)
        segments = [18.5, 25, 30, 40]
        start_x = 4
        total_span = segments[-1]  # treat as 40
        for i, thresh in enumerate(segments):
            seg_width = (thresh / total_span) * (width - 8)
            color = list(CATEGORY_COLORS.values())[i if i < 3 else 3]
            c.create_rectangle(start_x, 8, start_x + seg_width, 32, fill=color, outline="")
            start_x += seg_width
        # border
        c.create_rectangle(2, 6, width - 2, 34, outline="#111827")

    def setup_validation(self):
        self.weight_var.trace_add("write", lambda *_: self._validate_inputs())
        self.height_m_var.trace_add("write", lambda *_: self._validate_inputs())
        self.height_ft_var.trace_add("write", lambda *_: self._validate_inputs())
        self.height_in_var.trace_add("write", lambda *_: self._validate_inputs())

    def on_unit_change(self):
        unit = self.unit_var.get()
        if unit == "metric":
            self.height_m_entry.grid()
            self.height_m_unit_label.grid()
            self.height_ft_entry.grid_remove()
            self.height_in_entry.grid_remove()
            self.height_ft_label.grid_remove()
            self.height_in_label.grid_remove()
            self.weight_unit_label.config(text="kg")
        else:
            self.height_m_entry.grid_remove()
            self.height_m_unit_label.grid_remove()
            self.height_ft_entry.grid(row=3, column=1, sticky="w")
            self.height_ft_label.grid(row=3, column=2, sticky="w")
            self.height_in_entry.grid(row=3, column=3, sticky="w")
            self.height_in_label.grid(row=3, column=4, sticky="w")
            self.weight_unit_label.config(text="lb")

    def _validate_inputs(self):
        unit = self.unit_var.get()
        default_bg = self.cget("bg")

        def mark(widget, ok):
            try:
                widget.configure(background=("white" if ok else "#ffe4e6"))
            except Exception:
                pass

        w_ok = True
        try:
            w = float(self.weight_var.get())
            if unit == "metric":
                w_ok = 20 <= w <= 300
            else:
                w_ok = 44 <= w <= 660 
        except Exception:
            w_ok = False if self.weight_var.get() else True
        mark(self.weight_entry, w_ok)

        # Validate height
        if unit == "metric":
            h_ok = True
            try:
                h = float(self.height_m_var.get())
                h_ok = 0.5 <= h <= 2.5
            except Exception:
                h_ok = False if self.height_m_var.get() else True
            mark(self.height_m_entry, h_ok)
        else:
            ft_ok = True
            in_ok = True
            try:
                ft = float(self.height_ft_var.get())
                ft_ok = 1 <= ft <= 8
            except Exception:
                ft_ok = False if self.height_ft_var.get() else True
            try:
                inch = float(self.height_in_var.get())
                in_ok = 0 <= inch < 12
            except Exception:
                in_ok = False if self.height_in_var.get() else True
            mark(self.height_ft_entry, ft_ok)
            mark(self.height_in_entry, in_ok)

    def on_calculate(self):
        unit = self.unit_var.get()
        try:
            if unit == "metric":
                weight = float(self.weight_var.get())
                height_m = float(self.height_m_var.get())
                if not (20 <= weight <= 300):
                    raise ValueError("Weight out of realistic range (20-300 kg)")
                if not (0.5 <= height_m <= 2.5):
                    raise ValueError("Height out of realistic range (0.5-2.5 m)")
                bmi = calculate_bmi_metric(weight, height_m)
                weight_str = f"{weight:.1f} kg"
                height_str = f"{height_m:.2f} m"
            else:
                weight_lb = float(self.weight_var.get())
                ft = float(self.height_ft_var.get())
                inch = float(self.height_in_var.get()) if self.height_in_var.get() else 0.0
                if not (44 <= weight_lb <= 660):
                    raise ValueError("Weight out of realistic range (44-660 lb)")
                if not (1 <= ft <= 8):
                    raise ValueError("Height feet out of range (1-8)")
                if not (0 <= inch < 12):
                    raise ValueError("Height inches must be 0-11")
                kg = kg_from_lb(weight_lb)
                m = m_from_ft_inches(ft, inch)
                bmi = calculate_bmi_metric(kg, m)
                weight_str = f"{weight_lb:.1f} lb"
                height_str = f"{int(ft)} ft {int(inch)} in"

            category = classify_bmi(bmi)
            self.result_bmi_var.set(f"BMI: {bmi}")
            self.result_category_var.set(f"Category: {category}")
            self._update_category_style(category)
            self.update_visual_scale(bmi)
            self._add_to_history(weight_str, height_str, bmi, category)
        except ValueError as ve:
            messagebox.showerror("Input error", str(ve))
        except Exception:
            messagebox.showerror("Error", "Please enter valid numeric values.")

    def _update_category_style(self, category: str):
        color = CATEGORY_COLORS.get(category, "#6b7280")
        try:
            self.cat_label.config(background=color, foreground="white")
        except Exception:
            self.cat_label.config(foreground=color)

    def update_visual_scale(self, bmi: float):
        c = self.scale_canvas
        c.delete("pointer")
        width = int(c.winfo_width() or c.winfo_reqwidth())
        bmi_clamped = max(0.0, min(bmi, 40.0))
        pos = (bmi_clamped / 40.0) * (width - 8) + 4
        c.create_line(pos, 4, pos, 36, width=3, fill="#111827", tags=("pointer",))

    def _add_to_history(self, weight_str, height_str, bmi, category):
        item = f"{weight_str}, {height_str} — BMI {bmi} ({category})"
        self.history.insert(0, item)
        self.history = self.history[:8]
        self._refresh_history_listbox()

    def _refresh_history_listbox(self):
        self.history_listbox.delete(0, tk.END)
        for it in self.history:
            self.history_listbox.insert(tk.END, it)

    def on_history_select(self, _event=None):
        sel = self.history_listbox.curselection()
        if not sel:
            return
        item = self.history[sel[0]]
        try:
            weight_part, rest = item.split(",", 1)
            h_part, bmi_part = rest.split(" — ", 1)
            
            if "kg" in weight_part:
                self.unit_var.set("metric")
                self.on_unit_change()
                self.weight_var.set(weight_part.replace("kg", "").strip())
                self.height_m_var.set(h_part.replace("m", "").strip())
            else:
                self.unit_var.set("imperial")
                self.on_unit_change()
                self.weight_var.set(weight_part.replace("lb", "").strip())
                parts = h_part.strip().split()
                if len(parts) >= 2:
                    ft = parts[0]
                    inch = parts[2] if len(parts) > 2 else "0"
                    self.height_ft_var.set(ft)
                    self.height_in_var.set(inch)
        except Exception:
            pass

    def on_clear(self):
        self.weight_var.set("")
        self.height_m_var.set("")
        self.height_ft_var.set("")
        self.height_in_var.set("")
        self.result_bmi_var.set("BMI: —")
        self.result_category_var.set("Category: —")
        self._update_category_style("")
        self.scale_canvas.delete("pointer")

    def on_copy(self):
        # copy current result to clipboard
        bmi_text = self.result_bmi_var.get()
        cat_text = self.result_category_var.get()
        if "—" in bmi_text:
            messagebox.showinfo("No result", "No result to copy.")
            return
        text = f"{bmi_text} — {cat_text}"
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Copied", "Result copied to clipboard.")


if __name__ == "__main__":
    app = BMICalculatorApp()
    app.mainloop()
