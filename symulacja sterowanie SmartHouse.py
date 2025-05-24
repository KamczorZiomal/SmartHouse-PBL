
import serial
import time
import tkinter as tk
from tkinter import ttk, messagebox
from threading import Thread
import re
import random

# Konfiguracja
PORT_SZEREGOWY = 'COM3'
PREDKOSC = 9600
TRYB_SYMULACJI = True

class SymulowanyPort:
    def __init__(self):
        self.in_waiting = 1
        self.counter = 0

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

# Klasa aplikacji - niezmieniona poza źródłem danych
class AplikacjaSterowania:
    def __init__(self, root, polaczenie_szeregowe):
        self.root = root
        self.root.title("System Smart House - Sterowanie")
        self.ser = polaczenie_szeregowe
        self.running = True

        self.temperatura = tk.StringVar(value="0.0 °C")
        self.wilgotnosc = tk.StringVar(value="0.0 %")
        self.jakosc_powietrza = tk.StringVar(value="0 %")
        self.naswietlenie = tk.StringVar(value="0 %")
        self.ruch = tk.StringVar(value="BRAK")
        self.status_alarmu = tk.StringVar(value="Monitoring")

        self.root.geometry("800x600")
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        title_label = ttk.Label(main_frame, text="System Smart House - Akademia WSB", font=("Helvetica", 16, "bold"))
        title_label.pack(pady=10)
        split_frame = ttk.Frame(main_frame)
        split_frame.pack(fill=tk.BOTH, expand=True)
        control_frame = ttk.LabelFrame(split_frame, text="Panel Sterowania", padding="10")
        control_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        readings_frame = ttk.LabelFrame(split_frame, text="Odczyty Czujników", padding="10")
        readings_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        servo_frame = ttk.LabelFrame(control_frame, text="Serwo SG90", padding="10")
        servo_frame.pack(fill=tk.X, pady=10)
        self.servo_value = tk.IntVar(value=90)
        servo_slider = ttk.Scale(servo_frame, from_=0, to=180, orient=tk.HORIZONTAL, variable=self.servo_value, length=300)
        servo_slider.pack(fill=tk.X, pady=5)
        servo_button = ttk.Button(servo_frame, text="Ustaw Serwo", command=lambda: self.wyslij_komende(f"S{self.servo_value.get()}"))
        servo_button.pack(pady=5)

        stepper_frame = ttk.LabelFrame(control_frame, text="Silnik Krokowy 28BYJ-48", padding="10")
        stepper_frame.pack(fill=tk.X, pady=10)
        self.stepper_value = tk.IntVar(value=0)
        stepper_slider = ttk.Scale(stepper_frame, from_=-2048, to=2048, orient=tk.HORIZONTAL, variable=self.stepper_value, length=300)
        stepper_slider.pack(fill=tk.X, pady=5)
        stepper_label = ttk.Label(stepper_frame, text="0", width=6)
        stepper_label.pack()
        self.stepper_value.trace_add("write", lambda *args: stepper_label.config(text=str(self.stepper_value.get())))
        stepper_button = ttk.Button(stepper_frame, text="Wykonaj Kroki", command=lambda: self.wyslij_komende(f"M{self.stepper_value.get()}"))
        stepper_button.pack(pady=5)

        quick_frame = ttk.LabelFrame(control_frame, text="Szybkie Sterowanie", padding="10")
        quick_frame.pack(fill=tk.X, pady=10)
        for kat in [0, 90, 180]:
            ttk.Button(quick_frame, text=f"Serwo {kat}°", command=lambda k=kat: self.wyslij_komende(f"S{k}")).pack(side=tk.LEFT, padx=5, pady=5)

        buzzer_frame = ttk.LabelFrame(control_frame, text="Buzzer", padding="10")
        buzzer_frame.pack(fill=tk.X, pady=10)
        ttk.Button(buzzer_frame, text="Włącz Buzzer", command=lambda: self.wyslij_komende("B1")).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(buzzer_frame, text="Wyłącz Buzzer", command=lambda: self.wyslij_komende("B0")).pack(side=tk.LEFT, padx=5, pady=5)

        readings_inner_frame = ttk.Frame(readings_frame)
        readings_inner_frame.pack(fill=tk.BOTH, expand=True)
        labels = [
            ("Temperatura:", self.temperatura),
            ("Wilgotność:", self.wilgotnosc),
            ("Jakość tlenu:", self.jakosc_powietrza),
            ("Naświetlenie:", self.naswietlenie),
            ("Ruch:", self.ruch),
            ("Status:", self.status_alarmu),
        ]
        for i, (txt, var) in enumerate(labels):
            ttk.Label(readings_inner_frame, text=txt).grid(row=i, column=0, sticky=tk.W, pady=5)
            ttk.Label(readings_inner_frame, textvariable=var).grid(row=i, column=1, sticky=tk.W, pady=5)

        log_frame = ttk.LabelFrame(main_frame, text="Log komunikacji", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        self.log_text = tk.Text(log_frame, height=10, width=80, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.pack(fill=tk.Y, side=tk.RIGHT)
        self.log_text.config(yscrollcommand=scrollbar.set)

        footer_frame = ttk.Frame(main_frame)
        footer_frame.pack(fill=tk.X, pady=5)
        ttk.Label(footer_frame, text="© 2025 Akademia WSB - Projekt Smart House", font=("Helvetica", 8)).pack(side=tk.LEFT)
        ttk.Button(footer_frame, text="Zamknij", command=self.zamknij_aplikacje).pack(side=tk.RIGHT)

        self.thread = Thread(target=self.odczytuj_dane)
        self.thread.daemon = True
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
                    self.log_text.insert(tk.END, f"Odebrano: {line}\n")
                    self.log_text.see(tk.END)
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
        if messagebox.askokcancel("Zamknij", "Czy na pewno chcesz zamknąć aplikację?"):
            self.running = False
            if self.thread.is_alive():
                self.thread.join(timeout=1.0)
            self.root.destroy()

def main():
    try:
        if TRYB_SYMULACJI:
            ser = SymulowanyPort()
        else:
            ser = serial.Serial(PORT_SZEREGOWY, PREDKOSC, timeout=1)
            time.sleep(2)
        root = tk.Tk()
        app = AplikacjaSterowania(root, ser)
        root.mainloop()
        if not TRYB_SYMULACJI and ser.is_open:
            ser.close()
    except Exception as e:
        messagebox.showerror("Błąd aplikacji", f"Wystąpił nieoczekiwany błąd: {str(e)}")

if __name__ == "__main__":
    main()
