import logging
from pydantic import BaseModel, Field
from autogen_core.tools import BaseTool
from starknet_py.net.client import Client
from starknet_py.net.account.account import Account
from starknet_py.net.models import StarknetChainId
from starknet_py.net.signer.stark_curve_signer import KeyPair
from starknet_py.hash.address import compute_address
from starknet_py.net.full_node_client import FullNodeClient
from starknet_py.net.client_errors import ClientError
from starknet_py.net.client_models import ResourceBounds
from starknet_py.contract import Contract
import asyncio
import asyncio
from typing import List, Optional, Any
from autogen_core import CancellationToken
import dotenv
import os

dotenv.load_dotenv(override=True)
# NODE_URL = "https://starknet-sepolia.public.blastapi.io" # Sepolia
NODE_URL = "https://starknet-mainnet.public.blastapi.io/rpc/v0_7" # Mainnet
P = 3618502788666131213697322783095070105623107215331596699973092056135872020481 # starknet curve prime field
OZ_ACCOUNT_CLASS_HASH = 0x00e2eb8f5672af4e6a4e8a8f1b44989685e668489b0a25437733756c5a34a1d6
STRK = 0x04718f5a0fc34cc1af16a1cdee98ffb20c31f5cd61d6ab07201858f4287c938d
USDC = 0x053b40a647cedfca6ca84f542a0fe36736031905a9639a7f19a3c1e66bfd5080
DATE_MEMORIES_SEPOLIA = 0x04bfc11f94899a782d20d4f3ea3259eb115fde449803279b3d613fa0d8fb2c6e
DATE_MEMORIES_MAINNET = 0x07881ce471fad37b0344100cf86efdccce1c93dafc15c52c1c3114da5193419e
IS_SEPOLIA = "sepolia" in NODE_URL
DATE_MEMORIES = DATE_MEMORIES_SEPOLIA if IS_SEPOLIA else DATE_MEMORIES_MAINNET

MAX_GAS = 60

SIMPLE_ABI_ERC20 = [
    {'type': 'function', 'name': 'name', 'inputs': [], 'outputs': [{'type': 'core::felt252'}], 'state_mutability': 'view'},
    {'type': 'function', 'name': 'symbol', 'inputs': [], 'outputs': [{'type': 'core::felt252'}], 'state_mutability': 'view'},
    {'type': 'function', 'name': 'decimals', 'inputs': [], 'outputs': [{'type': 'core::integer::u8'}], 'state_mutability': 'view'},
    {'type': 'function', 'name': 'balance_of', 'inputs': [{'name': 'account', 'type': 'core::starknet::contract_address::ContractAddress'}], 'outputs': [{'type': 'core::integer::u256'}], 'state_mutability': 'view'},
    {'type': 'function', 'name': 'transfer', 'inputs': [{'name': 'recipient', 'type': 'core::starknet::contract_address::ContractAddress'}, {'name': 'amount', 'type': 'core::integer::u256'}], 'outputs': [{'type': 'core::bool'}], 'state_mutability': 'external'},
    {'type': 'function', 'name': 'transfer_from', 'inputs': [{'name': 'sender', 'type': 'core::starknet::contract_address::ContractAddress'}, {'name': 'recipient', 'type': 'core::starknet::contract_address::ContractAddress'}, {'name': 'amount', 'type': 'core::integer::u256'}], 'outputs': [{'type': 'core::bool'}], 'state_mutability': 'external'}
]
FUNDER_SEED = os.environ.get("FUNDER_SEED")

