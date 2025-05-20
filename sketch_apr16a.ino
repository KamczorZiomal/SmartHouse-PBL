#include <DHT.h>            // Biblioteka do obsługi czujnika temperatury i wilgotności
#include <Wire.h>           // Biblioteka do komunikacji I2C
#include <Adafruit_GFX.h>   // Biblioteka graficzna dla wyświetlaczy
#include <Adafruit_SSD1306.h>  // Biblioteka dla wyświetlacza OLED
#include <MQ135.h>          // Biblioteka do obsługi czujnika jakości powietrza
#include <BH1750.h>         // Biblioteka do obsługi czujnika natężenia światła
#include <limits.h>         // Biblioteka z definicjami limitów typów danych
#include <Servo.h>          // Biblioteka do obsługi serwo SG90
#include <Stepper.h>        // Biblioteka do obsługi silnika krokowego 28BYJ-48
#include <String.h>         // Biblioteka do obsługi łańcuchów znaków

// Definicje pinów - tutaj podłączamy nasze czujniki i elementy wykonawcze
#define DHT_DATA_PIN 2        // Pin danych DHT22 - mierzy temperaturę i wilgotność
#define PIR_PIN 3             // Pin czujnika ruchu HC-SR501 - wykrywa ruch
#define MQ135_A0_PIN A2       // Pin analogowy A2 dla MQ135 - czujnik jakości powietrza
#define BUZZER_PIN 53         // Pin dla buzzera KY-012 - sygnał dźwiękowy
#define SSR_RELAY_PIN 22      // Pin dla przekaźnika SSR do sterowania LEDami
#define SERVO_PIN 9           // Pin dla serwa SG90 - silnik sterujący
// Piny dla silnika krokowego 28BYJ-48
#define IN1 30    // Piny sterujące poszczególnymi cewkami silnika krokowego
#define IN2 31
#define IN3 32
#define IN4 33

// Parametry wyświetlacza OLED - musimy je ustawić dla poprawnej inicjalizacji
#define SCREEN_WIDTH 128      // Szerokość wyświetlacza w pikselach
#define SCREEN_HEIGHT 64      // Wysokość wyświetlacza w pikselach
#define OLED_RESET -1         // -1 jeśli brak pinu reset (większość wyświetlaczy)
#define SCREEN_ADDRESS 0x3C   // Typowy adres I2C dla SSD1306 (można sprawdzić skanerem I2C)

// Inicjalizacja wyświetlacza OLED - tworzymy obiekt do sterowania wyświetlaczem
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// Inicjalizacja czujników - tworzymy obiekty do obsługi każdego z czujników
DHT dht(DHT_DATA_PIN, DHT22);       // Czujnik temperatury i wilgotności
MQ135 gasSensor(MQ135_A0_PIN);      // Czujnik zanieczyszczeń powietrza
BH1750 lightMeter;                  // Czujnik natężenia światła

// Inicjalizacja serwo i silnika krokowego - choć nie będziemy ich aktywnie używać w tej wersji
Servo sg90;                         // Serwo SG90
const int STEPS_PER_REV = 2048;     // Silnik krokowy 28BYJ-48 ma 2048 kroków na pełny obrót (z przekładnią)
Stepper stepper(STEPS_PER_REV, IN1, IN2, IN3, IN4);

// Definicje zmiennych globalnych - tutaj przechowujemy wartości odczytów z czujników
float temperature = 0.0;    // Temperatura w stopniach Celsjusza
float humidity = 0.0;       // Wilgotność względna w procentach
float airQuality = 0.0;     // Jakość powietrza (wartość surowa)
float lightLevel = 0.0;     // Natężenie światła w luksach
int dhtErrorCount = 0;      // Licznik błędów odczytu z DHT22
bool mqCalibrated = false;  // Flaga kalibracji czujnika MQ135

