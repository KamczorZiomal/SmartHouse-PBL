import sqlite3
import serial
import time
from threading import Thread

# Konfiguracja portu szeregowego
PORT_SZEREGOWY = 'COM4'  # Zmień na własny port (np. '/dev/ttyUSB0' na Linux)
PREDKOSC = 9600

# Ścieżka do bazy danych SQLite
DB_PATH = 'dane_czujnikow.db'

def odczyt_z_bazy():
    """Odczytuje najnowsze dane z bazy danych."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT temperatura, wilgotnosc, jakosc_tlenu, naswietlenie, ruch, status
            FROM czujniki
            ORDER BY timestamp DESC LIMIT 1
        ''')
        row = cursor.fetchone()
        return {
            'temperatura': row[0],
            'wilgotnosc': row[1],
            'jakosc_tlenu': row[2],
            'naswietlenie': row[3],
            'ruch': row[4],
            'status': row[5]
        } if row else None
    except Exception as e:
        print(f"Błąd odczytu z bazy: {e}")
        return None
    finally:
        conn.close()

def wyslij_dane(ser, dane):
    """Wysyła dane w odpowiednim formacie przez port szeregowy."""
    if not dane:
        return
    # Przykład formatu: 
    # T:25.3;W:40.2;J:82;N:70;R:BRAK;S:Monitoring
    komenda = (
        f"T:{dane['temperatura']};"
        f"W:{dane['wilgotnosc']};"
        f"J:{dane['jakosc_tlenu']};"
        f"N:{dane['naswietlenie']};"
        f"R:{dane['ruch']};"
        f"S:{dane['status']}"
    )
    try:
        ser.write((komenda + '\n').encode('utf-8'))
        print(f"Wysłano: {komenda}")
    except Exception as e:
        print(f"Błąd wysyłki: {e}")

def main():
    # Nawiązanie połączenia z portem szeregowym
    try:
        ser = serial.Serial(PORT_SZEREGOWY, PREDKOSC, timeout=1)
        time.sleep(2)  # odczekaj na inicjalizację portu
    except Exception as e:
        print(f"Nie można otworzyć portu {PORT_SZEREGOWY}: {e}")
        return

    def cykl():
        while True:
            dane = odczyt_z_bazy()
            wyslij_dane(ser, dane)
            time.sleep(5)  # odśwież co 5 sekund

    # Wykonuj cykl w wątku
    thread = Thread(target=cykl, daemon=True)
    thread.start()

    # Główny wątek – pozwala na zatrzymanie Ctrl+C
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Zakończono.")
        if ser.is_open:
            ser.close()

if __name__ == '__main__':
    main()