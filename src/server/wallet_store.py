import asyncio
from typing import Optional
from cdp.wallet import Wallet, WalletData
from src.storage.manager import StorageManager
from src.config import Config
import nest_asyncio


class WalletStore:
    def __init__(self):
        """Initialize wallet store using storage manager"""
        self.storage_manager = StorageManager()
        # Allow nested event loops for sync operations
        try:
            nest_asyncio.apply()
        except:
            pass
    
    async def save_wallet(self, agent_id: str, wallet: Wallet) -> None:
        """Save a wallet for an agent"""
        wallet_data = wallet.export_data().to_dict()
        path = Config.get_wallet_path(agent_id)
        await self.storage_manager.storage.write_json(path, wallet_data)
    
    async def load_wallet(self, agent_id: str) -> Optional[WalletData]:
        """Load a wallet for an agent if it exists"""
        path = Config.get_wallet_path(agent_id)
        
        if await self.storage_manager.storage.exists(path):
            wallet_data = await self.storage_manager.storage.read_json(path)
            return WalletData.from_dict(wallet_data)
        return None
    
    def load_wallet_sync(self, agent_id: str) -> Optional[WalletData]:
        """Synchronous version of load_wallet that handles nested event loops"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.load_wallet(agent_id))
    
    async def delete_wallet(self, agent_id: str) -> None:
        """Delete a wallet for an agent"""
        path = Config.get_wallet_path(agent_id)
        if await self.storage_manager.storage.exists(path):
            await self.storage_manager.storage.delete(path)
    
    async def list_wallets(self) -> list[str]:
        """List all wallet agent IDs"""
        return await self.storage_manager.storage.list_dir(Config.WALLETS_PATH) 