import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pygame
import os
import time
import wave
import struct
import threading
import random 

# --- FARBPALETTE FC RSK FREYBURG ---
RSK_BLUE = "#00529F"
RSK_WHITE = "#FFFFFF"
BG_COLOR = "#F0F2F5"
TEXT_COLOR = "#333333"
ACCENT_GREEN = "#28a745"
ACCENT_RED = "#dc3545"

# ====================================================================
# --- KLASSE: ANZEIGETAFEL-FENSTER (BLAU-WEISS, OHNE STATUS) ---
# ====================================================================

class ScoreboardDisplay:
    """Repräsentiert das separate Anzeigetafel-Fenster mit blau-weißem Schema."""
    def __init__(self, master):
        self.window = tk.Toplevel(master) 
        self.window.title("Anzeigetafel - FC RSK Freyburg")
        self.window.geometry("1024x576") 
        self.window.configure(bg=RSK_BLUE) 
        self.window.protocol("WM_DELETE_WINDOW", self.hide) 

        # Variablen für die Anzeige
        self.time_str = tk.StringVar(value="00:00")
        self.home_score_str = tk.StringVar(value="0")
        self.away_score_str = tk.StringVar(value="0")
        
        # NEU: Teamnamen aktualisiert
        self.team_home_name = "Spielplan Links"
        self.team_away_name = "Spielplan Rechts"
        
        self.create_widgets()
        self.window.withdraw() 

    def create_widgets(self):
        main_frame = tk.Frame(self.window, bg=RSK_BLUE, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=0) 
        main_frame.grid_columnconfigure(2, weight=1)
        main_frame.grid_rowconfigure(0, weight=1) 
        main_frame.grid_rowconfigure(1, weight=3) 
        main_frame.grid_rowconfigure(2, weight=1) 

        # --- TITEL (GANZ OBEN) ---
        title_frame = tk.Frame(main_frame, bg=RSK_BLUE)
        title_frame.grid(row=0, column=0, columnspan=3, pady=(0, 5), sticky="n")
        tk.Label(title_frame, text="FC RSK FREYBURG", font=("Helvetica", 28, "bold"), bg=RSK_BLUE, fg=RSK_WHITE).pack() 
        
        # --- SPIELSTAND - HOME (Spielplan Links) ---
        home_frame = tk.Frame(main_frame, bg=RSK_BLUE)
        home_frame.grid(row=1, column=0, sticky="nsew")
        tk.Label(home_frame, text=self.team_home_name, font=("Arial", 22, "bold"), bg=RSK_BLUE, fg=RSK_WHITE).pack(pady=5)
        self.lbl_score_home = tk.Label(home_frame, textvariable=self.home_score_str, font=("Impact", 200), bg=RSK_BLUE, fg=RSK_WHITE)
        self.lbl_score_home.pack(fill="both", expand=True)

        # --- TRENNER (DOPPELPUNKT) ---
        tk.Label(main_frame, text=":", font=("Impact", 200), bg=RSK_BLUE, fg="#4477BB").grid(row=1, column=1, sticky="nsew", padx=10) 
        
        # --- SPIELSTAND - AWAY (Spielplan Rechts) ---
        away_frame = tk.Frame(main_frame, bg=RSK_BLUE)
        away_frame.grid(row=1, column=2, sticky="nsew")
        tk.Label(away_frame, text=self.team_away_name, font=("Arial", 22, "bold"), bg=RSK_BLUE, fg="#D0D0D0").pack(pady=5) 
        self.lbl_score_away = tk.Label(away_frame, textvariable=self.away_score_str, font=("Impact", 200), bg=RSK_BLUE, fg=RSK_WHITE)
        self.lbl_score_away.pack(fill="both", expand=True)

        # --- SPIELZEIT (GANZ UNTEN) ---
        time_frame = tk.Frame(main_frame, bg=RSK_BLUE)
        time_frame.grid(row=2, column=0, columnspan=3, pady=(10, 0), sticky="s")
        self.lbl_time = tk.Label(time_frame, textvariable=self.time_str, font=("Impact", 70), bg=RSK_BLUE, fg=RSK_WHITE) 
        self.lbl_time.pack()

    def update(self, time_str, half_text, home_score, away_score, time_color):
        """Aktualisiert alle Anzeigewerte."""
        self.time_str.set(time_str)
        self.home_score_str.set(str(home_score))
        self.away_score_str.set(str(away_score))
        
        if time_color == RSK_BLUE:
             self.lbl_time.config(fg=RSK_WHITE) 
        elif time_color == ACCENT_RED:
             self.lbl_time.config(fg=ACCENT_RED) 
        else:
             self.lbl_time.config(fg=time_color)
        
        if home_score > away_score:
            self.lbl_score_home.config(fg=RSK_WHITE) 
            self.lbl_score_away.config(fg="#88AAFF") 
        elif away_score > home_score:
            self.lbl_score_home.config(fg="#88AAFF")
            self.lbl_score_away.config(fg=RSK_WHITE)
        else:
            self.lbl_score_home.config(fg=RSK_WHITE)
            self.lbl_score_away.config(fg=RSK_WHITE)

    def show(self):
        self.window.deiconify() 
        self.window.lift()

    def hide(self):
        self.window.withdraw() 


