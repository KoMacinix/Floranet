"""
Service de communication LoRa via port série.
Lit les données JSON envoyées par la passerelle LoRa.
"""

import asyncio
import json
import logging
from datetime import datetime

import serial

logger = logging.getLogger(__name__)


class LoRaService:
    """Lecture asynchrone du port série connecté à la passerelle LoRa."""

    def __init__(self, port: str = "COM3", baudrate: int = 115200, timeout: float = 1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_conn = None
        self.running = False
        self.data_queue: asyncio.Queue = asyncio.Queue()

    async def connect(self):
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
            )
            logger.info("LoRa connecté: %s @ %d baud", self.port, self.baudrate)
        except Exception as e:
            logger.error("Erreur connexion LoRa: %s", e)
            raise

    def _parse_line(self, raw: str) -> dict | None:
        """Parser une ligne JSON reçue du gateway."""
        try:
            data = json.loads(raw)
            data["reception_time"] = datetime.now().isoformat()
            return data
        except (json.JSONDecodeError, ValueError):
            return None

    async def start(self):
        """Boucle de lecture du port série."""
        self.running = True
        logger.info("Service LoRa démarré — écoute sur %s", self.port)

        while self.running:
            try:
                if self.serial_conn and self.serial_conn.in_waiting:
                    raw = self.serial_conn.readline().decode("utf-8").strip()
                    if raw:
                        data = self._parse_line(raw)
                        if data:
                            await self.data_queue.put(data)
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error("Erreur lecture série: %s", e)
                await asyncio.sleep(1)

    async def stop(self):
        self.running = False
        if self.serial_conn:
            self.serial_conn.close()
            logger.info("Port série fermé")
