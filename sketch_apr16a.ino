#include <DHT.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <MQ135.h>
#include <BH1750.h>
#include <limits.h>
#include <Servo.h>       // Dodana biblioteka do obsługi serwo SG90
#include <Stepper.h>     // Dodana biblioteka do obsługi silnika krokowego 28BYJ-48 

// Definicje pinow
#define DHT_DATA_PIN 2        // Pin danych DHT22
#define PIR_PIN 3             // Pin czujnika ruchu HC-SR501
#define MQ135_A0_PIN A2       // Pin analogowy A2 dla MQ135
#define BUZZER_PIN 53         // Pin dla buzzera KY-012
#define SERVO_PIN 9           // Pin dla serwa SG90
// Piny dla silnika krokowego 28BYJ-48 - poprawione zgodnie z rzeczywistymi połączeniami
#define IN1 30
#define IN2 31
#define IN3 32
#define IN4 33

// Parametry wyswietlacza OLED
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1         // -1 jesli brak pinu reset
#define SCREEN_ADDRESS 0x3C   // Typowy adres I2C dla SSD1306

// Inicjalizacja wyswietlacza OLED
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// Inicjalizacja czujnikow
DHT dht(DHT_DATA_PIN, DHT22);       // Czujnik temperatury i wilgotnosci
MQ135 gasSensor(MQ135_A0_PIN);      // Czujnik zanieczyszczen powietrza
BH1750 lightMeter;                  // Czujnik natezenia swiatla

// Inicjalizacja serwa i silnika krokowego
Servo sg90;                          // Serwo SG90
// Silnik krokowy 28BYJ-48 ma 2048 kroków na pełny obrót (z przekładnią)
const int STEPS_PER_REV = 2048;
Stepper stepper(STEPS_PER_REV, IN1, IN2, IN3, IN4);

// Definicje zmiennych globalnych
float temperature = 0.0;
float humidity = 0.0;
float airQuality = 0.0;
float lightLevel = 0.0;
int dhtErrorCount = 0;
bool mqCalibrated = false;
bool buzzerActive = false;
unsigned long lastBuzzerToggle = 0;

// Flagi dla serwa i silnika krokowego
bool servoActivated = false;
bool stepperActivated = false;
unsigned long lastServoTime = 0;
unsigned long lastStepperTime = 0;
const unsigned long servoResetTime = 1000;     // Czas powrotu serwa do pozycji wyjściowej

// Stale i progi
#define MAX_ERROR_COUNT 5          // Maksymalna liczba bledow przed ostrzezeniem
#define LIGHT_THRESHOLD 100        // Prog aktywacji buzzera dla swiatla (lux)
#define AIR_QUALITY_THRESHOLD 20   // Prog aktywacji buzzera dla jakosci powietrza (%, ponizej tej wartosci)

// Zmienne dla czujnika ruchu
volatile bool motionInterrupted = false;
bool motionDetected = false;
unsigned long lastMotionTime = 0;
unsigned long lastDisplayUpdateTime = 0;
const unsigned long debounceTime = 500;     // Czas debouncingu w milisekundach
const unsigned long displayUpdateInterval = 1000; // Aktualizacja wyświetlacza co 1 sekundę
const unsigned long motionResetTime = 3000; // Czas resetowania stanu ruchu (3 sekundy)

// Funkcja obliczająca różnicę czasu z uwzględnieniem przepełnienia licznika millis()
unsigned long getTimeDifference(unsigned long currentTime, unsigned long previousTime) {
  return (currentTime >= previousTime) ? (currentTime - previousTime) : (ULONG_MAX - previousTime + currentTime + 1);
}

// Procedura obsługi przerwania dla czujnika ruchu
void motionISR() {
  unsigned long currentTime = millis();
  // Sprawdź czy minął czas debounce i czy pin faktycznie jest w stanie wysokim
  if (getTimeDifference(currentTime, lastMotionTime) > debounceTime && digitalRead(PIR_PIN) == HIGH) {
    motionInterrupted = true;
    motionDetected = true;
    lastMotionTime = currentTime;
    
    // Zaznaczamy, że buzzer powinien być aktywny, ale tylko jeśli naprawdę wykryliśmy ruch
    buzzerActive = true;
    // Aktywujemy serwomechanizm i silnik krokowy
    servoActivated = true;
    stepperActivated = true;
    lastServoTime = currentTime;
    lastStepperTime = currentTime;
    Serial.println(F("Wykryto ruch przez ISR - PIN jest HIGH"));
  }
}

