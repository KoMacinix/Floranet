# Embedded — Capteurs LoRa & Passerelle

Code firmware pour les capteurs BME280/ESP32 et la passerelle LoRa, compilé avec **PlatformIO** (framework Arduino).

## Architecture

```
embedded/
├── gateway/                 # Passerelle LoRa (réception des données)
│   ├── src/
│   │   └── LoraWebServer_Gateway.cpp
│   ├── platformio.ini
│   ├── include/
│   ├── lib/
│   └── test/
│
├── node/                    # Capteur LoRa (envoi des mesures)
│   ├── src/
│   │   ├── LoraTempSensor_Node.cpp
│   │   └── images.h
│   ├── lib/
│   │   └── Temperature/     # Bibliothèque capteur
│   ├── platformio.ini
│   ├── include/
│   └── test/
│
├── tools/                   # Outils de collecte et d'analyse
│   ├── serial_logger_gui.py # Logger série avec GUI (tkinter)
│   ├── analyze_data.py      # Visualisation matplotlib
│   └── data/                # Données collectées (CSV + graphiques)
│
├── .gitignore
└── README.md
```

## Hardware

| Composant         | Détails                                 |
|-------------------|-----------------------------------------|
| Microcontrôleur   | Heltec WiFi LoRa 32 V2 (ESP32)         |
| Capteur           | BME280 (température, humidité, pression)|
| Communication     | LoRa P2P (868 MHz / 915 MHz)           |
| Alimentation      | Powerbank 10 000 mAh                   |

## Protocole TDMA

Le système utilise un **sync word unique** (0xF3) avec des créneaux TDMA de 30 secondes :

| Nœud   | Créneau (slot)  |
|--------|-----------------|
| Node 1 | 0 – 8 secondes  |
| Node 2 | 10 – 18 secondes|
| Node 3 | 20 – 28 secondes|

La passerelle envoie un **beacon SYNC** toutes les 30 secondes pour corriger la dérive d'horloge, et des **WAKE beacons** si un nœud est hors ligne.

## Compilation et upload

### Prérequis

- [PlatformIO](https://platformio.org/) (extension VSCode ou CLI)
- Câble USB-C connecté au Heltec

### Gateway

```bash
cd embedded/gateway
pio run --target upload
pio device monitor --baud 115200
```

### Node

```bash
cd embedded/node
pio run --target upload
pio device monitor --baud 115200
```

## Outils de collecte

### Logger série (GUI)

```bash
cd embedded/tools
py serial_logger_gui.py
```

> **Note :** Utiliser `py.exe` (pas `python.exe`) pour éviter le conflit avec l'environnement PlatformIO qui n'a pas tkinter.

### Analyse des données

```bash
cd embedded/tools
py analyze_data.py
```

## Notes importantes

- Le **BME280** du Node 1 nécessite un remapping I2C (GPIO 21/22 au lieu de 4/15), avec initialisation I2C **avant** `Heltec.begin()` puis réinitialisation après.
- Le Node 2 a un **OLED mort** mais le BME280 fonctionne normalement.
- Le mode **Light Sleep** cible ~7-8 jours d'autonomie, mais certains powerbanks coupent le courant si la consommation descend sous ~10 mA pendant le sommeil.
