// ============================================
// FIRE DETECTION NODE 3 - TDMA + Battery Optimized
// ✅ Light Sleep entre slots
// ✅ OLED ON/OFF avec bouton PRG (OFF par défaut)
// ✅ Cycle 18s - Slot 12s → 18s
// ✅ Watchdog software + hardware (reset auto)
// ✅ Détection NaN / valeurs aberrantes → reset
// ✅ Seuils adaptés détection feux de forêt
// ✅ Recalibration SYNC depuis le gateway
// ✅ MQ-2 allumé 20s avant slot, éteint après TX
// ============================================
#include <Arduino.h>
#include <heltec.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#include <Wire.h>
#include <Temperature.h>
#include <esp_sleep.h>
#include <esp_task_wdt.h>

// ============================================
// ⭐ CONFIGURATION NODE 3
// ============================================
#define NODE_ID        3
#define NODE_SYNC_WORD 0xF3

#define SEND_INTERVAL  18000   // Cycle complet 18s
#define NODE_SLOT      12000   // Slot Node 3 : 12s → 18s
#define SLOT_DURATION   6000
#define WAKE_MARGIN      300   // ms de marge avant le slot

// ============================================
// ⭐ MQ-2 (FC-22)
//
// Branchements :
//   VCC  → 5V  (Heltec)
//   GND  → GND (Heltec)
//   AOUT → GPIO 36 (VP) — pas de diviseur nécessaire en pratique
//   DOUT → GPIO 33
//   (pas de transistor — VCC toujours alimenté via 5V)
// ============================================
#define SMOKE_POWER_PIN      13    // Non utilisé (VCC direct sur 5V)
#define SMOKE_DOUT_PIN       33
#define SMOKE_AOUT_PIN       36    // VP - entrée analogique dédiée
#define SMOKE_PREHEAT_MS      0    // MQ-2 branché sur 5V direct → toujours chaud
#define SMOKE_ALERT_ANALOG 2000    // Seuil alerte (ajuster selon tests terrain)

// ============================================
// ⭐ Watchdog
// ============================================
#define WATCHDOG_HW_TIMEOUT   60                    // secondes
#define WATCHDOG_SW_TIMEOUT   (SEND_INTERVAL * 3)   // 54s sans TX → reset

// ============================================
// ⭐ Seuils feux de forêt
// ============================================
#define TEMP_MIN_VALID    -40.0
#define TEMP_MAX_VALID     85.0
#define TEMP_ALERT         50.0   // °C

#define PRESSURE_MIN_VALID  850.0
#define PRESSURE_MAX_VALID 1100.0

#define HUMIDITY_MIN_VALID    0.0
#define HUMIDITY_MAX_VALID  100.0

// ============================================
// ⭐ Bouton PRG (GPIO 0)
// ============================================
#define PRG_BUTTON       0
bool          oledEnabled  = false;   // OFF par défaut → reste OFF après RST
bool          lastBtnState = HIGH;
unsigned long lastDebounce = 0;

// ============================================
// Configuration LoRa
// ============================================
#define LORA_BAND        915E6
#define LORA_ADDRESS     (byte)(0x04 + NODE_ID)   // 0x07
#define LORA_WEB_ADDRESS (byte)0x01

// ============================================
// Configuration I2C
// ============================================
#define SDA 21
#define SCL 22
TwoWire I2C = TwoWire(1);

// ============================================
// Variables globales
// ============================================
using temp_sensor::TemperatureSensor;
using temp_sensor::TemperatureData;

TemperatureSensor* mySensor;
String        loraMessage;
bool          newMessage     = false;
unsigned long lastTempUpdate = 0;
long          cycleOffset    = 0;

bool          smokeHeaterOn  = false;
int           smokeAnalog    = 0;
bool          smokeDigital   = false;

// ============================================
// ⭐ Position dans le cycle TDMA
// ============================================
unsigned long getPosInCycle(unsigned long now) {
    long raw = (long)(now % SEND_INTERVAL) + cycleOffset;
    raw = raw % (long)SEND_INTERVAL;
    if (raw < 0) raw += SEND_INTERVAL;
    return (unsigned long)raw;
}

