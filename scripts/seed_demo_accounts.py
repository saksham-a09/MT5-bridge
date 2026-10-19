#!/usr/bin/env python3
import sys
import os

# Add backend directory to path
backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
sys.path.insert(0, backend_dir)

from app.db import init_db, create_account, update_account_telemetry, register_node

def seed():
    print("Initializing Database...")
    init_db()

    print("Registering default Local Node...")
    register_node(
        node_id="local-node-1",
        name="Primary Local Node",
        api_key="local_secret_key",
        ip_address="127.0.0.1",
        max_terminals=20,
        os_info="Local Windows Workstation"
    )

    print("Seeding initial MT5 accounts...")
    accounts_to_seed = [
        {"login": 26302967, "password": "P6c&Lcju", "server": "VantageMarkets-Demo", "name": "Vantage Account 26302967"},
        {"login": 26302966, "password": "*tJ#F*5X", "server": "VantageMarkets-Demo", "name": "Vantage Account 26302966"},
    ]

    for acc in accounts_to_seed:
        create_account(
            login=acc["login"],
            password=acc["password"],
            server=acc["server"],
            name=acc["name"],
            target_node_id="auto",
            expert="",
            symbol="XAUUSD",
            timeframe="M1"
        )
        print(f"Seeded account {acc['login']} ({acc['server']})")

    print("Database successfully seeded with requested Vantage accounts!")

if __name__ == "__main__":
    seed()