// Zmienne dla czujnika ruchu
bool motionDetected = false;       // Flaga wykrycia ruchu
unsigned long lastMotionTime = 0;  // Czas ostatniego wykrycia ruchu
unsigned long lastDisplayUpdateTime = 0;  // Czas ostatniej aktualizacji wyświetlacza

// Zmienne do śledzenia stanu urządzeń
int servoPosition = 0;       // Śledzenie aktualnej pozycji serwo

// Zmienne do obsługi komend przez Serial
String incomingCommand = "";      // Przechowuje otrzymaną komendę
bool commandComplete = false;     // Flaga informująca o kompletności komendy

// Stałe czasowe - określają jak często aktualizować różne elementy
const unsigned long debounceTime = 500;     // Czas debouncingu w milisekundach (eliminacja drgań styków)
const unsigned long displayUpdateInterval = 1000; // Aktualizacja wyświetlacza co 1 sekundę
const unsigned long motionResetTime = 3000; // Czas resetowania stanu ruchu (3 sekundy)

// Funkcja obliczająca różnicę czasu z uwzględnieniem przepełnienia licznika millis()
// Jest to ważne, bo millis() wraca do zera po około 50 dniach ciągłej pracy
unsigned long getTimeDifference(unsigned long currentTime, unsigned long previousTime) {
  return (currentTime >= previousTime) ? (currentTime - previousTime) : (ULONG_MAX - previousTime + currentTime + 1);
}

// Funkcja odczytu stanu czujnika ruchu
void readMotion() {
  // Sprawdź aktualny stan pinu czujnika ruchu
  bool currentPinState = digitalRead(PIR_PIN) == HIGH;
  
  // Reagujemy tylko gdy stan się zmienił - to pozwala uniknąć ciągłego wyświetlania tego samego stanu
  if (currentPinState != motionDetected) {
    unsigned long currentTime = millis();
    
    // Dodatkowe sprawdzenie debounce przy zmianie stanu - eliminuje fałszywe odczyty
    if (getTimeDifference(currentTime, lastMotionTime) > debounceTime) {
      motionDetected = currentPinState;
      lastMotionTime = currentTime;
    }
  }
  
  // Automatyczne resetowanie flagi wykrycia ruchu po określonym czasie
  // To jest potrzebne, żeby nie pokazywać ciągle "WYKRYTO", gdy ruch ustał
  unsigned long currentTime = millis();
  if (motionDetected && getTimeDifference(currentTime, lastMotionTime) > motionResetTime) {
    motionDetected = false;
    // Serial.println(F("Ruch: BRAK (automatyczny reset po czasie)"));
  }
}

// Funkcja do wyświetlania ASCII Art na początku programu
// Ten efekt wizualny pokazuje nazwę projektu przy starcie
void showASCIIArt() {
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  
  // Wycentrowanie tekstu "AKADEMIA WSB" horyzontalnie
  // To wymaga obliczenia szerokości tekstu, żeby go umieścić na środku ekranu
  String text1 = "AKADEMIA WSB";
  int16_t x1, y1;
  uint16_t w1, h1;
  display.getTextBounds(text1, 0, 0, &x1, &y1, &w1, &h1);
  display.setCursor((SCREEN_WIDTH - w1) / 2, (SCREEN_HEIGHT - 16) / 2);
  display.println(text1);
  
  // Wycentrowanie tekstu "PROJEKT SMART HOUSE" horyzontalnie
  String text2 = "PROJEKT SMART HOUSE";
  int16_t x2, y2;
  uint16_t w2, h2;
  display.getTextBounds(text2, 0, 0, &x2, &y2, &w2, &h2);
  display.setCursor((SCREEN_WIDTH - w2) / 2, ((SCREEN_HEIGHT - 16) / 2) + 16);
  display.println(text2);
  
  display.display();
  delay(2000);  // Pokazujemy ekran powitalny przez 2 sekundy
}

