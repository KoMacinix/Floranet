// ============================================
// GATEWAY - Auto Wake-Up Intelligent
// ✅ Wake beacon UNIQUEMENT pendant le slot du nœud offline
// ✅ Cycle TDMA 18s (synchronisé avec les nœuds)
// ✅ Toujours branché - pas d'économie d'énergie
// ============================================
#include "heltec.h"
#include <WiFi.h>
#include "ESPAsyncWebServer.h"
#include <SPIFFS.h>
#include <SPI.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <NTPClient.h>
#include <WiFiUdp.h>

// ============================================
// CONFIGURATION WIFI
// ============================================
const char* ssid     = "KoNaw";
const char* password = "A1b2c3d4f5*";

// ============================================
// Configuration LoRa
// ============================================
#define BAND         915E6
#define LORA_ADDRESS (byte)0x1
#define SYNC_WORD    0xF3

// ============================================
// TDMA - doit correspondre aux nœuds
// ============================================
#define TDMA_CYCLE     18000   // 18s (6s × 3 nœuds)
#define SLOT_DURATION   6000
// Slot de chaque nœud (index 0 = Node 1)
const unsigned long NODE_SLOTS[3] = { 0, 6000, 12000 };

// ============================================
// Auto-Wake config
// ============================================
#define NODE_TIMEOUT       90000   // 90s sans nouvelles → offline
#define MAX_WAKE_ATTEMPTS      5   // tentatives max avant pause
#define WAKE_RESET_DELAY   60000   // pause 60s avant de réessayer

// ============================================
// Configuration OLED
// ============================================
#define OLED_SDA 4
#define OLED_SCL 15
#define OLED_RST 16
#define SCREEN_WIDTH  128
#define SCREEN_HEIGHT  64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RST);

// ============================================
// Variables globales
// ============================================
struct NodeData {
    int           nodeId;
    float         temperature;
    float         humidity;
    float         pressure;
    int           smokeAnalog;    // ⭐ MQ-2 valeur analogique (0-4095)
    bool          smokeDigital;   // ⭐ MQ-2 seuil numérique
    String        lastUpdate;
    int           rssi;
    bool          active;
    unsigned long lastSeen;
};

NodeData nodes[3] = {
    {1, 0, 0, 0, 0, false, "Never", 0, false, 0},
    {2, 0, 0, 0, 0, false, "Never", 0, false, 0},
    {3, 0, 0, 0, 0, false, "Never", 0, false, 0}
};

unsigned long lastWakeAttempt[3] = {0, 0, 0};
int           wakeAttempts[3]    = {0, 0, 0};

int           rssi;
String        loraMessage;
bool          newMessage       = false;

unsigned long totalMessagesReceived = 0;
unsigned long messagesPerNode[3]    = {0, 0, 0};
unsigned long messagesMissed        = 0;
unsigned long syncBeaconsSent       = 0;
unsigned long wakeBeaconsSent       = 0;
// ============================================
// SYNC beacon - envoyé pendant le slot de chaque nœud
// ============================================
#define SYNC_BEACON_INTERVAL 300000   // 5 minutes entre chaque cycle de sync
bool          syncPending        = false;   // un cycle de sync est en cours
bool          syncSentPerNode[3] = {false, false, false};
unsigned long lastSyncCycle      = 0;