// Funkcja do obsługi serwa SG90
void handleServo() {
  if (servoActivated) {
    unsigned long currentTime = millis();
    
    // Obracamy serwo o 90 stopni
    sg90.write(90);
    Serial.println(F("Serwo obrócone o 90 stopni"));
    
    // Resetujemy flagę, żeby nie obracać serwa ponownie
    servoActivated = false;
    
    // Po upływie czasu servoResetTime, serwo wróci do pozycji początkowej
    delay(servoResetTime);
    sg90.write(0);
    Serial.println(F("Serwo powróciło do pozycji początkowej"));
  }
}

// Funkcja do obsługi silnika krokowego 28BYJ-48
void handleStepper() {
  if (stepperActivated) {
    Serial.println(F("Rozpoczynanie sekwencji silnika krokowego"));
    
    // 3 pełne obroty zgodnie z ruchem wskazówek zegara
    for (int i = 0; i < 3; i++) {
      Serial.print(F("Obrót zgodny z ruchem wskazówek #"));
      Serial.println(i + 1);
      stepper.step(STEPS_PER_REV);
    }
    
    // 3 pełne obroty przeciwnie do ruchu wskazówek zegara
    for (int i = 0; i < 3; i++) {
      Serial.print(F("Obrót przeciwny do ruchu wskazówek #"));
      Serial.println(i + 1);
      stepper.step(-STEPS_PER_REV);
    }
    
    // Resetujemy flagę, żeby nie obracać silnika ponownie
    stepperActivated = false;
    Serial.println(F("Zakończono sekwencję silnika krokowego"));
  }
}

// Funkcja odczytu czujnika ruchu
void readMotion() {
  // Aktualizuj stan czujnika ruchu tylko jeśli nie było przerwania
  if (!motionInterrupted) {
    bool currentPinState = digitalRead(PIR_PIN) == HIGH;
    
    // Tylko gdy stan się zmienił
    if (currentPinState != motionDetected) {
      unsigned long currentTime = millis();
      
      // Dodatkowe sprawdzenie debounce przy zmianie stanu
      if (getTimeDifference(currentTime, lastMotionTime) > debounceTime) {
        motionDetected = currentPinState;
        lastMotionTime = currentTime;
        
        if (motionDetected) {
          Serial.println(F("Ruch wykryty w readMotion()"));
          buzzerActive = true;
          // Aktywujemy serwomechanizm i silnik krokowy gdy wykryto ruch
          servoActivated = true;
          stepperActivated = true;
          lastServoTime = currentTime;
          lastStepperTime = currentTime;
        } else {
          Serial.println(F("Ruch ustał w readMotion()"));
        }
      }
    }
  }
  
  // Resetowanie flagi wykrycia ruchu po krótszym czasie (3 sekundy zamiast 5)
  unsigned long currentTime = millis();
  if (motionDetected && getTimeDifference(currentTime, lastMotionTime) > motionResetTime) {
    motionDetected = false;
    Serial.println(F("Automatyczny reset wykrycia ruchu po 3 sekundach"));
  }
}

// Funkcja do wyswietlania ASCII Art
void showASCIIArt() {
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  
  // Wycentrowanie tekstu "AKADEMIA WSB" horyzontalnie
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
  delay(2000);
}

// Funkcja do rysowania paska postepu
void drawProgressBar(int x, int y, int width, int height, int progress) {
  // Rysuj ramke
  display.drawRect(x, y, width, height, SSD1306_WHITE);
  // Rysuj wypelnienie
  int fillWidth = (progress * (width - 4)) / 100;
  display.fillRect(x + 2, y + 2, fillWidth, height - 4, SSD1306_WHITE);
  display.display();
}

