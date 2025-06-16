#include <DHT.h>            
#include <Wire.h>           
#include <Adafruit_GFX.h>   
#include <Adafruit_SSD1306.h>  
#include <MQ135.h>          
#include <BH1750.h>         
#include <limits.h>         
#include <Servo.h>          
#include <Stepper.h>        
#include <String.h>
#include <ArduinoJson.h>    // Firebase przez JSON
#include <SoftwareSerial.h> // ESP32  serial

// Tutaj mówimy Arduino które piny używamy
#define DHT_DATA_PIN 2        // Czujnik temperatury DHT22
#define PIR_PIN 3             // Czujnik ruchu PIR
#define MQ135_A0_PIN A2       // Czujnik jakości powietrza
#define BUZZER_PIN 53         // Buzzer do piszczenia
#define SSR_RELAY_PIN 22      // Pin do sterowania LEDami
#define SERVO_PIN 9           // Serwo SG90
#define IN1 30    
#define IN2 31
#define IN3 32
#define IN4 33                // Te 4 piny to silnik krokowy
#define ESP32_RX_PIN 10       // ESP32 będzie słuchało na tym pinie
#define ESP32_TX_PIN 11       // ESP32 będzie wysyłać przez ten pin
SoftwareSerial esp32Serial(ESP32_TX_PIN, ESP32_RX_PIN);

// Ustawienia dla wyświetlacza OLED - ten mały ekranik
#define SCREEN_WIDTH 128      
#define SCREEN_HEIGHT 64      
#define OLED_RESET -1         
#define SCREEN_ADDRESS 0x3C   

// Tworzymy obiekty dla wszystkich urządzeń
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
DHT dht(DHT_DATA_PIN, DHT22);       // Czujnik temperatury
MQ135 gasSensor(MQ135_A0_PIN);      // Czujnik powietrza
BH1750 lightMeter;                  // Czujnik światła
Servo sg90;                         // Serwo
const int STEPS_PER_REV = 2048;     // Ile kroków na pełny obrót silnika
Stepper stepper(STEPS_PER_REV, IN1, IN2, IN3, IN4);

// Tutaj trzymamy wszystkie nasze dane z czujników
float temperature = 0.0;    // Temperatura w Celsjuszach
float humidity = 0.0;       // Wilgotność w procentach
float airQuality = 0.0;     // Jakość powietrza
float lightLevel = 0.0;     // Ile światła jest w pokoju
int dhtErrorCount = 0;      // Liczymy błędy czujnika temperatury
bool mqCalibrated = false;  // Czy czujnik powietrza się już nagrzał
bool motionDetected = false;       // Czy ktoś się rusza
unsigned long lastMotionTime = 0;  // Kiedy ostatnio ktoś się ruszał
unsigned long lastDisplayUpdateTime = 0;  // Kiedy ostatnio odświeżyliśmy ekran
int servoPosition = 0;       // Gdzie teraz jest serwo
String incomingCommand = "";      // Jaka komenda przyszła przez serial
bool commandComplete = false;     // Czy komenda jest kompletna

// Zmienne dla Firebase - żeby wysyłać dane do internetu
const String DEVICE_ID = "smart_house_001";  // ID naszego urządzenia
const String LOCATION = "Living Room";       // Gdzie stoi
const String FIRMWARE = "v1.2.3";           // Wersja oprogramowania
unsigned long lastFirebaseSend = 0;          // Kiedy ostatnio wysłaliśmy dane
int dataCount = 0;                           // Ile razy już wysłaliśmy dane
bool esp32Connected = false;                 // Czy ESP32 żyje

// Czasy w milisekundach - żeby nie spamować
const unsigned long debounceTime = 500;     // Czas na uspokojenie czujnika ruchu
const unsigned long displayUpdateInterval = 1000;  // Co ile odświeżać ekran
const unsigned long motionResetTime = 3000; // Po jakim czasie uznać że nie ma ruchu
const unsigned long FIREBASE_INTERVAL = 15000;    // Co ile wysyłać do Firebase (15 sekund)

// Ta funkcja liczy różnicę czasu tak żeby nie było problemów z overflow
unsigned long getTimeDifference(unsigned long currentTime, unsigned long previousTime) {
  return (currentTime >= previousTime) ? (currentTime - previousTime) : (ULONG_MAX - previousTime + currentTime + 1);
}

