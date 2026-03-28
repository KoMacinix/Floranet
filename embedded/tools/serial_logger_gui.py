#!/usr/bin/env python3
"""
ESP32 Serial Logger - Version Robuste
Parse TOUTES les lignes pour trouver les données
"""

import serial
import csv
import datetime
import re
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext

class SerialLoggerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🔥 ESP32 Fire Detection Logger")
        self.root.geometry("800x600")
        
        self.serial_port = None
        self.is_running = False
        
        # Config frame
        config_frame = ttk.Frame(root, padding="10")
        config_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        ttk.Label(config_frame, text="Port:").grid(row=0, column=0)
        self.port_var = tk.StringVar(value="COM3")
        ttk.Entry(config_frame, textvariable=self.port_var, width=10).grid(row=0, column=1)
        
        ttk.Label(config_frame, text="Baud:").grid(row=0, column=2)
        self.baud_var = tk.StringVar(value="115200")
        ttk.Entry(config_frame, textvariable=self.baud_var, width=10).grid(row=0, column=3)
        
        self.start_btn = ttk.Button(config_frame, text="▶ Start", command=self.start_logging)
        self.start_btn.grid(row=0, column=4, padx=5)
        
        self.stop_btn = ttk.Button(config_frame, text="⏹ Stop", command=self.stop_logging, state='disabled')
        self.stop_btn.grid(row=0, column=5)
        
        # Status
        self.status_var = tk.StringVar(value="⚪ Not connected")
        ttk.Label(root, textvariable=self.status_var, font=('Arial', 10, 'bold')).grid(row=1, column=0)
        
        # Stats
        stats_frame = ttk.Frame(root, padding="10")
        stats_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))
        
        self.total_var = tk.StringVar(value="Total: 0")
        ttk.Label(stats_frame, textvariable=self.total_var).grid(row=0, column=0, padx=10)
        
        self.node1_var = tk.StringVar(value="Node 1: 0")
        ttk.Label(stats_frame, textvariable=self.node1_var).grid(row=0, column=1, padx=10)
        
        self.node2_var = tk.StringVar(value="Node 2: 0")
        ttk.Label(stats_frame, textvariable=self.node2_var).grid(row=0, column=2, padx=10)
        
        self.node3_var = tk.StringVar(value="Node 3: 0")
        ttk.Label(stats_frame, textvariable=self.node3_var).grid(row=0, column=3, padx=10)
        
        # Log display
        ttk.Label(root, text="📋 Log:").grid(row=3, column=0, sticky=tk.W, padx=10)
        self.log_text = scrolledtext.ScrolledText(root, height=20, width=100)
        self.log_text.grid(row=4, column=0, padx=10, pady=10)
        
        # Stats
        self.counts = {'total': 0, 1: 0, 2: 0, 3: 0}
    
    def log(self, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
    
    def update_stats(self, node_id):
        self.counts['total'] += 1
        self.counts[node_id] += 1
        
        self.total_var.set(f"Total: {self.counts['total']}")
        self.node1_var.set(f"Node 1: {self.counts[1]}")
        self.node2_var.set(f"Node 2: {self.counts[2]}")
        self.node3_var.set(f"Node 3: {self.counts[3]}")
    
    def start_logging(self):
        port = self.port_var.get()
        baud = int(self.baud_var.get())
        
        try:
            self.serial_port = serial.Serial(port, baud, timeout=1)
            self.is_running = True
            self.status_var.set(f"🟢 Connected to {port}")
            self.start_btn.config(state='disabled')
            self.stop_btn.config(state='normal')
            
            self.log(f"✅ Connected to {port} at {baud} baud")
            
            # Thread
            thread = threading.Thread(target=self.read_serial, daemon=True)
            thread.start()
            
        except Exception as e:
            self.log(f"❌ Error: {e}")
            self.status_var.set("🔴 Connection failed")
    
    def stop_logging(self):
        self.is_running = False
        if self.serial_port:
            self.serial_port.close()
        self.status_var.set("⚪ Disconnected")
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.log("⏹️  Stopped")
    
    def read_serial(self):
        # ⭐ Buffer pour RSSI
        last_rssi = None
        
        while self.is_running:
            try:
                if self.serial_port.in_waiting > 0:
                    line = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                    
                    if line:
                        # ⭐⭐⭐ PATTERN PRINCIPAL - Cherche partout dans la ligne
                        # Pattern: X;Y.Y;Z.Z;W.W (n'importe où dans la ligne)
                        data_match = re.search(r'(\d+);([\d.]+);([\d.]+);([\d.]+)', line)
                        
                        if data_match:
                            node_id = int(data_match.group(1))
                            temp = float(data_match.group(2))
                            hum = float(data_match.group(3))
                            press = float(data_match.group(4))
                            
                            # Utiliser dernier RSSI connu ou 0
                            rssi = last_rssi if last_rssi else 0
                            
                            # Sauvegarder
                            self.save_to_csv({
                                'node_id': node_id,
                                'temperature': temp,
                                'humidity': hum,
                                'pressure': press,
                                'rssi': rssi
                            })
                            
                            # Log
                            self.log(f"💾 Node {node_id}: {temp}°C, {hum}%, RSSI {rssi}")
                            
                            # Stats
                            self.update_stats(node_id)
                            
                            # Reset RSSI
                            last_rssi = None
                        
                        # Chercher RSSI
                        rssi_match = re.search(r'RSSI:\s*(-?\d+)', line)
                        if rssi_match:
                            last_rssi = int(rssi_match.group(1))
                            
            except Exception as e:
                self.log(f"❌ {e}")
    
    def save_to_csv(self, data):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open('fire_data.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            # Header si fichier vide
            if f.tell() == 0:
                writer.writerow(['timestamp', 'node_id', 'temperature', 'humidity', 'pressure', 'rssi'])
            
            writer.writerow([
                timestamp,
                data['node_id'],
                data['temperature'],
                data['humidity'],
                data['pressure'],
                data['rssi']
            ])

if __name__ == "__main__":
    root = tk.Tk()
    app = SerialLoggerGUI(root)
    root.mainloop()