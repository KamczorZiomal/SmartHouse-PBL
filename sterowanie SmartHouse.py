import serial
import time
import tkinter as tk
from tkinter import ttk, messagebox
from threading import Thread
import re

# Konfiguracja
PORT_SZEREGOWY = 'COM1'  # Zmień to na port Twojego Arduino (np. COM3, /dev/ttyUSB0)
PREDKOSC = 9600

class AplikacjaSterowania:
    def __init__(self, root, polaczenie_szeregowe):
        self.root = root
        self.root.title("System Smart House - Sterowanie")
        self.ser = polaczenie_szeregowe
        self.running = True

        # Ramka główna
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Tytuł
        title_label = ttk.Label(main_frame, text="System Smart House - Akademia WSB", font=("Helvetica", 16, "bold"))
        title_label.pack(pady=10)

        # Panel sterowania i odczytów
        split_frame = ttk.Frame(main_frame)
        split_frame.pack(fill=tk.BOTH, expand=True)

        control_frame = ttk.LabelFrame(split_frame, text="Panel Sterowania", padding="10")
        control_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        readings_frame = ttk.LabelFrame(split_frame, text="Odczyty Czujników", padding="10")
        readings_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        # Sterowanie serwo SG90
        servo_frame = ttk.LabelFrame(control_frame, text="Serwo SG90", padding="10")
        servo_frame.pack(fill=tk.X, pady=10)
        self.servo_value = tk.IntVar(value=90)
        servo_slider = ttk.Scale(servo_frame, from_=0, to=180, orient=tk.HORIZONTAL, 
                                 variable=self.servo_value, length=300)
        servo_slider.pack(fill=tk.X, pady=5)
        ttk.Button(servo_frame, text="Ustaw Serwo", 
                   command=lambda: self.wyslij_komende(f"S{self.servo_value.get()}")).pack(pady=5)

        # Silnik krokowy
        stepper_frame = ttk.LabelFrame(control_frame, text="Silnik Krokowy 28BYJ-48", padding="10")
        stepper_frame.pack(fill=tk.X, pady=10)
        self.stepper_value = tk.IntVar(value=0)
        stepper_slider = ttk.Scale(stepper_frame, from_=-2048, to=2048, orient=tk.HORIZONTAL, 
                                   variable=self.stepper_value, length=300)
        stepper_slider.pack(fill=tk.X, pady=5)
        ttk.Button(stepper_frame, text="Wykonaj Kroki", 
                   command=lambda: self.wyslij_komende(f"M{self.stepper_value.get()}")).pack(pady=5)

        # Przyciski szybkiego sterowania
        quick_frame = ttk.LabelFrame(control_frame, text="Szybkie Sterowanie", padding="10")
        quick_frame.pack(fill=tk.X, pady=10)
        ttk.Button(quick_frame, text="Serwo 0°", command=lambda: self.wyslij_komende("S0")).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(quick_frame, text="Serwo 90°", command=lambda: self.wyslij_komende("S90")).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(quick_frame, text="Serwo 180°", command=lambda: self.wyslij_komende("S180")).pack(side=tk.LEFT, padx=5, pady=5)

        # Buzzer
        buzzer_frame = ttk.LabelFrame(control_frame, text="Buzzer", padding="10")
        buzzer_frame.pack(fill=tk.X, pady=10)
        ttk.Button(buzzer_frame, text="Włącz Buzzer", command=lambda: self.wyslij_komende("B1")).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(buzzer_frame, text="Wyłącz Buzzer", command=lambda: self.wyslij_komende("B0")).pack(side=tk.LEFT, padx=5, pady=5)

    def wyslij_komende(self, komenda):
        """Wysyła komendę do Arduino"""
        try:
            self.ser.write(f"{komenda}\n".encode('utf-8'))
            print(f"Wysyłano: {komenda}")
        except Exception as e:
            messagebox.showerror("Błąd komunikacji", f"Nie można wysłać komendy: {str(e)}")

def main():
    try:
        ser = serial.Serial(PORT_SZEREGOWY, PREDKOSC, timeout=1)
        time.sleep(2)  # poczekaj aż Arduino się zainicjalizuje
        root = tk.Tk()
        app = AplikacjaSterowania(root, ser)
        root.mainloop()
        if ser.is_open:
            ser.close()
    except serial.SerialException as e:
        print(f"Błąd połączenia: {e}")

if __name__ == "__main__":
    main()