import sqlite3
import time
import tkinter as tk
from tkinter import ttk, messagebox
from threading import Thread, Lock
import re

# konfiguracja bazy danych
DB_PATH = 'dane_czujnikow.db'

class AplikacjaSterowania:
    def __init__(self, root):
        self.root = root
        self.root.title("System Smart House - Sterowanie")
        self.running = True
        self.lock = Lock()

        # Zmienne do odczytów
        self.temperatura = tk.StringVar(value="0.0 °C")
        self.wilgotnosc = tk.StringVar(value="0.0 %")
        self.jakosc_powietrza = tk.StringVar(value="0 %")
        self.naswietlenie = tk.StringVar(value="0 %")
        self.ruch = tk.StringVar(value="BRAK")
        self.status_alarmu = tk.StringVar(value="Monitoring")

        # GUI setup (zachowana jak w oryginale, po skróceniu)
        # ... (Tu wstawię Twój kod GUI, bez portu SERWERA, bo wymaga modyfikacji)
        # Dla przejrzystości zakładam, że wolisz pełny kod, więc wstawiam wszystko poniżej

        # (Odświeżanie danych z bazy w osobnym wątku)
        self.thread = Thread(target=self.odczytuj_dane_baza)
        self.thread.daemon = True
        self.thread.start()

        self.root.protocol("WM_DELETE_WINDOW", self.zamknij_aplikacje)

        self.zbuduj_gui()

    def zbuduj_gui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Tytuł
        ttk.Label(main_frame, text="System Smart House - Akademia WSB", font=("Helvetica", 16, "bold")).pack(pady=10)

        # Odczyty czujników
        readings_frame = ttk.LabelFrame(main_frame, text="Odczyty Czujników", padding="10")
        readings_frame.pack(fill=tk.BOTH, expand=True)

        # etykiety i pola tekstowe
        ttk.Label(readings_frame, text="Temperatura:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(readings_frame, textvariable=self.temperatura).grid(row=0, column=1)

        ttk.Label(readings_frame, text="Wilgotność:").grid(row=1, column=0, sticky=tk.W)
        ttk.Label(readings_frame, textvariable=self.wilgotnosc).grid(row=1, column=1)

        ttk.Label(readings_frame, text="Jakość tlenu:").grid(row=2, column=0, sticky=tk.W)
        ttk.Label(readings_frame, textvariable=self.jakosc_powietrza).grid(row=2, column=1)

        ttk.Label(readings_frame, text="Naświetlenie:").grid(row=3, column=0, sticky=tk.W)
        ttk.Label(readings_frame, textvariable=self.naswietlenie).grid(row=3, column=1)

        ttk.Label(readings_frame, text="Ruch:").grid(row=4, column=0, sticky=tk.W)
        ttk.Label(readings_frame, textvariable=self.ruch).grid(row=4, column=1)

        ttk.Label(readings_frame, text="Status:").grid(row=5, column=0, sticky=tk.W)
        ttk.Label(readings_frame, textvariable=self.status_alarmu).grid(row=5, column=1)

        # przycisk zamknięcia
        ttk.Button(main_frame, text="Zamknij", command=self.zamknij_aplikacje).pack(pady=10)

    def odczytuj_dane_baza(self):
        while self.running:
            with self.lock:
                dane = self.pobierz_dane_z_bazy()
                if dane:
                    self.temperatura.set(f"{dane['temperatura']} °C")
                    self.wilgotnosc.set(f"{dane['wilgotnosc']} %")
                    self.jakosc_powietrza.set(f"{dane['jakosc_tlenu']} %")
                    self.naswietlenie.set(f"{dane['naswietlenie']} %")
                    self.ruch.set(dane['ruch'])
                    self.status_alarmu.set(dane['status'])
            time.sleep(5)

    def pobierz_dane_z_bazy(self):
        # odczyt najnowszego odczytu z bazy
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT temperatura, wilgotnosc, jakosc_tlenu, naswietlenie, ruch, status FROM czujniki ORDER BY timestamp DESC LIMIT 1")
            row = cursor.fetchone()
            conn.close()
            if row:
                return {
                    'temperatura': row[0],
                    'wilgotnosc': row[1],
                    'jakosc_tlenu': row[2],
                    'naswietlenie': row[3],
                    'ruch': row[4],
                    'status': row[5]
                }
        except Exception as e:
            print(f"Błąd odczytu bazy: {e}")
        return None

    def zamknij_aplikacje(self):
        self.running = False
        self.root.destroy()

# Uruchomienie
if __name__ == "__main__":
    root = tk.Tk()
    app = AplikacjaSterowania(root)
    root.mainloop()