// Funkcja serwoTest - sprawdza poprawne działanie serwo wykonując pełny ruch testowy
void servoTest() {
  Serial.println(F("Test serwo SG90:"));
  
  // Ruch w pełnym zakresie od 0 do 180 i z powrotem
  for (int angle = 0; angle <= 180; angle += 45) {
    sg90.write(angle);
    servoPosition = angle;
    Serial.print(F("Serwo w pozycji: "));
    Serial.print(angle);
    Serial.println(F(" stopni"));
    delay(300);
  }

  // Powrót do pozycji 0
  sg90.write(0);
  servoPosition = 0;
  Serial.println(F("Serwo powróciło do pozycji 0 stopni"));
  delay(300);
}

// Funkcja do obsługi komend przychodzących przez Serial
void processCommand() {
  // Komenda powinna być już kompletna (zakończona znakiem nowej linii, który został usunięty)
  incomingCommand.trim();  // Usuwamy ewentualne białe znaki z początku i końca
  
  Serial.print(F("Otrzymano komendę: "));
  Serial.println(incomingCommand);
  
  // Sprawdzamy rodzaj komendy i odpowiednio reagujemy
  if (incomingCommand.equals("LED_ON")) {
    digitalWrite(SSR_RELAY_PIN, HIGH);
    Serial.println(F("Włączono LEDy"));
  } 
  else if (incomingCommand.equals("LED_OFF")) {
    digitalWrite(SSR_RELAY_PIN, LOW);
    Serial.println(F("Wyłączono LEDy"));
  }
  else if (incomingCommand.equals("BUZZER_ON")) {
    digitalWrite(BUZZER_PIN, HIGH);
    Serial.println(F("Włączono buzzer"));
  }
  else if (incomingCommand.equals("BUZZER_OFF")) {
    digitalWrite(BUZZER_PIN, LOW);
    Serial.println(F("Wyłączono buzzer"));
  }
  else if (incomingCommand.equals("SG90_0")) {  // NOWA KOMENDA: Powrót serwo do pozycji 0 stopni
    sg90.write(0);
    servoPosition = 0;
    Serial.println(F("Obrócono serwo do pozycji 0 stopni (pozycja początkowa)"));
  }
  else if (incomingCommand.equals("SG90_1")) {
    sg90.write(90);  // Obracamy serwo o 90 stopni
    servoPosition = 90;
    Serial.println(F("Obrócono serwo do pozycji 90 stopni"));
  }
  else if (incomingCommand.equals("SG90_2")) {
    sg90.write(180);  // Obracamy serwo o 180 stopni
    servoPosition = 180;
    Serial.println(F("Obrócono serwo do pozycji 180 stopni"));
  }
  else if (incomingCommand.startsWith("SG90_")) {  // NOWA FUNKCJA: Obsługa dowolnego kąta serwo
    // Pobieranie wartości kąta z komendy, np. SG90_45 ustawi serwo na 45 stopni
    int angle = incomingCommand.substring(5).toInt();
    
    // Sprawdzanie czy kąt jest w poprawnym zakresie
    if (angle >= 0 && angle <= 180) {
      sg90.write(angle);
      servoPosition = angle;
      Serial.print(F("Obrócono serwo do pozycji "));
      Serial.print(angle);
      Serial.println(F(" stopni"));
    } else {
      Serial.println(F("Błąd: Kąt poza zakresem (0-180 stopni)"));
    }
  }
  else if (incomingCommand.equals("Silnik_ruch")) {
    // Obracamy silnik krokowy o 500 kroków w prawo
    stepper.step(500);
    Serial.println(F("Wykonano 500 kroków silnikiem w prawo"));
  }
  else if (incomingCommand.equals("Silnik_lewo")) {  // NOWA KOMENDA: Obrót silnika w lewo
    // Obracamy silnik krokowy o 500 kroków w lewo
    stepper.step(-500);
    Serial.println(F("Wykonano 500 kroków silnikiem w lewo"));
  }
  else if (incomingCommand.equals("SERWO_TEST")) {  // NOWA KOMENDA: Test serwo
    servoTest();
  }
  else {
    Serial.println(F("Nieznana komenda"));
  }
  
  // Czyszczenie komendy po przetworzeniu
  incomingCommand = "";
  commandComplete = false;
}