// ============================================
// ⭐ BOUTON PRG - Toggle OLED
// ============================================
void checkButton() {
    bool state = digitalRead(PRG_BUTTON);
    if (state == LOW && lastBtnState == HIGH) {
        if (millis() - lastDebounce > 200) {
            oledEnabled = !oledEnabled;
            if (oledEnabled) {
                Heltec.display->displayOn();
                Serial.println("🖥️  OLED ON");
            } else {
                Heltec.display->displayOff();
                Serial.println("🖥️  OLED OFF");
            }
            lastDebounce = millis();
        }
    }
    lastBtnState = state;
}

// ============================================
// Callback LoRa - Réception
// ============================================
void onReceive(int packetSize) {
    if (packetSize == 0) return;
    int    recipient      = LoRa.read();
    byte   sender         = LoRa.read();
    byte   incomingLength = LoRa.read();
    String incoming       = "";
    while (LoRa.available()) incoming += (char)LoRa.read();
    if (recipient != LORA_ADDRESS && recipient != 0xFF) return;
    if (incomingLength != incoming.length())              return;
    loraMessage = incoming;
    newMessage  = true;
    Serial.print("📩 Command from Gateway: ");
    Serial.println(loraMessage);
}

// ============================================
// Envoi message LoRa
// ============================================
void sendMessage(byte dest, String message) {
    digitalWrite(LED_BUILTIN, HIGH);
    LoRa.beginPacket();
    LoRa.write(dest);
    LoRa.write(LORA_ADDRESS);
    LoRa.write(message.length());
    LoRa.print(message);
    LoRa.endPacket();
    digitalWrite(LED_BUILTIN, LOW);
    LoRa.receive();
}

// ============================================
// ⭐ MQ-2
// ============================================
void smokeHeaterOn_fn() {
    if (!smokeHeaterOn) {
        digitalWrite(SMOKE_POWER_PIN, HIGH);
        smokeHeaterOn = true;
        Serial.println("🌫️  MQ-2 ON (préchauffage 20s)");
    }
}

void smokeHeaterOff_fn() {
    if (smokeHeaterOn) {
        digitalWrite(SMOKE_POWER_PIN, LOW);
        smokeHeaterOn = false;
        Serial.println("💤 MQ-2 OFF");
    }
}

void readSmokeSensor() {
    smokeAnalog  = analogRead(SMOKE_AOUT_PIN);
    smokeDigital = (digitalRead(SMOKE_DOUT_PIN) == LOW);
    Serial.print("🌫️  Fumée - Analog: "); Serial.print(smokeAnalog);
    Serial.print("/4095 | Digital: ");
    Serial.println(smokeDigital ? "FUMÉE ⚠️" : "OK");
}

// ============================================
// Validation BME280
// ============================================
bool validateSensorData(TemperatureData data) {
    if (isnan(data.temperature) || isnan(data.humidity) || isnan(data.pressure)) {
        Serial.println("\n💀 SENSOR ERROR: NaN!"); return false;
    }
    if (data.temperature < TEMP_MIN_VALID || data.temperature > TEMP_MAX_VALID) {
        Serial.println("\n💀 SENSOR ERROR: température hors plage!");
        Serial.print("  T: "); Serial.println(data.temperature); return false;
    }
    if (data.humidity < HUMIDITY_MIN_VALID || data.humidity > HUMIDITY_MAX_VALID) {
        Serial.println("\n💀 SENSOR ERROR: humidité hors plage!");
        Serial.print("  H: "); Serial.println(data.humidity); return false;
    }
    if (data.pressure < PRESSURE_MIN_VALID || data.pressure > PRESSURE_MAX_VALID) {
        Serial.println("\n💀 SENSOR ERROR: pression hors plage!");
        Serial.print("  P: "); Serial.println(data.pressure); return false;
    }
    return true;
}

