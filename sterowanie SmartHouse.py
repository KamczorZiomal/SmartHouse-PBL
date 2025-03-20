import serial
import time
import tkinter as tk
from tkinter import ttk, messagebox
from threading import Thread
import re
import queue

# Konfiguracja
PORT_SZEREGOWY = 'COM1'  # zmień na własny port
PREDKOSC = 9600

class AplikacjaSterowania:
    def __init__(self, root, ser):
        self.root = root
        self.ser = ser
        self.running = True
        self.queue = queue.Queue()

        # Zmienne odczytów
        self.temperatura = tk.StringVar(value="0.0 °C")
        self.wilgotnosc = tk.StringVar(value="0.0 %")
        self.jakosc_powietrza = tk.StringVar(value="0 %")
        self.naswietlenie = tk.StringVar(value="0 %")
        self.ruch = tk.StringVar(value="BRAK")
        self.status_alarmu = tk.StringVar(value="Monitoring")

        # GUI - prosty case
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(main_frame, text="Aktualne Czujniki:", font=("Helvetica", 14)).pack()

        ttk.Label(main_frame, textvariable=self.temperatura).pack()
        ttk.Label(main_frame, textvariable=self.wilgotnosc).pack()
        ttk.Label(main_frame, textvariable=self.jakosc_powietrza).pack()
        ttk.Label(main_frame, textvariable=self.naswietlenie).pack()
        ttk.Label(main_frame, textvariable=self.ruch).pack()
        ttk.Label(main_frame, textvariable=self.status_alarmu).pack()

        # Odczyt w osobnym wątku
        self.thread = Thread(target=self.odczytuj_dane)
        self.thread.daemon = True
        self.thread.start()

        # Pętla odświeżania GUI
        self.root.after(100, self.aktualizuj_gui)

        self.root.protocol("WM_DELETE_WINDOW", self.zamknij_aplikacje)

    def odczytuj_dane(self):
        while self.running:
            try:
                if self.ser.in_waiting > 0:
                    line = self.ser.readline().decode('utf-8').strip()
                    self.queue.put(line)
            except:
                pass
            time.sleep(0.1)

    def aktualizuj_gui(self):
        # Aktualizuj na podstawie kolejki
        while not self.queue.empty():
            line = self.queue.get()
            print(f"Parsed line: {line}")
            # Parsowanie
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
                else:
                    self.ruch.set("BRAK")
            elif "Status:" in line:
                if "ALARM" in line:
                    self.status_alarmu.set("ALARM")
                else:
                    self.status_alarmu.set("Monitoring")

        # zaplanuj ponowne odświeżenie GUI
        self.root.after(100, self.aktualizuj_gui)

    def zamknij_aplikacje(self):
        self.running = False
        self.root.destroy()

def main():
    try:
        ser = serial.Serial(PORT_SZEREGOWY, PREDKOSC, timeout=1)
        time.sleep(2)
        root = tk.Tk()
        app = AplikacjaSterowania(root, ser)
        root.mainloop()
        if ser.is_open:
            ser.close()
    except serial.SerialException as e:
        print(f"Błąd połączenia: {e}")

if __name__ == "__main__":
    main()