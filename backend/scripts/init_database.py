"""
Script d'initialisation de la base de données PostgreSQL.
Crée les tables et insère les capteurs depuis la configuration.

Usage:
    python scripts/init_database.py
"""

import sys
from pathlib import Path

# Ajouter le dossier backend/ au path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg2
from src.core.config import DatabaseConfig, SENSORS


def init_database():
    print("=" * 60)
    print("  INITIALISATION BASE DE DONNÉES POSTGRESQL")
    print("=" * 60)

    try:
        conn = psycopg2.connect(
            host=DatabaseConfig.HOST,
            port=DatabaseConfig.PORT,
            dbname=DatabaseConfig.NAME,
            user=DatabaseConfig.USER,
            password=DatabaseConfig.PASSWORD,
            sslmode="disable",
        )
        cur = conn.cursor()

        # Lire et exécuter le script SQL
        sql_path = Path(__file__).resolve().parent.parent / "db" / "init.sql"
        with open(sql_path, "r", encoding="utf-8") as f:
            sql = f.read()
        cur.execute(sql)
        conn.commit()

        # Afficher les résultats
        cur.execute("SELECT sensor_id, name, zone FROM sensors")
        sensors = cur.fetchall()

        print(f"\nCapteurs enregistrés: {len(sensors)}")
        for s in sensors:
            print(f"  - {s[0]}: {s[1]} ({s[2]})")

        print("\nTables créées:")
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' ORDER BY table_name
        """)
        for row in cur.fetchall():
            print(f"  - {row[0]}")

        cur.close()
        conn.close()

        print("\n" + "=" * 60)
        print("  BASE DE DONNÉES INITIALISÉE AVEC SUCCÈS")
        print("=" * 60)

    except psycopg2.OperationalError as e:
        print(f"\n[ERREUR CONNEXION] {e}")
        print("\nVérifications:")
        print("  1. Le conteneur Docker tourne-t-il? → docker ps")
        print("  2. Si arrêté: docker start floranet-db")
        print("  3. Le fichier .env est-il correctement rempli?")
        print(f"  4. Le mot de passe dans .env correspond-il à celui du docker run?")
    except Exception as e:
        print(f"\n[ERREUR] {e}")


if __name__ == "__main__":
    init_database()
