# Projekt Smart House - AKADEMIA WSB

## 📋 Spis treści
- Opis projektu
- Komponenty
- Schemat połączeń
- Instalacja
- Instrukcja obsługi
- Dostępne komendy
- Funkcjonalności
- Rozwiązywanie problemów
- Autorzy

## 📝 Opis projektu
Projekt Smart House to wieloczujnikowy system monitoringu i sterowania dla inteligentnego domu, stworzony jako projekt studencki dla Akademii WSB. System umożliwia monitoring parametrów środowiskowych (temperatura, wilgotność, jakość powietrza, natężenie światła), wykrywanie ruchu oraz sterowanie urządzeniami wykonawczymi (LEDy, buzzer, serwo, silnik krokowy).

**Główne cechy systemu:**
- Monitoring parametrów środowiskowych w czasie rzeczywistym
- Wykrywanie ruchu w pomieszczeniu
- Sterowanie oświetleniem LED
- Sterowanie elementami wykonawczymi (serwo, silnik krokowy)
- Sygnalizacja dźwiękowa (buzzer)
- Wizualizacja danych na wyświetlaczu OLED
- Możliwość sterowania poprzez komendy przesyłane przez port szeregowy
- Komunikacja bezprzewodowa przez ESP32

## 🛠️ Komponenty
Do zbudowania systemu potrzebne są następujące komponenty:

**Czujniki:**
- DHT22 - czujnik temperatury i wilgotności
- MQ135 - czujnik jakości powietrza
- BH1750 - czujnik natężenia światła
- HC-SR501 (PIR) - czujnik ruchu

**Elementy wykonawcze:**
- MOSFET IRFZ44N - do sterowania LEDami
- Serwo SG90 - silnik sterujący
- Silnik krokowy 28BYJ-48 z modułem sterownika ULN2003
- Buzzer KY-012 - sygnalizator dźwiękowy

**Wyświetlacz:**
- Wyświetlacz OLED SSD1306 (128x64 piksele) z interfejsem I2C

**Płytki główne:**
- Arduino Mega 2560 (lub kompatybilna)
- **ESP32 DevKit V1 C6** - moduł komunikacji bezprzewodowej

**Dodatkowe elementy:**
- Kable połączeniowe
- Płytki stykowe
- Zasilacz 12V DC

## 🔌 Schemat połączeń

**Piny Arduino:**
- Pin 2: DHT22 (dane)
- Pin 3: PIR (czujnik ruchu)
- Pin A2: MQ135 (wyjście analogowe)
- Pin 53: Buzzer
- Pin 22: MOSFET IRFZ44N (sterowanie LEDami)
- Pin 9: Serwo SG90
- Piny 30-33: Silnik krokowy 28BYJ-48 (IN1-IN4)
- Piny SDA/SCL: Wyświetlacz OLED SSD1306 i BH1750 (I2C)
- **Pin 18: TX (komunikacja z ESP32)**
- **Pin 19: RX (komunikacja z ESP32)**

**ESP32 DevKit V1 C6:**
- **Pin 18: RX (połączenie z Arduino pin 18 TX)**
- **Pin 19: TX (połączenie z Arduino pin 19 RX)**

## 💻 Instalacja

**Wymagane biblioteki:**
Przed wgraniem kodu należy zainstalować następujące biblioteki:

- DHT.h (by Adafruit) - do obsługi czujnika temperatury i wilgotności DHT22
- Wire.h - do komunikacji I2C (wbudowana w Arduino IDE)
- Adafruit_GFX.h - biblioteka graficzna dla wyświetlaczy
- Adafruit_SSD1306.h - obsługa wyświetlacza OLED SSD1306
- MQ135.h (by GeorgK) - obsługa czujnika jakości powietrza MQ135
- BH1750.h (by Christopher Laws) - obsługa czujnika natężenia światła BH1750
- Servo.h - obsługa serwomechanizmu SG90 (wbudowana w Arduino IDE)
- Stepper.h - obsługa silnika krokowego 28BYJ-48 (wbudowana w Arduino IDE)

**Procedura instalacji:**
1. Zainstaluj Arduino IDE ze strony arduino.cc
2. Zainstaluj wymagane biblioteki poprzez Menedżer Bibliotek (Szkic > Dołącz bibliotekę > Zarządzaj bibliotekami...)
3. Podłącz komponenty zgodnie ze schematem
4. Podłącz Arduino do komputera za pomocą kabla USB
5. **Podłącz ESP32 DevKit V1 C6 do pinów 18,19 Arduino (RX,TX)**
6. Wybierz odpowiednią płytkę (Arduino Mega 2560) i port COM
7. Wgraj kod do Arduino
8. Wgraj kod do ESP32 
9. Otwórz Monitor Portu Szeregowego (9600 baud) do obserwacji danych i wysyłania komend

## 🎮 Instrukcja obsługi

**Uruchomienie systemu:**
Po wgraniu kodu i podłączeniu zasilania, system przeprowadzi procedurę inicjalizacji:

1. Pokaże ekran powitalny "AKADEMIA WSB - PROJEKT SMART HOUSE"
2. Zainicjalizuje wszystkie czujniki z paskiem postępu
3. Ustanowi komunikację z ESP32
4. Wykona test buzzera (dwa krótkie sygnały)
5. Przeprowadzi test serwo SG90
6. Przeprowadzi 60-sekundową stabilizację czujnika ruchu PIR