// Czytamy czy ktoś się rusza - ale z filtrowaniem żeby nie było fałszywych alarmów
void readMotion() {
  bool currentPinState = digitalRead(PIR_PIN) == HIGH;
  
  if (currentPinState != motionDetected) {
    unsigned long currentTime = millis();
    
    // Sprawdzamy czy minęło wystarczająco czasu od ostatniej zmiany
    if (getTimeDifference(currentTime, lastMotionTime) > debounceTime) {
      motionDetected = currentPinState;
      lastMotionTime = currentTime;
    }
  }
  
  // Po 3 sekundach automatycznie resetujemy wykrycie ruchu
  unsigned long currentTime = millis();
  if (motionDetected && getTimeDifference(currentTime, lastMotionTime) > motionResetTime) {
    motionDetected = false;
  }
}

// Pokazujemy fajny napis na starcie
void showASCIIArt() {
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  
  // Centrujemy tekst na ekranie
  String text1 = "AKADEMIA WSB";
  int16_t x1, y1;
  uint16_t w1, h1;
  display.getTextBounds(text1, 0, 0, &x1, &y1, &w1, &h1);
  display.setCursor((SCREEN_WIDTH - w1) / 2, (SCREEN_HEIGHT - 16) / 2);
  display.println(text1);
  
  String text2 = "FIREBASE READY";
  int16_t x2, y2;
  uint16_t w2, h2;
  display.getTextBounds(text2, 0, 0, &x2, &y2, &w2, &h2);
  display.setCursor((SCREEN_WIDTH - w2) / 2, ((SCREEN_HEIGHT - 16) / 2) + 16);
  display.println(text2);
  
  display.display();
  delay(2000);
}

// Test serwa - obracamy je po kolei żeby sprawdzić czy działa
void servoTest() {
  Serial.println(F("Test serwo SG90:"));
  
  // Obracamy serwo co 45 stopni
  for (int angle = 0; angle <= 180; angle += 45) {
    sg90.write(angle);
    servoPosition = angle;
    Serial.print(F("Serwo w pozycji: "));
    Serial.print(angle);
    Serial.println(F(" stopni"));
    delay(300);
  }

  // Wracamy do pozycji startowej
  sg90.write(0);
  servoPosition = 0;
  Serial.println(F("Serwo powróciło do pozycji 0 stopni"));
  delay(300);
}

// Rysujemy pasek postępu na ekranie - żeby pokazać że coś się dzieje
void drawProgressBar(int x, int y, int width, int height, int progress) {
  display.drawRect(x, y, width, height, SSD1306_WHITE);  // Ramka
  int fillWidth = (progress * (width - 4)) / 100;
  display.fillRect(x + 2, y + 2, fillWidth, height - 4, SSD1306_WHITE);  // Wypełnienie
  display.display();
}

// Test buzzera - piszczenie 2 razy żeby sprawdzić czy działa
void testBuzzer() {
  digitalWrite(BUZZER_PIN, HIGH);
  delay(200);
  digitalWrite(BUZZER_PIN, LOW);
  delay(200);
  digitalWrite(BUZZER_PIN, HIGH);
  delay(200);
  digitalWrite(BUZZER_PIN, LOW);
}

// Przeliczamy jakość powietrza na procenty żeby było czytelniej
int calculateAirQualityPercent() {
  float maxPPM = 100.0;  // Maksymalna wartość którą uznajemy za 100%
  int qualityPercent = (int)((airQuality / maxPPM) * 100.0);
  
  // Ograniczamy do 0-100%
  if (qualityPercent > 100) qualityPercent = 100;
  if (qualityPercent < 0) qualityPercent = 0;
  
  return qualityPercent;
}

// Przeliczamy światło na procenty
int calculateLightPercent() {
  int lightPercent = (int)(lightLevel);
  
  // Ograniczamy do 0-100%
  if (lightPercent > 100) lightPercent = 100;
  if (lightPercent < 0) lightPercent = 0;
  
  return lightPercent;
}

