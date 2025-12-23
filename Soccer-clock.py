import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, ttk, colorchooser
import csv
import pygame
import os
import sys
import time
import wave
import struct
import threading
import random
import json
import math
from pathlib import Path

# --- FARBPALETTE FC RSK FREYBURG ---
RSK_BLUE = "#00529F"
RSK_WHITE = "#FFFFFF"
BG_COLOR = "#F0F2F5"
TEXT_COLOR = "#333333"
ACCENT_GREEN = "#28a745"
ACCENT_RED = "#dc3545"


def get_settings_path():
    """Return a user-writable path for the default settings file.

    Falls back to platform-appropriate config locations to avoid writing
    into the executable directory (problematic in onefile builds).
    """

    if os.name == "nt":
        base_dir = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA")
        base_path = Path(base_dir) if base_dir else Path.home() / "AppData" / "Local"
    elif sys.platform == "darwin":
        base_path = Path.home() / "Library" / "Application Support"
    else:
        base_path = Path(os.getenv("XDG_CONFIG_HOME") or (Path.home() / ".config"))

    config_dir = base_path / "SoccerClock"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "settings.json"

# ====================================================================
# --- KLASSE: ANZEIGETAFEL-FENSTER (BLAU-WEISS, OHNE STATUS) ---
# ====================================================================