void handleSyncBeacons() {
    unsigned long now        = millis();
    unsigned long posInCycle = now % TDMA_CYCLE;

    // Déclencher un nouveau cycle de sync toutes les 5 minutes
    if (now - lastSyncCycle >= SYNC_BEACON_INTERVAL) {
        syncPending = true;
        syncSentPerNode[0] = false;
        syncSentPerNode[1] = false;
        syncSentPerNode[2] = false;
        lastSyncCycle = now;
        Serial.println("📡 Cycle SYNC déclenché → envoi pendant le slot de chaque nœud");
    }

    // Envoyer le SYNC pendant le slot du nœud concerné (radio actif = reçu garanti)
    if (syncPending) {
        for (int i = 0; i < 3; i++) {
            if (!syncSentPerNode[i]) {
                bool inSlot = (posInCycle >= NODE_SLOTS[i] &&
                               posInCycle <  NODE_SLOTS[i] + SLOT_DURATION);
                if (inSlot) {
                    String msg = "SYNC;" + String(now);
                    digitalWrite(BUILTIN_LED, HIGH);
                    LoRa.idle();
                    LoRa.beginPacket();
                    LoRa.write(0xFF);
                    LoRa.write(LORA_ADDRESS);
                    LoRa.write(msg.length());
                    LoRa.print(msg);
                    LoRa.endPacket();
                    digitalWrite(BUILTIN_LED, LOW);
                    LoRa.receive();

                    syncSentPerNode[i] = true;
                    syncBeaconsSent++;
                    Serial.print("📡 SYNC #"); Serial.print(syncBeaconsSent);
                    Serial.print(" → Node "); Serial.print(i + 1);
                    Serial.print(" (slot actif) @ "); Serial.print(now / 1000); Serial.println("s");
                }
            }
        }

        // Cycle terminé quand les 3 nœuds ont reçu leur SYNC
        if (syncSentPerNode[0] && syncSentPerNode[1] && syncSentPerNode[2]) {
            syncPending = false;
            Serial.println("✅ Cycle SYNC complet - tous les nœuds synchronisés\n");
        }
    }
}

WiFiUDP   ntpUDP;
NTPClient timeClient(ntpUDP);
String    timestamp;

AsyncWebServer server(80);

// ============================================
// Forward declarations
// ============================================
void updateOLEDDisplay();
void decodeMessage();
void sendMessage(byte dest, String message);
void handleSyncBeacons();
void sendWakeBeacon(int nodeId);
void checkNodeStatus();

// ============================================
// OLED update
// ============================================
void updateOLEDDisplay() {
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(WHITE);

    display.setCursor(0, 0);  display.print("Gateway AutoWake");
    display.setCursor(0,10);  display.print("----------------");

    int y = 20;
    for (int i = 0; i < 3; i++) {
        display.setCursor(0, y);
        bool alive = nodes[i].active && (millis() - nodes[i].lastSeen < NODE_TIMEOUT);
        bool fire  = alive && ((nodes[i].temperature > 50.0) ||
                               nodes[i].smokeDigital          ||
                               (nodes[i].smokeAnalog > 2000));

        if (alive) {
            display.print("N"); display.print(nodes[i].nodeId); display.print(":");
            display.print(nodes[i].temperature, 1); display.print("C ");
            display.print((int)nodes[i].humidity); display.print("%");
            if (fire) display.write(15);   // symbole feu
        } else {
            display.print("N"); display.print(i + 1); display.print(": OFFLINE");
            if (wakeAttempts[i] > 0) {
                display.print(" W"); display.print(wakeAttempts[i]);
                display.print("/"); display.print(MAX_WAKE_ATTEMPTS);
            }
        }
        y += 12;
    }

    display.setCursor(0, 56);
    display.print("M:"); display.print(totalMessagesReceived);
    display.print(" W:"); display.print(wakeBeaconsSent);
    display.display();
}

// ============================================
// Callback LoRa
// ============================================
void onReceive(int packetSize) {
    digitalWrite(BUILTIN_LED, HIGH);
    if (packetSize == 0) { digitalWrite(BUILTIN_LED, LOW); return; }

    int    recipient      = LoRa.read();
    byte   sender         = LoRa.read();
    byte   incomingLength = LoRa.read();
    String incoming       = "";

    while (LoRa.available()) incoming += (char)LoRa.read();
    digitalWrite(BUILTIN_LED, LOW);

    if (incomingLength != incoming.length()) { messagesMissed++; return; }

    rssi        = LoRa.packetRssi();
    loraMessage = incoming;
    newMessage  = true;
}