// Wysyłamy dane z czujników do Firebase przez ESP32
void sendDataToFirebase() {
  dataCount++;  // Liczymy ile razy wysłaliśmy dane
  
  // Pakujemy wszystkie dane do JSON-a
  StaticJsonDocument<600> doc;
  doc["type"] = "sensor_data";  // Typ wiadomości
  doc["temperature"] = temperature;
  doc["humidity"] = humidity;
  doc["airQuality"] = calculateAirQualityPercent();
  doc["lightLevel"] = (int)lightLevel;
  doc["motionDetected"] = motionDetected;
  doc["batteryLevel"] = random(85, 100);  // Symulujemy poziom baterii
  doc["signalStrength"] = -45;  // Symulujemy siłę sygnału
  doc["timestamp"] = millis();  // Znacznik czasu
  doc["deviceId"] = DEVICE_ID;
  doc["location"] = LOCATION;
  doc["firmware"] = FIRMWARE;
  doc["dataCount"] = dataCount;
  doc["source"] = "arduino";
  doc["isSimulated"] = false;
  doc["servoPosition"] = servoPosition;
  doc["ledStatus"] = digitalRead(SSR_RELAY_PIN) == HIGH;
  doc["buzzerStatus"] = digitalRead(BUZZER_PIN) == HIGH;
  
  // Konwertujemy JSON na string i wysyłamy do ESP32
  String output;
  serializeJson(doc, output);
  esp32Serial.println(output);
  
  Serial.println("📡 Dane #" + String(dataCount) + " wysłane do Firebase");
}

// Wysyłamy alert gdy coś się dzieje (za wysoka temperatura itp.)
void sendAlertToFirebase(String alertType, String message) {
  StaticJsonDocument<500> doc;
  doc["type"] = "alert";  // To jest alert, nie zwykłe dane
  doc["alertType"] = alertType;
  doc["message"] = message;
  doc["severity"] = "HIGH";  // Wysoki priorytet
  doc["temperature"] = temperature;
  doc["humidity"] = humidity;
  doc["airQuality"] = calculateAirQualityPercent();
  doc["lightLevel"] = (int)lightLevel;
  doc["motionDetected"] = motionDetected;
  doc["timestamp"] = millis();
  doc["deviceId"] = DEVICE_ID;
  doc["location"] = LOCATION;
  doc["source"] = "arduino";
  doc["processed"] = false;  // Jeszcze nie przetworzony
  
  // Wysyłamy do ESP32
  String output;
  serializeJson(doc, output);
  esp32Serial.println(output);
  
  Serial.println("🚨 ALERT: " + alertType + " - " + message);
}

// Sprawdzamy czy ESP32 coś do nas napisało
void checkESP32Response() {
  if (esp32Serial.available()) {
    String response = esp32Serial.readStringUntil('\n');
    response.trim();
    
    if (response.length() > 0) {
      Serial.println("ESP32: " + response);
      
      // Sprawdzamy status połączenia z Firebase
      if (response.indexOf("firebase_ok") != -1) {
        esp32Connected = true;
      } else if (response.indexOf("firebase_error") != -1) {
        esp32Connected = false;
      }
    }
  }
}

// Czytamy wszystkie czujniki - temperatura, wilgotność, powietrze, światło, ruch
void readSensors() {
  // Czujnik temperatury DHT22
  float newTemp = dht.readTemperature();
  float newHumidity = dht.readHumidity();
  
  // Sprawdzamy czy odczyt jest OK
  if (!isnan(newTemp) && !isnan(newHumidity)) {
    // Sprawdzamy czy wartości są w rozsądnym zakresie
    if (newTemp >= -40.0 && newTemp <= 80.0 && 
        newHumidity >= 0.0 && newHumidity <= 100.0) {
      temperature = newTemp;
      humidity = newHumidity;
      dhtErrorCount = 0;  // Reset licznika błędów
    } else {
      dhtErrorCount++;
    }
  } else {
    dhtErrorCount++;
    if (dhtErrorCount > 5) {
      Serial.println(F("Powtarzające się błędy DHT - sprawdź okablowanie"));
    }
  }
  
  // Czujnik jakości powietrza MQ135 - robimy średnią z 5 pomiarów
  int analogMQ = 0;
  for (int i = 0; i < 5; i++) {
    analogMQ += analogRead(MQ135_A0_PIN);
    delay(10);
  }
  analogMQ /= 5;  // Średnia
  airQuality = analogMQ * 0.1;  // Przeliczamy na nasze jednostki
  
  // Czujnik światła BH1750
  float lux = lightMeter.readLightLevel();
  if (lux >= 0 && lux < 65535) {  // Sprawdzamy czy wartość jest OK
    lightLevel = lux;
  }
  
  // Czujnik ruchu PIR
  readMotion();
}