class ScoreboardDisplay:
    """Repräsentiert das separate Anzeigetafel-Fenster mit blau-weißem Schema."""

    def __init__(
        self,
        master,
        bg_color=RSK_BLUE,
        text_color=RSK_WHITE,
        home_name="Spielplan Links",
        away_name="Spielplan Rechts",
        board_title="FC RSK FREYBURG",
        on_close_callback=None,
    ):
        self.window = tk.Toplevel(master)
        self.window.title(f"Anzeigetafel - {board_title}")
        self.window.geometry("1024x576")
        self.window.configure(bg=bg_color)
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

        self.on_close_callback = on_close_callback

        self.bg_color = bg_color
        self.text_color = text_color
        self.board_title = tk.StringVar(value=board_title)

        # Variablen für die Anzeige
        self.time_str = tk.StringVar(value="00:00")
        self.home_score_str = tk.StringVar(value="0")
        self.away_score_str = tk.StringVar(value="0")

        # NEU: Teamnamen aktualisiert
        self.team_home_name = tk.StringVar(value=home_name)
        self.team_away_name = tk.StringVar(value=away_name)
        self.team_home_name_raw = home_name
        self.team_away_name_raw = away_name

        self.create_widgets()
        self.window.withdraw()

    def create_widgets(self):
        self.main_frame = tk.Frame(self.window, bg=self.bg_color, padx=14, pady=14)
        self.main_frame.pack(fill="both", expand=True)

        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(1, weight=0)
        self.main_frame.grid_columnconfigure(2, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=3)
        self.main_frame.grid_rowconfigure(2, weight=1)

        # --- TITEL (GANZ OBEN) ---
        self.title_frame = tk.Frame(self.main_frame, bg=self.bg_color)
        self.title_frame.grid(row=0, column=0, columnspan=3, pady=(0, 2), sticky="n")
        self.lbl_title = tk.Label(self.title_frame, textvariable=self.board_title, font=("Helvetica", 24, "bold"), bg=self.bg_color, fg=self.text_color)
        self.lbl_title.pack()

        # --- SPIELSTAND - HOME (Spielplan Links) ---
        self.home_frame = tk.Frame(self.main_frame, bg=self.bg_color)
        self.home_frame.grid(row=1, column=0, sticky="nsew")
        self.lbl_home_team = tk.Label(
            self.home_frame,
            textvariable=self.team_home_name,
            font=("Arial", 18, "bold"),
            bg=self.bg_color,
            fg=self.text_color,
            wraplength=320,
            justify="center",
            height=3,
        )
        self.lbl_home_team.pack(pady=(4, 2), padx=6, fill="x")
        self.lbl_score_home = tk.Label(self.home_frame, textvariable=self.home_score_str, font=("Impact", 150), bg=self.bg_color, fg=self.text_color)
        self.lbl_score_home.pack(fill="both", expand=True)

        # --- TRENNER (DOPPELPUNKT) ---
        self.lbl_divider = tk.Label(self.main_frame, text=":", font=("Impact", 140), bg=self.bg_color, fg="#4477BB")
        self.lbl_divider.grid(row=1, column=1, sticky="nsew", padx=4)

        # --- SPIELSTAND - AWAY (Spielplan Rechts) ---
        self.away_frame = tk.Frame(self.main_frame, bg=self.bg_color)
        self.away_frame.grid(row=1, column=2, sticky="nsew")
        self.lbl_away_team = tk.Label(
            self.away_frame,
            textvariable=self.team_away_name,
            font=("Arial", 18, "bold"),
            bg=self.bg_color,
            fg=self.text_color,
            wraplength=320,
            justify="center",
            height=3,
        )
        self.lbl_away_team.pack(pady=(4, 2), padx=6, fill="x")
        self.lbl_score_away = tk.Label(self.away_frame, textvariable=self.away_score_str, font=("Impact", 150), bg=self.bg_color, fg=self.text_color)
        self.lbl_score_away.pack(fill="both", expand=True)

        # --- SPIELZEIT (GANZ UNTEN) ---
        self.time_frame = tk.Frame(self.main_frame, bg=self.bg_color)
        self.time_frame.grid(row=2, column=0, columnspan=3, pady=(6, 0), sticky="s")
        self.lbl_time_title = tk.Label(self.time_frame, text="SPIELZEIT", font=("Arial", 12, "bold"), bg=self.bg_color, fg=self.text_color)
        self.lbl_time_title.pack()
        self.lbl_time = tk.Label(self.time_frame, textvariable=self.time_str, font=("Impact", 60), bg=self.bg_color, fg=self.text_color)
        self.lbl_time.pack()
        self._update_wrapped_team_names()

    def update(self, time_str, half_text, home_score, away_score, time_color):
        """Aktualisiert alle Anzeigewerte ohne Statuszeile."""
        self.time_str.set(time_str)
        self.home_score_str.set(str(home_score))
        self.away_score_str.set(str(away_score))

        if time_color == self.bg_color:
            time_fg = self.text_color
        elif time_color == ACCENT_RED:
            time_fg = ACCENT_RED
        else:
            time_fg = time_color

        self.lbl_time.config(fg=time_fg)
        self.lbl_time_title.config(fg=ACCENT_RED if time_fg == ACCENT_RED else self.text_color)
        
        if home_score > away_score:
            self.lbl_score_home.config(fg=self.text_color)
            self.lbl_score_away.config(fg="#88AAFF")
        elif away_score > home_score:
            self.lbl_score_home.config(fg="#88AAFF")
            self.lbl_score_away.config(fg=self.text_color)
        else:
            self.lbl_score_home.config(fg=self.text_color)
            self.lbl_score_away.config(fg=self.text_color)

    def show(self):
        self.window.deiconify()
        self.window.lift()

    def hide(self):
        self.window.withdraw()

    def _on_close(self):
        if self.on_close_callback:
            self.on_close_callback()
        else:
            self.hide()

    def set_colors(self, bg_color, text_color):
        self.bg_color = bg_color
        self.text_color = text_color
        for widget in [self.window, self.main_frame, self.title_frame, self.home_frame, self.away_frame, self.time_frame]:
            widget.configure(bg=self.bg_color)
        self.lbl_title.configure(bg=self.bg_color, fg=self.text_color)
        self.lbl_home_team.configure(bg=self.bg_color, fg=self.text_color)
        self.lbl_away_team.configure(bg=self.bg_color, fg=self.text_color)
        self.lbl_score_home.configure(bg=self.bg_color, fg=self.text_color)
        self.lbl_score_away.configure(bg=self.bg_color, fg=self.text_color)
        self.lbl_time.configure(bg=self.bg_color, fg=self.text_color)
        self.lbl_time_title.configure(bg=self.bg_color, fg=self.text_color)
        self.lbl_divider.configure(bg=self.bg_color)

    def set_team_names(self, home, away):
        self.team_home_name_raw = home
        self.team_away_name_raw = away
        self._update_wrapped_team_names()
        self._sync_team_font_size()

    def set_resolution(self, width, height):
        self.window.geometry(f"{width}x{height}")
        self.window.update_idletasks()
        wrap_len = max(200, (width // 3) - 20)
        for lbl in (self.lbl_home_team, self.lbl_away_team):
            lbl.configure(wraplength=wrap_len)
        self._sync_team_font_size()

    def set_board_title(self, title):
        self.board_title.set(title)
        self.window.title(f"Anzeigetafel - {title}")

    def _sync_team_font_size(self):
        wrap_len = int(self.lbl_home_team.cget("wraplength")) or 240
        names = [self.team_home_name_raw, self.team_away_name_raw]
        max_size = 26
        min_size = 14

        for size in range(max_size, min_size - 1, -1):
            font = tkfont.Font(family="Arial", size=size, weight="bold")
            fits_all = True
            for name in names:
                if not name:
                    continue
                longest_word = max((font.measure(word) for word in name.split()), default=0)
                est_lines = (font.measure(name) // max(1, wrap_len)) + 1
                if longest_word > wrap_len or est_lines > 3:
                    fits_all = False
                    break
            if fits_all:
                self.lbl_home_team.configure(font=("Arial", size, "bold"))
                self.lbl_away_team.configure(font=("Arial", size, "bold"))
                self._update_wrapped_team_names()
                return

        self.lbl_home_team.configure(font=("Arial", min_size, "bold"))
        self.lbl_away_team.configure(font=("Arial", min_size, "bold"))
        self._update_wrapped_team_names()

    def _format_team_name_lines(self, name, wrap_len):
        font = tkfont.Font(font=self.lbl_home_team["font"])
        words = name.split()
        if not words:
            return [""]

        lines = []
        current = words[0]

        for word in words[1:]:
            trial = f"{current} {word}"
            if font.measure(trial) <= wrap_len:
                current = trial
            else:
                lines.append(current)
                current = word

        lines.append(current)
        return lines[:3]

    def _update_wrapped_team_names(self):
        wrap_len = int(self.lbl_home_team.cget("wraplength")) or 240
        home_lines = self._format_team_name_lines(self.team_home_name_raw, wrap_len)
        away_lines = self._format_team_name_lines(self.team_away_name_raw, wrap_len)

        line_count = max(len(home_lines), len(away_lines), self.lbl_home_team.cget("height"))
        while len(home_lines) < line_count:
            home_lines.append("")
        while len(away_lines) < line_count:
            away_lines.append("")

        self.team_home_name.set("\n".join(home_lines))
        self.team_away_name.set("\n".join(away_lines))


# ====================================================================
# --- HAUPTKLASSE: FUSSBALL-TIMER ---
# ====================================================================

class FussballTimer:
    def __init__(self, root):
        self.root = root
        self.controller_title = tk.StringVar(value="FC RSK FREYBURG")
        self.controller_width = tk.IntVar(value=400)
        self.controller_height = tk.IntVar(value=800)
        self.controller_bg_color = BG_COLOR
        self.controller_header_color = RSK_BLUE
        self.controller_card_bg = RSK_WHITE
        self.controller_text_color = TEXT_COLOR
        self.scoreboard_bg_color = RSK_BLUE
        self.scoreboard_text_color = RSK_WHITE
        self.scoreboard_title = "FC RSK FREYBURG"
        self.scoreboard_enabled = tk.BooleanVar(value=False)
        self.scoreboard_width = tk.IntVar(value=1024)
        self.scoreboard_height = tk.IntVar(value=576)
        self.settings_path = get_settings_path()
        self.settings_path_var = tk.StringVar(value=str(self.settings_path))
        self.match_mode = tk.StringVar(value="normal")
        self.tournament_matches = []
        self.match_number_var = tk.StringVar(value="")
        self.total_halves = 2
        self.current_half = 1

        self.mode_info_var = tk.StringVar(value="")
        self.auto_jingle_enabled = tk.BooleanVar(value=True)
        self.auto_jingle_user_choice = None
        self.hall_buzzer_enabled = tk.BooleanVar(value=False)
        self.csv_status_var = tk.StringVar(value="Kein CSV geladen")

        # Team- und Spielzeit-Defaults müssen vor dem Laden der Einstellungen existieren
        self.team_home_name = "Spielplan Links"
        self.team_away_name = "Spielplan Rechts"
        self.match_duration_minutes = tk.IntVar(value=45)
        self.current_match_duration_seconds = self.match_duration_minutes.get() * 60
        self.scores = {self.team_home_name: 0, self.team_away_name: 0}

        # --- Logik-Variablen ---
        self.seconds = 0
        self.running = False
        self._after_id = None

        self.default_settings = {
            "controller_title": self.controller_title.get(),
            "controller_width": self.controller_width.get(),
            "controller_height": self.controller_height.get(),
            "controller_bg_color": self.controller_bg_color,
            "controller_header_color": self.controller_header_color,
            "controller_card_bg": self.controller_card_bg,
            "controller_text_color": self.controller_text_color,
            "scoreboard_bg_color": self.scoreboard_bg_color,
            "scoreboard_text_color": self.scoreboard_text_color,
            "scoreboard_title": self.scoreboard_title,
            "scoreboard_width": self.scoreboard_width.get(),
            "scoreboard_height": self.scoreboard_height.get(),
            "team_home_name": self.team_home_name,
            "team_away_name": self.team_away_name,
            "match_duration": self.match_duration_minutes.get(),
            "match_mode": self.match_mode.get(),
            "auto_jingle_enabled": self.auto_jingle_enabled.get(),
            "hall_buzzer_enabled": self.hall_buzzer_enabled.get(),
        }

        self._load_settings()
        self._update_mode_label()

        self.root.title("Soccer Clock")
        self.root.geometry(f"{self.controller_width.get()}x{self.controller_height.get()}")
        self.root.minsize(self.controller_width.get(), self.controller_height.get())
        self.root.configure(bg=self.controller_bg_color)

        self.jingle_paths = []
        self.jingle_triggered = False
        
        self.scoreboard = ScoreboardDisplay(
            root,
            bg_color=self.scoreboard_bg_color,
            text_color=self.scoreboard_text_color,
            home_name=self.team_home_name,
            away_name=self.team_away_name,
            board_title=self.scoreboard_title,
            on_close_callback=self._handle_scoreboard_closed,
        )
        self.scoreboard_enabled.trace_add("write", self._toggle_scoreboard)
        
        # Audio
        try:
            # Behebungsvorschlag aus der vorherigen Konversation: Frequenz auf 22050 gesetzt, falls 44100 nicht geht.
            pygame.mixer.init(frequency=22050)
        except Exception:
            messagebox.showerror("Fehler", "Pygame Mixer konnte nicht initialisiert werden. Audiofunktionen sind deaktiviert.")
            
        self.jingle_playing = False
        self.jingle_start_time = None
        self.wave_reduced = None
        self.wave_duration = 0
        self.max_amp_scale = 1.0
        self.current_jingle_path = None
        self._buzzer_sound = None

        self.create_widgets()

        self._set_mode(self.match_mode.get())
        self._apply_controller_colors()
        self.scoreboard.set_colors(self.scoreboard_bg_color, self.scoreboard_text_color)
        self.scoreboard.set_resolution(self.scoreboard_width.get(), self.scoreboard_height.get())
        self.scoreboard.set_board_title(self.scoreboard_title)
        self.scoreboard.set_team_names(self.team_home_name, self.team_away_name)
        self._sync_auto_jingle_controls()
        self._update_scoreboard_display(RSK_BLUE, "SPIEL BEREIT")

        self.wave_canvas.bind("<Configure>", self._on_resize)
        self.root.bind("<space>", lambda e: self.toggle_timer())

    # --- UI HELPER METHODEN (Unverändert) ---
    def _big_btn(self, parent, text, cmd, color):
        return tk.Button(parent, text=text, font=("Arial", 12, "bold"), bg=color, fg="white",
                         command=cmd, relief="flat", padx=15, pady=5, cursor="hand2")

    def _text_btn(self, parent, text, cmd):
        return tk.Button(parent, text=text, font=("Arial", 10, "underline"), bg=RSK_WHITE, fg="#666", 
                         command=cmd, relief="flat", cursor="hand2")

    def _circle_btn(self, parent, text, cmd, color):
        f = tk.Frame(parent, bg=RSK_WHITE, padx=2)
        f.pack(side="left")
        tk.Button(f, text=text, font=("Arial", 14, "bold"), bg=color, fg="white", width=3,
                  command=cmd, relief="flat", cursor="hand2").pack()

    def _icon_btn(self, parent, text, cmd, color):
        return tk.Button(parent, text=text, font=("Arial", 10, "bold"), bg=color, fg="white", 
                         command=cmd, relief="flat", padx=10, pady=4, cursor="hand2")

    def create_widgets(self):
        # --- HEADER ---
        self.header_frame = tk.Frame(self.root, bg=self.controller_header_color, height=50)
        self.header_frame.pack(fill="x")
        self.header_label = tk.Label(
            self.header_frame,
            textvariable=self.controller_title,
            font=("Helvetica", 16, "bold"),
            bg=self.controller_header_color,
            fg=self.scoreboard_text_color
        )
        self.header_label.pack(pady=10, side="left", padx=10)

        self.settings_btn = tk.Button(
            self.header_frame,
            text="⚙ Einstellungen",
            font=("Arial", 10, "bold"),
            bg=self.controller_header_color,
            fg=self.scoreboard_text_color,
            relief="flat",
            cursor="hand2",
            command=self._open_settings_menu
        )
        self.settings_btn.pack(side="right", padx=10)

        # Anzeigetafel-Option GANZ OBEN platziert
        self._create_card_scoreboard_option_top()

        # --- HAUPTBEREICH ---
        self.main_container = tk.Frame(self.root, bg=self.controller_bg_color)
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

        self._create_card_timer(self.main_container)
        self._create_card_score(self.main_container)
        self._create_card_audio(self.main_container)
        self._update_tournament_controls()

    def _recolor_container(self, widget, color, fg_color=None):
        for child in widget.winfo_children():
            if child.winfo_children():
                self._recolor_container(child, color, fg_color)
            if child.winfo_class() not in ("Button", "TButton"):
                try:
                    child.configure(bg=color)
                except tk.TclError:
                    pass
            if fg_color and child.winfo_class() in ("Label", "Checkbutton", "Radiobutton"):
                try:
                    child.configure(fg=fg_color)
                except tk.TclError:
                    pass

    def _set_mode(self, mode_value):
        valid_modes = ("halle", "halle_turnier", "normal")
        previous_mode = self.match_mode.get()
        self.match_mode.set(mode_value if mode_value in valid_modes else "normal")
        is_hallenmodus = self.match_mode.get() in ("halle", "halle_turnier")
        self.total_halves = 1 if is_hallenmodus else 2
        self.current_half = min(self.current_half, self.total_halves)
        self.jingle_triggered = False
        self._apply_mode_default_duration(previous_mode)
        if hasattr(self, "next_half_btn"):
            if self.total_halves == 1:
                if self.next_half_btn.winfo_manager():
                    self.next_half_btn.pack_forget()
            else:
                if not self.next_half_btn.winfo_manager():
                    self.next_half_btn.pack(side="left", padx=5)
                self.next_half_btn.config(state="normal")
        self._sync_auto_jingle_controls()
        self._update_mode_label()
        self._update_half_ready_label()
        self._update_tournament_controls()

    def _apply_mode_default_duration(self, previous_mode):
        new_mode = self.match_mode.get()
        default_new = 12 if new_mode in ("halle", "halle_turnier") else 45
        default_prev = 12 if previous_mode in ("halle", "halle_turnier") else 45

        if self.match_duration_minutes.get() == default_prev:
            self.match_duration_minutes.set(default_new)
            if not self.running:
                self.current_match_duration_seconds = default_new * 60
            if hasattr(self, "match_duration_var"):
                self.match_duration_var.set(default_new)

    def _load_settings(self, path=None):
        target_path = Path(path or self.settings_path)
        if not target_path.exists():
            return

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return

        self.settings_path = target_path
        self.settings_path_var.set(str(target_path))

        self.controller_title.set(data.get("controller_title", self.controller_title.get()))
        self.controller_width.set(int(data.get("controller_width", self.controller_width.get())))
        self.controller_height.set(int(data.get("controller_height", self.controller_height.get())))
        self.controller_bg_color = data.get("controller_bg_color", self.controller_bg_color)
        self.controller_header_color = data.get("controller_header_color", self.controller_header_color)
        self.controller_card_bg = data.get("controller_card_bg", self.controller_card_bg)
        self.controller_text_color = data.get("controller_text_color", self.controller_text_color)

        self.scoreboard_bg_color = data.get("scoreboard_bg_color", self.scoreboard_bg_color)
        self.scoreboard_text_color = data.get("scoreboard_text_color", self.scoreboard_text_color)
        self.scoreboard_title = data.get("scoreboard_title", self.scoreboard_title)
        self.scoreboard_width.set(int(data.get("scoreboard_width", self.scoreboard_width.get())))
        self.scoreboard_height.set(int(data.get("scoreboard_height", self.scoreboard_height.get())))

        self.team_home_name = data.get("team_home_name", self.team_home_name)
        self.team_away_name = data.get("team_away_name", self.team_away_name)
        self.scores = {self.team_home_name: 0, self.team_away_name: 0}

        self.match_duration_minutes.set(int(data.get("match_duration", self.match_duration_minutes.get())))
        self.current_match_duration_seconds = self.match_duration_minutes.get() * 60
        if "auto_jingle_enabled" in data:
            self.auto_jingle_enabled.set(bool(data.get("auto_jingle_enabled", self.auto_jingle_enabled.get())))
            self.auto_jingle_user_choice = self.auto_jingle_enabled.get()
        if "hall_buzzer_enabled" in data:
            self.hall_buzzer_enabled.set(bool(data.get("hall_buzzer_enabled", self.hall_buzzer_enabled.get())))
        self._set_mode(data.get("match_mode", self.match_mode.get()))

    def _save_settings(self):
        data = {
            "controller_title": self.controller_title.get(),
            "controller_width": self.controller_width.get(),
            "controller_height": self.controller_height.get(),
            "controller_bg_color": self.controller_bg_color,
            "controller_header_color": self.controller_header_color,
            "controller_card_bg": self.controller_card_bg,
            "controller_text_color": self.controller_text_color,
            "scoreboard_bg_color": self.scoreboard_bg_color,
            "scoreboard_text_color": self.scoreboard_text_color,
            "scoreboard_title": self.scoreboard_title,
            "scoreboard_width": self.scoreboard_width.get(),
            "scoreboard_height": self.scoreboard_height.get(),
            "team_home_name": self.team_home_name,
            "team_away_name": self.team_away_name,
            "match_duration": self.match_duration_minutes.get(),
            "match_mode": self.match_mode.get(),
            "auto_jingle_enabled": self.auto_jingle_enabled.get(),
            "hall_buzzer_enabled": self.hall_buzzer_enabled.get(),
        }

        try:
            Path(self.settings_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as exc:
            messagebox.showerror("Speichern fehlgeschlagen", f"Einstellungen konnten nicht gespeichert werden: {exc}")

    def _reset_settings_to_defaults(self):
        if not messagebox.askyesno("Einstellungen zurücksetzen", "Alle Einstellungen auf Standardwerte setzen?"):
            return

        defaults = self.default_settings

        self.controller_title.set(defaults["controller_title"])
        self.controller_width.set(defaults["controller_width"])
        self.controller_height.set(defaults["controller_height"])
        self.controller_bg_color = defaults["controller_bg_color"]
        self.controller_header_color = defaults["controller_header_color"]
        self.controller_card_bg = defaults["controller_card_bg"]
        self.controller_text_color = defaults["controller_text_color"]

        self.scoreboard_bg_color = defaults["scoreboard_bg_color"]
        self.scoreboard_text_color = defaults["scoreboard_text_color"]
        self.scoreboard_title = defaults["scoreboard_title"]
        self.scoreboard_width.set(defaults["scoreboard_width"])
        self.scoreboard_height.set(defaults["scoreboard_height"])

        self._set_team_names(defaults["team_home_name"], defaults["team_away_name"])
        self.match_duration_minutes.set(defaults["match_duration"])
        if not self.running:
            self.current_match_duration_seconds = self.match_duration_minutes.get() * 60

        self.match_mode.set(defaults["match_mode"])
        self.auto_jingle_enabled.set(defaults["auto_jingle_enabled"])
        self.auto_jingle_user_choice = self.auto_jingle_enabled.get()
        self.hall_buzzer_enabled.set(defaults.get("hall_buzzer_enabled", False))
        self._set_mode(self.match_mode.get())

        if hasattr(self, "home_name_var"):
            self.home_name_var.set(self.team_home_name)
        if hasattr(self, "away_name_var"):
            self.away_name_var.set(self.team_away_name)
        if hasattr(self, "controller_title_var"):
            self.controller_title_var.set(self.controller_title.get())
        if hasattr(self, "controller_width_var"):
            self.controller_width_var.set(self.controller_width.get())
        if hasattr(self, "controller_height_var"):
            self.controller_height_var.set(self.controller_height.get())
        if hasattr(self, "controller_bg_color_var"):
            self.controller_bg_color_var.set(self.controller_bg_color)
        if hasattr(self, "controller_header_color_var"):
            self.controller_header_color_var.set(self.controller_header_color)
        if hasattr(self, "controller_card_color_var"):
            self.controller_card_color_var.set(self.controller_card_bg)
        if hasattr(self, "controller_text_color_var"):
            self.controller_text_color_var.set(self.controller_text_color)
        if hasattr(self, "scoreboard_width_var"):
            self.scoreboard_width_var.set(self.scoreboard_width.get())
        if hasattr(self, "scoreboard_height_var"):
            self.scoreboard_height_var.set(self.scoreboard_height.get())
        if hasattr(self, "scoreboard_bg_color_var"):
            self.scoreboard_bg_color_var.set(self.scoreboard_bg_color)
        if hasattr(self, "scoreboard_text_color_var"):
            self.scoreboard_text_color_var.set(self.scoreboard_text_color)
        if hasattr(self, "hall_buzzer_enabled_var"):
            self.hall_buzzer_enabled_var.set(self.hall_buzzer_enabled.get())

    def _refresh_settings_form(self):
        if not hasattr(self, "settings_window") or not self.settings_window.winfo_exists():
            return

        self.home_name_var.set(self.team_home_name)
        self.away_name_var.set(self.team_away_name)
        self.controller_title_var.set(self.controller_title.get())
        self.controller_width_var.set(self.controller_width.get())
        self.controller_height_var.set(self.controller_height.get())
        self.scoreboard_width_var.set(self.scoreboard_width.get())
        self.scoreboard_height_var.set(self.scoreboard_height.get())
        self.scoreboard_title_var.set(self.scoreboard_title)
        self.match_duration_var.set(self.match_duration_minutes.get())
        self.match_mode_var.set(self.match_mode.get())

        self.controller_bg_color_var.set(self.controller_bg_color)
        self.controller_header_color_var.set(self.controller_header_color)
        self.controller_card_color_var.set(self.controller_card_bg)
        self.controller_text_color_var.set(self.controller_text_color)
        self.scoreboard_bg_color_var.set(self.scoreboard_bg_color)
        self.scoreboard_text_color_var.set(self.scoreboard_text_color)
        self.hall_buzzer_enabled_var.set(self.hall_buzzer_enabled.get())
        self.settings_path_var.set(str(self.settings_path))

    def _prompt_load_settings_file(self):
        path = filedialog.askopenfilename(
            title="Einstellungen laden",
            filetypes=[("JSON Dateien", "*.json"), ("Alle Dateien", "*.*")],
        )
        if not path:
            return

        try:
            self._load_settings(path)
            self._set_mode(self.match_mode.get())
            self._set_team_names(self.team_home_name, self.team_away_name)
            self._apply_controller_colors()
            self.scoreboard.set_colors(self.scoreboard_bg_color, self.scoreboard_text_color)
            self.scoreboard.set_resolution(self.scoreboard_width.get(), self.scoreboard_height.get())
            self.scoreboard.set_board_title(self.scoreboard_title)
            self._refresh_settings_form()
            messagebox.showinfo("Einstellungen geladen", f"Die Datei wurde geladen:\n{path}")
        except Exception as exc:
            messagebox.showerror("Laden fehlgeschlagen", f"Die Einstellungen konnten nicht geladen werden: {exc}")

    def _prompt_save_settings_as(self):
        initial_dir = os.path.dirname(self.settings_path) if self.settings_path else os.getcwd()
        initial_file = os.path.basename(self.settings_path) if self.settings_path else "settings.json"
        path = filedialog.asksaveasfilename(
            title="Einstellungen speichern unter",
            defaultextension=".json",
            filetypes=[("JSON Dateien", "*.json"), ("Alle Dateien", "*.*")],
            initialdir=initial_dir,
            initialfile=initial_file,
        )
        if not path:
            return

        self.settings_path = Path(path)
        self.settings_path_var.set(str(self.settings_path))
        self._save_settings()
        messagebox.showinfo("Gespeichert", f"Einstellungen gespeichert unter:\n{path}")
        if hasattr(self, "scoreboard_title_var"):
            self.scoreboard_title_var.set(self.scoreboard_title)
        if hasattr(self, "match_duration_var"):
            self.match_duration_var.set(self.match_duration_minutes.get())
        if hasattr(self, "match_mode_var"):
            self.match_mode_var.set(self.match_mode.get())
        if hasattr(self, "controller_bg_color_var"):
            self.controller_bg_color_var.set(self.controller_bg_color)
        if hasattr(self, "controller_header_color_var"):
            self.controller_header_color_var.set(self.controller_header_color)
        if hasattr(self, "controller_card_color_var"):
            self.controller_card_color_var.set(self.controller_card_bg)
        if hasattr(self, "controller_text_color_var"):
            self.controller_text_color_var.set(self.controller_text_color)
        if hasattr(self, "hall_buzzer_enabled_var"):
            self.hall_buzzer_enabled_var.set(self.hall_buzzer_enabled.get())
        if hasattr(self, "controller_card_color_var"):
            self.controller_card_color_var.set(self.controller_card_bg)
        if hasattr(self, "scoreboard_bg_color_var"):
            self.scoreboard_bg_color_var.set(self.scoreboard_bg_color)
        if hasattr(self, "scoreboard_text_color_var"):
            self.scoreboard_text_color_var.set(self.scoreboard_text_color)

        self.root.geometry(f"{self.controller_width.get()}x{self.controller_height.get()}")
        self.root.minsize(self.controller_width.get(), self.controller_height.get())
        self.root.update_idletasks()

        self.scoreboard.set_colors(self.scoreboard_bg_color, self.scoreboard_text_color)
        self.scoreboard.set_resolution(self.scoreboard_width.get(), self.scoreboard_height.get())
        self.scoreboard.set_board_title(self.scoreboard_title)
        self._apply_controller_colors()
        self._update_scoreboard_display(self.timer_label['fg'], self.half_label['text'])
        self._save_settings()

    def _get_half_prefix(self):
        return "HALLE" if self.match_mode.get() in ("halle", "halle_turnier") else f"{self.current_half}. HALBZEIT"

    def _get_mode_display_text(self):
        if self.match_mode.get() == "halle":
            return "Modus: Halle (1 Halbzeit, Auto-Jingle)"
        if self.match_mode.get() == "halle_turnier":
            return "Modus: Hallen Turnier (1 Halbzeit, Auto-Jingle, CSV)"
        return "Modus: Normal (2 Halbzeiten)"

    def _update_mode_label(self):
        if hasattr(self, "mode_info_var"):
            self.mode_info_var.set(self._get_mode_display_text())

    def _update_half_ready_label(self):
        if not hasattr(self, "half_label"):
            return

        ready_text = f"{self._get_half_prefix()} BEREIT" if not self.running else self.half_label.cget("text")
        self.half_label.config(text=ready_text)

        if hasattr(self, "timer_label"):
            self._update_scoreboard_display(self.timer_label['fg'], ready_text)

    def _on_auto_jingle_toggled(self):
        self.auto_jingle_user_choice = self.auto_jingle_enabled.get()

    def _sync_auto_jingle_controls(self):
        mode = self.match_mode.get()
        auto_on = mode in ("halle", "halle_turnier")
        if self.auto_jingle_user_choice is None:
            self.auto_jingle_enabled.set(auto_on)
        if hasattr(self, "chk_auto_jingle"):
            label_text = "Auto-Jingle letzte Minute"
            if mode in ("halle", "halle_turnier"):
                label_text += " (empfohlen)"
            self.chk_auto_jingle.configure(state="normal", text=label_text)

    def _next_half(self):
        if self.match_mode.get() in ("halle", "halle_turnier") or self.current_half >= self.total_halves:
            return

        self.stop_jingle()
        self.stop_timer()
        self.current_half += 1
        duration = self._get_desired_match_seconds()
        self.seconds = duration * (self.current_half - 1)
        self.jingle_triggered = False
        self.current_match_duration_seconds = duration * self.current_half if self.match_mode.get() == "normal" else duration
        minutes = self.seconds // 60
        self.timer_label.config(text=f"{minutes}:{self.seconds % 60:02}", fg=RSK_BLUE)
        self._update_half_ready_label()

    def _open_settings_menu(self):
        if hasattr(self, "settings_window") and self.settings_window.winfo_exists():
            self.settings_window.lift()
            return

        self.settings_window = tk.Toplevel(self.root)
        self.settings_window.title("Einstellungen")
        self.settings_window.configure(bg=self.controller_bg_color)
        self.settings_window.geometry("620x760")

        self.home_name_var = tk.StringVar(value=self.team_home_name)
        self.away_name_var = tk.StringVar(value=self.team_away_name)
        self.controller_title_var = tk.StringVar(value=self.controller_title.get())
        self.controller_width_var = tk.IntVar(value=self.controller_width.get())
        self.controller_height_var = tk.IntVar(value=self.controller_height.get())
        self.scoreboard_width_var = tk.IntVar(value=self.scoreboard_width.get())
        self.scoreboard_height_var = tk.IntVar(value=self.scoreboard_height.get())
        self.scoreboard_title_var = tk.StringVar(value=self.scoreboard_title)
        self.match_duration_var = tk.IntVar(value=self.match_duration_minutes.get())
        self.match_mode_var = tk.StringVar(value=self.match_mode.get())
        self.hall_buzzer_enabled_var = tk.BooleanVar(value=self.hall_buzzer_enabled.get())

        self.controller_bg_color_var = tk.StringVar(value=self.controller_bg_color)
        self.controller_header_color_var = tk.StringVar(value=self.controller_header_color)
        self.controller_card_color_var = tk.StringVar(value=self.controller_card_bg)
        self.controller_text_color_var = tk.StringVar(value=self.controller_text_color)
        self.scoreboard_bg_color_var = tk.StringVar(value=self.scoreboard_bg_color)
        self.scoreboard_text_color_var = tk.StringVar(value=self.scoreboard_text_color)

        def color_row(parent, label_text, var, row, col):
            cell = tk.Frame(parent, bg=self.controller_bg_color)
            cell.grid(row=row, column=col, sticky="ew", padx=4, pady=3)
            tk.Label(cell, text=label_text, bg=self.controller_bg_color, fg=self.controller_text_color, font=("Arial", 10, "bold"))\
                .pack(anchor="w")
            entry_row = tk.Frame(cell, bg=self.controller_bg_color)
            entry_row.pack(fill="x", pady=(2, 0))
            tk.Entry(entry_row, textvariable=var, width=10).pack(side="left")

            def pick_color():
                color = colorchooser.askcolor(color=var.get())[1]
                if color:
                    var.set(color)

            tk.Button(entry_row, text="🎨", command=pick_color, bg=RSK_WHITE, relief="groove", width=3).pack(side="left", padx=4)

        content = tk.Frame(self.settings_window, bg=self.controller_bg_color)
        content.pack(fill="both", expand=True, padx=10, pady=10)

        settings_file_frame = tk.LabelFrame(content, text="Einstellungsdatei", bg=self.controller_bg_color, fg=self.controller_text_color)
        settings_file_frame.pack(fill="x", pady=(0, 8))

        file_path_row = tk.Frame(settings_file_frame, bg=self.controller_bg_color)
        file_path_row.pack(fill="x", padx=5, pady=4)
        tk.Label(file_path_row, text="Aktive Datei:", bg=self.controller_bg_color, fg=self.controller_text_color).pack(side="left")
        tk.Label(file_path_row, textvariable=self.settings_path_var, bg=self.controller_bg_color, fg="#666", anchor="w", wraplength=360, justify="left").pack(side="left", padx=5, fill="x", expand=True)

        file_btn_row = tk.Frame(settings_file_frame, bg=self.controller_bg_color)
        file_btn_row.pack(fill="x", padx=5, pady=(0, 6))
        tk.Button(file_btn_row, text="Laden...", command=self._prompt_load_settings_file, bg=self.controller_card_bg, fg=self.controller_text_color).pack(side="left", padx=4)
        tk.Button(file_btn_row, text="Speichern unter...", command=self._prompt_save_settings_as, bg=ACCENT_GREEN, fg=RSK_WHITE).pack(side="left", padx=4)

        controller_section = tk.LabelFrame(content, text="Steuerpult", bg=self.controller_bg_color, fg=self.controller_text_color)
        controller_section.pack(fill="x", pady=5)

        tk.Label(controller_section, text="Titel", bg=self.controller_bg_color, fg=self.controller_text_color).pack(anchor="w", padx=5, pady=(5, 2))
        tk.Entry(controller_section, textvariable=self.controller_title_var).pack(fill="x", padx=5)

        ctrl_res_row = tk.Frame(controller_section, bg=self.controller_bg_color)
        ctrl_res_row.pack(fill="x", pady=5)
        tk.Label(ctrl_res_row, text="Auflösung (BxH)", bg=self.controller_bg_color, fg=self.controller_text_color).pack(side="left", padx=5)
        tk.Entry(ctrl_res_row, width=6, textvariable=self.controller_width_var).pack(side="left")
        tk.Label(ctrl_res_row, text="x", bg=self.controller_bg_color, fg=self.controller_text_color).pack(side="left", padx=3)
        tk.Entry(ctrl_res_row, width=6, textvariable=self.controller_height_var).pack(side="left")

        duration_row = tk.Frame(controller_section, bg=self.controller_bg_color)
        duration_row.pack(fill="x", pady=5)
        tk.Label(duration_row, text="Spielzeit (Minuten)", bg=self.controller_bg_color, fg=self.controller_text_color).pack(side="left", padx=5)
        tk.Entry(duration_row, width=6, textvariable=self.match_duration_var).pack(side="left")

        scoreboard_section = tk.LabelFrame(content, text="Anzeigetafel", bg=self.controller_bg_color, fg=self.controller_text_color)
        scoreboard_section.pack(fill="x", pady=5)
        tk.Label(scoreboard_section, text="Titel", bg=self.controller_bg_color, fg=self.controller_text_color).pack(anchor="w", padx=5, pady=(5, 2))
        tk.Entry(scoreboard_section, textvariable=self.scoreboard_title_var).pack(fill="x", padx=5)
        tk.Label(scoreboard_section, text="Heim (links)", bg=self.controller_bg_color, fg=self.controller_text_color).pack(anchor="w", padx=5, pady=2)
        tk.Entry(scoreboard_section, textvariable=self.home_name_var).pack(fill="x", padx=5)
        tk.Label(scoreboard_section, text="Gast (rechts)", bg=self.controller_bg_color, fg=self.controller_text_color).pack(anchor="w", padx=5, pady=2)
        tk.Entry(scoreboard_section, textvariable=self.away_name_var).pack(fill="x", padx=5, pady=(0, 5))

        board_res_row = tk.Frame(scoreboard_section, bg=self.controller_bg_color)
        board_res_row.pack(fill="x", pady=5)
        tk.Label(board_res_row, text="Auflösung (BxH)", bg=self.controller_bg_color, fg=self.controller_text_color).pack(side="left", padx=5)
        tk.Entry(board_res_row, width=6, textvariable=self.scoreboard_width_var).pack(side="left")
        tk.Label(board_res_row, text="x", bg=self.controller_bg_color, fg=self.controller_text_color).pack(side="left", padx=3)
        tk.Entry(board_res_row, width=6, textvariable=self.scoreboard_height_var).pack(side="left")

        mode_section = tk.LabelFrame(scoreboard_section, text="Spielmodus", bg=self.controller_bg_color, fg=self.controller_text_color)
        mode_section.pack(fill="x", pady=5, padx=5)
        tk.Radiobutton(
            mode_section,
            text="Normal (2 Halbzeiten, manuell)",
            variable=self.match_mode_var,
            value="normal",
            bg=self.controller_bg_color,
            fg=self.controller_text_color,
            anchor="w"
        ).pack(fill="x", pady=2)
        tk.Radiobutton(
            mode_section,
            text="Halle (1 Halbzeit, Jingle & Stop automatisch)",
            variable=self.match_mode_var,
            value="halle",
            bg=self.controller_bg_color,
            fg=self.controller_text_color,
            anchor="w"
        ).pack(fill="x", pady=2)
        tk.Radiobutton(
            mode_section,
            text="Hallen Turniermodus (CSV Import)",
            variable=self.match_mode_var,
            value="halle_turnier",
            bg=self.controller_bg_color,
            fg=self.controller_text_color,
            anchor="w"
        ).pack(fill="x", pady=2)

        tk.Checkbutton(
            mode_section,
            text="Hupe am Spielende (Hallenmodus)",
            variable=self.hall_buzzer_enabled_var,
            bg=self.controller_bg_color,
            fg=self.controller_text_color,
            anchor="w",
            relief="flat",
            cursor="hand2",
        ).pack(fill="x", pady=(4, 0))

        csv_row = tk.Frame(scoreboard_section, bg=self.controller_bg_color)
        csv_row.pack(fill="x", padx=5, pady=(2, 0))
        tk.Label(csv_row, text="CSV Import (Turnier)", bg=self.controller_bg_color, fg=self.controller_text_color).pack(side="left")
        self.csv_load_btn = tk.Button(csv_row, text="Datei wählen", command=self.load_tournament_csv, bg=ACCENT_GREEN, fg=RSK_WHITE)
        self.csv_load_btn.pack(side="left", padx=6)
        tk.Label(csv_row, textvariable=self.csv_status_var, bg=self.controller_bg_color, fg="#666").pack(side="left")

        section_colors = tk.LabelFrame(content, text="Farben (kompakt)", bg=self.controller_bg_color, fg=self.controller_text_color)
        section_colors.pack(fill="x", pady=5)

        colors_grid = tk.Frame(section_colors, bg=self.controller_bg_color)
        colors_grid.pack(fill="x", padx=2, pady=2)
        colors_grid.columnconfigure((0, 1), weight=1)

        color_rows = [
            ("Steuerpult Hintergrund", self.controller_bg_color_var),
            ("Steuerpult Kopfzeile", self.controller_header_color_var),
            ("Karten Hintergrund", self.controller_card_color_var),
            ("Steuerpult Text", self.controller_text_color_var),
            ("Anzeigetafel Hintergrund", self.scoreboard_bg_color_var),
            ("Anzeigetafel Text", self.scoreboard_text_color_var),
        ]

        for idx, (label_text, var) in enumerate(color_rows):
            row = idx // 2
            col = idx % 2
            color_row(colors_grid, label_text, var, row, col)

        btn_row = tk.Frame(content, bg=self.controller_bg_color)
        btn_row.pack(fill="x", pady=10)
        tk.Button(btn_row, text="Speichern", command=self._apply_settings, bg=ACCENT_GREEN, fg=RSK_WHITE).pack(side="right", padx=5)
        tk.Button(btn_row, text="Schließen", command=self.settings_window.destroy, bg=ACCENT_RED, fg=RSK_WHITE).pack(side="right", padx=5)
        tk.Button(
            btn_row,
            text="Zurücksetzen",
            command=self._reset_settings_to_defaults,
            bg=self.controller_card_bg,
            fg=self.controller_text_color,
        ).pack(side="left", padx=5)
        
    def _create_card_scoreboard_option_top(self):
        self.scoreboard_option_card = tk.Frame(self.root, bg=self.controller_card_bg, bd=1, relief="flat", padx=10, pady=6)
        self.scoreboard_option_card.pack(fill="x", pady=(0, 8), padx=10)

        row = tk.Frame(self.scoreboard_option_card, bg=self.controller_card_bg)
        row.pack(fill="x")

        tk.Label(row, text="Anzeigetafel", font=("Arial", 10, "bold"), bg=self.controller_card_bg, fg=RSK_BLUE).pack(side="left")

        self.scoreboard_toggle = tk.Checkbutton(
            row,
            text="Fenster anzeigen",
            variable=self.scoreboard_enabled,
            bg=self.controller_card_bg,
            font=("Arial", 10),
            fg=self.controller_text_color,
            relief="flat",
            cursor="hand2"
        )
        self.scoreboard_toggle.pack(side="right")

        self.mode_label = tk.Label(
            self.scoreboard_option_card,
            textvariable=self.mode_info_var,
            font=("Arial", 10, "bold"),
            bg=self.controller_card_bg,
            fg=RSK_BLUE,
            anchor="w"
        )
        self.mode_label.pack(fill="x", pady=(4, 0))
    
    def _toggle_scoreboard(self, *args):
        if self.scoreboard_enabled.get():
            self.scoreboard.show()
            self._update_scoreboard_display(self.timer_label['fg'], self.half_label['text'])
        else:
            self.scoreboard.hide()

    def _handle_scoreboard_closed(self):
        if self.scoreboard_enabled.get():
            self.scoreboard_enabled.set(False)

    def _apply_controller_colors(self):
        self.root.configure(bg=self.controller_bg_color)
        self.main_container.configure(bg=self.controller_bg_color)
        self.header_frame.configure(bg=self.controller_header_color)
        self.header_label.configure(bg=self.controller_header_color, fg=self.scoreboard_text_color)
        self.settings_btn.configure(bg=self.controller_header_color, fg=self.scoreboard_text_color)

        for widget in [self.scoreboard_option_card, self.timer_card, self.score_card, self.audio_card]:
            widget.configure(bg=self.controller_card_bg)
            self._recolor_container(widget, self.controller_card_bg, self.controller_text_color)

        if hasattr(self, "mode_label"):
            self.mode_label.configure(bg=self.controller_card_bg, fg=RSK_BLUE)

    def _set_team_names(self, home, away):
        old_home = self.home_title_label.cget("text")
        old_away = self.away_title_label.cget("text")
        self.team_home_name = home or old_home
        self.team_away_name = away or old_away

        self.scores = {
            self.team_home_name: self.scores.get(old_home, 0),
            self.team_away_name: self.scores.get(old_away, 0)
        }

        self.home_title_label.config(text=self.team_home_name)
        self.away_title_label.config(text=self.team_away_name)

        self.scoreboard.set_team_names(self.team_home_name, self.team_away_name)
        self._update_scoreboard_display(self.timer_label['fg'], self.half_label['text'])

    def _apply_settings(self):
        self.controller_bg_color = self.controller_bg_color_var.get()
        self.controller_header_color = self.controller_header_color_var.get()
        self.controller_card_bg = self.controller_card_color_var.get()
        self.controller_text_color = self.controller_text_color_var.get()
        self.scoreboard_bg_color = self.scoreboard_bg_color_var.get()
        self.scoreboard_text_color = self.scoreboard_text_color_var.get()

        self._set_mode(self.match_mode_var.get())

        self._set_team_names(self.home_name_var.get().strip(), self.away_name_var.get().strip())
        self.scoreboard_title = self.scoreboard_title_var.get().strip() or self.scoreboard_title
        self.scoreboard.set_board_title(self.scoreboard_title)

        new_controller_title = self.controller_title_var.get().strip() or self.controller_title.get()
        self.controller_title.set(new_controller_title)
        self.root.title("Soccer Clock")

        try:
            desired_minutes = max(1, int(self.match_duration_var.get()))
        except Exception:
            desired_minutes = self.match_duration_minutes.get()
        self.match_duration_minutes.set(desired_minutes)
        if not self.running:
            self.current_match_duration_seconds = desired_minutes * 60

        try:
            cw = max(300, int(self.controller_width_var.get()))
            ch = max(400, int(self.controller_height_var.get()))
        except Exception:
            cw, ch = self.controller_width.get(), self.controller_height.get()

        self.controller_width.set(cw)
        self.controller_height.set(ch)
        self.root.geometry(f"{cw}x{ch}")
        self.root.minsize(cw, ch)
        self.root.update_idletasks()

        try:
            sw = max(300, int(self.scoreboard_width_var.get()))
            sh = max(200, int(self.scoreboard_height_var.get()))
        except Exception:
            sw, sh = self.scoreboard_width.get(), self.scoreboard_height.get()

        self.scoreboard_width.set(sw)
        self.scoreboard_height.set(sh)
        self.scoreboard.set_resolution(sw, sh)

        self._apply_controller_colors()
        self.scoreboard.set_colors(self.scoreboard_bg_color, self.scoreboard_text_color)

        self.hall_buzzer_enabled.set(bool(self.hall_buzzer_enabled_var.get()))

        self._save_settings()

        if hasattr(self, "settings_window") and self.settings_window.winfo_exists():
            self.settings_window.destroy()

    def _update_tournament_controls(self):
        if not hasattr(self, "tournament_row"):
            return

        is_turnier = self.match_mode.get() == "halle_turnier"

        if is_turnier:
            if not self.tournament_row.winfo_manager():
                self.tournament_row.pack(fill="x", padx=10, pady=(5, 0))
            combobox_state = "readonly" if self.tournament_matches else "disabled"
            self.match_number_cb.configure(state=combobox_state)
        else:
            if self.tournament_row.winfo_manager():
                self.tournament_row.pack_forget()
            self.match_number_cb.configure(state="disabled")

    def load_tournament_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV Dateien", "*.csv")])
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                matches = []
                for row in reader:
                    nr = (row.get("Nr") or "").strip()
                    team1 = (row.get("Team1") or "").strip()
                    team2 = (row.get("Team2") or "").strip()
                    if not nr:
                        continue
                    matches.append({"Nr": nr, "Team1": team1, "Team2": team2})
        except Exception as exc:
            messagebox.showerror("CSV Import fehlgeschlagen", f"Die Datei konnte nicht geladen werden: {exc}")
            return

        if not matches:
            messagebox.showwarning("Keine Daten", "In der gewählten CSV wurden keine Spiele gefunden.")
            return

        self.tournament_matches = matches
        numbers = [m["Nr"] for m in matches]
        self.match_number_cb.configure(values=numbers, state="readonly")
        self.match_number_var.set(numbers[0])
        self.csv_status_var.set(f"{len(matches)} Spiele geladen")
        self._apply_selected_match()

    def _apply_selected_match(self, event=None):
        if not self.tournament_matches:
            return

        selected_nr = self.match_number_var.get().strip()
        match = next((m for m in self.tournament_matches if m["Nr"] == selected_nr), None)
        if not match:
            messagebox.showwarning("Unbekannte Spielnummer", "Bitte wähle eine gültige Spielnummer aus der CSV.")
            return

        self._set_team_names(match.get("Team1", ""), match.get("Team2", ""))


    def _create_card_timer(self, parent):
        self.timer_card = tk.Frame(parent, bg=self.controller_card_bg, bd=1, relief="flat")
        self.timer_card.pack(fill="x", pady=(0, 10), ipady=5)

        self.half_label = tk.Label(self.timer_card, text="SPIEL BEREIT", font=("Arial", 12, "bold"), bg=self.controller_card_bg, fg="#888")
        self.half_label.pack(pady=(10, 0))

        self.timer_label = tk.Label(self.timer_card, text="0:00", font=("Impact", 75), bg=self.controller_card_bg, fg=RSK_BLUE)
        self.timer_label.pack(pady=0)

        btn_frame = tk.Frame(self.timer_card, bg=self.controller_card_bg)
        btn_frame.pack(pady=10)
        self._big_btn(btn_frame, "START", self.start_timer, ACCENT_GREEN).pack(side="left", padx=5)
        self._big_btn(btn_frame, "STOPP", self.stop_timer, ACCENT_RED).pack(side="left", padx=5)

        sub_btn_frame = tk.Frame(self.timer_card, bg=self.controller_card_bg)
        sub_btn_frame.pack(pady=(0, 10))

        tk.Label(sub_btn_frame, text="Länge:", font=("Arial", 10), bg=self.controller_card_bg, fg="#666").pack(side="left", padx=5)

        self.duration_input = tk.Spinbox(
            sub_btn_frame,
            from_=1, to=120,
            textvariable=self.match_duration_minutes,
            width=3,
            font=("Arial", 10),
            relief="flat"
        )
        self.duration_input.pack(side="left")
        tk.Label(sub_btn_frame, text="Min", font=("Arial", 10), bg=self.controller_card_bg, fg="#666").pack(side="left", padx=(0, 10))

        self._text_btn(sub_btn_frame, "Reset", self.reset_timer).pack(side="left", padx=5)
        self.next_half_btn = self._text_btn(sub_btn_frame, "Nächste Halbzeit", self._next_half)
        self.next_half_btn.pack(side="left", padx=5)

    def _create_card_score(self, parent):
        self.score_card = tk.Frame(parent, bg=self.controller_card_bg, bd=1, relief="flat")
        self.score_card.pack(fill="x", pady=(0, 10), ipady=10)
        self.score_grid = tk.Frame(self.score_card, bg=self.controller_card_bg)
        self.score_grid.pack()

        # NEU: Text auf Spielplan Links geändert
        home_frame = tk.Frame(self.score_grid, bg=self.controller_card_bg)
        home_frame.grid(row=0, column=0, padx=10)
        self.home_title_label = tk.Label(home_frame, text=self.scoreboard.team_home_name.get(), font=("Arial", 14, "bold"), bg=self.controller_card_bg, fg=RSK_BLUE)
        self.home_title_label.pack()
        self.lbl_score_home = tk.Label(home_frame, text="0", font=("Arial", 50, "bold"), bg=self.controller_card_bg, fg=self.controller_text_color)
        self.lbl_score_home.pack()
        h_btns = tk.Frame(home_frame, bg=self.controller_card_bg)
        h_btns.pack()
        self._circle_btn(h_btns, "+", lambda: self.update_score("Home", 1), RSK_BLUE)
        self._circle_btn(h_btns, "-", lambda: self.update_score("Home", -1), "#999")

        self.score_divider_label = tk.Label(self.score_grid, text=":", font=("Arial", 40, "bold"), bg=self.controller_card_bg, fg="#ccc")
        self.score_divider_label.grid(row=0, column=1, pady=20)

        # NEU: Text auf Spielplan Rechts geändert
        away_frame = tk.Frame(self.score_grid, bg=self.controller_card_bg)
        away_frame.grid(row=0, column=2, padx=10)
        self.away_title_label = tk.Label(away_frame, text=self.scoreboard.team_away_name.get(), font=("Arial", 14, "bold"), bg=self.controller_card_bg, fg="#555")
        self.away_title_label.pack()
        self.lbl_score_away = tk.Label(away_frame, text="0", font=("Arial", 50, "bold"), bg=self.controller_card_bg, fg=self.controller_text_color)
        self.lbl_score_away.pack()
        a_btns = tk.Frame(away_frame, bg=self.controller_card_bg)
        a_btns.pack()
        self._circle_btn(a_btns, "+", lambda: self.update_score("Away", 1), RSK_BLUE)
        self._circle_btn(a_btns, "-", lambda: self.update_score("Away", -1), "#999")

        self.tournament_row = tk.Frame(self.score_card, bg=self.controller_card_bg)
        self.tournament_row.pack(fill="x", padx=10, pady=(5, 0))
        tk.Label(self.tournament_row, text="Hallen Turnier Nr:", bg=self.controller_card_bg, fg=self.controller_text_color).pack(side="left")
        self.match_number_cb = ttk.Combobox(self.tournament_row, textvariable=self.match_number_var, state="disabled", width=8)
        self.match_number_cb.pack(side="left", padx=4)
        self.match_number_cb.bind("<<ComboboxSelected>>", self._apply_selected_match)
        tk.Label(self.tournament_row, textvariable=self.csv_status_var, bg=self.controller_card_bg, fg="#666").pack(side="left", padx=6)

    def _create_card_audio(self, parent):
        self.audio_card = tk.Frame(parent, bg=self.controller_card_bg, bd=1, relief="flat")
        self.audio_card.pack(fill="x", pady=(0, 0), ipady=5)

        self.audio_top_frame = tk.Frame(self.audio_card, bg=self.controller_card_bg)
        self.audio_top_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(self.audio_top_frame, text="JINGLE / AUDIO", font=("Arial", 12, "bold"), bg=self.controller_card_bg, fg=RSK_BLUE).pack(anchor="w")
        self.file_label = tk.Label(self.audio_top_frame, text="(Kein Jingle gewählt)", font=("Arial", 9, "italic"), bg=self.controller_card_bg, fg="#888", anchor="w")
        self.file_label.pack(fill="x")

        self.auto_jingle_frame = tk.Frame(self.audio_card, bg=self.controller_card_bg)
        self.auto_jingle_frame.pack(fill="x", padx=10, pady=(0, 5))

        self.chk_auto_jingle = tk.Checkbutton(
            self.auto_jingle_frame,
            text="Auto-Jingle letzte Minute",
            variable=self.auto_jingle_enabled,
            command=self._on_auto_jingle_toggled,
            bg=self.controller_card_bg,
            font=("Arial", 10),
            fg=self.controller_text_color,
            relief="flat",
            cursor="hand2"
        )
        self.chk_auto_jingle.pack(anchor="w")


        self.audio_ctrl_frame = tk.Frame(self.audio_card, bg=self.controller_card_bg)
        self.audio_ctrl_frame.pack(pady=5)
        self._icon_btn(self.audio_ctrl_frame, "📂 Wählen", self.choose_jingle, "#6c757d").pack(side="left", padx=2)
        self._icon_btn(self.audio_ctrl_frame, "▶ PLAY", self.play_jingle, ACCENT_GREEN).pack(side="left", padx=2)
        self._icon_btn(self.audio_ctrl_frame, "■ STOP", self.stop_jingle, ACCENT_RED).pack(side="left", padx=2)

        self.audio_vis_frame = tk.Frame(self.audio_card, bg=self.controller_card_bg, padx=10, pady=5)
        self.audio_vis_frame.pack(fill="x")
        self.wave_canvas = tk.Canvas(self.audio_vis_frame, height=80, bg="#FAFAFA", highlightthickness=0)
        self.wave_canvas.pack(fill="x")

        leg = tk.Frame(self.audio_vis_frame, bg=self.controller_card_bg)
        leg.pack(fill="x", pady=2)
        tk.Label(leg, text="■ Pause", fg=ACCENT_GREEN, bg=self.controller_card_bg, font=("Arial", 8)).pack(side="left", padx=5)
        tk.Label(leg, text="■ Laut", fg=ACCENT_RED, bg=self.controller_card_bg, font=("Arial", 8)).pack(side="left", padx=5)

        style = ttk.Style()
        style.theme_use('default')
        style.configure("RSK.Horizontal.TProgressbar", thickness=5, background=RSK_BLUE, troughcolor="#E0E0E0", borderwidth=0)
        self.progress = ttk.Progressbar(
            self.audio_vis_frame,
            orient="horizontal",
            mode="determinate",
            style="RSK.Horizontal.TProgressbar"
        )
        self.progress.pack(fill="x", pady=(5, 0))


    def _generate_buzzer_wave(self, path, duration=1.0, freq=600):
        sample_rate = 22050
        amplitude = 32767
        total_samples = int(sample_rate * duration)
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with wave.open(str(path), "w") as wav_file:
            wav_file.setparams((1, 2, sample_rate, total_samples, "NONE", "not compressed"))
            for i in range(total_samples):
                angle = 2 * math.pi * freq * (i / sample_rate)
                value = int(amplitude * 0.35 * math.sin(angle))
                wav_file.writeframes(struct.pack("<h", value))

    def _ensure_buzzer_sound(self):
        if self._buzzer_sound:
            return self._buzzer_sound

        try:
            buzzer_path = Path(self.settings_path).with_name("hall_buzzer.wav")
            if not buzzer_path.exists():
                self._generate_buzzer_wave(buzzer_path)
            self._buzzer_sound = pygame.mixer.Sound(str(buzzer_path))
        except Exception:
            self._buzzer_sound = None

        return self._buzzer_sound

    def _play_hall_buzzer(self):
        if not self.hall_buzzer_enabled.get():
            return

        sound = self._ensure_buzzer_sound()
        if sound:
            try:
                sound.play()
            except Exception:
                pass

    def _get_desired_match_seconds(self):
        try:
            minutes = self.match_duration_minutes.get()
            return max(1, minutes) * 60
        except Exception:
            return 45 * 60

    # ----------------------------------------------------
    # --- TIMER LOGIK ---
    # ----------------------------------------------------
    def start_timer(self):
        if not self.running:
            if self.seconds == 0:
                self.current_match_duration_seconds = self._get_desired_match_seconds()
                self.jingle_triggered = False

            self.half_label.config(text=f"{self._get_half_prefix()} LÄUFT")
            if self.seconds < self.current_match_duration_seconds:
                self.timer_label.config(fg=RSK_BLUE)

            self.running = True
            if self.scoreboard_enabled.get():
                self.scoreboard.show()
            self._tick()
            
    def stop_timer(self):
        if self.running:
            self.running = False
            pause_text = f"{self._get_half_prefix()} PAUSE"
            self.half_label.config(text=pause_text)
            self._update_scoreboard_display(self.timer_label['fg'], pause_text)
        
        if not self.scoreboard_enabled.get() and self.seconds < self.current_match_duration_seconds:
            self.scoreboard.hide()


    def reset_timer(self):
        self.stop_jingle()
        self.stop_timer()
        self.seconds = 0
        self.jingle_triggered = False
        self.current_half = 1
        self.current_match_duration_seconds = self._get_desired_match_seconds()

        self.timer_label.config(text="0:00", fg=RSK_BLUE)
        self._update_half_ready_label()

        self.scores = {self.team_home_name: 0, self.team_away_name: 0}
        self.lbl_score_home.config(text="0")
        self.lbl_score_away.config(text="0")
        
        self._update_scoreboard_display(RSK_BLUE, "SPIEL BEREIT") 

    
    def _tick(self):
        if self.running:
            self.seconds += 1
            minutes = self.seconds // 60
            seconds_part = self.seconds % 60

            target_time = self.current_match_duration_seconds
            color_to_use = RSK_BLUE
            half_text = f"{self._get_half_prefix()} LÄUFT"

            if self.match_mode.get() in ("halle", "halle_turnier"):
                last_minute_threshold = target_time - 60
                if self.seconds >= last_minute_threshold:
                    color_to_use = ACCENT_RED

                    if not self.jingle_triggered and self.jingle_paths and self.auto_jingle_enabled.get():
                        path_to_play = random.choice(self.jingle_paths)
                        self.start_jingle_load_and_play(path_to_play)
                        self.jingle_triggered = True

                if self.seconds >= target_time:
                    self.running = False
                    self.stop_jingle()
                    end_color = ACCENT_RED if color_to_use == ACCENT_RED else "#FF8C00"
                    time_str = f"{minutes}:{seconds_part:02}"
                    self.timer_label.config(text=time_str, fg=end_color)
                    self.half_label.config(text="SPIEL ENDE")

                    self._update_scoreboard_display(end_color, "SPIEL ENDE")
                    self._play_hall_buzzer()
                    return
            else:
                if self.seconds >= target_time:
                    color_to_use = ACCENT_RED

            time_str = f"{minutes}:{seconds_part:02}"
            self.timer_label.config(text=time_str, fg=color_to_use)

            self._update_scoreboard_display(color_to_use, half_text)

            self._after_id = self.root.after(1000, self._tick)

    def _update_scoreboard_display(self, time_color, half_text):
        minutes = self.seconds // 60
        seconds_part = self.seconds % 60
        time_str = f"{minutes:02}:{seconds_part:02}"

        self.scoreboard.update(
            time_str,
            half_text,
            self.scores[self.team_home_name],
            self.scores[self.team_away_name],
            time_color
        )


    def update_score(self, team_key, val):
        # Aktualisiert den richtigen Team-Namen, unabhängig davon, ob es Heim/Away oder Links/Rechts ist
        if team_key == "Home":
            t_name = self.team_home_name
            lbl = self.lbl_score_home
        else:
            t_name = self.team_away_name
            lbl = self.lbl_score_away
            
        self.scores[t_name] = max(0, self.scores[t_name] + val)
        lbl.config(text=str(self.scores[t_name]))
            
        self._update_scoreboard_display(self.timer_label['fg'], self.half_label['text']) 

    def toggle_timer(self):
        if self.running:
            self.stop_timer()
        else:
            self.start_timer()

    # --- AUDIO/VISUALISIERUNG LOGIK (Unverändert) ---
    def choose_jingle(self):
        paths = filedialog.askopenfilenames(filetypes=[("WAV Datei", "*.wav")])
        if not paths: return
        self.jingle_paths = list(paths)

        count = len(self.jingle_paths)
        self.file_label.config(text=f"{count} Jingle{'s' if count != 1 else ''} geladen")
        
        if self.jingle_paths:
            path_to_analyze = self.jingle_paths[0]
            self.current_jingle_path = path_to_analyze 
            self.wave_canvas.delete("all")
            self.wave_canvas.create_text(self.wave_canvas.winfo_width()/2, 40, text="Lade Visualisierungsdaten...", fill="#999")
            threading.Thread(target=self._analyze_wav_thread, args=(path_to_analyze, False), daemon=True).start()
        else:
            self.wave_reduced = None
            self.wave_duration = 0
            self.wave_canvas.delete("all")

    def _perform_wav_analysis(self, path):
        samples = []
        duration = 0
        try:
            with wave.open(path, "rb") as wf:
                n_channels = wf.getnchannels()
                n_frames = wf.getnframes()
                duration = n_frames / float(wf.getframerate())
                
                step = max(1, n_frames // 3000) 
                raw = wf.readframes(n_frames)
                sampwidth = wf.getsampwidth()
                
                if sampwidth == 4:
                    fmt_code = 'f' 
                    max_val = 1.0 
                elif sampwidth == 2:
                    fmt_code = 'h'
                    max_val = float(2 ** 15)
                elif sampwidth == 1:
                    fmt_code = 'B'
                    max_val = float(2 ** 7)
                else:
                    return [], 0 
                
                total = n_frames * n_channels
                fmt = f"<{total}{fmt_code}"
                unpacked = struct.unpack(fmt, raw)
                
                simple_data = unpacked[::n_channels*step] if n_channels > 1 else unpacked[::step]
                
                samples = []
                if sampwidth == 1:
                    samples = [abs(s - 128) / max_val for s in simple_data]
                else:
                    samples = [abs(s) / max_val for s in simple_data]
                
        except Exception as e: 
             return [], 0
        
        reduced = self._reduce_samples(samples, 400)
        return reduced, duration

    def _analyze_wav_thread(self, path, start_audio_after_analysis):
        reduced, duration = self._perform_wav_analysis(path)
        self.root.after(0, lambda: self._finish_loading(reduced, duration, path, start_audio_after_analysis))


    def _reduce_samples(self, samples, count):
        if not samples: return []
        block = max(1, len(samples) // count)
        reduced = []
        for i in range(0, len(samples), block):
            chunk = samples[i:i+block]
            if chunk: reduced.append(max(chunk))
        return reduced

    def _finish_loading(self, reduced_data, duration, path, start_audio):
        self.wave_reduced = reduced_data
        self.wave_duration = duration
        self.current_jingle_path = path
        
        if self.wave_duration == 0 and path:
            try:
                pygame.mixer.music.load(path)
                pygame_duration = pygame.mixer.music.get_length() 
                if pygame_duration > 0:
                    self.wave_duration = pygame_duration / 1000 
            except Exception:
                pass 

        if reduced_data and max(reduced_data) > 0.001:
            self.max_amp_scale = max(reduced_data)
        else:
            self.max_amp_scale = 1.0 
            
        self._draw_waveform()
        
        if not reduced_data and self.wave_duration > 0:
            self.wave_canvas.delete("all")
            self.wave_canvas.create_text(self.wave_canvas.winfo_width()/2, 40, 
                                         text="Visualisierung nicht unterstützt (Dateiformat)", 
                                         font=("Arial", 10, "bold"), fill=ACCENT_RED)

        if start_audio:
            self._start_audio_playback(path)

    def start_jingle_load_and_play(self, path):
        self.stop_jingle()
        self.wave_canvas.delete("all")
        self.wave_canvas.create_text(self.wave_canvas.winfo_width()/2, 40, text="Lade Zufallsaudio...", fill="#999")
        threading.Thread(target=self._analyze_wav_thread, args=(path, True), daemon=True).start()

    def _draw_waveform(self):
        self.wave_canvas.delete("all")
        w = self.wave_canvas.winfo_width()
        h = self.wave_canvas.winfo_height()
        mid = h / 2
        if not self.wave_reduced: return
        bar_w = w / len(self.wave_reduced)
        
        scale_factor = self.max_amp_scale if self.max_amp_scale > 0 else 1.0
        
        for i, val in enumerate(self.wave_reduced):
            val_amp = min(1.0, val / scale_factor) 
            bar_h = val_amp * (h / 2) * 0.90
            
            if val_amp < 0.15: color = "#DDD"
            elif val_amp < 0.30: color = ACCENT_GREEN
            elif val_amp < 0.60: color = "#ffc107"
            else: color = ACCENT_RED
            self.wave_canvas.create_rectangle(i * bar_w, mid - bar_h, (i * bar_w) + bar_w, mid + bar_h, fill=color, outline="")

    def _on_resize(self, event):
        if self.wave_reduced: self._draw_waveform()

    def _start_audio_playback(self, path_to_play):
        try:
            pygame.mixer.music.load(path_to_play)
            pygame.mixer.music.play()
            self.jingle_playing = True
            self.jingle_start_time = time.time()
            self._update_loop()
        except Exception as e: messagebox.showerror("Fehler beim Abspielen", str(e))

    def play_jingle(self):
        if not self.jingle_paths: return
        path_to_play = random.choice(self.jingle_paths) 
        self.start_jingle_load_and_play(path_to_play)

    def stop_jingle(self):
        try: pygame.mixer.music.stop()
        except: pass
        self.jingle_playing = False
        self.progress['value'] = 0
        self.wave_canvas.delete("playhead")

    def _update_loop(self):
        if not self.jingle_playing: return
        if not pygame.mixer.music.get_busy():
            self.stop_jingle()
            return
        
        elapsed = time.time() - self.jingle_start_time
        dur = self.wave_duration if self.wave_duration > 0 else 1
        perc = (elapsed / dur) * 100
        self.progress['value'] = perc
        w = self.wave_canvas.winfo_width()
        x = (elapsed / dur) * w
        self.wave_canvas.delete("playhead")
        self.wave_canvas.create_line(x, 0, x, 200, fill=RSK_BLUE, width=3, tags="playhead")
        self.root.after(50, self._update_loop)

if __name__ == "__main__":
    root = tk.Tk()
    app = FussballTimer(root)
    root.mainloop()