// ============================================
// Décoder message
// ============================================
void decodeMessage() {
    // Format: NODE_ID;TEMP;HUM;PRESS;SMOKE_ANALOG;SMOKE_DIGITAL
    int t1 = loraMessage.indexOf(';');
    int t2 = loraMessage.indexOf(';', t1 + 1);
    int t3 = loraMessage.indexOf(';', t2 + 1);
    int t4 = loraMessage.indexOf(';', t3 + 1);
    int t5 = loraMessage.indexOf(';', t4 + 1);

    if (t1 == -1 || t2 == -1 || t3 == -1) { messagesMissed++; return; }

    int nodeId = loraMessage.substring(0, t1).toInt();
    if (nodeId < 1 || nodeId > 3) { messagesMissed++; return; }

    int idx = nodeId - 1;

    if (!nodes[idx].active) {
        Serial.println("\n🎉🎉🎉 NODE " + String(nodeId) + " BACK ONLINE! 🎉🎉🎉");
        Serial.println("   Wake-up beacon successful!\n");
        wakeAttempts[idx] = 0;
    }

    nodes[idx].temperature  = loraMessage.substring(t1+1, t2).toFloat();
    nodes[idx].humidity     = loraMessage.substring(t2+1, t3).toFloat();
    nodes[idx].pressure     = loraMessage.substring(t3+1, t4 != -1 ? t4 : loraMessage.length()).toFloat();
    nodes[idx].smokeAnalog  = (t4 != -1) ? loraMessage.substring(t4+1, t5 != -1 ? t5 : loraMessage.length()).toInt() : 0;
    nodes[idx].smokeDigital = (t5 != -1) ? (loraMessage.substring(t5+1).toInt() == 1) : false;
    nodes[idx].lastUpdate   = timestamp;
    nodes[idx].rssi         = rssi;
    nodes[idx].active       = true;
    nodes[idx].lastSeen     = millis();

    totalMessagesReceived++;
    messagesPerNode[idx]++;

    bool fireAlert = (nodes[idx].temperature > 50.0) ||
                     nodes[idx].smokeDigital           ||
                     (nodes[idx].smokeAnalog > 2000);

    Serial.println("════════════════════════════════");
    Serial.print("📦 Node "); Serial.print(nodeId); Serial.println(" [TDMA 18s]");
    Serial.println("────────────────────────────────");
    Serial.print("  🌡️  Temp:  "); Serial.print(nodes[idx].temperature, 1); Serial.println(" °C");
    Serial.print("  💧 Hum:   "); Serial.print(nodes[idx].humidity,     1); Serial.println(" %");
    Serial.print("  🌪️  Press: "); Serial.print(nodes[idx].pressure,    1); Serial.println(" hPa");
    Serial.print("  🌫️  Fumée: "); Serial.print(nodes[idx].smokeAnalog);
    Serial.print("/4095 | "); Serial.println(nodes[idx].smokeDigital ? "DÉTECTÉE ⚠️" : "OK");
    Serial.print("  📡 RSSI:  "); Serial.print(rssi); Serial.println(" dBm");
    Serial.print("  📊 Msgs:  "); Serial.println(messagesPerNode[idx]);
    Serial.println("════════════════════════════════\n");

    if (fireAlert) {
        Serial.println("🔥🔥🔥 FIRE ALERT Node " + String(nodeId) + " 🔥🔥🔥");
        if (nodes[idx].temperature > 50.0)
            Serial.println("   → Temp: " + String(nodes[idx].temperature,1) + " °C");
        if (nodes[idx].smokeDigital)
            Serial.println("   → Fumée numérique détectée!");
        if (nodes[idx].smokeAnalog > 2000)
            Serial.println("   → Fumée analogique: " + String(nodes[idx].smokeAnalog) + "/4095");
        Serial.println();
    }

    updateOLEDDisplay();
}