// Przetwarzamy komendy które przyszły przez Serial Monitor
void processCommand() {
  incomingCommand.trim();  // Usuwamy białe znaki
  
  Serial.print(F("Otrzymano komendę: "));
  Serial.println(incomingCommand);
  
  // Sterowanie LEDami
  if (incomingCommand.equals("LED_ON")) {
    digitalWrite(SSR_RELAY_PIN, HIGH);
    Serial.println(F("Włączono LEDy"));
  } 
  else if (incomingCommand.equals("LED_OFF")) {
    digitalWrite(SSR_RELAY_PIN, LOW);
    Serial.println(F("Wyłączono LEDy"));
  }
  // Sterowanie buzzerem
  else if (incomingCommand.equals("BUZZER_ON")) {
    digitalWrite(BUZZER_PIN, HIGH);
    Serial.println(F("Włączono buzzer"));
  }
  else if (incomingCommand.equals("BUZZER_OFF")) {
    digitalWrite(BUZZER_PIN, LOW);
    Serial.println(F("Wyłączono buzzer"));
  }
  // Sterowanie serwem - predefiniowane pozycje
  else if (incomingCommand.equals("SG90_0")) {
    sg90.write(0);
    servoPosition = 0;
    Serial.println(F("Obrócono serwo do pozycji 0 stopni"));
  }
  else if (incomingCommand.equals("SG90_1")) {
    sg90.write(90);
    servoPosition = 90;
    Serial.println(F("Obrócono serwo do pozycji 90 stopni"));
  }
  else if (incomingCommand.equals("SG90_2")) {
    sg90.write(180);
    servoPosition = 180;
    Serial.println(F("Obrócono serwo do pozycji 180 stopni"));
  }
  // Sterowanie serwem - dowolny kąt
  else if (incomingCommand.startsWith("SG90_")) {
    int angle = incomingCommand.substring(5).toInt();  // Wyciągamy liczbę z komendy
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
  // Sterowanie silnikiem krokowym
  else if (incomingCommand.equals("Silnik_ruch")) {
    stepper.step(500);  // 500 kroków w prawo
    Serial.println(F("Wykonano 500 kroków silnikiem w prawo"));
  }
  else if (incomingCommand.equals("Silnik_lewo")) {
    stepper.step(-500);  // 500 kroków w lewo
    Serial.println(F("Wykonano 500 kroków silnikiem w lewo"));
  }
  else if (incomingCommand.equals("SERWO_TEST")) {
    servoTest();  // Test całego cyklu serwa
  }
  // Nowe komendy Firebase
  else if (incomingCommand.equals("FIREBASE_SEND")) {
    sendDataToFirebase();  // Wymuś wysłanie danych
  }
  else if (incomingCommand.equals("FIREBASE_TEST")) {
    sendAlertToFirebase("TEST_ALERT", "Test alertu z Arduino");  // Test alertu
  }
  else {
    Serial.println(F("Nieznana komenda"));
  }
  
  // Czyścimy komendę
  incomingCommand = "";
  commandComplete = false;
}

// Inicjalizujemy wszystkie czujniki i urządzenia przy starcie
void initSensors() {
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.println(F("Inicjalizacja systemu..."));
  
  // Inicjalizujemy komunikację z ESP32
  drawProgressBar(10, 30, 108, 10, 10);
  esp32Serial.begin(9600);
  Serial.println(F("ESP32 komunikacja OK"));
  delay(500);
  
  // Inicjalizujemy czujnik temperatury
  drawProgressBar(10, 30, 108, 10, 20);
  dht.begin();
  delay(500);
  
  // Inicjalizujemy czujnik powietrza
  drawProgressBar(10, 30, 108, 10, 35);
  pinMode(MQ135_A0_PIN, INPUT);
  delay(500);
  
  // Inicjalizujemy czujnik światła
  drawProgressBar(10, 30, 108, 10, 50);
  if (lightMeter.begin(BH1750::CONTINUOUS_HIGH_RES_MODE)) {
    Serial.println(F("Czujnik BH1750 zainicjalizowany pomyślnie"));
  } else {
    Serial.println(F("Błąd inicjalizacji czujnika BH1750!"));
  }
  delay(500);
  
  // Inicjalizujemy czujnik ruchu
  drawProgressBar(10, 30, 108, 10, 65);
  pinMode(PIR_PIN, INPUT);
  delay(500);
  
  // Inicjalizujemy serwo
  drawProgressBar(10, 30, 108, 10, 75);
  sg90.attach(SERVO_PIN);
  sg90.write(0);  // Ustawiamy na pozycję startową
  servoPosition = 0;
  delay(500);
  
  // Inicjalizujemy silnik krokowy
  drawProgressBar(10, 30, 108, 10, 85);
  stepper.setSpeed(10);  // 10 RPM
  delay(500);
  
  // Inicjalizujemy przekaźnik LEDów
  drawProgressBar(10, 30, 108, 10, 90);
  pinMode(SSR_RELAY_PIN, OUTPUT);
  digitalWrite(SSR_RELAY_PIN, HIGH);  // Włączamy LEDy na start
  delay(500);
  
  // Inicjalizujemy buzzer
  drawProgressBar(10, 30, 108, 10, 95);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);  // Wyłączony na start
  delay(500);
  
  // Test buzzera i koniec
  drawProgressBar(10, 30, 108, 10, 100);
  testBuzzer();
  delay(500);
  
  display.setCursor(0, 55);
  display.println(F("Firebase Ready!"));
  display.display();
  delay(1000);
}