Po zakończeniu inicjalizacji, system rozpocznie regularny monitoring:
- Dane z czujników będą wyświetlane na ekranie OLED
- Pełny raport będzie wysyłany przez port szeregowy co 1 sekundę
- System będzie reagował na wykrycie ruchu
- ESP32 umożliwi bezprzewodową komunikację i sterowanie

**Obserwacja danych:**
Wyświetlacz OLED pokazuje aktualne odczyty:
- Temperatura w °C
- Wilgotność w %
- Jakość powietrza w %
- Natężenie światła w %
- Status wykrycia ruchu
- Status przekaźnika (LEDy)
- Pozycja serwo
- Status połączenia ESP32

Monitor Portu Szeregowego wyświetla szczegółowy raport zawierający:
- Wszystkie dane z czujników
- Status urządzeń wykonawczych
- Status komunikacji ESP32
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

**Monitoring parametrów środowiskowych:**
- **Temperatura:** Pomiar aktualnej temperatury otoczenia w stopniach Celsjusza
- **Wilgotność:** Pomiar względnej wilgotności powietrza w procentach
- **Jakość powietrza:** Określenie jakości powietrza w skali procentowej
- **Natężenie światła:** Pomiar natężenia oświetlenia w procentach i luksach

**Wykrywanie ruchu:**
- System wykrywa ruch w pomieszczeniu za pomocą czujnika PIR
- Automatyczne resetowanie stanu wykrycia ruchu po 3 sekundach braku aktywności

**Sterowanie urządzeniami:**
- **LEDy:** Włączanie/wyłączanie oświetlenia LED poprzez przekaźnik SSR
- **Buzzer:** Sterowanie sygnalizacją dźwiękową
- **Serwo SG90:** Możliwość ustawienia pozycji serwo w zakresie 0-180 stopni
- **Silnik krokowy:** Sterowanie obrotem silnika krokowego w obu kierunkach

**Komunikacja bezprzewodowa:**
- **ESP32 DevKit V1 C6:** Umożliwia bezprzewodowe sterowanie i monitoring systemu
- Komunikacja przez UART (piny 18,19)

**Wizualizacja danych:**
- Wyświetlanie wszystkich parametrów na ekranie OLED
- Wysyłanie szczegółowych raportów przez port szeregowy

## 🔧 Rozwiązywanie problemów

**Problem: Zawieszający się pasek led / nie przestaje świecić**
*Rozwiązanie:*
- Upewnij się, że rezystor podciągający (10kΩ) jest podłączony między bramką (gate) a źródłem (source) Mosfeta (zapewni to stabilny stan niski, gdy Arduino nie podaje sygnału, co zapobiega zawieszaniu się tranzystora)
- Zrestartuj Arduino

**Problem: Brak danych z czujnika DHT22**
*Rozwiązanie:*
- Sprawdź prawidłowość podłączenia (pin danych, zasilanie)
- Upewnij się, że rezystor podciągający (4.7kΩ) jest podłączony między pinem danych a VCC
- Zrestartuj Arduino

**Problem: Brak wykrywania ruchu**
*Rozwiązanie:*
- Odczekaj 60 sekund po uruchomieniu systemu (czas stabilizacji PIR)
- Sprawdź regulację czułości na module PIR (potencjometr)
- Zweryfikuj zasilanie czujnika (wymaga stabilnego 5V)

**Problem: Nieprawidłowe wskazania czujnika MQ135**
*Rozwiązanie:*
- Czujnik MQ135 wymaga wstępnego nagrzewania (około 24 godziny dla pełnej kalibracji)
- Sprawdź czy jest odpowiednio zasilany (5V)

**Problem: Nie działa wyświetlacz OLED**
*Rozwiązanie:*
- Sprawdź połączenia I2C (SDA, SCL)
- Zweryfikuj adres I2C wyświetlacza (domyślnie 0x3C, niektóre modele używają 0x3D)
- Uruchom skaner I2C aby znaleźć prawidłowy adres urządzenia

**Problem: Serwo nie reaguje na komendy**
*Rozwiązanie:*
- Upewnij się, że serwo jest podłączone do odpowiedniego pinu PWM
- Sprawdź zasilanie serwo (może wymagać dodatkowego źródła zasilania)
- Zweryfikuj poprawność podłączenia przewodów (GND, VCC, sygnał)

**Problem: Brak komunikacji z ESP32**
*Rozwiązanie:*
- Sprawdź połączenia TX/RX (pin 18 Arduino -> pin 19 ESP32, pin 19 Arduino -> pin 18 ESP32)
- Zweryfikuj zasilanie ESP32 (3.3V lub 5V zgodnie ze specyfikacją)
- Sprawdź czy ESP32 ma wgrany odpowiedni kod
- Upewnij się, że prędkość transmisji (baud rate) jest zgodna w obu urządzeniach

## 👨‍💻 Autorzy
Projekt został stworzony jako praca studencka w ramach zajęć na Akademii WSB.

© 2025 Autorzy projektu. Projekt studencki wykonany w ramach zajęć na Akademii WSB.