// ============================================
// Envoi données (BME280 + MQ-2)
// Format: NODE_ID;TEMP;HUM;PRESS;SMOKE_ANALOG;SMOKE_DIGITAL
// ============================================
void sendSensorData(TemperatureData data) {
    if (!validateSensorData(data)) {
        Serial.println("  → RESET dans 2s...");
        Serial.flush();
        if (oledEnabled) {
            Heltec.display->clear();
            Heltec.display->setFont(ArialMT_Plain_10);
            Heltec.display->drawString(0,  0, "SENSOR ERROR");
            Heltec.display->drawString(0, 16, "T:" + String(data.temperature, 1));
            Heltec.display->drawString(0, 32, "RESET dans 2s...");
            Heltec.display->display();
        }
        delay(2000); ESP.restart();
    }

    bool fireAlert = (data.temperature >= TEMP_ALERT) ||
                     smokeDigital ||
                     (smokeAnalog >= SMOKE_ALERT_ANALOG);

    String message = String(NODE_ID)            + ";" +
                     String(data.temperature, 2) + ";" +
                     String(data.humidity, 2)    + ";" +
                     String(data.pressure, 2)    + ";" +
                     String(smokeAnalog)          + ";" +
                     String(smokeDigital ? 1 : 0);

    sendMessage(LORA_WEB_ADDRESS, message);

    Serial.print("📤 [Slot 12s] Sent: ");
    Serial.println(message);

    if (fireAlert) {
        Serial.println("🔥🔥🔥 FIRE ALERT! 🔥🔥🔥");
        if (data.temperature >= TEMP_ALERT)
            Serial.println("   → Temp: " + String(data.temperature, 1) + "°C");
        if (smokeDigital)
            Serial.println("   → Fumée numérique!");
        if (smokeAnalog >= SMOKE_ALERT_ANALOG)
            Serial.println("   → Fumée analog: " + String(smokeAnalog) + "/4095");
    }

    if (oledEnabled) {
        Heltec.display->clear();
        Heltec.display->setFont(ArialMT_Plain_10);
        Heltec.display->drawString(0,  0, fireAlert ? "🔥 FIRE Node 3" : "Node 3 - TX OK");
        Heltec.display->drawString(0, 12, "T:" + String(data.temperature,1) + "C H:" + String(data.humidity,0) + "%");
        Heltec.display->drawString(0, 24, "P:" + String(data.pressure, 0) + " hPa");
        Heltec.display->drawString(0, 36, "Fumee:" + String(smokeAnalog) + (smokeDigital ? " ⚠️" : " OK"));
        Heltec.display->drawString(0, 48, fireAlert ? ">>> ALERTE FEU <<<" : "Tout normal");
        Heltec.display->display();
    }
}

// ============================================
// ⭐ Traitement commandes + SYNC
// ============================================
void handleCommand() {
    Serial.print("📩 Command: "); Serial.println(loraMessage);

    if (loraMessage.startsWith("SYNC;")) {
        unsigned long gatewayTime = strtoul(loraMessage.substring(5).c_str(), NULL, 10);
        unsigned long now         = millis();
        unsigned long gatewayPos  = gatewayTime % SEND_INTERVAL;
        unsigned long myRawPos    = now % SEND_INTERVAL;
        long diff = (long)gatewayPos - (long)myRawPos;
        if (diff >  (long)(SEND_INTERVAL / 2)) diff -= SEND_INTERVAL;
        if (diff < -(long)(SEND_INTERVAL / 2)) diff += SEND_INTERVAL;
        cycleOffset = diff;

        Serial.println("🕐 SYNC → recalibré");
        Serial.print("   Offset: "); Serial.print(cycleOffset); Serial.println("ms");

        unsigned long myPos      = getPosInCycle(now);
        unsigned long timeToSlot = (myPos < NODE_SLOT) ? NODE_SLOT - myPos :
                                   (myPos >= NODE_SLOT + SLOT_DURATION) ?
                                   SEND_INTERVAL - myPos + NODE_SLOT : 0;
        Serial.print("   Slot dans: "); Serial.print(timeToSlot / 1000); Serial.println("s");
        return;
    }

    if (oledEnabled) {
        Heltec.display->clear();
        Heltec.display->setFont(ArialMT_Plain_10);
        Heltec.display->drawString(0,  0, "Node 3");
        Heltec.display->drawString(0, 12, "Message GW:");
        Heltec.display->drawString(0, 24, loraMessage.substring(0, 21));
        if (loraMessage.length() > 21)
            Heltec.display->drawString(0, 36, loraMessage.substring(21));
        Heltec.display->display();
    }
}

