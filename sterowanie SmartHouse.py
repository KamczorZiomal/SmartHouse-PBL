import serial
import time
import tkinter as tk
from tkinter import ttk, messagebox
from threading import Thread
import re

# Konfiguracja
PORT_SZEREGOWY = 'COM4'  # Zmień to na port Twojego Arduino (np. COM3, /dev/ttyUSB0)
PREDKOSC = 9600

class AplikacjaSterowania:
    def __init__(self, root, polaczenie_szeregowe):
        self.root = root
        self.root.title("System Smart House - Sterowanie")
        self.ser = polaczenie_szeregowe
        self.running = True
        
        # Zmienne do przechowywania odczytów z czujników
        self.temperatura = tk.StringVar(value="0.0 °C")
        self.wilgotnosc = tk.StringVar(value="0.0 %")
        self.jakosc_powietrza = tk.StringVar(value="0 %")
        self.naswietlenie = tk.StringVar(value="0 %")
        self.ruch = tk.StringVar(value="BRAK")
        self.status_alarmu = tk.StringVar(value="Monitoring")
        
        # Szerokość i wysokość okna aplikacji
        self.root.geometry("800x600")
        
        # Ramka główna
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Tytuł aplikacji
        title_label = ttk.Label(main_frame, text="System Smart House - Akademia WSB", font=("Helvetica", 16, "bold"))
        title_label.pack(pady=10)
        
        # Ramka z podziałem na panel sterowania i panel odczytów
        split_frame = ttk.Frame(main_frame)
        split_frame.pack(fill=tk.BOTH, expand=True)
        
        # Panel sterowania (lewa strona)
        control_frame = ttk.LabelFrame(split_frame, text="Panel Sterowania", padding="10")
        control_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Panel odczytów (prawa strona)
        readings_frame = ttk.LabelFrame(split_frame, text="Odczyty Czujników", padding="10")
        readings_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Sterowanie serwo SG90
        servo_frame = ttk.LabelFrame(control_frame, text="Serwo SG90", padding="10")
        servo_frame.pack(fill=tk.X, pady=10)
        
        self.servo_value = tk.IntVar(value=90)
        
        servo_slider = ttk.Scale(servo_frame, from_=0, to=180, orient=tk.HORIZONTAL, 
                                 variable=self.servo_value, length=300)
        servo_slider.pack(fill=tk.X, pady=5)
        
        servo_value_frame = ttk.Frame(servo_frame)
        servo_value_frame.pack(fill=tk.X)
        
        ttk.Label(servo_value_frame, text="Kąt:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(servo_value_frame, textvariable=tk.StringVar(value=lambda: f"{self.servo_value.get()}°"),
                  width=5).pack(side=tk.LEFT)
        
        servo_button = ttk.Button(servo_frame, text="Ustaw Serwo", 
                                  command=lambda: self.wyslij_komende(f"S{self.servo_value.get()}"))
        servo_button.pack(pady=5)
        
        # Sterowanie silnikiem krokowym 28BYJ-48
        stepper_frame = ttk.LabelFrame(control_frame, text="Silnik Krokowy 28BYJ-48", padding="10")
        stepper_frame.pack(fill=tk.X, pady=10)
        
        self.stepper_value = tk.IntVar(value=0)
        
        stepper_slider = ttk.Scale(stepper_frame, from_=-2048, to=2048, orient=tk.HORIZONTAL, 
                                  variable=self.stepper_value, length=300)
        stepper_slider.pack(fill=tk.X, pady=5)
        
        stepper_value_frame = ttk.Frame(stepper_frame)
        stepper_value_frame.pack(fill=tk.X)
        
        ttk.Label(stepper_value_frame, text="Kroki:").pack(side=tk.LEFT, padx=(0, 5))
        
        def update_step_label(*args):
            stepper_label["text"] = str(self.stepper_value.get())
        
        self.stepper_value.trace_add("write", update_step_label)
        stepper_label = ttk.Label(stepper_value_frame, text="0", width=6)
        stepper_label.pack(side=tk.LEFT)
        
        stepper_button = ttk.Button(stepper_frame, text="Wykonaj Kroki", 
                                   command=lambda: self.wyslij_komende(f"M{self.stepper_value.get()}"))
        stepper_button.pack(pady=5)
        
        # Przyciski szybkiego dostępu
        quick_frame = ttk.LabelFrame(control_frame, text="Szybkie Sterowanie", padding="10")
        quick_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(quick_frame, text="Serwo 0°", 
                  command=lambda: self.wyslij_komende("S0")).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(quick_frame, text="Serwo 90°", 
                  command=lambda: self.wyslij_komende("S90")).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(quick_frame, text="Serwo 180°", 
                  command=lambda: self.wyslij_komende("S180")).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Sterowanie buzzerem
        buzzer_frame = ttk.LabelFrame(control_frame, text="Buzzer", padding="10")
        buzzer_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(buzzer_frame, text="Włącz Buzzer", 
                  command=lambda: self.wyslij_komende("B1")).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(buzzer_frame, text="Wyłącz Buzzer", 
                  command=lambda: self.wyslij_komende("B0")).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Panel odczytów z czujników
        readings_inner_frame = ttk.Frame(readings_frame)
        readings_inner_frame.pack(fill=tk.BOTH, expand=True)
        
        # Etykiety i pola wartości dla odczytów
        readings_style = ttk.Style()
        readings_style.configure("Reading.TLabel", font=("Helvetica", 12))
        readings_style.configure("ReadingValue.TLabel", font=("Helvetica", 12, "bold"))
        
        # Temperatura
        ttk.Label(readings_inner_frame, text="Temperatura:", style="Reading.TLabel").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Label(readings_inner_frame, textvariable=self.temperatura, style="ReadingValue.TLabel").grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # Wilgotność
        ttk.Label(readings_inner_frame, text="Wilgotność:", style="Reading.TLabel").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Label(readings_inner_frame, textvariable=self.wilgotnosc, style="ReadingValue.TLabel").grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Jakość powietrza
        ttk.Label(readings_inner_frame, text="Jakość tlenu:", style="Reading.TLabel").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Label(readings_inner_frame, textvariable=self.jakosc_powietrza, style="ReadingValue.TLabel").grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # Natężenie światła
        ttk.Label(readings_inner_frame, text="Naświetlenie:", style="Reading.TLabel").grid(row=3, column=0, sticky=tk.W, pady=5)
        ttk.Label(readings_inner_frame, textvariable=self.naswietlenie, style="ReadingValue.TLabel").grid(row=3, column=1, sticky=tk.W, pady=5)
        
        # Status ruchu
        ttk.Label(readings_inner_frame, text="Ruch:", style="Reading.TLabel").grid(row=4, column=0, sticky=tk.W, pady=5)
        ruch_label = ttk.Label(readings_inner_frame, textvariable=self.ruch, style="ReadingValue.TLabel")
        ruch_label.grid(row=4, column=1, sticky=tk.W, pady=5)
        
        # Status alarmu
        ttk.Label(readings_inner_frame, text="Status:", style="Reading.TLabel").grid(row=5, column=0, sticky=tk.W, pady=5)
        status_label = ttk.Label(readings_inner_frame, textvariable=self.status_alarmu, style="ReadingValue.TLabel")
        status_label.grid(row=5, column=1, sticky=tk.W, pady=5)
        
        # Terminal - log komunikacji
        log_frame = ttk.LabelFrame(main_frame, text="Log komunikacji", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.log_text = tk.Text(log_frame, height=10, width=80, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.pack(fill=tk.Y, side=tk.RIGHT)
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        # Stopka
        footer_frame = ttk.Frame(main_frame)
        footer_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(footer_frame, text="© 2025 Akademia WSB - Projekt Smart House", 
                 font=("Helvetica", 8)).pack(side=tk.LEFT)
        
        ttk.Button(footer_frame, text="Zamknij", command=self.zamknij_aplikacje).pack(side=tk.RIGHT)
        
        # Rozpocznij odczyt danych w tle
        self.thread = Thread(target=self.odczytuj_dane)
        self.thread.daemon = True
        self.thread.start()
        
        # Reaguj na zamknięcie okna
        self.root.protocol("WM_DELETE_WINDOW", self.zamknij_aplikacje)
    
    def wyslij_komende(self, komenda):
        """Wysyła komendę do Arduino"""
        try:
            self.log_text.insert(tk.END, f"Wysyłanie: {komenda}\n")
            self.log_text.see(tk.END)
            self.ser.write(f"{komenda}\n".encode('utf-8'))
        except Exception as e:
            messagebox.showerror("Błąd komunikacji", f"Nie można wysłać komendy: {str(e)}")
    
    def odczytuj_dane(self):
        """Wątek do ciągłego odczytu danych z Arduino"""
        while self.running:
            try:
                if self.ser.in_waiting > 0:
                    line = self.ser.readline().decode('utf-8').strip()
                    self.log_text.insert(tk.END, f"Odebrano: {line}\n")
                    self.log_text.see(tk.END)
                    
                    # Parsowanie odczytów z czujników
                    if "Temperatura:" in line:
                        match = re.search(r"Temperatura:\s+(\d+\.\d+)", line)
                        if match:
                            self.temperatura.set(f"{match.group(1)} °C")
                    
                    elif "Wilgotnosc:" in line:
                        match = re.search(r"Wilgotnosc:\s+(\d+\.\d+)", line)
                        if match:
                            self.wilgotnosc.set(f"{match.group(1)} %")
                    
                    elif "Jakosc Tlenu:" in line:
                        match = re.search(r"Jakosc Tlenu:\s+(\d+)", line)
                        if match:
                            self.jakosc_powietrza.set(f"{match.group(1)} %")
                    
                    elif "Naswietlenie:" in line:
                        match = re.search(r"Naswietlenie:\s+(\d+)", line)
                        if match:
                            self.naswietlenie.set(f"{match.group(1)} %")
                    
                    elif "Ruch:" in line:
                        if "WYKRYTO" in line:
                            self.ruch.set("WYKRYTO!")
                        elif "BRAK" in line:
                            self.ruch.set("BRAK")
                    
                    elif "Status:" in line:
                        if "ALARM" in line:
                            self.status_alarmu.set("ALARM")
                        else:
                            self.status_alarmu.set("Monitoring")
                    
            except Exception as e:
                self.log_text.insert(tk.END, f"Błąd odczytu: {str(e)}\n")
            
            time.sleep(0.1)
    
    def zamknij_aplikacje(self):
        """Zamyka aplikację i zwalnia zasoby"""
        if messagebox.askokcancel("Zamknij", "Czy na pewno chcesz zamknąć aplikację?"):
            self.running = False
            if self.thread.is_alive():
                self.thread.join(timeout=1.0)
            self.root.destroy()

def main():
    try:
        # Nawiązanie połączenia z Arduino
        ser = serial.Serial(PORT_SZEREGOWY, PREDKOSC, timeout=1)
        # Daj czas na inicjalizację połączenia
        time.sleep(2)
        
        # Inicjalizacja aplikacji
        root = tk.Tk()
        app = AplikacjaSterowania(root, ser)
        root.mainloop()
        
        # Zamknięcie połączenia po zakończeniu aplikacji
        if ser.is_open:
            ser.close()
            
    except serial.SerialException as e:
        messagebox.showerror("Błąd połączenia", 
                             f"Nie udało się połączyć z Arduino na porcie {PORT_SZEREGOWY}.\n"
                             f"Błąd: {str(e)}\n\n"
                             "Sprawdź czy:\n"
                             "1. Arduino jest podłączone do komputera\n"
                             "2. Port szeregowy jest prawidłowy\n"
                             "3. Nie ma innego programu używającego tego portu")
    except Exception as e:
        messagebox.showerror("Błąd aplikacji", f"Wystąpił nieoczekiwany błąd: {str(e)}")

if __name__ == "__main__":
    main()