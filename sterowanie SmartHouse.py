import sqlite3          # Biblioteka do obsługi bazy SQLite
import datetime         # Do operacji na datach i czasie
import ttkbootstrap as ttk     # Nowoczesny styl dla tkinter
from ttkbootstrap.constants import *   # Stałe stylizacji
import tkinter as tk
from tkinter import messagebox
from threading import Thread    # Wątek do odczytu danych w tle
import re                      # Operacje na wyrażeniach regularnych
import random
import time
import sys

# ---- KONFIGURACJA ----
PORT_SZEREGOWY = 'COM3'       # Domyślny port szeregowy do komunikacji ze sprzętem
PREDKOSC = 9600               # Szybkość transmisji danych (baud rate)
TRYB_SYMULACJI = False         # True - użyj symulacji
DB_FILENAME = "smarthouse.db" # Nazwa pliku lokalnej bazy danych SQLite

# Słownik z nazwami czujników do wyświetlania w GUI
SENSOR_LABELS = {
    "temperature": "Temperatura",
    "humidity": "Wilgotność",
    "oxygen": "Jakość tlenu",
    "light": "Naświetlenie",
    "motion": "Ruch",
    "status": "Status",
}

# Klasa zarządzająca bazą danych SQLite
class SensorDatabase:
    def __init__(self):
        # Połączenie do bazy (plik lub nowy jeśli nie istnieje)
        self.conn = sqlite3.connect(DB_FILENAME, check_same_thread=False)
        self._init_schema()  # Tworzenie tabeli jeśli jej brak

    def _init_schema(self):
        # Tworzy tabelę sensor_data jeśli nie istnieje z kolumnami id, czas, typ i wartość czujnika
        self.conn.execute('''CREATE TABLE IF NOT EXISTS sensor_data (
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
             sensor_type TEXT,
             sensor_value TEXT
        )''')
        self.conn.commit()

    def save(self, sensor_type, sensor_value):
        # Wstawia nowy odczyt do tabeli sensor_data
        self.conn.execute(
            "INSERT INTO sensor_data (sensor_type, sensor_value) VALUES (?,?)",
            (sensor_type, str(sensor_value))
        )
        self.conn.commit()

    def get_by_day(self, date, sensor_type):
        # Pobiera dane z tabeli dla wybranego dnia i typu czujnika, posortowane po czasie
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT time, sensor_value FROM sensor_data WHERE date(time)=? AND sensor_type=? ORDER BY time ASC",
            (date, sensor_type)
        )
        return cursor.fetchall()

# Klasa symulująca port szeregowy (dla trybu demonstracyjnego)
class SymulowanyPort:
    def __init__(self):
        self.counter = 0

    @property
    def in_waiting(self):
        # Symuluje stałą dostepność danych do odczytu
        return 1

    def readline(self):
        # Zwraca losową linię odpowiadającą jednemu odczytowi z czujników
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
        # Symuluje zapisywanie komendy - wypisuje do konsoli
        print(f"(SYMU): Komenda wysłana: {data.decode('utf-8').strip()}")

    def close(self):
        # Symuluje zamknięcie portu
        print("(SYMU): Port zamknięty.")

    @property
    def is_open(self):
        # Symulowany port jest zawsze "otwarty"
        return True