def get_salt(seed: int):
    if isinstance(seed, str):
        seed = int(seed, 16)
    return (seed // 2 ** 8) % 2 ** 251

def get_key_pair(seed: int):
    if isinstance(seed, str):
        seed = int(seed, 16)
    return KeyPair.from_private_key(seed % P)

def get_address(seed: int):
    return compute_address(
        salt=get_salt(seed),
        class_hash=OZ_ACCOUNT_CLASS_HASH,
        constructor_calldata=[get_key_pair(seed).public_key],
        deployer_address=0,
    )
    
def get_address_str(seed: int):
    return f'0x{get_address(seed):064x}'

def get_account(seed: int):
    client = FullNodeClient(node_url=NODE_URL)
    return Account(
        address=get_address(seed),
        key_pair=get_key_pair(seed),
        client=client,
        chain=StarknetChainId.SEPOLIA if IS_SEPOLIA else StarknetChainId.MAINNET)
    
async def is_deployed(address: int):
    client = FullNodeClient(node_url=NODE_URL)
    try:
        class_hash = await client.get_class_hash_at(address)
        return True
    except ClientError as error:
        if "Contract not found" in error.message:
            return False
        raise error
    
async def get_or_deploy_account(seed: int):
    if await is_deployed(get_account(seed).address):
        return get_account(seed)
    client = FullNodeClient(node_url=NODE_URL) 
    account_deployment_result = await Account.deploy_account_v3(
        address=get_address(seed),
        class_hash=OZ_ACCOUNT_CLASS_HASH,
        salt=get_salt(seed),
        key_pair=get_key_pair(seed),
        client=client,
        l1_resource_bounds=ResourceBounds(
            max_amount=MAX_GAS, max_price_per_unit=int(1e15)
        ),
    )
    await asyncio.sleep(0.5)
    # TODO check transaction status
    # await account_deployment_result.wait_for_acceptance() # fails with `ValidationError: {'execution_resources': {'data_availability': ['Missing data for required field.']}}` atm
    return account_deployment_result.account

async def transfer_token(seed: int, recipient_address: int, amount: float, token_address: int):
    # token = await Contract.from_address(token_address, get_account(seed))
    token = Contract(token_address, SIMPLE_ABI_ERC20, get_account(seed))
    decimals, = await token.functions['decimals'].call()
    transfer_tx = await token.functions['transfer'].invoke_v3(
        recipient=recipient_address,
        amount=int(amount * 10 ** decimals),
        l1_resource_bounds=ResourceBounds(
            max_amount=MAX_GAS, max_price_per_unit=int(1e15)
        ),  
    )
    await asyncio.sleep(1)
    return transfer_tx

async def transfer_usdc(seed: int, recipient_address: int, amount: float):
    return await transfer_token(seed, recipient_address, amount, USDC)

async def transfer_strk(seed: int, recipient_address: int, amount: float):
    return await transfer_token(seed, recipient_address, amount, STRK)

async def get_token_balance(seed: int, token_address: int):
    token = Contract(token_address, SIMPLE_ABI_ERC20, get_account(seed))
    balance, = await token.functions['balance_of'].call(get_address(seed))
    decimals, = await token.functions['decimals'].call()
    return balance / 10 ** decimals

async def get_usdc_balance(seed: int):
    return await get_token_balance(seed, USDC)

async def get_strk_balance(seed: int):
    return await get_token_balance(seed, STRK)

async def fund_and_deploy_account(seed: int, funder_seed: int):
    deployed = await is_deployed(get_address(seed))
    if deployed:
        return get_account(seed)
    strk_amount = 0.2 if IS_SEPOLIA else 10.1
    await transfer_strk(funder_seed, get_address(seed), strk_amount)
    if IS_SEPOLIA:
        await transfer_usdc(funder_seed, get_address(seed), 10)
    account = await get_or_deploy_account(seed)
    logging.info(f"Funded and deployed account {get_address_str(seed)}")
    return account

async def mint_nft(seed: int, recipient: int, token_id: int, token_address: int):
    nft = await Contract.from_address(token_address, get_account(seed))
    tx = await nft.functions['safe_mint'].invoke_v3(
        recipient=recipient,
        token_id=token_id,
        data=b'',
        l1_resource_bounds=ResourceBounds(
            max_amount=MAX_GAS, max_price_per_unit=int(1e15)
        ), 
    )
    await asyncio.sleep(1)
    return tx

async def mint_date_memory(seed: int, recipient: int, token_id: int):
    return await mint_nft(seed, recipient, token_id, DATE_MEMORIES)



# Input/Output models for the tools
class TransferTokenInput(BaseModel):
    recipient_address: str = Field(..., description="Recipient's StarkNet address")
    amount: float = Field(..., description="Amount of USDC to transfer")

class NFTMintInput(BaseModel):
    recipient: str = Field(..., description="Recipient's StarkNet address")
    token_id: int = Field(..., description="Token ID to mint")

class EmptyInput(BaseModel):
    pass

class GetWalletTool(BaseTool[EmptyInput, str]):
    def __init__(self, toolkit: 'StarknetToolkit'):
        super().__init__(
            name="get_wallet",
            description="Get wallet address and balance information",
            args_type=EmptyInput,
            return_type=str
        )
        self.toolkit = toolkit

    async def run(self, args: EmptyInput, cancellation_token: CancellationToken) -> str:
        return await self.toolkit.get_wallet_info()

class GetUSDCBalanceTool(BaseTool[EmptyInput, str]):
    def __init__(self, toolkit: 'StarknetToolkit'):
        super().__init__(
            name="get_usdc_balance",
            description="Get USDC balance for the account",
            args_type=EmptyInput,
            return_type=str
        )
        self.toolkit = toolkit

    async def run(self, args: EmptyInput, cancellation_token: CancellationToken) -> str:
        return await self.toolkit.get_usdc_balance()
    
class GetSTRKBalanceTool(BaseTool[EmptyInput, str]):
    def __init__(self, toolkit: 'StarknetToolkit'):
        super().__init__(
            name="get_strk_balance",
            description="Get STRK balance for the account",
            args_type=EmptyInput,
            return_type=str
        )
        self.toolkit = toolkit

    async def run(self, args: EmptyInput, cancellation_token: CancellationToken) -> str:
        return await self.toolkit.get_strk_balance()

class TransferUSDCTool(BaseTool[TransferTokenInput, str]):
    def __init__(self, toolkit: 'StarknetToolkit'):
        super().__init__(
            name="transfer_usdc",
            description="Transfer USDC to a recipient",
            args_type=TransferTokenInput,
            return_type=str
        )
        self.toolkit = toolkit

    async def run(self, args: TransferTokenInput, cancellation_token: CancellationToken) -> str:
        return await self.toolkit.transfer_usdc(args.recipient_address, args.amount)

class TransferSTRKTool(BaseTool[TransferTokenInput, str]):
    def __init__(self, toolkit: 'StarknetToolkit'):
        super().__init__(
            name="transfer_strk",
            description="Transfer STRK to a recipient",
            args_type=TransferTokenInput,
            return_type=str
        )
        self.toolkit = toolkit

    async def run(self, args: TransferTokenInput, cancellation_token: CancellationToken) -> str:
        return await self.toolkit.transfer_strk(args.recipient_address, args.amount)

class MintNFTTool(BaseTool[NFTMintInput, str]):
    def __init__(self, toolkit: 'StarknetToolkit'):
        super().__init__(
            name="mint_nft",
            description="Mint an NFT with a specific token ID",
            args_type=NFTMintInput,
            return_type=str
        )
        self.toolkit = toolkit

    async def run(self, args: NFTMintInput, cancellation_token: CancellationToken) -> str:
        return await self.toolkit.mint_nft(args.recipient, args.token_id)

class StarknetToolkit:
    def __init__(
        self,
        seed: int | str
    ):
        """Initialize StarkNet toolkit with account details and contracts"""
        self.provider_url = NODE_URL
        self._seed = seed
        self.account = get_account(seed)
        self.explorer_url = "https://sepolia.voyager.online" if IS_SEPOLIA else "https://voyager.online"
        
        self.nft_contract = None
        self._account_deployed = False
        
    async def deploy_user_account(self):
        strk_balance = await get_strk_balance(self._seed)
        if strk_balance < 1:
            return "Please fund your account with at least 1 STRK so it can be deployed"
        self.account = await get_or_deploy_account(self._seed)
        self._account_deployed = True
        return "Your account was successfully deployed"
    
    async def setup_account_if_needed(self, funder_seed: Optional[int] = None):
        if not self._account_deployed:
            self.account = await fund_and_deploy_account(self._seed, funder_seed)
            self._account_deployed = True
        return self.account
    
    def get_address(self):
        return get_address_str(self._seed)

    async def get_wallet_info(self) -> str:
        """Get wallet address and network"""
        network = 'starknet-sepolia'
        return f"Wallet Address: {get_address_str(self._seed)} on network {network}"

    async def get_usdc_balance(self) -> str:
        """Get USDC balance for the account"""
        return f"Wallet Address: {get_address_str(self._seed)}\nUSDC Balance: {await get_usdc_balance(self._seed)} USDC"

    async def get_strk_balance(self) -> str:
        """Get STRK balance for the account"""
        return f"Wallet Address: {get_address_str(self._seed)}\nSTRK Balance: {await get_strk_balance(self._seed)} STRK"

    async def transfer_usdc(self, recipient: str, amount: float) -> str:
        """Transfer USDC to recipient"""
        await self.setup_account_if_needed(FUNDER_SEED)
        balance = await get_usdc_balance(self._seed)
        if balance < amount:
            return f"You do not have enough USDC to transfer. Your balance is {balance:.2f} USDC, you are missing {amount - balance:.2f} USDC"
        tx = await transfer_usdc(self._seed, int(recipient, 16), amount)
        tx_hash = hex(tx.hash)
        explorer_link = f"{self.explorer_url}/tx/{tx_hash}"
        
        return (
            f"Transferred {amount} USDC to {recipient}\n"
            f"Transaction Hash: {tx_hash}\n"
            f"Explorer Link: {explorer_link}"
        )
    
    async def transfer_strk(self, recipient: str, amount: float) -> str:
        """Transfer STRK to recipient"""
        await self.setup_account_if_needed(FUNDER_SEED)
        balance = await get_strk_balance(self._seed)
        if balance < amount:
            return f"You do not have enough STRK to transfer. Your balance is {balance:.2f} STRK, you are missing {amount - balance:.2f} STRK"
        tx = await transfer_strk(self._seed, int(recipient, 16), amount)
        tx_hash = hex(tx.hash)
        explorer_link = f"{self.explorer_url}/tx/{tx_hash}"
        
        return (
            f"Transferred {amount} STRK to {recipient}\n"
            f"Transaction Hash: {tx_hash}\n"
            f"Explorer Link: {explorer_link}"
        )

    async def mint_nft(self, recipient: str, token_id: int) -> str:
        """Mint NFT with given token ID, you need to be the owner of the NFT contract to mint"""
        await self.setup_account_if_needed(FUNDER_SEED)
        logging.info(f"Minting NFT with token ID: {token_id} on STARKNET to {recipient}")
        tx = await mint_date_memory(self._seed, int(recipient, 16), token_id)        
        tx_hash = hex(tx.hash)
        #explorer_link = f"{self.explorer_url}/tx/{tx_hash}"
        if IS_SEPOLIA:
            marketplace_link = f"https://starknet-sepolia.openmark.io/nft/{hex(DATE_MEMORIES)}:{token_id}"
        else:
            marketplace_link = f"{self.explorer_url}/nft/{hex(DATE_MEMORIES)}/{token_id}"
        
        return (
            f"Minted NFT with token ID: {token_id}\n"
            f"Transaction Hash: {tx_hash}\n"
            f"View NFT on {marketplace_link}"
        )

    def get_tools(self, include_mint_nft: bool = False) -> List[BaseTool]:
        """Get list of AutoGen tools"""
        tools = [
            GetWalletTool(self),
            # GetUSDCBalanceTool(self),
            GetSTRKBalanceTool(self),
            # TransferUSDCTool(self),
            TransferSTRKTool(self)
        ]
        if include_mint_nft:
            tools.append(MintNFTTool(self))
        return tools