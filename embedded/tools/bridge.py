"""
Bridge Gateway → Backend
Interroge le gateway ESP32 via HTTP et envoie les données au backend FastAPI.
Interval par défaut: 6s (aligné avec le slot TDMA).

Usage:
    python bridge.py --gateway http://192.168.X.X
    python bridge.py --gateway http://192.168.X.X --backend http://127.0.0.1:8000 --interval 6
"""

import requests
import time
import argparse
from datetime import datetime


def parse_args():
    parser = argparse.ArgumentParser(description="Bridge Gateway LoRa → Backend API")
    parser.add_argument("--gateway", default="http://192.168.4.1",
                        help="URL du gateway ESP32 (default: http://192.168.4.1)")
    parser.add_argument("--backend", default="http://127.0.0.1:8000",
                        help="URL du backend FastAPI (default: http://127.0.0.1:8000)")
    parser.add_argument("--interval", type=int, default=6,
                        help="Intervalle de polling en secondes (default: 6, aligné TDMA)")
    return parser.parse_args()


def fetch_gateway_data(gateway_url: str) -> list | None:
    """Récupérer les données des nœuds depuis le gateway."""
    try:
        resp = requests.get(f"{gateway_url}/nodes", timeout=3)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        print(f"  [ERREUR] Gateway inaccessible: {e}")
        return None


def send_to_backend(backend_url: str, node: dict) -> dict | None:
    """Envoyer les données complètes d'un nœud au backend."""
    try:
        payload = {
            "sensor_id": f"sensor_{node['id']}",
            "temperature": node.get("temperature", 0),
            "humidity": node.get("humidity", 0),
            "pressure": node.get("pressure"),
            "smoke_analog": node.get("smokeAnalog"),
            "smoke_digital": node.get("smokeDigital", False),
            "rssi": node.get("rssi"),
        }
        resp = requests.post(f"{backend_url}/api/sensors/data", json=payload, timeout=3)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        print(f"  [ERREUR] Backend: {e}")
        return None


def main():
    args = parse_args()

    print("=" * 56)
    print("  BRIDGE — Gateway LoRa → Backend API")
    print("=" * 56)
    print(f"  Gateway : {args.gateway}")
    print(f"  Backend : {args.backend}")
    print(f"  Interval: {args.interval}s (TDMA slot)")
    print("=" * 56)
    print()

    # Vérifier la connexion au backend
    try:
        r = requests.get(f"{args.backend}/", timeout=3)
        info = r.json()
        print(f"[OK] Backend connecté — {info.get('message', '')}")
    except Exception as e:
        print(f"[ERREUR] Backend non disponible: {e}")
        print("         Lancez d'abord: cd backend && uvicorn src.api.main:app --reload --port 8000")
        return

    print("[OK] Démarrage du bridge — Ctrl+C pour arrêter\n")

    cycle = 0
    while True:
        try:
            cycle += 1
            now = datetime.now().strftime("%H:%M:%S")
            print(f"[{now}] Cycle #{cycle}")

            # 1. Récupérer les données du gateway
            nodes = fetch_gateway_data(args.gateway)
            if nodes is None:
                print(f"  Retry dans {args.interval}s...\n")
                time.sleep(args.interval)
                continue

            # 2. Envoyer chaque nœud actif au backend
            sent = 0
            for node in nodes:
                node_id = node.get("id")
                active = node.get("active", False)

                if not active:
                    print(f"  Node {node_id}: OFFLINE — ignoré")
                    continue

                result = send_to_backend(args.backend, node)
                if result:
                    risk = result.get("risk", 0)
                    status = result.get("status", "?")
                    temp = node.get("temperature", 0)
                    hum = node.get("humidity", 0)
                    rssi = node.get("rssi", 0)
                    smoke = node.get("smokeAnalog", 0)

                    line = f"  Node {node_id}: {temp}°C | {hum}% | {rssi}dBm"
                    if node_id == 3 and smoke:
                        line += f" | fumée:{smoke}"
                    line += f" → risque: {risk*100:.1f}% ({status})"
                    print(line)
                    sent += 1

            print(f"  → {sent}/{len(nodes)} nœuds envoyés\n")
            time.sleep(args.interval)

        except KeyboardInterrupt:
            print("\n[ARRÊT] Bridge stoppé.")
            break


if __name__ == "__main__":
    main()