// ============================================
// Envoi message LoRa
// ============================================
void sendMessage(byte dest, String message) {
    digitalWrite(BUILTIN_LED, HIGH);
    LoRa.beginPacket();
    LoRa.write(dest);
    LoRa.write(LORA_ADDRESS);
    LoRa.write(message.length());
    LoRa.print(message);
    LoRa.endPacket();
    digitalWrite(BUILTIN_LED, LOW);
    LoRa.receive();
}

// ============================================
// ⭐ WAKE beacon - pendant le slot du nœud offline
//
// Pourquoi pendant le slot ?
//   Les nœuds font du light sleep entre leurs slots.
//   Ils se réveillent WAKE_MARGIN ms avant leur fenêtre.
//   → Pendant le slot, le radio LoRa du nœud est actif
//     et peut recevoir le WAKE beacon.
//   Envoyer hors slot = nœud en sleep = message perdu.
// ============================================
void sendWakeBeacon(int nodeId) {
    String msg = "WAKE;" + String(nodeId);
    digitalWrite(BUILTIN_LED, HIGH);   // ⭐ LED ON
    LoRa.idle();
    LoRa.beginPacket();
    LoRa.write(0xFF);
    LoRa.write(LORA_ADDRESS);
    LoRa.write(msg.length());
    LoRa.print(msg);
    LoRa.endPacket();
    digitalWrite(BUILTIN_LED, LOW);    // ⭐ LED OFF
    LoRa.receive();

    wakeBeaconsSent++;
    wakeAttempts[nodeId - 1]++;
    lastWakeAttempt[nodeId - 1] = millis();

    Serial.println("\n🔔🔔🔔 WAKE BEACON SENT 🔔🔔🔔");
    Serial.print("   Target: Node "); Serial.println(nodeId);
    Serial.print("   Attempt: "); Serial.print(wakeAttempts[nodeId-1]);
    Serial.print("/"); Serial.println(MAX_WAKE_ATTEMPTS);
    Serial.println("   Envoyé pendant le slot du nœud → radio actif\n");
}

// ============================================
// ⭐ Vérifier nœuds + Auto-Wake intelligent
// ============================================
void checkNodeStatus() {
    unsigned long now        = millis();
    unsigned long posInCycle = now % TDMA_CYCLE;

    for (int i = 0; i < 3; i++) {

        // ── Marquer offline si timeout ──────────────────────────────
        if (nodes[i].active && (now - nodes[i].lastSeen > NODE_TIMEOUT)) {
            nodes[i].active = false;
            Serial.println("\n⚠️⚠️⚠️ NODE " + String(i+1) + " OFFLINE ⚠️⚠️⚠️");
            Serial.print("   Dernier contact il y a ");
            Serial.print((now - nodes[i].lastSeen) / 1000);
            Serial.println("s");
            Serial.println("   Démarrage auto-wake...\n");
        }

        // ── ⭐ Auto-Wake : seulement pendant le slot du nœud ─────────
        if (!nodes[i].active) {
            bool inNodeSlot = (posInCycle >= NODE_SLOTS[i] &&
                               posInCycle <  NODE_SLOTS[i] + SLOT_DURATION);

            unsigned long timeSinceWake = now - lastWakeAttempt[i];

            // Envoyer si :
            //  1. On est dans la fenêtre de slot du nœud (radio actif)
            //  2. Pas déjà envoyé durant ce cycle
            //  3. Sous le seuil max de tentatives
            if (inNodeSlot &&
                timeSinceWake > TDMA_CYCLE &&
                wakeAttempts[i] < MAX_WAKE_ATTEMPTS) {

                sendWakeBeacon(i + 1);
            }

            // Pause après MAX tentatives → reset et réessayer plus tard
            if (wakeAttempts[i] >= MAX_WAKE_ATTEMPTS && timeSinceWake > WAKE_RESET_DELAY) {
                Serial.println("🔄 Node " + String(i+1) + " - Reset tentatives wake");
                wakeAttempts[i] = 0;
            }
        } else {
            wakeAttempts[i] = 0; // Nœud actif → reset
        }
    }
}

