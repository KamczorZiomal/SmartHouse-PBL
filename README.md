# Smart House - System Sterowania i Monitoringu 🏠💡

![sterowaniev2](https://github.com/user-attachments/assets/0042981f-a723-418d-9e5e-0d5e5594d13b)

---

## Opis projektu 📋

**Smart House** to aplikacja desktopowa napisana w Pythonie z wykorzystaniem biblioteki `tkinter` oraz `ttkbootstrap`.  
Umożliwia **sterowanie urządzeniami IoT** (serwo, silnik krokowy, buzzer) oraz **monitorowanie różnych parametrów środowiskowych** (temperatura, wilgotność, jakość tlenu, natężenie światła, wykrycie ruchu, status alarmu).

Projekt powstał w celach edukacyjnych na potrzeby Akademii WSB i demonstruje m.in.:

- 🔌 Komunikację przez port szeregowy z rzeczywistym sprzętem (np. Arduino),
- 🤖 Tryb symulacji bez sprzętu — generowanie losowych danych,
- ⏳ Obsługę asynchronicznego odczytu danych w tle,
- 💾 Zapis i archiwizację odczytów do lokalnej bazy SQLite,
- 🖥️ Interfejs użytkownika w stylu modernistycznym z użyciem `ttkbootstrap`,
- 📅 Możliwość przeglądania historii pomiarów z wybranego dnia i konkretnego czujnika.

---

## Funkcjonalności ⚙️

- **Odczyt i wyświetlanie w czasie rzeczywistym** wartości czujników:
  - 🌡️ Temperatura,
  - 💧 Wilgotność,
  - 🌬️ Jakość tlenu,
  - 💡 Naświetlenie,
  - 🚶‍♂️ Ruch (wykrywanie),
  - 🚨 Status alarmu.

- **Sterowanie urządzeniami:**
  - 🎛️ Serwo SG90 (ustawianie kąta od 0° do 180°),
  - 🔄 Silnik krokowy 28BYJ-48 (wykonanie kroków),
  - 📢 Buzzer (włączanie/wyłączanie).

- 📝 **Log komunikacji** — podgląd wysyłanych komend i odebranych danych.

- 🧪 **Tryb symulacji** — brak sprzętu? Dane są generowane losowo.

- 📚 **Historia odczytów:**
  - Zapis danych do `SQLite`,
  - Możliwość wybrania daty i czujnika do przeglądania danych archiwalnych.

---

## Wymagania 📦

- Python 3.7 lub nowszy
- Biblioteki Pythona:
  - `ttkbootstrap` (nowoczesny GUI),
  - `pyserial` (do komunikacji z portem szeregowym, opcjonalne przy symulacji),

Instalacja:

```bash
pip install ttkbootstrap pyserial
```

### Uruchomienie ▶️

- Należy ustawić odpowiedni port szeregowy w konfiguracji — domyślnie `COM3`
Jeśli nie masz sprzętu, możesz zasymulować otrzymywanie danych
- W konfiguracji ustaw parametr `TRYB_SYMULACJI = True`