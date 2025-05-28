import sqlite3
import datetime
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import tkinter as tk
from tkinter import messagebox
from threading import Thread
import re
import random
import time
import sys

# ---- KONFIGURACJA ----
PORT_SZEREGOWY = 'COM3'
PREDKOSC = 9600
TRYB_SYMULACJI = True  # Zmień na False, żeby korzystać ze sprzętu
DB_FILENAME = "smarthouse.db"

SENSOR_LABELS = {
    "temperature": "Temperatura",
    "humidity": "Wilgotność",
    "oxygen": "Jakość tlenu",
    "light": "Naświetlenie",
    "motion": "Ruch",
    "status": "Status",
}

class SensorDatabase:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILENAME, check_same_thread=False)
        self._init_schema()

    def _init_schema(self):
        self.conn.execute('''CREATE TABLE IF NOT EXISTS sensor_data (
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
             sensor_type TEXT,
             sensor_value TEXT
        )''')
        self.conn.commit()

    def save(self, sensor_type, sensor_value):
        self.conn.execute(
            "INSERT INTO sensor_data (sensor_type, sensor_value) VALUES (?,?)",
            (sensor_type, str(sensor_value))
        )
        self.conn.commit()

    def get_by_day(self, date, sensor_type):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT time, sensor_value FROM sensor_data WHERE date(time)=? AND sensor_type=? ORDER BY time ASC",
            (date, sensor_type)
        )
        return cursor.fetchall()

class SymulowanyPort:
    def __init__(self):
        self.counter = 0

    @property
    def in_waiting(self):
        # Zawsze zwraca 1, aby symulować dane
        return 1

    def readline(self):
        self.counter += 1
        dane = [
            f"Temperatura: {random.uniform(18, 28):.1f}",
            f"Wilgotnosc: {random.uniform(30, 60):.1f}",
            f"Jakosc Tlenu: {random.randint(85, 100)}",
            f"Naswietlenie: {random.randint(100, 800)}",
            f"Ruch: {'WYKRYTO' if random.random() < 0.2 else 'BRAK'}",
            f"Status: {'ALARM' if random.random() < 0.1 else 'Monitoring'}",
        ]
        return (random.choice(dane) + "\n").encode('utf-8')

    def write(self, data):
        print(f"(SYMU): Komenda wysłana: {data.decode('utf-8').strip()}")

    def close(self):
        print("(SYMU): Port zamknięty.")

    @property
    def is_open(self):
        return True

