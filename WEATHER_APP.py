import os
import sys
import math
import json
import time
import threading
from datetime import datetime, timezone
from queue import Queue, Empty

# Try imports
try:
    import customtkinter as ctk # pyright: ignore[reportMissingImports]
    from PIL import Image, ImageTk, ImageDraw
    import requests
    import tkinter as tk  # still need tk for Canvas fallback
except Exception as e:
    print("Missing dependencies. Please install customtkinter, pillow, requests:")
    print("  pip install customtkinter pillow requests")
    raise e

# ---------- Configuration ----------
API_KEY = os.environ.get("OPENWEATHER_API_KEY", "6d4708305ad0e97b7ff5cfa497d2c84e")  # or paste your key here (not recommended)
OWM_WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
OWM_ONECALL_URL = "https://api.openweathermap.org/data/2.5/onecall"
FAVORITES_FILE = "favorites.json"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

MIN_LEN = 8
MAX_LEN = 64
SYMBOLS = "!@#$%^&*()-_=+[]{}|;:,.<>?/~"

# ---------- Utilities ----------
def load_favorites():
    try:
        with open(FAVORITES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_favorites(favs):
    try:
        with open(FAVORITES_FILE, "w", encoding="utf-8") as f:
            json.dump(favs, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def safe_get(d, *keys, default=None):
    cur = d
    try:
        for k in keys:
            cur = cur[k]
        return cur
    except Exception:
        return default

def meters_per_sec_to_kmh(ms):
    try:
        return ms * 3.6
    except Exception:
        return 0.0

def timestamp_to_local(dt_ts, tz_offset):
    try:
        return datetime.fromtimestamp(dt_ts + tz_offset, timezone.utc).astimezone()
    except Exception:
        return datetime.fromtimestamp(dt_ts)

# ---------- WeatherCanvas (robust) ----------
class WeatherCanvas:
    """
    Lightweight, robust animated weather canvas.
    Uses an internal tk.Canvas placed into CTkFrame's internal bg frame if present;
    falls back to placing into parent directly.
    """
    def __init__(self, parent, width=420, height=240):
        self.parent = parent
        self.width = int(width)
        self.height = int(height)
        
        tk_parent = None
        if hasattr(parent, "_bg_frame"):
            tk_parent = parent._bg_frame
        else:
            tk_parent = parent
        self.canvas = tk.Canvas(tk_parent, width=self.width, height=self.height, highlightthickness=0)
        self._stop = False
        self._anim_t = 0
        self.condition = "clear"
        self._lock = threading.Lock()
        self._anim_thread = threading.Thread(target=self._anim_loop, daemon=True)
        self._anim_thread.start()

    def set_condition(self, condition):
        with self._lock:
            self.condition = (condition or "clear").lower()
            self._anim_t = 0
            try:
                self.canvas.delete("all")
            except Exception:
                pass

    def stop_animation(self):
        self._stop = True
        try:
            self.canvas.delete("all")
        except Exception:
            pass

    def _anim_loop(self):
        while not self._stop:
            try:
                self._step()
            except Exception:
                pass
            time.sleep(0.05)
            self._anim_t += 1

    def _step(self):
        with self._lock:
            cond = self.condition
        self.canvas.delete("all")
        if "rain" in cond or "drizzle" in cond:
            self._draw_cloud()
            self._draw_rain(self._anim_t)
        elif "snow" in cond:
            self._draw_cloud()
            self._draw_snow(self._anim_t)
        elif "cloud" in cond:
            self._draw_cloud(cover=0.7)
        elif "fog" in cond or "mist" in cond or "haze" in cond:
            self._draw_fog(self._anim_t)
        elif "thunder" in cond or "storm" in cond:
            self._draw_cloud()
            if (self._anim_t // 15) % 10 == 0:
                self._draw_lightning()
        else:
            self._draw_sun(self._anim_t)

    def _draw_sun(self, t):
        cx, cy = self.width * 0.5, self.height * 0.45
        r = min(self.width, self.height) * 0.18
        rays = 8
        for i in range(rays):
            angle = (t * 3 + i * (360 / rays)) * math.pi / 180.0
            x1 = cx + math.cos(angle) * (r + 8)
            y1 = cy + math.sin(angle) * (r + 8)
            x2 = cx + math.cos(angle) * (r + 24)
            y2 = cy + math.sin(angle) * (r + 24)
            self.canvas.create_line(x1, y1, x2, y2, fill="#FFD166", width=3, capstyle="round")
        self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#FFB703", outline="#FB8500", width=2)

    def _draw_cloud(self, cover=0.5):
        w, h = self.width, self.height
        base_y = h * 0.55
        base_x = w * 0.5
        sizes = [50, 36, 42]
        offsets = [-60, -10, 40]
        for s, ox in zip(sizes, offsets):
            x = base_x + ox
            y = base_y - 10
            self.canvas.create_oval(x - s, y - s, x + s, y + s, fill="#d1d5db", outline="#9ca3af")
        self.canvas.create_rectangle(base_x - 90, base_y - 6, base_x + 90, base_y + 24, fill="#d1d5db", outline="#9ca3af")

    def _draw_rain(self, t):
        w, h = self.width, self.height
        base_y = h * 0.72
        count = 18
        for i in range(count):
            phase = (t / 2.0 + i * 13) % 60
            x = (i * (w / count)) + (phase % 10) - 10
            y = base_y + (phase % 40)
            self.canvas.create_line(x, y, x, y + 10, fill="#60a5fa", width=2)

    def _draw_snow(self, t):
        w, h = self.width, self.height
        base_y = h * 0.72
        count = 14
        for i in range(count):
            phase = (t + i * 17) % 100
            x = (i * (w / count)) + (phase % 20) - 10
            y = base_y + (phase % 60)
            self.canvas.create_text(x, y, text="❆", fill="#ffffff", font=("Arial", 10))

    def _draw_fog(self, t):
        w, h = self.width, self.height
        for i in range(4):
            offset = (t * 0.6 + i * 40) % (w + 200) - 100
            y = h * (0.45 + i * 0.08)
            self.canvas.create_rectangle(offset, y, offset + w * 0.6, y + 18, fill="#e6e7e8", outline="")

    def _draw_lightning(self):
        w, h = self.width, self.height
        x = w * 0.5
        y = h * 0.55
        pts = [(x - 10, y - 10), (x + 10, y), (x - 6, y + 6), (x + 12, y + 22)]
        for i in range(len(pts) - 1):
            self.canvas.create_line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], fill="#facc15", width=4)

# ---------- Weather fetcher ----------
class WeatherFetcher:
    def __init__(self, api_key):
        self.api_key = api_key

    def fetch(self, location):
        if not self.api_key:
            raise ValueError("OpenWeatherMap API key not set.")
        params = {"q": location, "appid": self.api_key}
        r = requests.get(OWM_WEATHER_URL, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        lat = safe_get(data, "coord", "lat")
        lon = safe_get(data, "coord", "lon")
        tz_offset = safe_get(data, "timezone", default=0)
        oc_params = {
            "lat": lat,
            "lon": lon,
            "exclude": "minutely,alerts",
            "appid": self.api_key,
            "units": "metric",
        }
        r2 = requests.get(OWM_ONECALL_URL, params=oc_params, timeout=10)
        r2.raise_for_status()
        oc = r2.json()
        combined = {
            "location_name": f"{safe_get(data,'name','')}, {safe_get(data,'sys','country','')}",
            "lat": lat,
            "lon": lon,
            "tz_offset": tz_offset,
            "current": oc.get("current", {}),
            "hourly": oc.get("hourly", []),
            "daily": oc.get("daily", []),
            "raw_weather": data,
        }
        return combined

# ---------- Main UI ----------
class WeatherDashboard(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Weather Dashboard Pro")
        self.geometry("980x640")
        self.minsize(880, 560)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # top bar
        top = ctk.CTkFrame(self, corner_radius=8)
        top.grid(row=0, column=0, sticky="ew", padx=14, pady=12)
        top.grid_columnconfigure(1, weight=1)

        title = ctk.CTkLabel(top, text="🌤 Weather Dashboard Pro", font=ctk.CTkFont(size=18, weight="bold"))
        title.grid(row=0, column=0, padx=(6,12))

        self.search_var = ctk.StringVar(value="New York,US")
        self.entry = ctk.CTkEntry(top, textvariable=self.search_var, width=360)
        self.entry.grid(row=0, column=1, sticky="ew", padx=(0,8))
        self.entry.bind("<Return>", lambda evt: self.on_search())

        btn_search = ctk.CTkButton(top, text="Search", command=self.on_search, width=90)
        btn_search.grid(row=0, column=2, padx=(0,8))

        btn_refresh = ctk.CTkButton(top, text="Refresh", command=self.on_refresh, width=90)
        btn_refresh.grid(row=0, column=3, padx=(0,8))

        self.theme_toggle = ctk.CTkSwitch(top, text="Light Mode", command=self.on_theme_toggle)
        self.theme_toggle.grid(row=0, column=4, padx=(0,8))

        # favorites
        self.favorites = load_favorites()
        fav_values = ["(none)"] + self.favorites
        self.fav_menu = ctk.CTkOptionMenu(top, values=fav_values, command=self.on_favorite_select)
        self.fav_menu.grid(row=0, column=5, padx=(0,4))
        self.save_fav_btn = ctk.CTkButton(top, text="☆ Save", width=72, command=self.save_current_favorite)
        self.save_fav_btn.grid(row=0, column=6, padx=(0,4))

        # content area
        content = ctk.CTkFrame(self, corner_radius=8)
        content.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0,12))
        content.grid_columnconfigure(0, weight=2)
        content.grid_columnconfigure(1, weight=3)
        content.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(content, corner_radius=8)
        left.grid(row=0, column=0, sticky="nsew", padx=(0,8), pady=8)
        left.grid_rowconfigure(1, weight=1)

        self.weather_canvas = WeatherCanvas(left, width=420, height=240)

        self.card = ctk.CTkFrame(left, corner_radius=8)
        self.card.pack(fill="both", expand=False, padx=12, pady=(6,12))
        self.card.grid_columnconfigure(1, weight=1)

        self.lbl_location = ctk.CTkLabel(self.card, text="Location —", font=ctk.CTkFont(size=16, weight="bold"))
        self.lbl_location.grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(8,2))

        self.lbl_temp = ctk.CTkLabel(self.card, text="--°C", font=ctk.CTkFont(size=30, weight="bold"))
        self.lbl_temp.grid(row=1, column=0, sticky="w", padx=8)
        self.lbl_feels = ctk.CTkLabel(self.card, text="Feels like --°C")
        self.lbl_feels.grid(row=1, column=1, sticky="w", padx=8)

        self.lbl_descr = ctk.CTkLabel(self.card, text="—", font=ctk.CTkFont(size=12))
        self.lbl_descr.grid(row=2, column=0, columnspan=2, sticky="w", padx=8, pady=(0,8))

        stats_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        stats_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=6, pady=(0,12))
        stats_frame.grid_columnconfigure((0,1,2,3), weight=1)

        self.stat_humidity = ctk.CTkLabel(stats_frame, text="💧 Humidity: —")
        self.stat_humidity.grid(row=0, column=0, sticky="w")
        self.stat_wind = ctk.CTkLabel(stats_frame, text="💨 Wind: —")
        self.stat_wind.grid(row=0, column=1, sticky="w")
        self.stat_pressure = ctk.CTkLabel(stats_frame, text="🧭 Pressure: —")
        self.stat_pressure.grid(row=0, column=2, sticky="w")
        self.stat_visibility = ctk.CTkLabel(stats_frame, text="👁 Visibility: —")
        self.stat_visibility.grid(row=0, column=3, sticky="w")

        self.sun_canvas = tk.Canvas(self.card._bg_frame if hasattr(self.card, "_bg_frame") else self.card, width=360, height=60, highlightthickness=0)
        self.sun_canvas.grid(row=4, column=0, columnspan=2, padx=8, pady=(0,12))
        self.sunrise_label = ctk.CTkLabel(self.card, text="Sunrise: --:--")
        self.sunrise_label.grid(row=5, column=0, sticky="w", padx=8)
        self.sunset_label = ctk.CTkLabel(self.card, text="Sunset: --:--")
        self.sunset_label.grid(row=5, column=1, sticky="e", padx=8)

        right = ctk.CTkFrame(content, corner_radius=8)
        right.grid(row=0, column=1, sticky="nsew", padx=(8,0), pady=8)
        right.grid_rowconfigure(1, weight=1)

        header_label = ctk.CTkLabel(right, text="Hourly Forecast (next 12 hrs)", font=ctk.CTkFont(size=14, weight="bold"))
        header_label.pack(anchor="w", padx=12, pady=(12,6))

        scroll_frame = ctk.CTkScrollableFrame(right, width=520, height=320, corner_radius=8)
        scroll_frame.pack(fill="both", expand=True, padx=12, pady=(0,12))
        self.hourly_container = scroll_frame

        self.status_label = ctk.CTkLabel(self, text="Ready", anchor="w")
        self.status_label.grid(row=2, column=0, sticky="ew", padx=14, pady=(0,10))

        self.fetcher = WeatherFetcher(API_KEY)
        self.queue = Queue()
        self.current_data = None
        self.favorites = load_favorites()
        self.fav_menu.configure(values=["(none)"] + self.favorites)

        self.after(200, self.on_search)

    # ---------- actions ----------
    def set_status(self, text):
        self.status_label.configure(text=text)

    def on_theme_toggle(self):
        new = "light" if ctk.get_appearance_mode() == "dark" else "dark"
        ctk.set_appearance_mode(new)

    def on_favorite_select(self, val):
        if not val or val == "(none)":
            return
        self.search_var.set(val)
        self.on_search()

    def save_current_favorite(self):
        loc = self.search_var.get().strip()
        if not loc:
            self.set_status("No location to save.")
            return
        if loc not in self.favorites:
            self.favorites.insert(0, loc)
            self.favorites = self.favorites[:12]
            save_favorites(self.favorites)
            self.fav_menu.configure(values=["(none)"] + self.favorites)
            self.set_status(f"Saved favorite: {loc}")
        else:
            self.set_status(f"Already in favorites: {loc}")

    def on_search(self):
        loc = self.search_var.get().strip()
        if not loc:
            self.set_status("Enter a location (city or City,Country).")
            return
        self.set_status(f"Searching: {loc} ...")
        threading.Thread(target=self._background_fetch, args=(loc,), daemon=True).start()
        self.after(100, self._process_queue)

    def on_refresh(self):
        loc = self.search_var.get().strip()
        if not loc:
            self.set_status("No location to refresh.")
            return
        self.on_search()

    def _background_fetch(self, loc):
        try:
            data = self.fetcher.fetch(loc)
            self.queue.put(("ok", data))
        except requests.HTTPError as he:
            try:
                msg = he.response.json().get("message", str(he))
            except Exception:
                msg = str(he)
            self.queue.put(("error", f"API error: {msg}"))
        except Exception as e:
            self.queue.put(("error", f"Fetch error: {e}"))

    def _process_queue(self):
        try:
            typ, payload = self.queue.get_nowait()
        except Empty:
            self.after(100, self._process_queue)
            return
        if typ == "error":
            self.set_status(payload)
            ctk.CTkLabel(self, text=payload)  
            return
        self.current_data = payload
        self.set_status("Data loaded.")
        self._update_ui_with_data(payload)

    # ---------- update UI ----------
    def _update_ui_with_data(self, combined):
        try:
            loc_name = combined.get("location_name", "Unknown location")
            self.lbl_location.configure(text=loc_name)

            tz_off = combined.get("tz_offset", 0)
            cur = combined.get("current", {})
            temp = cur.get("temp")
            feels = cur.get("feels_like")
            desc = safe_get(cur, "weather", 0, "description", default="").title()
            cond_main = safe_get(cur, "weather", 0, "main", default="Clear").lower()

            self.weather_canvas.set_condition(cond_main)

            if temp is not None:
                self.lbl_temp.configure(text=f"{temp:.1f}°C")
            if feels is not None:
                self.lbl_feels.configure(text=f"Feels like {feels:.1f}°C")
            self.lbl_descr.configure(text=desc or "—")

            humidity = cur.get("humidity")
            wind_speed = cur.get("wind_speed", 0)
            pressure = cur.get("pressure")
            visibility = cur.get("visibility")

            self.stat_humidity.configure(text=f"💧 Humidity: {humidity}%")
            self.stat_wind.configure(text=f"💨 Wind: {meters_per_sec_to_kmh(wind_speed):.0f} km/h")
            self.stat_pressure.configure(text=f"🧭 Pressure: {pressure} hPa")
            if visibility is None:
                self.stat_visibility.configure(text=f"👁 Visibility: —")
            else:
                self.stat_visibility.configure(text=f"👁 Visibility: {visibility/1000:.1f} km")

            sunrise = cur.get("sunrise")
            sunset = cur.get("sunset")
            if sunrise and sunset:
                local_sunrise = timestamp_to_local(sunrise, tz_off)
                local_sunset = timestamp_to_local(sunset, tz_off)
                self.sunrise_label.configure(text=f"Sunrise: {local_sunrise.strftime('%H:%M')}")
                self.sunset_label.configure(text=f"Sunset: {local_sunset.strftime('%H:%M')}")
                self._draw_sun_arc(sunrise, sunset, tz_off)
            else:
                self.sunrise_label.configure(text="Sunrise: --:--")
                self.sunset_label.configure(text="Sunset: --:--")
                self.sun_canvas.delete("all")

            hourly = combined.get("hourly", [])[:12]
            for widget in self.hourly_container.winfo_children():
                widget.destroy()
            for i, h in enumerate(hourly):
                frame = ctk.CTkFrame(self.hourly_container, corner_radius=8, fg_color="transparent")
                frame.grid(row=0, column=i, padx=8, pady=6)
                ts = h.get("dt")
                local_time = timestamp_to_local(ts, combined.get("tz_offset", 0))
                tlabel = ctk.CTkLabel(frame, text=local_time.strftime("%H:%M"))
                tlabel.pack(anchor="center", pady=(6,2), padx=8)
                main = safe_get(h, "weather", 0, "main", default="Clear").lower()
                ic = "☀️"
                if "rain" in main:
                    ic = "🌧️"
                elif "cloud" in main:
                    ic = "☁️"
                elif "snow" in main:
                    ic = "❄️"
                elif "fog" in main or "mist" in main:
                    ic = "🌫️"
                ctk.CTkLabel(frame, text=ic).pack()
                temp_h = h.get("temp")
                ctk.CTkLabel(frame, text=f"{temp_h:.0f}°C").pack(pady=(4,6))

            self.set_status(f"Showing: {loc_name}")
        except Exception as e:
            self.set_status(f"UI update error: {e}")

    def _draw_sun_arc(self, sunrise_ts, sunset_ts, tz_off):
        try:
            self.sun_canvas.delete("all")
            w = int(self.sun_canvas.winfo_width() or 360)
            h = int(self.sun_canvas.winfo_height() or 60)
            cx = w // 2
            cy = h
            r = min(w // 2 - 8, 80)
            self.sun_canvas.create_arc(cx - r, cy - r, cx + r, cy + r, start=180, extent=180, fill="#111827", outline="#374151")
            now_ts = int(datetime.now(timezone.utc).timestamp())
            total = sunset_ts - sunrise_ts
            elapsed = max(0, min(now_ts - sunrise_ts, total))
            pct = elapsed / total if total > 0 else 0
            fill_extent = pct * 180
            self.sun_canvas.create_arc(cx - r, cy - r, cx + r, cy + r, start=180, extent=fill_extent, fill="#f59e0b", outline="")
            angle_deg = 180 + fill_extent
            angle_rad = math.radians(angle_deg)
            sx = cx + math.cos(angle_rad) * r
            sy = cy + math.sin(angle_rad) * r
            self.sun_canvas.create_oval(sx - 6, sy - 6, sx + 6, sy + 6, fill="#FFD166", outline="")
            perc_label = f"{int(pct*100)}% daylight"
            self.sun_canvas.create_text(12, 12, text=perc_label, anchor="nw", fill="#e5e7eb")
        except Exception:
            pass

    def _on_close(self):
        try:
            self.weather_canvas.stop_animation()
        except Exception:
            pass
        self.destroy()

# ---------- run ----------
def main():
    if not API_KEY:
        print("OpenWeatherMap API key not set. Set OPENWEATHER_API_KEY environment variable.")
    app = WeatherDashboard()
    app.protocol("WM_DELETE_WINDOW", app._on_close)
    app.mainloop()

if __name__ == "__main__":
    main()
main()