// Aktualizujemy wyświetlacz OLED - pokazujemy wszystkie dane
void updateDisplay() {
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  
  // Temperatura
  display.setCursor(0, 0);
  display.print(F("Temperatura: "));
  display.print(temperature, 1);
  display.println(F(" C"));
  
  // Wilgotność
  display.setCursor(0, 10);
  display.print(F("Wilgotnosc: "));
  display.print(humidity, 1);
  display.println(F(" %"));
  
  // Jakość powietrza w procentach
  int airQualityPercent = calculateAirQualityPercent();
  display.setCursor(0, 20);
  display.print(F("Jakosc Tlenu: "));
  display.print(airQualityPercent);
  display.println(F(" %"));
  
  // Światło w procentach
  int lightPercent = calculateLightPercent();
  display.setCursor(0, 30);
  display.print(F("Naswietlenie: "));
  display.print(lightPercent);
  display.println(F(" %"));
  
  // Ruch - sprawdzamy czy rzeczywiście jest ruch
  display.setCursor(0, 40);
  display.print(F("Ruch: "));
  bool motionConfirmed = motionDetected && (digitalRead(PIR_PIN) == HIGH);
  display.println(motionConfirmed ? F("WYKRYTO!") : F("BRAK"));
  
  // Status LEDów
  display.setCursor(0, 50);
  display.print(F("LEDy: "));
  display.print(digitalRead(SSR_RELAY_PIN) == HIGH ? F("ON") : F("OFF"));
  
  // Status Firebase
  display.setCursor(70, 50);
  display.print(F("FB:"));
  display.print(esp32Connected ? F("OK") : F("OFF"));
  
  // Pozycja serwa i licznik danych
  display.setCursor(0, 57);
  display.print(F("SG90:"));
  display.print(servoPosition);
  display.print(F(" #"));
  display.print(dataCount);
  
  display.display();
}

// SETUP - uruchamia się raz na początku
void setup() {
  Serial.begin(9600);
  Serial.println(F("Smart House IoT + Firebase - Inicjalizacja..."));
  
  incomingCommand.reserve(32);  // Rezerwujemy miejsce na komendę
  
  // Ustawiamy piny silnika krokowego
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);
  
  // Inicjalizujemy wyświetlacz OLED
  if(!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS)) {
    Serial.println(F("Błąd inicjalizacji wyświetlacza SSD1306!"));
    while(1);  // Zatrzymujemy się tutaj jeśli ekran nie działa
  }
  
  showASCIIArt();    // Pokazujemy ekran powitalny
  initSensors();     // Inicjalizujemy wszystkie czujniki
  servoTest();       // Testujemy serwo
  
  // Czujnik ruchu potrzebuje czasu na stabilizację
  Serial.println(F("Stabilizacja czujnika ruchu (10 sekund)..."));
  
  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println(F("Stabilizacja"));
  display.setCursor(0, 10);
  display.println(F("czujnika ruchu"));
  display.setCursor(0, 30);
  display.println(F("Prosze czekac..."));
  display.display();
  
  delay(10000);  // 10 sekund stabilizacji - nie ruszaj się!
  
  // Inicjalizujemy czasy
  lastMotionTime = millis();
  lastDisplayUpdateTime = millis();
  lastFirebaseSend = millis();
  
  Serial.println(F("Smart House IoT z Firebase gotowy!"));
  Serial.println(F("Nowe komendy Firebase:"));
  Serial.println(F("FIREBASE_SEND - wyślij dane"));
  Serial.println(F("FIREBASE_TEST - test alertu"));
}