// Funkcja do inicjalizacji wszystkich czujnikow z paskiem postepu
void initSensors() {
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.println(F("Inicjalizacja systemu..."));
  
  // Inicjalizacja DHT22 - 15%
  drawProgressBar(10, 30, 108, 10, 15);
  dht.begin();
  Serial.println(F("Czujnik DHT22 zainicjalizowany"));
  delay(500);
  
  // Inicjalizacja MQ135 - 30%
  drawProgressBar(10, 30, 108, 10, 30);
  pinMode(MQ135_A0_PIN, INPUT);
  Serial.println(F("Czujnik MQ135 zainicjalizowany"));
  delay(500);
  
  // Inicjalizacja BH1750 - 45%
  drawProgressBar(10, 30, 108, 10, 45);
  if (lightMeter.begin(BH1750::CONTINUOUS_HIGH_RES_MODE)) {
    Serial.println(F("Czujnik BH1750 zainicjalizowany pomyslnie"));
  } else {
    Serial.println(F("Blad inicjalizacji czujnika BH1750!"));
  }
  delay(500);
  
  // Inicjalizacja PIR - 60%
  drawProgressBar(10, 30, 108, 10, 60);
  pinMode(PIR_PIN, INPUT);
  Serial.println(F("Czujnik ruchu PIR zainicjalizowany"));
  delay(500);
  
  // Inicjalizacja serwo SG90 - 75%
  drawProgressBar(10, 30, 108, 10, 75);
  sg90.attach(SERVO_PIN);
  sg90.write(0);  // Ustaw serwo w pozycji początkowej
  Serial.println(F("Serwo SG90 zainicjalizowane"));
  delay(500);
  
  // Inicjalizacja silnika krokowego - 90%
  drawProgressBar(10, 30, 108, 10, 90);
  stepper.setSpeed(10);  // RPM (obroty na minutę)
  Serial.println(F("Silnik krokowy 28BYJ-48 zainicjalizowany"));
  delay(500);
  
  // Inicjalizacja buzzera - 100%
  drawProgressBar(10, 30, 108, 10, 100);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);  // Ensure buzzer is off initially
  Serial.println(F("Pin buzzera zainicjalizowany"));
  delay(500);
  
  // Test buzzera
  display.setCursor(0, 45);
  display.println(F("Testowanie buzzera..."));
  display.display();
  
  digitalWrite(BUZZER_PIN, HIGH);
  delay(200);
  digitalWrite(BUZZER_PIN, LOW);
  delay(200);
  digitalWrite(BUZZER_PIN, HIGH);
  delay(200);
  digitalWrite(BUZZER_PIN, LOW);
  Serial.println(F("Test buzzera zakonczony"));
  
  display.setCursor(0, 55);
  display.println(F("System GOTOWY!"));
  display.display();
  delay(1000);
}

// Funkcja do kontroli buzzera
void handleBuzzer() {
  // Pobierz procent jakości powietrza
  int airQualityPercent = calculateAirQualityPercent();
  
  // Sprawdz warunki aktywacji buzzera
  bool lightTrigger = (lightLevel > LIGHT_THRESHOLD);
  bool airTrigger = (airQualityPercent < AIR_QUALITY_THRESHOLD);  // Poniżej progu
  
  // Dodano: Sprawdzanie czy ruch jest naprawdę wykryty (dodatkowa weryfikacja)
  bool motionTrigger = motionDetected && (digitalRead(PIR_PIN) == HIGH);
  
  bool shouldActivate = lightTrigger || airTrigger || motionTrigger;
  
  // Debug - print detailed status
  Serial.print(F("Buzzer check - Light: "));
  Serial.print(lightLevel);
  Serial.print(F("/"));
  Serial.print(LIGHT_THRESHOLD);
  Serial.print(F(", Air Quality: "));
  Serial.print(airQualityPercent);
  Serial.print(F("% (Threshold: <"));
  Serial.print(AIR_QUALITY_THRESHOLD);
  Serial.print(F("%), Motion: "));
  Serial.print(motionTrigger ? F("YES") : F("NO"));
  Serial.print(F(", Should activate: "));
  Serial.println(shouldActivate ? F("YES") : F("NO"));
  
  // For KY-012 active buzzer - create a beeping pattern
  unsigned long currentMillis = millis();
  
  if (shouldActivate) {
    // Create a beeping pattern (500ms on, 500ms off)
    if (!buzzerActive) {
      buzzerActive = true;
      Serial.println(F("ALARM AKTYWOWANY"));
    }
    
    // Beep pattern
    if (currentMillis - lastBuzzerToggle >= 500) {
      lastBuzzerToggle = currentMillis;
      
      // Read the current state and toggle it
      int currentState = digitalRead(BUZZER_PIN);
      digitalWrite(BUZZER_PIN, !currentState);
      
      // Debug output
      Serial.print(F("Toggling buzzer to: "));
      Serial.println(!currentState ? F("HIGH") : F("LOW"));
    }
  } else if (buzzerActive) {
    // Turn off the buzzer
    buzzerActive = false;
    digitalWrite(BUZZER_PIN, LOW);
    Serial.println(F("ALARM DEAKTYWOWANY"));
  }
}