// Funkcja do rysowania paska postępu - używana podczas inicjalizacji
// Pasek postępu pokazuje jak daleko zaawansowana jest inicjalizacja systemu
void drawProgressBar(int x, int y, int width, int height, int progress) {
  // Rysujemy ramkę paska postępu
  display.drawRect(x, y, width, height, SSD1306_WHITE);
  
  // Rysujemy wypełnienie proporcjonalne do postępu (0-100%)
  int fillWidth = (progress * (width - 4)) / 100;
  display.fillRect(x + 2, y + 2, fillWidth, height - 4, SSD1306_WHITE);
  display.display();
}

// Funkcja do testowania buzzera przy starcie
void testBuzzer() {
  // Krótki sygnał - sprawdzenie czy buzzer działa
  digitalWrite(BUZZER_PIN, HIGH);
  delay(200);
  digitalWrite(BUZZER_PIN, LOW);
  delay(200);
  digitalWrite(BUZZER_PIN, HIGH);
  delay(200);
  digitalWrite(BUZZER_PIN, LOW);
  
  // Serial.println(F("Test buzzera wykonany"));
}

// Funkcja do inicjalizacji wszystkich czujników z paskiem postępu
// Ta funkcja uruchamia wszystkie czujniki i pokazuje postęp na ekranie
void initSensors() {
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.println(F("Inicjalizacja systemu..."));
  
  // Inicjalizacja DHT22 - 15% postępu
  drawProgressBar(10, 30, 108, 10, 15);
  dht.begin();
  // Serial.println(F("Czujnik DHT22 zainicjalizowany - mierzy temperaturę i wilgotność"));
  delay(500);
  
  // Inicjalizacja MQ135 - 30% postępu
  drawProgressBar(10, 30, 108, 10, 30);
  pinMode(MQ135_A0_PIN, INPUT);
  // Serial.println(F("Czujnik MQ135 zainicjalizowany - mierzy jakość powietrza"));
  delay(500);
  
  // Inicjalizacja BH1750 - 45% postępu
  drawProgressBar(10, 30, 108, 10, 45);
  if (lightMeter.begin(BH1750::CONTINUOUS_HIGH_RES_MODE)) {
    // Serial.println(F("Czujnik BH1750 zainicjalizowany pomyślnie - mierzy natężenie światła"));
  } else {
    // Serial.println(F("Błąd inicjalizacji czujnika BH1750! Sprawdź połączenia I2C"));
  }
  delay(500);
  
  // Inicjalizacja PIR - 60% postępu
  drawProgressBar(10, 30, 108, 10, 60);
  pinMode(PIR_PIN, INPUT);
  // Serial.println(F("Czujnik ruchu PIR zainicjalizowany - wykrywa ruch w pomieszczeniu"));
  delay(500);
  
  // Inicjalizacja serwo SG90 - 75% postępu
  drawProgressBar(10, 30, 108, 10, 75);
  sg90.attach(SERVO_PIN);
  sg90.write(0);  // Ustaw serwo w pozycji początkowej
  servoPosition = 0;  // Zapisz pozycję początkową serwo
  delay(500);
  
  // Inicjalizacja silnika krokowego - 85% postępu
  drawProgressBar(10, 30, 108, 10, 85);
  stepper.setSpeed(10);  // RPM (obroty na minutę)
  // Serial.println(F("Silnik krokowy 28BYJ-48 zainicjalizowany - nie będzie aktywnie używany w tej wersji"));
  delay(500);
  
  // Inicjalizacja przekaźnika SSR - 90% postępu
  drawProgressBar(10, 30, 108, 10, 90);
  pinMode(SSR_RELAY_PIN, OUTPUT);
  digitalWrite(SSR_RELAY_PIN, HIGH);  // Włączenie przekaźnika przy starcie
  // Serial.println(F("Przekaźnik SSR zainicjalizowany - steruje LEDami"));
  delay(500);
  
  // Inicjalizacja buzzera - 95% postępu
  drawProgressBar(10, 30, 108, 10, 95);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);  // Wyłączenie buzzera na początku
  // Serial.println(F("Pin buzzera zainicjalizowany"));
  delay(500);
  
  // Test buzzera - 100% postępu
  drawProgressBar(10, 30, 108, 10, 100);
  testBuzzer();
  delay(500);
  
  // Informacja o zakończeniu inicjalizacji
  display.setCursor(0, 55);
  display.println(F("System GOTOWY!"));
  display.display();
  delay(1000);
}