// LOOP - główna pętla która się wykonuje w nieskończoność
void loop() {
  unsigned long currentTime = millis();
  
  // Czytamy wszystkie czujniki
  readSensors();
  
  // Sprawdzamy czy przyszła jakaś komenda przez Serial Monitor
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    if (inChar == '\n') {  // Enter = koniec komendy
      commandComplete = true;
    } else {
      incomingCommand += inChar;  // Dodajemy znak do komendy
    }
  }
  
  // Jeśli komenda jest kompletna, przetwarzamy ją
  if (commandComplete) {
    processCommand();
  }
  
  // Sprawdzamy czy ESP32 coś do nas napisało
  checkESP32Response();
  
  // Automatycznie wysyłamy dane do Firebase co 15 sekund
  if (getTimeDifference(currentTime, lastFirebaseSend) >= FIREBASE_INTERVAL) {
    sendDataToFirebase();
    lastFirebaseSend = currentTime;
    
    // Sprawdzamy czy są jakieś problemy i wysyłamy alerty
    if (temperature > 30.0) {
      sendAlertToFirebase("HIGH_TEMPERATURE", "Temperatura: " + String(temperature) + "°C");
    }
    if (humidity > 80.0) {
      sendAlertToFirebase("HIGH_HUMIDITY", "Wilgotność: " + String(humidity) + "%");
    }
    if (calculateAirQualityPercent() > 70) {
      sendAlertToFirebase("POOR_AIR_QUALITY", "Jakość powietrza: " + String(calculateAirQualityPercent()) + "%");
    }
    if (motionDetected) {
      sendAlertToFirebase("MOTION_DETECTED", "Wykryto ruch w " + LOCATION);
    }
  }
  
  // Odświeżamy wyświetlacz co sekundę
  if (getTimeDifference(currentTime, lastDisplayUpdateTime) > displayUpdateInterval) {
    updateDisplay();
    lastDisplayUpdateTime = currentTime;
  }
  
  // Wysyłamy szczegółowy raport przez Serial co 5 sekund
  static unsigned long lastSerialReport = 0;
  if (getTimeDifference(currentTime, lastSerialReport) >= 5000) {
    Serial.println(F("\n==== RAPORT Z CZUJNIKÓW SMART HOUSE + FIREBASE ===="));
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
    Serial.print(F(" % ("));
    Serial.print(lightLevel);
    Serial.println(F(" lux)"));
    
    Serial.print(F("Wykrycie ruchu: "));
    bool motionConfirmed = motionDetected && (digitalRead(PIR_PIN) == HIGH);
    if (motionConfirmed) {
      Serial.println(F("TAK - WYKRYTO RUCH!"));
    } else {
      Serial.println(F("NIE - brak ruchu"));
    }
    
    Serial.print(F("Status LEDów: "));
    Serial.println(digitalRead(SSR_RELAY_PIN) == HIGH ? F("WŁĄCZONY") : F("WYŁĄCZONY"));
    
    Serial.print(F("Status buzzera: "));
    Serial.println(digitalRead(BUZZER_PIN) == HIGH ? F("WŁĄCZONY") : F("WYŁĄCZONY"));
    
    Serial.print(F("ESP32 Firebase: "));
    Serial.println(esp32Connected ? F("POŁĄCZONY") : F("ROZŁĄCZONY"));
    
    Serial.print(F("Dane wysłane do Firebase: #"));
    Serial.println(dataCount);
    
    Serial.println(F("======================================"));
    Serial.println(F("Dostępne komendy:"));
    Serial.println(F("LED_ON/LED_OFF, BUZZER_ON/BUZZER_OFF"));
    Serial.println(F("SG90_1, SG90_2, Silnik_ruch, Silnik_lewo"));
    Serial.println(F("FIREBASE_SEND, FIREBASE_TEST"));
    Serial.println(F("======================================"));
    
    lastSerialReport = currentTime;
  }
  
  delay(100);
}
