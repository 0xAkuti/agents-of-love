import asyncio
import sqlite3
import json
import pathlib
from typing import Dict, Any
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.storage.manager import StorageManager
from src.config import Config


async def migrate_wallets(sqlite_path: str) -> None:
    """
    Migrate wallet data from SQLite to JSON files.
    
    Args:
        sqlite_path: Path to the SQLite database file
    """
    if not pathlib.Path(sqlite_path).exists():
        print(f"SQLite database not found at {sqlite_path}")
        return
        
    # Connect to SQLite database
    conn = sqlite3.connect(sqlite_path)
    cursor = conn.cursor()
    
    # Get all wallet data
    cursor.execute('SELECT agent_id, wallet_id, seed, network_id FROM wallets')
    wallets = cursor.fetchall()
    
    # Initialize storage manager
    storage_manager = StorageManager()
    
    # Migrate each wallet
    for agent_id, wallet_id, seed, network_id in wallets:
        wallet_data = {
            "wallet_id": wallet_id,
            "seed": seed,
            "network_id": network_id
        }
        
        # Save to new storage
        path = Config.get_wallet_path(agent_id)
        await storage_manager.storage.write_json(path, wallet_data)
        print(f"Migrated wallet for agent {agent_id}")
    
    print(f"\nMigration complete. Migrated {len(wallets)} wallets.")
    
    # Close SQLite connection
    conn.close()
    
    # Rename old database file
    old_db = pathlib.Path(sqlite_path)
    old_db.rename(old_db.with_suffix('.sqlite.bak'))
    print(f"\nRenamed old database to {old_db.with_suffix('.sqlite.bak')}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python migrate_wallets.py <sqlite_db_path>")
        sys.exit(1)
        
    sqlite_path = sys.argv[1]
    asyncio.run(migrate_wallets(sqlite_path)) 