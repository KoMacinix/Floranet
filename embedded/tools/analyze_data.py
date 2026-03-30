import matplotlib
import pandas as pd
import matplotlib.pyplot as plt
matplotlib.use('TkAgg')

# Charger données
df = pd.read_csv('fire_data.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Statistiques par nœud
print("📊 Statistiques par Nœud:")
print(df.groupby('node_id')[['temperature', 'humidity', 'pressure']].describe())

# Graphiques
fig, axes = plt.subplots(3, 1, figsize=(12, 10))

# Température
for node_id in df['node_id'].unique():
    node_data = df[df['node_id'] == node_id]
    axes[0].plot(node_data['timestamp'], node_data['temperature'], label=f'Node {node_id}')
axes[0].set_ylabel('Temperature (°C)')
axes[0].legend()
axes[0].grid(True)

# Humidité
for node_id in df['node_id'].unique():
    node_data = df[df['node_id'] == node_id]
    axes[1].plot(node_data['timestamp'], node_data['humidity'], label=f'Node {node_id}')
axes[1].set_ylabel('Humidity (%)')
axes[1].legend()
axes[1].grid(True)

# RSSI
for node_id in df['node_id'].unique():
    node_data = df[df['node_id'] == node_id]
    axes[2].plot(node_data['timestamp'], node_data['rssi'], label=f'Node {node_id}')
axes[2].set_ylabel('RSSI (dBm)')
axes[2].set_xlabel('Time')
axes[2].legend()
axes[2].grid(True)

plt.tight_layout()
plt.savefig('fire_data_analysis.png', dpi=300)
plt.show()