// ============================================
// Setup LoRa
// ============================================
void setupLoRa() {
    Serial.println("📡 Initializing LoRa...");
    if (!LoRa.begin(BAND, true)) {
        Serial.println("❌ LoRa setup failed"); while (1) delay(10);
    }
    LoRa.setSpreadingFactor(10);
    LoRa.setSignalBandwidth(125E3);
    LoRa.setCodingRate4(8);
    LoRa.setTxPower(20, RF_PACONFIG_PASELECT_PABOOST);
    LoRa.setSyncWord(SYNC_WORD);
    LoRa.onReceive(onReceive);
    LoRa.receive();
    Serial.println("  ✅ LoRa ready (SF10, BW125, TX20dBm, Sync 0xF3)");
    Serial.println("  🔔 Auto-Wake: ENABLED (pendant slot nœud)\n");
}

// ============================================
// Setup OLED
// ============================================
void startOLED() {
    Serial.println("📺 Initializing OLED...");
    pinMode(OLED_RST, OUTPUT);
    digitalWrite(OLED_RST, LOW);  delay(20);
    digitalWrite(OLED_RST, HIGH);
    Wire.begin(OLED_SDA, OLED_SCL);

    if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3c, false, false)) {
        Serial.println("❌ OLED failed"); for (;;);
    }
    display.clearDisplay();
    display.setTextColor(WHITE);
    display.setTextSize(1);
    display.setCursor(0, 0);  display.print("Gateway AutoWake");
    display.setCursor(0,12);  display.print("TDMA 18s");
    display.setCursor(0,24);  display.print("Smart Wake ON");
    display.display();
    Serial.println("  ✅ OLED ready\n");
}

// ============================================
// Setup WiFi
// ============================================
void connectWiFi() {
    Serial.print("🌐 WiFi connecting");
    WiFi.begin(ssid, password);
    int att = 0;
    while (WiFi.status() != WL_CONNECTED && att < 40) {
        delay(500); Serial.print("."); att++;
    }
    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\n✅ WiFi OK");
        Serial.print("📍 IP: "); Serial.println(WiFi.localIP());
    } else {
        Serial.println("\n❌ WiFi failed");
    }
    delay(1000);
}