// Przelicza jakość powietrza na procenty
// Konwertuje surowe odczyty na wartość procentową dla łatwiejszego zrozumienia
int calculateAirQualityPercent() {
  // Ustalamy nowy zakres dla pełnej skali 0-100%
  float maxPPM = 100.0;  // Maksymalne zanieczyszczenie dla 100%
  
  int qualityPercent = (int)((airQuality / maxPPM) * 100.0);
  
  // Ograniczenie do zakresu 0-100%
  if (qualityPercent > 100) qualityPercent = 100;
  if (qualityPercent < 0) qualityPercent = 0;
  
  return qualityPercent;
}

// Przelicza natężenie światła na procenty
// Ułatwia interpretację wyników przez użytkownika
int calculateLightPercent() {
  int lightPercent = (int)(lightLevel);
  
  // Ograniczenie do maksymalnie 100%
  if (lightPercent > 100) lightPercent = 100;
  if (lightPercent < 0) lightPercent = 0;
  
  return lightPercent;
}

// Funkcja do odczytu wszystkich czujników
// Zbiera dane ze wszystkich podłączonych sensorów
void readSensors() {
  // Odczyt DHT22 - temperatura i wilgotność
  float newTemp = dht.readTemperature();
  float newHumidity = dht.readHumidity();
  
  // Sprawdzenie poprawności odczytów (funkcja isnan sprawdza czy wartość to NaN - Not a Number)
  if (!isnan(newTemp) && !isnan(newHumidity)) {
    // Dodatkowo sprawdzamy czy odczyty mieszczą się w sensownym zakresie
    if (newTemp >= -40.0 && newTemp <= 80.0 && 
        newHumidity >= 0.0 && newHumidity <= 100.0) {
      temperature = newTemp;
      humidity = newHumidity;
      dhtErrorCount = 0;
    } else {
      dhtErrorCount++;
      // Serial.println(F("Odczyty DHT poza zakresem! Sprawdź warunki pomiaru"));
    }
  } else {
    dhtErrorCount++;
    // Serial.println(F("Błąd odczytu z czujnika DHT! Sprawdź połączenia"));
    
    if (dhtErrorCount > 5) {
      // Serial.println(F("Powtarzające się błędy DHT - sprawdź okablowanie i czy czujnik działa poprawnie"));
    }
  }
  
  // Odczyt MQ135 z uśrednianiem - pomaga wyeliminować szumy pomiarowe
  int analogMQ = 0;
  for (int i = 0; i < 5; i++) {
    analogMQ += analogRead(MQ135_A0_PIN);
    delay(10);
  }
  analogMQ /= 5;  // Średnia z 5 pomiarów
  
  // Przeliczanie na ppm - wartość proporcjonalna do zanieczyszczenia
  // W rzeczywistości wymagałoby to dokładniejszej kalibracji dla konkretnych gazów
  airQuality = analogMQ * 0.1;
  
  // Odczyt BH1750 - czujnik natężenia światła w luksach
  float lux = lightMeter.readLightLevel();
  if (lux >= 0 && lux < 65535) {  // Sprawdzenie czy odczyt jest sensowny
    lightLevel = lux;
  }
  
  // Odczyt czujnika ruchu PIR
  readMotion();
}