# Główna klasa aplikacji - graficzny interfejs i logika sterowania
class AplikacjaSterowania:
    def __init__(self, root, polaczenie_szeregowe):
        self.root = root                 # Okno tkinter
        self.ser = polaczenie_szeregowe # Obiekt portu szeregowego lub symulacji
        self.running = True             # Flaga sterująca wątkiem odczytu
        self.db = SensorDatabase()      # Obiekt bazy danych
        self.ostatni_odczyt = {}        # Pamięć ostatnich odczytów (szybki dostęp)

        style = ttk.Style(theme="minty")      # Styl graficzny ttkbootstrap
        self.root.title("Smart House - Modern")
        self.root.geometry("1200x1000")       # Rozmiar okna głównego
        main = ttk.Frame(self.root, padding=18)
        main.pack(fill=tk.BOTH, expand=True)

        # Tytuł aplikacji
        lab_title = ttk.Label(main, text="Smart House - Akademia WSB", font=("Arial", 18, "bold"), bootstyle=INFO)
        lab_title.pack(pady=(8, 20))

        frm_panel = ttk.Frame(main)
        frm_panel.pack(fill=tk.BOTH, expand=True)

        # Lewy panel - odczyty czujników na żywo
        panel_left = ttk.LabelFrame(frm_panel, text="Odczyty na żywo", bootstyle=INFO, padding=15)
        panel_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        # Prawy panel - archiwum i historia odczytów
        panel_history = ttk.LabelFrame(frm_panel, text="Archiwum / Historia odczytów", bootstyle=SECONDARY, padding=15)
        panel_history.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))

        # Inicjuj zmienne StringVar dla powiązania z etykietami tekstowymi (szybka aktualizacja GUI)
        self.sensor_vars = {k: tk.StringVar(value='-') for k in SENSOR_LABELS}
        # Tworzenie i układanie etykiet na lewej ramce do wyświetlania dzisiejszych odczytów
        for i, k in enumerate(SENSOR_LABELS):
            ttk.Label(panel_left, text=SENSOR_LABELS[k]+":", font=("Arial", 13)).grid(row=i, column=0, sticky=tk.W, pady=7)
            ttk.Label(panel_left, textvariable=self.sensor_vars[k], font=("Arial", 13, "bold"), bootstyle=SUCCESS).grid(row=i, column=1, sticky=tk.W, pady=7, padx=20)

        # Separator graficzny (linia pozioma) między odczytami i panel sterowania
        control_sep = ttk.Separator(panel_left, orient='horizontal')
        control_sep.grid(row=len(SENSOR_LABELS), columnspan=3, sticky="ew", pady=20)

        # Panel sterowania urządzeniami
        ctlfrm = ttk.Frame(panel_left)
        ctlfrm.grid(row=len(SENSOR_LABELS)+1, column=0, columnspan=3, pady=(10, 0), sticky=tk.W+tk.E)

        # Sterowanie serwem SG90 - suwak do ustawienia kąta i przycisk do wysłania komendy
        ttk.Label(ctlfrm, text="Serwo SG90: ", font=("Arial", 11)).grid(row=0, column=0, sticky=tk.W)
        self.servo_value = tk.IntVar(value=90)
        servo = ttk.Scale(ctlfrm, from_=0, to=180, orient="horizontal", variable=self.servo_value, length=190, bootstyle=SUCCESS)
        servo.grid(row=0, column=1, sticky=tk.W)
        ttk.Button(ctlfrm, text="Ustaw", bootstyle=SUCCESS, width=8,
                    command=lambda: self.wyslij_komende(f"S{self.servo_value.get()}")).grid(row=0, column=2, padx=10)

        # Sterowanie silnikiem krokowym - suwak liczby kroków i przycisk wysłania komendy
        ttk.Label(ctlfrm, text="Silnik Krokowy:", font=("Arial", 11)).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.stepper_value = tk.IntVar(value=0)
        stepper = ttk.Scale(ctlfrm, from_=-2048, to=2048, orient="horizontal", variable=self.stepper_value, length=190, bootstyle=PRIMARY)
        stepper.grid(row=1, column=1, sticky=tk.W)
        ttk.Button(ctlfrm, text="Kroki", bootstyle=PRIMARY, width=8,
                    command=lambda: self.wyslij_komende(f"M{self.stepper_value.get()}")).grid(row=1, column=2, padx=10)

        # Sterowanie buzzerem - dwa przyciski ON/OFF
        ttk.Label(ctlfrm, text="Buzzer: ", font=("Arial", 11)).grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Button(ctlfrm, text="ON", bootstyle=WARNING, command=lambda: self.wyslij_komende("B1")).grid(row=2, column=1, sticky=tk.W)
        ttk.Button(ctlfrm, text="OFF", bootstyle=SECONDARY, command=lambda: self.wyslij_komende("B0")).grid(row=2, column=2, sticky=tk.W, padx=10)

        # Szybkie przyciski ustawień serwa w popularnych pozycjach
        quickfrm = ttk.Frame(ctlfrm)
        quickfrm.grid(row=3, column=0, columnspan=3, pady=(15,5), sticky=tk.W)
        ttk.Label(quickfrm, text="Szybkie pozycje serwa: ").pack(side=tk.LEFT)
        for kat in [0, 90, 180]:
            ttk.Button(quickfrm, text=f"{kat}°", width=6,
                       bootstyle=INFO, command=lambda k=kat: self.wyslij_komende(f"S{k}")).pack(side=tk.LEFT, padx=3)

        # Panel wyboru daty i czujnika dla historii odczytów
        day_today = datetime.date.today().strftime("%Y-%m-%d")  # Domyślnie dzisiejsza data
        self.history_sensor_type = tk.StringVar(value="temperature")
        self.history_date = tk.StringVar(value=day_today)

        # Pole tekstowe dla daty
        ttk.Label(panel_history, text="Data (RRRR-MM-DD):", font=("Arial", 11)).grid(row=0, column=0, sticky=tk.E, pady=4, padx=(2,2))
        ent_date = ttk.Entry(panel_history, textvariable=self.history_date, width=13, font=("Arial", 11))
        ent_date.grid(row=0, column=1, sticky=tk.W, pady=4, padx=(2,13))

        # Lista rozwijana z czujnikami do wyboru
        ttk.Label(panel_history, text="Czujnik:", font=("Arial", 11)).grid(row=0, column=2, sticky=tk.E, padx=(5,2))
        sens_list = list(SENSOR_LABELS.keys())
        cmb_czujnik = ttk.Combobox(panel_history,
                                   values=sens_list,
                                   textvariable=self.history_sensor_type,
                                   width=17,
                                   state="readonly",
                                   font=("Arial", 11))
        cmb_czujnik.grid(row=0, column=3, sticky=tk.W, pady=4)

        # Przycisk pokazujący historię po wybraniu daty i czujnika
        ttk.Button(panel_history, text="Pokaż", bootstyle="info", command=self.pokaz_historie).grid(row=0, column=4, padx=10, pady=4)

        # Tekst do wyświetlania historii
        self.historia_text = tk.Text(panel_history, height=18, width=70, font=("Courier", 10), state="disabled", wrap="none")
        self.historia_text.grid(row=1, column=0, columnspan=5, pady=(20,5), padx=5)

        # Pionowy scrollbar do historii
        scrollbar = ttk.Scrollbar(panel_history, orient=tk.VERTICAL, command=self.historia_text.yview)
        scrollbar.grid(row=1, column=5, sticky=tk.N+tk.S+tk.W, pady=(20,5))
        self.historia_text.config(yscrollcommand=scrollbar.set)

        # Panel logu komunikacji sprzętowej -- pokazuje wysyłane / odebrane dane
        log_frame = ttk.LabelFrame(main, text="Log komunikacji", bootstyle=DARK, padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.log_text = tk.Text(log_frame, height=10, font=("Courier", 10))
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar_log = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar_log.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar_log.set)

        # Stopka z informacją i przyciskiem zamknięcia aplikacji
        footer_frame = ttk.Frame(main)
        footer_frame.pack(fill=tk.X, pady=5)
        ttk.Label(footer_frame, text="© 2025 Akademia WSB - Projekt Smart House", font=("Arial", 9)).pack(side=tk.LEFT)
        ttk.Button(footer_frame, text="Zamknij", bootstyle="danger", command=self.zamknij_aplikacje).pack(side=tk.RIGHT)

        # Uruchomienie wątku do odczytu danych w tle (daemon - zakończy się z głównym wątkiem)
        self.thread = Thread(target=self.odczytuj_dane, daemon=True)
        self.thread.start()

        # Przechwycenie zamknięcia okna (krzyżyk)
        self.root.protocol("WM_DELETE_WINDOW", self.zamknij_aplikacje)

    # Funkcja wysyłająca polecenia do sprzętu/symulacji przez port szeregowy
    def wyslij_komende(self, komenda):
        try:
            self.log_text.insert(tk.END, f"Wysyłanie: {komenda}\n")
            self.log_text.see(tk.END)  # przewinięcie do końca
            self.ser.write(f"{komenda}\n".encode('utf-8'))
        except Exception as e:
            messagebox.showerror("Błąd komunikacji", f"Nie można wysłać komendy: {str(e)}")

    # Wątek ciągłego odczytu danych z portu
    def odczytuj_dane(self):
        while self.running:
            try:
                if self.ser.in_waiting > 0:                 # jeśli są dane do odczytu
                    line = self.ser.readline().decode('utf-8').strip()  # odczytaj linię
                    if not line:
                        continue
                    # Dodaj odczyt do logu tekstowego
                    self.log_text.insert(tk.END, f"Odebrano: {line}\n")
                    self.log_text.see(tk.END)

                    # Definicja wzorców do parsowania linii z danymi
                    parsers = [
                        ('temperature', r'Temperatura:\s+([0-9.]+)'),
                        ('humidity', r'Wilgotnosc:\s+([0-9.]+)'),
                        ('oxygen', r'Jakosc Tlenu:\s+([0-9]+)'),
                        ('light', r'Naswietlenie:\s+([0-9]+)'),
                        ('motion', r'Ruch:\s+(WYKRYTO|BRAK)'),
                        ('status', r'Status:\s+(ALARM|Monitoring)'),
                    ]
                    # Parsuj linię pod kątem wzorców i aktualizuj GUI oraz bazę
                    for key, pattern in parsers:
                        m = re.search(pattern, line)
                        if m:
                            val = m.group(1)
                            self.ostatni_odczyt[key] = val
                            self.sensor_vars[key].set(val)
                            self.db.save(key, val)
            except Exception as e:
                # W przypadku błędu umieszczamy go w logu
                self.log_text.insert(tk.END, f"Błąd odczytu: {str(e)}\n")
                self.log_text.see(tk.END)
            time.sleep(0.15)  # krótka pauza aby nie zablokować CPU

    # Funkcja wyświetlająca w panelu historię odczytów dla wybranego dnia i czujnika
    def pokaz_historie(self):
        date = self.history_date.get()
        sensor = self.history_sensor_type.get()
        if not date or not sensor:
            messagebox.showwarning("Uwaga", "Proszę wybrać datę i czujnik.")
            return

        # Walidacja formatu daty YYYY-MM-DD
        try:
            datetime.datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Błąd", "Niepoprawny format daty, użyj RRRR-MM-DD")
            return

        # Pobieramy rekordy z bazy
        rows = self.db.get_by_day(date, sensor)
        self.historia_text.config(state="normal")
        self.historia_text.delete("1.0", tk.END)
        if not rows:
            self.historia_text.insert(tk.END, "Brak odczytów dla wybranego dnia i czujnika.\n")
        else:
            # Wypisujemy czas i wartość
            for t, val in rows:
                self.historia_text.insert(tk.END, f"{t[:19]} | {val}\n")
        self.historia_text.config(state="disabled")

    # Funkcja zamykająca aplikację - zatrzymuje wątek i zamyka port
    def zamknij_aplikacje(self):
        if messagebox.askokcancel("Zamknij", "Czy na pewno chcesz zamknąć aplikację?"):
            self.running = False
            if self.thread.is_alive():
                self.thread.join(timeout=1.0)
            if not TRYB_SYMULACJI and self.ser and self.ser.is_open:
                self.ser.close()
            self.root.destroy()