// Funkcja do odczytu wszystkich czujnikow
void readSensors() {
  // Odczyt DHT22
  float newTemp = dht.readTemperature();
  float newHumidity = dht.readHumidity();
  
  if (!isnan(newTemp) && !isnan(newHumidity)) {
    if (newTemp >= -40.0 && newTemp <= 80.0 && 
        newHumidity >= 0.0 && newHumidity <= 100.0) {
      temperature = newTemp;
      humidity = newHumidity;
      dhtErrorCount = 0;
    } else {
      dhtErrorCount++;
      Serial.println(F("Odczyty DHT poza zakresem!"));
    }
  } else {
    dhtErrorCount++;
    Serial.println(F("Blad odczytu z czujnika DHT!"));
    
    if (dhtErrorCount > MAX_ERROR_COUNT) {
      Serial.println(F("Powtarzajace sie bledy DHT - sprawdz okablowanie!"));
    }
  }
  
  // Odczyt MQ135 z usrednianiem
  int analogMQ = 0;
  for (int i = 0; i < 5; i++) {
    analogMQ += analogRead(MQ135_A0_PIN);
    delay(10);
  }
  analogMQ /= 5;  // Srednia z 5 pomiarow
  
  // Przeliczanie na ppm - teraz bezpośrednio proporcjonalne do zanieczyszczenia
  airQuality = analogMQ * 0.1;
  
  // Odczyt BH1750
  float lux = lightMeter.readLightLevel();
  if (lux >= 0 && lux < 65535) {
    lightLevel = lux;
  }
  
  // Odczyt czujnika ruchu
  readMotion();
}

// Funkcja - Przelicz jakosc powietrza na procenty
int calculateAirQualityPercent() {
  // Ustalamy nowy zakres dla pełnej skali 0-100%
  float maxPPM = 100.0;  // Maksymalne zanieczyszczenie dla 100%
  
  int qualityPercent = (int)((airQuality / maxPPM) * 100.0);
  
  // Ograniczenie do zakresu 0-100%
  if (qualityPercent > 100) qualityPercent = 100;
  if (qualityPercent < 0) qualityPercent = 0;
  
  return qualityPercent;
}

// Przelicz natezenie swiatla na procenty (0-100 lux = 0-100%, >100 lux = 100%)
int calculateLightPercent() {
  int lightPercent = (int)(lightLevel);
  
  // Ograniczenie do maksymalnie 100%
  if (lightPercent > 100) lightPercent = 100;
  if (lightPercent < 0) lightPercent = 0;
  
  return lightPercent;
}