class AplikacjaSterowania:
    def __init__(self, root, polaczenie_szeregowe):
        self.root = root
        self.ser = polaczenie_szeregowe
        self.running = True
        self.db = SensorDatabase()
        self.ostatni_odczyt = {}

        style = ttk.Style(theme="minty")
        self.root.title("Smart House - Modern")
        self.root.geometry("1200x1000")
        main = ttk.Frame(self.root, padding=18)
        main.pack(fill=tk.BOTH, expand=True)

        lab_title = ttk.Label(main, text="Smart House - Akademia WSB", font=("Arial", 18, "bold"), bootstyle=INFO)
        lab_title.pack(pady=(8, 20))

        frm_panel = ttk.Frame(main)
        frm_panel.pack(fill=tk.BOTH, expand=True)

        # Panel odczytu na żywo
        panel_left = ttk.LabelFrame(frm_panel, text="Odczyty na żywo", bootstyle=INFO, padding=15)
        panel_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        # Panel historii
        panel_history = ttk.LabelFrame(frm_panel, text="Archiwum / Historia odczytów", bootstyle=SECONDARY, padding=15)
        panel_history.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))

        # Odczyty na żywo - etykiety i wartości
        self.sensor_vars = {k: tk.StringVar(value='-') for k in SENSOR_LABELS}
        for i, k in enumerate(SENSOR_LABELS):
            ttk.Label(panel_left, text=SENSOR_LABELS[k]+":", font=("Arial", 13)).grid(row=i, column=0, sticky=tk.W, pady=7)
            ttk.Label(panel_left, textvariable=self.sensor_vars[k], font=("Arial", 13, "bold"), bootstyle=SUCCESS).grid(row=i, column=1, sticky=tk.W, pady=7, padx=20)

        # Separator
        control_sep = ttk.Separator(panel_left, orient='horizontal')
        control_sep.grid(row=len(SENSOR_LABELS), columnspan=3, sticky="ew", pady=20)

        # Panel sterowania
        ctlfrm = ttk.Frame(panel_left)
        ctlfrm.grid(row=len(SENSOR_LABELS)+1, column=0, columnspan=3, pady=(10, 0), sticky=tk.W+tk.E)

        ttk.Label(ctlfrm, text="Serwo SG90: ", font=("Arial", 11)).grid(row=0, column=0, sticky=tk.W)
        self.servo_value = tk.IntVar(value=90)
        servo = ttk.Scale(ctlfrm, from_=0, to=180, orient="horizontal", variable=self.servo_value, length=190, bootstyle=SUCCESS)
        servo.grid(row=0, column=1, sticky=tk.W)
        ttk.Button(ctlfrm, text="Ustaw", bootstyle=SUCCESS, width=8, command=lambda: self.wyslij_komende(f"S{self.servo_value.get()}")).grid(row=0, column=2, padx=10)

        ttk.Label(ctlfrm, text="Silnik Krokowy:", font=("Arial", 11)).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.stepper_value = tk.IntVar(value=0)
        stepper = ttk.Scale(ctlfrm, from_=-2048, to=2048, orient="horizontal", variable=self.stepper_value, length=190, bootstyle=PRIMARY)
        stepper.grid(row=1, column=1, sticky=tk.W)
        ttk.Button(ctlfrm, text="Kroki", bootstyle=PRIMARY, width=8,
                   command=lambda: self.wyslij_komende(f"M{self.stepper_value.get()}")).grid(row=1, column=2, padx=10)

        ttk.Label(ctlfrm, text="Buzzer: ", font=("Arial", 11)).grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Button(ctlfrm, text="ON", bootstyle=WARNING, command=lambda: self.wyslij_komende("B1")).grid(row=2, column=1, sticky=tk.W)
        ttk.Button(ctlfrm, text="OFF", bootstyle=SECONDARY, command=lambda: self.wyslij_komende("B0")).grid(row=2, column=2, sticky=tk.W, padx=10)

        quickfrm = ttk.Frame(ctlfrm)
        quickfrm.grid(row=3, column=0, columnspan=3, pady=(15,5), sticky=tk.W)
        ttk.Label(quickfrm, text="Szybkie pozycje serwa: ").pack(side=tk.LEFT)
        for kat in [0, 90, 180]:
            ttk.Button(quickfrm, text=f"{kat}°", width=6,
                       bootstyle=INFO, command=lambda k=kat: self.wyslij_komende(f"S{k}")).pack(side=tk.LEFT, padx=3)

        # Pane history - wybór daty i czujnika
        day_today = datetime.date.today().strftime("%Y-%m-%d")
        self.history_sensor_type = tk.StringVar(value="temperature")
        self.history_date = tk.StringVar(value=day_today)

        ttk.Label(panel_history, text="Data (RRRR-MM-DD):", font=("Arial", 11)).grid(row=0, column=0, sticky=tk.E, pady=4, padx=(2,2))
        ent_date = ttk.Entry(panel_history, textvariable=self.history_date, width=13, font=("Arial", 11))
        ent_date.grid(row=0, column=1, sticky=tk.W, pady=4, padx=(2,13))

        ttk.Label(panel_history, text="Czujnik:", font=("Arial", 11)).grid(row=0, column=2, sticky=tk.E, padx=(5,2))
        sens_list = list(SENSOR_LABELS.keys())
        cmb_czujnik = ttk.Combobox(panel_history,
                                   values=sens_list,
                                   textvariable=self.history_sensor_type,
                                   width=17,
                                   state="readonly",
                                   font=("Arial", 11))
        cmb_czujnik.grid(row=0, column=3, sticky=tk.W, pady=4)

        ttk.Button(panel_history, text="Pokaż", bootstyle="info", command=self.pokaz_historie).grid(row=0, column=4, padx=10, pady=4)

        self.historia_text = tk.Text(panel_history, height=18, width=70, font=("Courier", 10), state="disabled", wrap="none")
        self.historia_text.grid(row=1, column=0, columnspan=5, pady=(20,5), padx=5)

        # Scrollbar dla historii
        scrollbar = ttk.Scrollbar(panel_history, orient=tk.VERTICAL, command=self.historia_text.yview)
        scrollbar.grid(row=1, column=5, sticky=tk.N+tk.S+tk.W, pady=(20,5))
        self.historia_text.config(yscrollcommand=scrollbar.set)

        # Log komunikacji
        log_frame = ttk.LabelFrame(main, text="Log komunikacji", bootstyle=DARK, padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.log_text = tk.Text(log_frame, height=10, font=("Courier", 10))
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar_log = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar_log.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar_log.set)

        # Stopka z przyciskiem zamknięcia
        footer_frame = ttk.Frame(main)
        footer_frame.pack(fill=tk.X, pady=5)
        ttk.Label(footer_frame, text="© 2025 Akademia WSB - Projekt Smart House", font=("Arial", 9)).pack(side=tk.LEFT)
        ttk.Button(footer_frame, text="Zamknij", bootstyle="danger", command=self.zamknij_aplikacje).pack(side=tk.RIGHT)

        # Start wątku odczytu danych
        self.thread = Thread(target=self.odczytuj_dane, daemon=True)
        self.thread.start()

        self.root.protocol("WM_DELETE_WINDOW", self.zamknij_aplikacje)

    def wyslij_komende(self, komenda):
        try:
            self.log_text.insert(tk.END, f"Wysyłanie: {komenda}\n")
            self.log_text.see(tk.END)
            self.ser.write(f"{komenda}\n".encode('utf-8'))
        except Exception as e:
            messagebox.showerror("Błąd komunikacji", f"Nie można wysłać komendy: {str(e)}")

    def odczytuj_dane(self):
        while self.running:
            try:
                if self.ser.in_waiting > 0:
                    line = self.ser.readline().decode('utf-8').strip()
                    if not line:
                        continue
                    # Log
                    self.log_text.insert(tk.END, f"Odebrano: {line}\n")
                    self.log_text.see(tk.END)

                    parsers = [
                        ('temperature', r'Temperatura:\s+([0-9.]+)'),
                        ('humidity', r'Wilgotnosc:\s+([0-9.]+)'),
                        ('oxygen', r'Jakosc Tlenu:\s+([0-9]+)'),
                        ('light', r'Naswietlenie:\s+([0-9]+)'),
                        ('motion', r'Ruch:\s+(WYKRYTO|BRAK)'),
                        ('status', r'Status:\s+(ALARM|Monitoring)'),
                    ]
                    for key, pattern in parsers:
                        m = re.search(pattern, line)
                        if m:
                            val = m.group(1)
                            self.ostatni_odczyt[key] = val
                            self.sensor_vars[key].set(val)
                            self.db.save(key, val)
            except Exception as e:
                self.log_text.insert(tk.END, f"Błąd odczytu: {str(e)}\n")
                self.log_text.see(tk.END)
            time.sleep(0.15)

    def pokaz_historie(self):
        date = self.history_date.get()
        sensor = self.history_sensor_type.get()
        if not date or not sensor:
            messagebox.showwarning("Uwaga", "Proszę wybrać datę i czujnik.")
            return

        # Prosta walidacja daty YYYY-MM-DD
        try:
            datetime.datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Błąd", "Niepoprawny format daty, użyj RRRR-MM-DD")
            return

        rows = self.db.get_by_day(date, sensor)
        self.historia_text.config(state="normal")
        self.historia_text.delete("1.0", tk.END)
        if not rows:
            self.historia_text.insert(tk.END, "Brak odczytów dla wybranego dnia i czujnika.\n")
        else:
            for t, val in rows:
                self.historia_text.insert(tk.END, f"{t[:19]} | {val}\n")
        self.historia_text.config(state="disabled")

    def zamknij_aplikacje(self):
        if messagebox.askokcancel("Zamknij", "Czy na pewno chcesz zamknąć aplikację?"):
            self.running = False
            if self.thread.is_alive():
                self.thread.join(timeout=1.0)
            if not TRYB_SYMULACJI and self.ser and self.ser.is_open:
                self.ser.close()
            self.root.destroy()


def main():
    try:
        ser = None
        if TRYB_SYMULACJI:
            ser = SymulowanyPort()
        else:
            try:
                import serial
            except ImportError:
                root = ttk.Window()
                root.withdraw()
                messagebox.showerror("Błąd importu", "Biblioteka 'pyserial' nie jest zainstalowana.\nAby użyć portu szeregowego, wykonaj: pip install pyserial")
                return
            try:
                ser = serial.Serial(PORT_SZEREGOWY, PREDKOSC, timeout=1)
                time.sleep(2)  # Czekaj na inicjalizację portu
            except Exception as e:
                root = ttk.Window()
                root.withdraw()
                messagebox.showerror("Błąd portu szeregowego", f"Nie udało się otworzyć {PORT_SZEREGOWY}:\n{str(e)}")
                return

        root = ttk.Window(themename="minty")
        app = AplikacjaSterowania(root, ser)
        root.mainloop()

        if not TRYB_SYMULACJI and ser and ser.is_open:
            ser.close()
    except Exception as e:
        root = ttk.Window()
        root.withdraw()
        messagebox.showerror("Błąd aplikacji", f"Wystąpił nieoczekiwany błąd:\n{str(e)}")

if __name__ == "__main__":
    main()