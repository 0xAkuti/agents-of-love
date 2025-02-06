import sqlite3
import os
import json
from pathlib import Path
from cdp.wallet import Wallet, WalletData

class WalletStore:
    def __init__(self, db_path="wallets.sqlite"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        # Create db directory if it doesn't exist
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            Path(db_dir).mkdir(parents=True, exist_ok=True)
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS wallets (
                    agent_id TEXT PRIMARY KEY,
                    wallet_id TEXT NOT NULL,
                    seed TEXT NOT NULL,
                    network_id TEXT NOT NULL
                )
            ''')
            conn.commit()

    def save_wallet(self, agent_id: str, wallet: Wallet):
        """Save a wallet for an agent"""
        wallet_data = wallet.export_data().to_dict()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT OR REPLACE INTO wallets 
                   (agent_id, wallet_id, seed, network_id) 
                   VALUES (?, ?, ?, ?)''',
                (
                    agent_id,
                    wallet_data["wallet_id"],
                    wallet_data["seed"],
                    wallet_data["network_id"]
                )
            )
            conn.commit()

    def load_wallet(self, agent_id: str) -> WalletData | None:
        """Load a wallet for an agent if it exists"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT wallet_id, seed, network_id 
                   FROM wallets 
                   WHERE agent_id = ?''', 
                (agent_id,)
            )
            result = cursor.fetchone()
            
            if result:
                wallet_id, seed, network_id = result
                wallet_dict = {
                    "wallet_id": wallet_id,
                    "seed": seed,
                    "network_id": network_id
                }
                return WalletData.from_dict(wallet_dict)
            return None

    def delete_wallet(self, agent_id: str):
        """Delete a wallet for an agent"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM wallets WHERE agent_id = ?', (agent_id,))
            conn.commit() 