# ====================================================================
# --- HAUPTKLASSE: FUSSBALL-TIMER ---
# ====================================================================

class FussballTimer:
    def __init__(self, root):
        self.root = root
        self.root.title("FC RSK Freyburg Halle - Steuerpult")
        self.root.geometry("400x800")
        self.root.minsize(400, 800)
        self.root.configure(bg=BG_COLOR)

        # --- Logik-Variablen ---
        self.seconds = 0
        self.running = False
        self._after_id = None
        
        # NEU: Teamnamen im Controller aktualisiert
        self.team_home_name = "Spielplan Links"
        self.team_away_name = "Spielplan Rechts"
        
        self.scores = {self.team_home_name: 0, self.team_away_name: 0}
        
        self.match_duration_minutes = tk.IntVar(value=45) 
        self.current_match_duration_seconds = 45 * 60 
        
        self.jingle_paths = []
        self.jingle_triggered = False
        self.auto_jingle_enabled = tk.BooleanVar(value=True) 
        
        self.scoreboard_enabled = tk.BooleanVar(value=False)
        self.scoreboard = ScoreboardDisplay(root) 
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
        
        self.create_widgets()
        
        self.wave_canvas.bind("<Configure>", self._on_resize)
        self.root.bind("<space>", lambda e: self.toggle_timer())
        
        self._update_scoreboard_display(RSK_BLUE, "SPIEL BEREIT") 

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
        header_frame = tk.Frame(self.root, bg=RSK_BLUE, height=50)
        header_frame.pack(fill="x")
        header_label = tk.Label(header_frame, text="FC RSK FREYBURG HALLE", 
                                 font=("Helvetica", 16, "bold"), bg=RSK_BLUE, fg=RSK_WHITE)
        header_label.pack(pady=10)
        
        # Anzeigetafel-Option GANZ OBEN platziert
        self._create_card_scoreboard_option_top()

        # --- HAUPTBEREICH ---
        main_container = tk.Frame(self.root, bg=BG_COLOR)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)

        self._create_card_timer(main_container)
        self._create_card_score(main_container)
        self._create_card_audio(main_container) 
        
    def _create_card_scoreboard_option_top(self):
        card = tk.Frame(self.root, bg=RSK_WHITE, bd=1, relief="flat")
        card.pack(fill="x", pady=(0, 10), padx=10, ipady=5)
        
        tk.Label(card, text="ANZEIGE", font=("Arial", 12, "bold"), bg=RSK_WHITE, fg=RSK_BLUE).pack(anchor="w", padx=10, pady=(5, 0))
        
        tk.Checkbutton(
            card,
            text="Anzeigetafel (Zweites Fenster) anzeigen",
            variable=self.scoreboard_enabled,
            bg=RSK_WHITE,
            font=("Arial", 10),
            fg=TEXT_COLOR,
            relief="flat",
            cursor="hand2"
        ).pack(anchor="w", padx=10, pady=5)
    
    def _toggle_scoreboard(self, *args):
        if self.scoreboard_enabled.get():
            self.scoreboard.show()
            self._update_scoreboard_display(self.timer_label['fg'], self.half_label['text']) 
        else:
            self.scoreboard.hide()


    def _create_card_timer(self, parent):
        card = tk.Frame(parent, bg=RSK_WHITE, bd=1, relief="flat")
        card.pack(fill="x", pady=(0, 10), ipady=5)

        self.half_label = tk.Label(card, text="SPIEL BEREIT", font=("Arial", 12, "bold"), bg=RSK_WHITE, fg="#888")
        self.half_label.pack(pady=(10, 0))

        self.timer_label = tk.Label(card, text="0:00", font=("Impact", 75), bg=RSK_WHITE, fg=RSK_BLUE)
        self.timer_label.pack(pady=0)

        btn_frame = tk.Frame(card, bg=RSK_WHITE)
        btn_frame.pack(pady=10)
        self._big_btn(btn_frame, "START", self.start_timer, ACCENT_GREEN).pack(side="left", padx=5)
        self._big_btn(btn_frame, "STOPP", self.stop_timer, ACCENT_RED).pack(side="left", padx=5)
        
        sub_btn_frame = tk.Frame(card, bg=RSK_WHITE)
        sub_btn_frame.pack(pady=(0, 10))

        tk.Label(sub_btn_frame, text="Länge:", font=("Arial", 10), bg=RSK_WHITE, fg="#666").pack(side="left", padx=5)

        self.duration_input = tk.Spinbox(
            sub_btn_frame, 
            from_=1, to=120, 
            textvariable=self.match_duration_minutes, 
            width=3, 
            font=("Arial", 10),
            relief="flat"
        )
        self.duration_input.pack(side="left")
        tk.Label(sub_btn_frame, text="Min", font=("Arial", 10), bg=RSK_WHITE, fg="#666").pack(side="left", padx=(0, 10))

        self._text_btn(sub_btn_frame, "Reset", self.reset_timer).pack(side="left", padx=5)

    def _create_card_score(self, parent):
        card = tk.Frame(parent, bg=RSK_WHITE, bd=1, relief="flat")
        card.pack(fill="x", pady=(0, 10), ipady=10)
        score_grid = tk.Frame(card, bg=RSK_WHITE)
        score_grid.pack()
        
        # NEU: Text auf Spielplan Links geändert
        home_frame = tk.Frame(score_grid, bg=RSK_WHITE)
        home_frame.grid(row=0, column=0, padx=10)
        tk.Label(home_frame, text=self.scoreboard.team_home_name, font=("Arial", 14, "bold"), bg=RSK_WHITE, fg=RSK_BLUE).pack() 
        self.lbl_score_home = tk.Label(home_frame, text="0", font=("Arial", 50, "bold"), bg=RSK_WHITE, fg=TEXT_COLOR)
        self.lbl_score_home.pack()
        h_btns = tk.Frame(home_frame, bg=RSK_WHITE)
        h_btns.pack()
        self._circle_btn(h_btns, "+", lambda: self.update_score("Home", 1), RSK_BLUE)
        self._circle_btn(h_btns, "-", lambda: self.update_score("Home", -1), "#999")

        tk.Label(score_grid, text=":", font=("Arial", 40, "bold"), bg=RSK_WHITE, fg="#ccc").grid(row=0, column=1, pady=20)

        # NEU: Text auf Spielplan Rechts geändert
        away_frame = tk.Frame(score_grid, bg=RSK_WHITE)
        away_frame.grid(row=0, column=2, padx=10)
        tk.Label(away_frame, text=self.scoreboard.team_away_name, font=("Arial", 14, "bold"), bg=RSK_WHITE, fg="#555").pack() 
        self.lbl_score_away = tk.Label(away_frame, text="0", font=("Arial", 50, "bold"), bg=RSK_WHITE, fg=TEXT_COLOR)
        self.lbl_score_away.pack()
        a_btns = tk.Frame(away_frame, bg=RSK_WHITE)
        a_btns.pack()
        self._circle_btn(a_btns, "+", lambda: self.update_score("Away", 1), RSK_BLUE)
        self._circle_btn(a_btns, "-", lambda: self.update_score("Away", -1), "#999")

    def _create_card_audio(self, parent):
        card = tk.Frame(parent, bg=RSK_WHITE, bd=1, relief="flat")
        card.pack(fill="x", pady=(0, 0), ipady=5) 

        top = tk.Frame(card, bg=RSK_WHITE)
        top.pack(fill="x", padx=10, pady=5)
        tk.Label(top, text="JINGLE / AUDIO", font=("Arial", 12, "bold"), bg=RSK_WHITE, fg=RSK_BLUE).pack(anchor="w")
        self.file_label = tk.Label(top, text="(Keine Datei ausgewählt)", font=("Arial", 9, "italic"), bg=RSK_WHITE, fg="#888", anchor="w")
        self.file_label.pack(fill="x")
        
        auto_jingle_frame = tk.Frame(card, bg=RSK_WHITE)
        auto_jingle_frame.pack(fill="x", padx=10, pady=(0, 5))
        
        self.chk_auto_jingle = tk.Checkbutton(
            auto_jingle_frame, 
            text="Automatische Wiedergabe in der letzten Minute aktivieren", 
            variable=self.auto_jingle_enabled, 
            bg=RSK_WHITE, 
            font=("Arial", 10), 
            fg=TEXT_COLOR,
            relief="flat",
            cursor="hand2"
        )
        self.chk_auto_jingle.pack(anchor="w")


        ctrl_frame = tk.Frame(card, bg=RSK_WHITE)
        ctrl_frame.pack(pady=5)
        self._icon_btn(ctrl_frame, "📂 Wählen", self.choose_jingle, "#6c757d").pack(side="left", padx=2) 
        self._icon_btn(ctrl_frame, "▶ PLAY", self.play_jingle, ACCENT_GREEN).pack(side="left", padx=2)
        self._icon_btn(ctrl_frame, "■ STOP", self.stop_jingle, ACCENT_RED).pack(side="left", padx=2)

        self.vis_frame = tk.Frame(card, bg=RSK_WHITE, padx=10, pady=5)
        self.vis_frame.pack(fill="x")
        self.wave_canvas = tk.Canvas(self.vis_frame, height=80, bg="#FAFAFA", highlightthickness=0)
        self.wave_canvas.pack(fill="x")

        leg = tk.Frame(self.vis_frame, bg=RSK_WHITE)
        leg.pack(fill="x", pady=2)
        tk.Label(leg, text="■ Pause", fg=ACCENT_GREEN, bg=RSK_WHITE, font=("Arial", 8)).pack(side="left", padx=5)
        tk.Label(leg, text="■ Laut", fg=ACCENT_RED, bg=RSK_WHITE, font=("Arial", 8)).pack(side="left", padx=5)

        style = ttk.Style()
        style.theme_use('default')
        style.configure("RSK.Horizontal.TProgressbar", thickness=5, background=RSK_BLUE, troughcolor="#E0E0E0", borderwidth=0)
        self.progress = ttk.Progressbar(self.vis_frame, orient="horizontal", mode="determinate", style="RSK.Horizontal.TProgressbar")
        self.progress.pack(fill="x", pady=(5,0))


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
                self.half_label.config(text="SPIEL LÄUFT")
                self.timer_label.config(fg=RSK_BLUE)
                
            self.running = True
            if self.scoreboard_enabled.get():
                self.scoreboard.show() 
            self._tick()
            
    def stop_timer(self): 
        if self.running:
            self.running = False
            self.half_label.config(text="PAUSE")
            self._update_scoreboard_display(self.timer_label['fg'], "SPIEL PAUSE")
        
        if not self.scoreboard_enabled.get() and self.seconds < self.current_match_duration_seconds:
             self.scoreboard.hide()


    def reset_timer(self):
        self.stop_jingle()
        self.stop_timer()
        self.seconds = 0
        self.jingle_triggered = False 
        
        self.timer_label.config(text="0:00", fg=RSK_BLUE)
        self.half_label.config(text="SPIEL BEREIT")
        
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
            last_minute_threshold = target_time - 60 
            
            color_to_use = RSK_BLUE 
            half_text = "SPIEL LÄUFT"
            
            if self.seconds >= last_minute_threshold: 
                color_to_use = ACCENT_RED 
                
                if not self.jingle_triggered and self.jingle_paths and self.auto_jingle_enabled.get():
                    path_to_play = random.choice(self.jingle_paths)
                    self.start_jingle_load_and_play(path_to_play)
                    self.jingle_triggered = True
            
            time_str = f"{minutes}:{seconds_part:02}"
            self.timer_label.config(text=time_str, fg=color_to_use)
            
            self._update_scoreboard_display(color_to_use, half_text)
            
            if self.seconds >= target_time: 
                self.running = False
                color_to_use = "#FF8C00" 
                self.timer_label.config(fg=color_to_use) 
                self.half_label.config(text="SPIEL ENDE")
                
                self._update_scoreboard_display(color_to_use, "SPIEL ENDE")
                return 

            self._after_id = self.root.after(1000, self._tick)

    def _update_scoreboard_display(self, time_color, half_text):
         if self.scoreboard_enabled.get() or "BEREIT" in half_text or "ENDE" in half_text: 
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
        self.file_label.config(text=f"{count} Datei{'en' if count != 1 else ''} ausgewählt (Zufallswiedergabe)")
        
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