# Funkcja uruchamiająca aplikację
def main():
    try:
        ser = None
        if TRYB_SYMULACJI:
            # Utworzenie symulowanego portu
            ser = SymulowanyPort()
        else:
            try:
                import serial  # import biblioteki do komunikacji z portem szeregowym
            except ImportError:
                root = ttk.Window()
                root.withdraw()
                messagebox.showerror("Błąd importu", "Biblioteka 'pyserial' nie jest zainstalowana.\nAby użyć portu szeregowego, wykonaj: pip install pyserial")
                return
            try:
                # Próba otwarcia portu szeregowego
                ser = serial.Serial(PORT_SZEREGOWY, PREDKOSC, timeout=1)
                time.sleep(2)  # Czekanie na inicjalizację urządzenia (np. Arduino)
            except Exception as e:
                root = ttk.Window()
                root.withdraw()
                messagebox.showerror("Błąd portu szeregowego", f"Nie udało się otworzyć {PORT_SZEREGOWY}:\n{str(e)}")
                return

        # Utworzenie głównego okna aplikacji
        root = ttk.Window(themename="minty")
        app = AplikacjaSterowania(root, ser)
        root.mainloop()

        # Zamknięcie portu po zamknięciu aplikacji
        if not TRYB_SYMULACJI and ser and ser.is_open:
            ser.close()
    except Exception as e:
        root = ttk.Window()
        root.withdraw()
        messagebox.showerror("Błąd aplikacji", f"Wystąpił nieoczekiwany błąd:\n{str(e)}")

# Standardowy warunek uruchomienia programu jako główny skrypt
if __name__ == "__main__":
    main()