// ============================================
// ⭐ LIGHT SLEEP - se réveille 20s avant le slot
// pour préchauffer le MQ-2
// ============================================
void sleepUntilMySlot() {
    unsigned long now        = millis();
    unsigned long posInCycle = getPosInCycle(now);
    unsigned long sleepMs    = 0;

    if (posInCycle < NODE_SLOT) {
        sleepMs = NODE_SLOT - posInCycle;
    } else if (posInCycle >= NODE_SLOT + SLOT_DURATION) {
        sleepMs = (SEND_INTERVAL - posInCycle) + NODE_SLOT;
    } else {
        return;  // Dans le slot
    }

    unsigned long totalMargin = SMOKE_PREHEAT_MS + WAKE_MARGIN;

    // Trop court pour dormir → allumer préchauffage et attendre
    if (sleepMs <= totalMargin + 50) {
        smokeHeaterOn_fn();
        return;
    }
    sleepMs -= totalMargin;

    Serial.print("😴 Light sleep ");
    Serial.print(sleepMs / 1000);
    Serial.print("s (réveil 20s avant slot pour préchauffage MQ-2)");
    Serial.println();
    Serial.flush();

    smokeHeaterOff_fn();       // MQ-2 OFF pendant le sleep
    esp_task_wdt_reset();      // Reset WDT avant sleep

    LoRa.sleep();
    esp_sleep_enable_timer_wakeup((uint64_t)sleepMs * 1000ULL);
    esp_light_sleep_start();

    // ⭐ Réveil - réinitialiser les périphériques
    LoRa.receive();
    delay(50);                          // Stabilisation UART
    I2C.begin(SDA, SCL, 100000);        // Re-init I2C (évite NaN après sleep)

    smokeHeaterOn_fn();        // MQ-2 ON → 20s de préchauffage
    Serial.println("⏰ Awake! Préchauffage MQ-2 en cours...");
}

// ============================================
// Setup
// ============================================
void setup() {
    Serial.begin(115200);
    delay(1000);

    Serial.println("\n========================================");
    Serial.println("🔥 FIRE DETECTION NODE 3 + MQ-2");
    Serial.println("========================================");
    Serial.print("📡 LoRa: 0x"); Serial.println(LORA_ADDRESS, HEX);
    Serial.println("   Slot: 12s → 18s | Cycle: 18s");
    Serial.println("   Light sleep:  ENABLED");
    Serial.println("   MQ-2 preheat: 20s avant slot");
    Serial.println("   OLED:         OFF par défaut (PRG)");
    Serial.print("   WDT HW: ");  Serial.print(WATCHDOG_HW_TIMEOUT); Serial.println("s");
    Serial.print("   WDT SW: ");  Serial.print(WATCHDOG_SW_TIMEOUT/1000); Serial.println("s");
    Serial.println("── MQ-2 ─────────────────────────────────");
    Serial.println("   AOUT → GPIO 36 (VP)");
    Serial.println("   DOUT → GPIO 33");
    Serial.print("   Seuil alerte: "); Serial.print(SMOKE_ALERT_ANALOG); Serial.println("/4095");
    Serial.println("── Seuils forêt ─────────────────────────");
    Serial.print("   Temp alerte: "); Serial.print(TEMP_ALERT); Serial.println(" °C");
    Serial.println("=========================================\n");

    // Watchdog hardware
    esp_task_wdt_init(WATCHDOG_HW_TIMEOUT, true);
    esp_task_wdt_add(NULL);
    Serial.println("✅ Watchdog HW armé");

    // Bouton PRG
    pinMode(PRG_BUTTON, INPUT_PULLUP);

    // MQ-2 pins - OFF par défaut au démarrage
    pinMode(SMOKE_POWER_PIN, OUTPUT);
    pinMode(SMOKE_DOUT_PIN,  INPUT);
    digitalWrite(SMOKE_POWER_PIN, LOW);
    smokeHeaterOn = false;
    Serial.println("✅ MQ-2 OFF (s'allumera 20s avant le slot)");

    // I2C
    I2C.begin(SDA, SCL, 100000);
    delay(200);

    // Heltec / LoRa
    Heltec.begin(true, true, true, true, LORA_BAND);
    LoRa.begin(LORA_BAND, true);
    LoRa.setSpreadingFactor(10);
    LoRa.setSignalBandwidth(125E3);
    LoRa.setCodingRate4(8);
    LoRa.setTxPower(20, RF_PACONFIG_PASELECT_PABOOST);
    LoRa.setSyncWord(NODE_SYNC_WORD);
    LoRa.onReceive(onReceive);
    LoRa.receive();
    Serial.println("✅ LoRa ready");

    // Re-init I2C après Heltec
    I2C.begin(SDA, SCL, 100000);
    delay(100);

    // BME280
    Serial.println("🌡️  Init BME280...");
    mySensor = new TemperatureSensor(&I2C);
    TemperatureData testData;
    mySensor->getTemperatureData(&testData);
    Serial.print("   T: "); Serial.print(testData.temperature, 1); Serial.println(" °C");
    Serial.print("   H: "); Serial.print(testData.humidity,    1); Serial.println(" %");
    Serial.print("   P: "); Serial.print(testData.pressure,    1); Serial.println(" hPa");
    if (!validateSensorData(testData)) {
        Serial.println("⚠️  BME280 KO → RESET 2s...");
        Serial.flush(); delay(2000); ESP.restart();
    }
    Serial.println("✅ BME280 OK\n");

    pinMode(LED_BUILTIN, OUTPUT);

    // OLED initial
    Heltec.display->clear();
    Heltec.display->setFont(ArialMT_Plain_10);
    Heltec.display->drawString(0,  0, "Fire Node 3 + MQ-2");
    Heltec.display->drawString(0, 12, "TDMA 18s | Slot 12-18s");
    Heltec.display->drawString(0, 24, "T:" + String(testData.temperature,1) + "C");
    Heltec.display->drawString(0, 36, "Alerte T>" + String((int)TEMP_ALERT) + "C Smoke>" + String(SMOKE_ALERT_ANALOG));
    Heltec.display->drawString(0, 48, "PRG = OLED ON/OFF");
    Heltec.display->display();

    Heltec.display->displayOff();   // OFF par défaut
    Serial.println("🖥️  OLED OFF (PRG pour allumer)\n");
    Serial.println("🚀 Ready! TDMA loop démarré.\n");
}