// Funkcja do aktualizacji wyswietlacza - wszystkie pomiary i status alarmu
void updateDisplay() {
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  
  // Temperatura
  display.setCursor(0, 0);
  display.print(F("Temperatura: "));
  display.print(temperature, 1);
  display.println(F(" C"));
  
  // Wilgotnosc
  display.setCursor(0, 10);
  display.print(F("Wilgotnosc: "));
  display.print(humidity, 1);
  display.println(F(" %"));
  
  // Czystosc powietrza jako procent
  int airQualityPercent = calculateAirQualityPercent();
  display.setCursor(0, 20);
  display.print(F("Jakosc Tlenu: "));
  display.print(airQualityPercent);
  display.println(F(" %"));
  
  // Natezenie swiatla jako procent
  int lightPercent = calculateLightPercent();
  display.setCursor(0, 30);
  display.print(F("Naswietlenie: "));
  display.print(lightPercent);
  display.println(F(" %"));
  
  // Status ruchu
  display.setCursor(0, 40);
  display.print(F("Ruch: "));
  // Dodatkowa weryfikacja - raportujemy tylko gdy pin jest fizycznie wysoki
  bool motionConfirmed = motionDetected && (digitalRead(PIR_PIN) == HIGH);
  display.println(motionConfirmed ? F("TAK") : F("NIE"));
  
  // Status alarmu
  display.setCursor(0, 50);
  if (buzzerActive) {
    display.println(F("UWAGA: WYKRYTO ALARM!"));
    
    // Przyczyny alarmu - wyświetlane są w konsoli, bo ekran OLED jest już prawie pełny
    Serial.println(F("Przyczyny alarmu:"));
    if (lightLevel > LIGHT_THRESHOLD) {
      Serial.println(F("- Wysokie natezenie swiatla"));
    }
    if (airQualityPercent < AIR_QUALITY_THRESHOLD) {
      Serial.println(F("- Zla jakosc powietrza"));
    }
    if (motionConfirmed) {
      Serial.println(F("- Wykryto ruch"));
    }
  } else {
    display.println(F("Status: OK"));
  }
  
  display.display();
}

// Funkcja resetująca flagę przerwania
void resetMotionInterrupt() {
  motionInterrupted = false;
}

void setup() {
  Serial.begin(9600);
  Serial.println(F("Inicjalizacja systemu wieloczujnikowego..."));
  
  // Konfiguracja pinów dla silnika krokowego
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);
  
  // Inicjalizacja wyswietlacza OLED
  if(!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS)) {
    Serial.println(F("Blad inicjalizacji wyswietlacza SSD1306"));
    while(1);
  }
  
  // Pokaz ASCII Art
  showASCIIArt();
  
  // Inicjalizacja wszystkich czujnikow z paskiem postepu
  initSensors();
  
  Serial.println(F("Stabilizacja czujnika ruchu (60 sekund)..."));
  
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
  
  // Zwiększ czas stabilizacji
  delay(60000);  // 60 sekund na stabilizację czujnika PIR
  
  // Konfiguracja przerwania dla czujnika ruchu
  attachInterrupt(digitalPinToInterrupt(PIR_PIN), motionISR, RISING);
  
  // Inicjalizacja zmiennych czasowych
  lastMotionTime = millis();
  lastDisplayUpdateTime = millis();
  
  Serial.println(F("System wieloczujnikowy gotowy!"));
}

void loop() {
  // Odczyt danych ze wszystkich czujnikow
  readSensors();
  
  // Sprawdzanie stanu ruchu
  if (motionInterrupted) {
    Serial.println(F("Wykryto ruch (przerwanie)"));
    resetMotionInterrupt();
  }
  
  // Obsługa serwa SG90 po wykryciu ruchu
  if (servoActivated) {
    handleServo();
  }
  
  // Obsługa silnika krokowego 28BYJ-48 po wykryciu ruchu
  if (stepperActivated) {
    handleStepper();
  }
  
  // Kontrola buzzera
  handleBuzzer();
  
  // Aktualizacja wyswietlacza
  unsigned long currentTime = millis();
  if (getTimeDifference(currentTime, lastDisplayUpdateTime) > displayUpdateInterval) {
    updateDisplay();
    lastDisplayUpdateTime = currentTime;
  }
  
  // Wyswietl dane w konsoli
  Serial.print(F("Temperatura: "));
  Serial.print(temperature);
  Serial.print(F(" C, Wilgotnosc: "));
  Serial.print(humidity);
  Serial.print(F(" %, Powietrze: "));
  Serial.print(calculateAirQualityPercent());
  Serial.print(F(" %, Swiatlo: "));
  Serial.print(calculateLightPercent());
  Serial.print(F(" %, Ruch: "));
  
  // Dodatkowa weryfikacja - raportujemy tylko gdy pin jest fizycznie wysoki
  bool motionConfirmed = motionDetected && (digitalRead(PIR_PIN) == HIGH);
  Serial.print(motionConfirmed ? "TAK" : "NIE");
  
  Serial.print(F(", Buzzer: "));
  Serial.println(buzzerActive ? "ON" : "OFF");
  
  // Opóźnienie dla stabilności systemu
  delay(1000);  // Zmniejszone dla lepszej responsywności
}