// Funkcja do aktualizacji wyświetlacza - wszystkie pomiary
// Wyświetla aktualne wartości na ekranie OLED
void updateDisplay() {
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  
  // Temperatura
  display.setCursor(0, 0);
  display.print(F("Temperatura: "));
  display.print(temperature, 1);  // Jedno miejsce po przecinku
  display.println(F(" C"));
  
  // Wilgotność
  display.setCursor(0, 10);
  display.print(F("Wilgotnosc: "));
  display.print(humidity, 1);  // Jedno miejsce po przecinku
  display.println(F(" %"));
  
  // Czystość powietrza jako procent
  int airQualityPercent = calculateAirQualityPercent();
  display.setCursor(0, 20);
  display.print(F("Jakosc Tlenu: "));
  display.print(airQualityPercent);
  display.println(F(" %"));
  
  // Natężenie światła jako procent
  int lightPercent = calculateLightPercent();
  display.setCursor(0, 30);
  display.print(F("Naswietlenie: "));
  display.print(lightPercent);
  display.println(F(" %"));
  
  // Status ruchu - pokazujemy aktualny stan czujnika PIR
  display.setCursor(0, 40);
  display.print(F("Ruch: "));
  // Dodatkowa weryfikacja - raportujemy tylko gdy pin jest fizycznie wysoki
  bool motionConfirmed = motionDetected && (digitalRead(PIR_PIN) == HIGH);
  display.println(motionConfirmed ? F("WYKRYTO!") : F("BRAK"));
  
  // Status przekaźnika SSR
  display.setCursor(0, 50);
  display.print(F("LEDy: "));
  display.print(digitalRead(SSR_RELAY_PIN) == HIGH ? F("WLACZONE") : F("WYLACZONE"));
  
  // Dodajemy informację o aktualnej pozycji serwo
  display.setCursor(90, 50);
  display.print(F("SG90:"));
  display.print(servoPosition);
  
  display.display();
}

void setup() {
  // Rozpocznij komunikację przez port szeregowy z prędkością 9600 bps
  Serial.begin(9600);
  // Serial.println(F("Inicjalizacja systemu wieloczujnikowego Smart House..."));
  // Serial.println(F("Projekt studencki dla Akademii WSB"));
  
  // Przygotowanie zmiennych do odbierania komend
  incomingCommand.reserve(32);  // Rezerwujemy pamięć na komendy (max 32 znaki)
  
  // Konfiguracja pinów dla silnika krokowego - ustawiamy jako wyjścia
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);
  
  // Inicjalizacja wyświetlacza OLED
  if(!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS)) {
    // Serial.println(F("Błąd inicjalizacji wyświetlacza SSD1306! Sprawdź połączenia"));
    while(1);  // Zatrzymaj program jeśli wyświetlacz nie działa
  }
  
  // Pokaż ekran powitalny
  showASCIIArt();
  
  // Inicjalizacja wszystkich czujników z paskiem postępu i testem buzzera
  initSensors();
  
  // Testowy ruch serwo - sprawdza czy działa prawidłowo
  servoTest();
  
  // Serial.println(F("Stabilizacja czujnika ruchu (60 sekund)..."));
  // Serial.println(F("Ten czas jest potrzebny, aby czujnik PIR ustabilizował swoje odczyty"));
  // Serial.println(F("i zaczął poprawnie wykrywać ruch (zmniejsza liczbę fałszywych alarmów)"));
  
  // Komunikat na wyświetlaczu o stabilizacji
  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println(F("Stabilizacja"));
  display.setCursor(0, 10);
  display.println(F("czujnika ruchu"));
  display.setCursor(0, 30);
  display.println(F("Prosze czekac..."));
  display.display();
  
  // Czas stabilizacji - można skrócić dla testów, ale w praktyce zalecane jest pełne 60s
  delay(60000);  // 60 sekund na stabilizację czujnika PIR
  
  // Inicjalizacja zmiennych czasowych
  lastMotionTime = millis();
  lastDisplayUpdateTime = millis();
  
  // Serial.println(F("System wieloczujnikowy Smart House gotowy do pracy!"));
  // Serial.println(F("Rozpoczynam monitoring..."));
}

