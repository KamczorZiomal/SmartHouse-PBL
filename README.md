# Projekt Smart House - AKADEMIA WSB

## 📋 Spis treści
- [Opis projektu](#opis-projektu)
- [Komponenty](#komponenty)
- [Schemat połączeń](#schemat-połączeń)
- [Instalacja](#instalacja)
- [Instrukcja obsługi](#instrukcja-obsługi)
- [Dostępne komendy](#dostępne-komendy)
- [Funkcjonalności](#funkcjonalności)
- [Rozwiązywanie problemów](#rozwiązywanie-problemów)
- [Autorzy](#autorzy)

## 📝 Opis projektu
Projekt Smart House to wieloczujnikowy system monitoringu i sterowania dla inteligentnego domu, stworzony jako projekt studencki dla Akademii WSB. System umożliwia monitoring parametrów środowiskowych (temperatura, wilgotność, jakość powietrza, natężenie światła), wykrywanie ruchu oraz sterowanie urządzeniami wykonawczymi (LEDy, buzzer, serwo, silnik krokowy).

Główne cechy systemu:
- Monitoring parametrów środowiskowych w czasie rzeczywistym
- Wykrywanie ruchu w pomieszczeniu
- Sterowanie oświetleniem LED
- Sterowanie elementami wykonawczymi (serwo, silnik krokowy)
- Sygnalizacja dźwiękowa (buzzer)
- Wizualizacja danych na wyświetlaczu OLED
- Możliwość sterowania poprzez komendy przesyłane przez port szeregowy

## 🛠️ Komponenty
Do zbudowania systemu potrzebne są następujące komponenty:

### Czujniki:
- DHT22 - czujnik temperatury i wilgotności
- MQ135 - czujnik jakości powietrza
- BH1750 - czujnik natężenia światła
- HC-SR501 (PIR) - czujnik ruchu

### Elementy wykonawcze:
- MOSFET IRFZ44N - do sterowania LEDami
- Serwo SG90 - silnik sterujący
- Silnik krokowy 28BYJ-48 z modułem sterownika ULN2003
- Buzzer KY-012 - sygnalizator dźwiękowy

### Wyświetlacz:
- Wyświetlacz OLED SSD1306 (128x64 piksele) z interfejsem I2C

### Płytka główna:
- Arduino Mega 2560 (lub kompatybilna)

### Dodatkowe elementy:
- Kable połączeniowe
- Płytki stykowe
- Zasilacz 12V DC

## 🔌 Schemat połączeń

### Piny Arduino:
- **Pin 2**: DHT22 (dane)
- **Pin 3**: PIR (czujnik ruchu)
- **Pin A2**: MQ135 (wyjście analogowe)
- **Pin 53**: Buzzer
- **Pin 22**: MOSFET IRFZ44N (sterowanie LEDami)
- **Pin 9**: Serwo SG90
- **Piny 30-33**: Silnik krokowy 28BYJ-48 (IN1-IN4)
- **Piny SDA/SCL**: Wyświetlacz OLED SSD1306 i BH1750 (I2C)

### Schemat graficzny:

![image](https://github.com/user-attachments/assets/f26600e6-63f5-4810-8ac6-7f70de848ec2)


## 💻 Instalacja

### Wymagane biblioteki:
Przed wgraniem kodu należy zainstalować następujące biblioteki:
- **DHT.h** (by Adafruit) - do obsługi czujnika temperatury i wilgotności DHT22
- **Wire.h** - do komunikacji I2C (wbudowana w Arduino IDE)
- **Adafruit_GFX.h** - biblioteka graficzna dla wyświetlaczy
- **Adafruit_SSD1306.h** - obsługa wyświetlacza OLED SSD1306
- **MQ135.h** (by GeorgK) - obsługa czujnika jakości powietrza MQ135
- **BH1750.h** (by Christopher Laws) - obsługa czujnika natężenia światła BH1750
- **Servo.h** - obsługa serwomechanizmu SG90 (wbudowana w Arduino IDE)
- **Stepper.h** - obsługa silnika krokowego 28BYJ-48 (wbudowana w Arduino IDE)

### Procedura instalacji:
1. Zainstaluj Arduino IDE ze strony [arduino.cc](https://www.arduino.cc/en/software)
2. Zainstaluj wymagane biblioteki poprzez Menedżer Bibliotek (Szkic > Dołącz bibliotekę > Zarządzaj bibliotekami...)
3. Podłącz komponenty zgodnie ze schematem
4. Podłącz Arduino do komputera za pomocą kabla USB
5. Wybierz odpowiednią płytkę (Arduino Mega 2560) i port COM
6. Wgraj kod do Arduino
7. Otwórz Monitor Portu Szeregowego (9600 baud) do obserwacji danych i wysyłania komend

## 🎮 Instrukcja obsługi

### Uruchomienie systemu:
1. Po wgraniu kodu i podłączeniu zasilania, system przeprowadzi procedurę inicjalizacji:
   - Pokaże ekran powitalny "AKADEMIA WSB - PROJEKT SMART HOUSE"
   - Zainicjalizuje wszystkie czujniki z paskiem postępu
   - Wykona test buzzera (dwa krótkie sygnały)
   - Przeprowadzi test serwo SG90
   - Przeprowadzi 60-sekundową stabilizację czujnika ruchu PIR

2. Po zakończeniu inicjalizacji, system rozpocznie regularny monitoring:
   - Dane z czujników będą wyświetlane na ekranie OLED
   - Pełny raport będzie wysyłany przez port szeregowy co 1 sekundę
   - System będzie reagował na wykrycie ruchu

### Obserwacja danych:
- Wyświetlacz OLED pokazuje aktualne odczyty:
  - Temperatura w °C
  - Wilgotność w %
  - Jakość powietrza w %
  - Natężenie światła w %
  - Status wykrycia ruchu
  - Status przekaźnika (LEDy)
  - Pozycja serwo

- Monitor Portu Szeregowego wyświetla szczegółowy raport zawierający:
  - Wszystkie dane z czujników
  - Status urządzeń wykonawczych
  - Listę dostępnych komend

## 📟 Dostępne komendy
System można sterować poprzez wysyłanie komend przez Monitor Portu Szeregowego:

- **LED_ON** - włączenie LEDów
- **LED_OFF** - wyłączenie LEDów
- **BUZZER_ON** - włączenie buzzera
- **BUZZER_OFF** - wyłączenie buzzera
- **SG90_0** - obrót serwo do pozycji 0 stopni (początkowej)
- **SG90_1** - obrót serwo do pozycji 90 stopni
- **SG90_2** - obrót serwo do pozycji 180 stopni
- **SG90_X** - obrót serwo do pozycji X stopni (gdzie X to liczba od 0 do 180)
- **Silnik_ruch** - obrót silnika krokowego o 500 kroków w prawo
- **Silnik_lewo** - obrót silnika krokowego o 500 kroków w lewo
- **SERWO_TEST** - przeprowadzenie testu ruchu serwo

## ⚙️ Funkcjonalności

### Monitoring parametrów środowiskowych:
- **Temperatura**: Pomiar aktualnej temperatury otoczenia w stopniach Celsjusza
- **Wilgotność**: Pomiar względnej wilgotności powietrza w procentach
- **Jakość powietrza**: Określenie jakości powietrza w skali procentowej
- **Natężenie światła**: Pomiar natężenia oświetlenia w procentach i luksach

### Wykrywanie ruchu:
- System wykrywa ruch w pomieszczeniu za pomocą czujnika PIR
- Automatyczne resetowanie stanu wykrycia ruchu po 3 sekundach braku aktywności

### Sterowanie urządzeniami:
- **LEDy**: Włączanie/wyłączanie oświetlenia LED poprzez przekaźnik SSR
- **Buzzer**: Sterowanie sygnalizacją dźwiękową
- **Serwo SG90**: Możliwość ustawienia pozycji serwo w zakresie 0-180 stopni
- **Silnik krokowy**: Sterowanie obrotem silnika krokowego w obu kierunkach

### Wizualizacja danych:
- Wyświetlanie wszystkich parametrów na ekranie OLED
- Wysyłanie szczegółowych raportów przez port szeregowy

## 🔧 Rozwiązywanie problemów

### Problem: Zawieszający się pasek led / nie przestaje świecić
**Rozwiązanie**: 
- Upewnij się, że rezystor podciągający (10kΩ) jest podłączony między bramką (gate) a źródłem (source) Mosfeta (zapewni to stabilny stan niski, gdy Arduino nie podaje sygnału, co zapobiega zawieszaniu się tranzystora)
- Zrestartuj Arduino

### Problem: Brak danych z czujnika DHT22
**Rozwiązanie**: 
- Sprawdź prawidłowość podłączenia (pin danych, zasilanie)
- Upewnij się, że rezystor podciągający (4.7kΩ) jest podłączony między pinem danych a VCC
- Zrestartuj Arduino

### Problem: Brak wykrywania ruchu
**Rozwiązanie**:
- Odczekaj 60 sekund po uruchomieniu systemu (czas stabilizacji PIR)
- Sprawdź regulację czułości na module PIR (potencjometr)
- Zweryfikuj zasilanie czujnika (wymaga stabilnego 5V)

### Problem: Nieprawidłowe wskazania czujnika MQ135
**Rozwiązanie**:
- Czujnik MQ135 wymaga wstępnego nagrzewania (około 24 godziny dla pełnej kalibracji)
- Sprawdź czy jest odpowiednio zasilany (5V)

### Problem: Nie działa wyświetlacz OLED
**Rozwiązanie**:
- Sprawdź połączenia I2C (SDA, SCL)
- Zweryfikuj adres I2C wyświetlacza (domyślnie 0x3C, niektóre modele używają 0x3D)
- Uruchom skaner I2C aby znaleźć prawidłowy adres urządzenia

### Problem: Serwo nie reaguje na komendy
**Rozwiązanie**:
- Upewnij się, że serwo jest podłączone do odpowiedniego pinu PWM
- Sprawdź zasilanie serwo (może wymagać dodatkowego źródła zasilania)
- Zweryfikuj poprawność podłączenia przewodów (GND, VCC, sygnał)

## 👨‍💻 Autorzy
Projekt został stworzony jako praca studencka w ramach zajęć na Akademii WSB.

---

© 2025 Autorzy projektu. Projekt studencki wykonany w ramach zajęć na Akademii WSB.