// ============================================
// Setup
// ============================================
void setup() {
    Serial.begin(115200);
    delay(1000);

    Serial.println("\n╔════════════════════════════════════════╗");
    Serial.println("║   🔥 GATEWAY - Auto Wake System 🔥    ║");
    Serial.println("║   TDMA 18s + Wake pendant slot nœud  ║");
    Serial.println("╚════════════════════════════════════════╝\n");
    Serial.println("📋 Features:");
    Serial.println("  🔐 Sync Word: 0xF3");
    Serial.println("  ⏱️  TDMA: 18s cycle (3 × 6s)");
    Serial.println("  📡 SYNC beacon: toutes les 5 minutes (pendant slot de chaque nœud)");
    Serial.println("  🔔 Wake beacon: pendant le slot du nœud offline");
    Serial.println("  ⏰ Node timeout: 90s");
    Serial.println("  🔄 Wake retry: max 5 × puis pause 60s\n");

    startOLED();
    setupLoRa();
    connectWiFi();
    pinMode(BUILTIN_LED, OUTPUT);

    if (!SPIFFS.begin()) Serial.println("❌ SPIFFS failed\n");
    else                  Serial.println("✅ SPIFFS OK\n");

    // ── API Routes ──────────────────────────────────────────────────────
    server.on("/", HTTP_GET, [](AsyncWebServerRequest *req) {
        req->send(SPIFFS, "/index.html");
    });

    server.on("/nodes", HTTP_GET, [](AsyncWebServerRequest *req) {
        String json = "[";
        for (int i = 0; i < 3; i++) {
            if (i) json += ",";
            json += "{\"id\":"               + String(nodes[i].nodeId)        + ","
                    "\"temperature\":"       + String(nodes[i].temperature,2) + ","
                    "\"humidity\":"          + String(nodes[i].humidity,2)    + ","
                    "\"pressure\":"          + String(nodes[i].pressure,2)    + ","
                    "\"smokeAnalog\":"       + String(nodes[i].smokeAnalog)   + ","
                    "\"smokeDigital\":"      + (nodes[i].smokeDigital ? "true" : "false") + ","
                    "\"rssi\":"              + String(nodes[i].rssi)          + ","
                    "\"active\":"            + (nodes[i].active?"true":"false")+ ","
                    "\"messagesReceived\":"  + String(messagesPerNode[i])     + "}";
        }
        json += "]";
        req->send(200, "application/json", json);
    });

    server.on("/stats", HTTP_GET, [](AsyncWebServerRequest *req) {
        int act = 0;
        for (int i = 0; i < 3; i++) if (nodes[i].active) act++;
        String json = "{\"totalMessages\":"  + String(totalMessagesReceived) + ","
                       "\"syncBeacons\":"    + String(syncBeaconsSent)       + ","
                       "\"wakeBeacons\":"    + String(wakeBeaconsSent)       + ","
                       "\"activeNodes\":"    + String(act)                   + "}";
        req->send(200, "application/json", json);
    });

    server.begin();
    Serial.println("✅ Web server started");

    timeClient.begin();
    timeClient.setTimeOffset(0);

    Serial.println("\n╔════════════════════════════════════════╗");
    Serial.println("║          🚀 GATEWAY READY! 🚀         ║");
    Serial.println("╚════════════════════════════════════════╝");
    Serial.println("📡 Listening for nodes...");
    Serial.println("🔔 Wake beacon envoyé pendant le slot du nœud offline\n");
}

// ============================================
// Loop
// ============================================
unsigned long lastStatusCheck  = 0;
unsigned long lastTimeUpdate   = 0;
unsigned long lastStatsDisplay = 0;
unsigned long lastOledRefresh  = 0;

void loop() {
    // ⭐ SYNC beacon par slot (garanti reçu par chaque nœud)
    handleSyncBeacons();

    // Timestamp NTP
    if (millis() - lastTimeUpdate > 1000) {
        timeClient.update();
        timestamp = timeClient.getFormattedTime();
        lastTimeUpdate = millis();
    }

    // Message LoRa entrant
    if (newMessage) {
        Serial.print("📥 RX: "); Serial.println(loraMessage);
        decodeMessage();
        newMessage = false;
    }

    // ⭐ Check status + Wake (500ms pour ne pas rater la fenêtre de slot)
    if (millis() - lastStatusCheck > 500) {
        checkNodeStatus();
        lastStatusCheck = millis();
    }

    // OLED refresh toutes les 5s
    if (millis() - lastOledRefresh > 5000) {
        updateOLEDDisplay();
        lastOledRefresh = millis();
    }

    // Stats série toutes les 60s
    if (millis() - lastStatsDisplay > 60000) {
        Serial.println("\n📊 ═══════ STATS ═══════");
        Serial.print("   Messages: ");    Serial.println(totalMessagesReceived);
        Serial.print("   N1:"); Serial.print(messagesPerNode[0]);
        Serial.print(" N2:"); Serial.print(messagesPerNode[1]);
        Serial.print(" N3:"); Serial.println(messagesPerNode[2]);
        Serial.print("   SYNC beacons: "); Serial.println(syncBeaconsSent);
        Serial.print("   WAKE beacons: "); Serial.println(wakeBeaconsSent);
        Serial.println("   ═══════════════════\n");
        lastStatsDisplay = millis();
    }

    delay(10);
}