void loop() {
  // Odczyt danych ze wszystkich czujników
  readSensors();
  
  // Sprawdzanie, czy są dostępne dane w porcie szeregowym
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    
    // Jeśli otrzymano znak nowej linii, oznacza to koniec komendy
    if (inChar == '\n') {
      commandComplete = true;
    } else {
      // W przeciwnym razie dodajemy znak do komendy
      incomingCommand += inChar;
    }
  }
  
  // Jeśli komenda jest kompletna, przetwórz ją
  if (commandComplete) {
    processCommand();
  }
  
  // Aktualizacja wyświetlacza - wykonujemy co określony czas dla płynności
  unsigned long currentTime = millis();
  if (getTimeDifference(currentTime, lastDisplayUpdateTime) > displayUpdateInterval) {
    updateDisplay();
    lastDisplayUpdateTime = currentTime;
  }
  
  // Wyświetl dane w terminalu - szczegółowy raport po polsku w osobnych linijkach
  Serial.println(F("\n==== RAPORT Z CZUJNIKÓW SMART HOUSE ===="));
  Serial.print(F("Temperatura: "));
  Serial.print(temperature);
  Serial.println(F(" °C"));
  
  Serial.print(F("Wilgotność: "));
  Serial.print(humidity);
  Serial.println(F(" %"));
  
  Serial.print(F("Jakość powietrza: "));
  Serial.print(calculateAirQualityPercent());
  Serial.println(F(" %"));
  
  Serial.print(F("Natężenie światła: "));
  Serial.print(calculateLightPercent());
  Serial.println(F(" % ("));
  Serial.print(lightLevel);
  Serial.println(F(" lux)"));
  
  Serial.print(F("Wykrycie ruchu: "));
  bool motionConfirmed = motionDetected && (digitalRead(PIR_PIN) == HIGH);
  if (motionConfirmed) {
    Serial.println(F("TAK - WYKRYTO RUCH!"));
  } else {
    Serial.println(F("NIE - brak ruchu"));
  }
  
  Serial.print(F("Status przekaźnika SSR (LEDy): "));
  Serial.println(digitalRead(SSR_RELAY_PIN) == HIGH ? F("WŁĄCZONY") : F("WYŁĄCZONY"));
  
  Serial.print(F("Status buzzera: "));
  Serial.println(digitalRead(BUZZER_PIN) == HIGH ? F("WŁĄCZONY") : F("WYŁĄCZONY"));
  
  Serial.println(F("======================================"));
  Serial.println(F("Dostępne komendy:"));
  Serial.println(F("LED_ON - włączenie LEDów"));
  Serial.println(F("LED_OFF - wyłączenie LEDów"));
  Serial.println(F("BUZZER_ON - włączenie buzzera"));
  Serial.println(F("BUZZER_OFF - wyłączenie buzzera"));
  Serial.println(F("SG90_1 - obrót serwo o 90 stopni"));
  Serial.println(F("SG90_2 - obrót serwo o 180 stopni"));
  Serial.println(F("Silnik_ruch - obrót silnika krokowego o 50 kroków"));
  Serial.println(F("======================================"));
  
  // Opóźnienie dla stabilności systemu i czytelności danych
  delay(1000);
}