// ============================================
// Loop Principal
// ============================================
void loop() {
    esp_task_wdt_reset();
    checkButton();

    unsigned long now        = millis();
    unsigned long posInCycle = getPosInCycle(now);
    bool inMySlot = (posInCycle >= NODE_SLOT &&
                     posInCycle <  NODE_SLOT + SLOT_DURATION);

    // ── Watchdog SOFTWARE ────────────────────────────────────────────
    if (lastTempUpdate > 0 && (now - lastTempUpdate > WATCHDOG_SW_TIMEOUT)) {
        Serial.println("\n💀 WDT SOFTWARE: pas de TX → RESET");
        Serial.flush(); delay(100); ESP.restart();
    }

    // ── Transmission ─────────────────────────────────────────────────
    if (inMySlot && (now - lastTempUpdate >= SEND_INTERVAL)) {
        Serial.print("⏰ ["); Serial.print(posInCycle/1000); Serial.println("s] Slot actif...");

        TemperatureData data;
        mySensor->getTemperatureData(&data);
        Serial.print("  T:"); Serial.print(data.temperature,1);
        Serial.print(" H:"); Serial.print(data.humidity,1);
        Serial.print(" P:"); Serial.println(data.pressure,1);

        // MQ-2 — si pas encore préchauffé, attendre 3s minimum
        if (!smokeHeaterOn) {
            Serial.println("⚠️  MQ-2 froid → ON + attente 3s");
            smokeHeaterOn_fn();
            delay(3000);
        }
        readSmokeSensor();

        sendSensorData(data);
        lastTempUpdate = now;

        // ⭐ MQ-2 OFF après TX → économie batterie
        smokeHeaterOff_fn();

        Serial.print("✅ TX done. Prochain slot dans ~");
        Serial.print(SEND_INTERVAL / 1000); Serial.println("s\n");
    }

    // ── Commandes reçues ─────────────────────────────────────────────
    if (newMessage) {
        handleCommand();
        newMessage = false;
    }

    // ── ⭐ Light Sleep (réveil 20s avant pour préchauffer MQ-2) ──────
    if (!newMessage && !inMySlot) {
        sleepUntilMySlot();
    }

    delay(10);
}