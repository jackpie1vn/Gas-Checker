"""
Farcaster Gas Checker Service
Flow: Username → FID → Primary Wallet → Volume/Gas Calculation
"""

import requests
from web3 import Web3
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from decimal import Decimal

# ============= PHẦN 1: CẤU HÌNH =============

# RPC Config
ETHEREUM_RPC = "https://eth-mainnet.g.alchemy.com/v2/Fo_ZjIX96YFpx431df48q"
BASE_RPC = "https://mainnet.base.org"
NEYNAR_API_KEY = "C74FA811-821E-4714-B6EF-CD247EA89A81"

# BaseScan Config (Etherscan API V2)
BASESCAN_API_KEY = '3QVRGCU5JHX592MP64DU2T1DEX3S2DY3BU'
BASESCAN_API_URL = 'https://api.etherscan.io/v2/api'
BASE_CHAIN_ID = '8453'
METHOD_ID = '0x1fff991f'

# Web3 connections
w3_eth = Web3(Web3.HTTPProvider(ETHEREUM_RPC))
w3_base = Web3(Web3.HTTPProvider(BASE_RPC))


# ============= PHẦN 2: DATA CLASSES =============

@dataclass
class GasResult:
    """Kết quả tính gas"""
    success: bool
    username: str
    fid: Optional[int]
    display_name: Optional[str]
    pfp_url: Optional[str]
    primary_wallet: Optional[str]
    total_transactions: int
    total_volume_eth: float
    total_gas_eth: float  # 1% của volume
    total_gas_usd: float
    eth_price: float
    error: Optional[str] = None


# ============= PHẦN 3: FARCASTER FUNCTIONS =============

def fname_to_fid(fname: str) -> Optional[int]:
    """Chuyển fname thành FID"""
    try:
        url = f"https://fnames.farcaster.xyz/transfers/current?name={fname}"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        return data.get("transfer", {}).get("to")
    except Exception as e:
        print(f"fname_to_fid error: {e}")
        return None


def ens_to_fid(ens_name: str) -> Optional[int]:
    """Chuyển ENS thành FID"""
    try:
        eth_addr = w3_eth.ens.address(ens_name)
        if not eth_addr:
            return None

        url = f"https://api.neynar.com/v2/farcaster/user/bulk-by-address/?addresses={eth_addr}"
        headers = {"accept": "application/json", "x-api-key": NEYNAR_API_KEY}

        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return None

        data = r.json()
        users = data.get(eth_addr.lower())
        if not users:
            return None
        return users[0].get("fid")
    except Exception as e:
        print(f"ens_to_fid error: {e}")
        return None


def username_to_fid(username: str) -> Optional[int]:
    """Chuyển username (fname hoặc ENS) thành FID"""
    # Clean username
    username = username.strip().lower()
    if username.startswith("@"):
        username = username[1:]
    
    # Try fname first
    fid = fname_to_fid(username)
    if fid:
        return fid
    
    # Try ENS
    if username.endswith(".eth"):
        fid = ens_to_fid(username)
    
    return fid


def get_eth_addresses(fid: int) -> List[str]:
    """Lấy tất cả verified ETH addresses từ FID"""
    try:
        url = f"https://hub.pinata.cloud/v1/verificationsByFid?fid={fid}"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return []
        
        data = r.json()
        messages = data.get("messages", [])
        eth_addresses = []
        
        for msg in messages:
            body = msg.get("data", {}).get("verificationAddAddressBody", {})
            if body.get("protocol") == "PROTOCOL_ETHEREUM" and body.get("address"):
                eth_addresses.append(body["address"])
        
        return eth_addresses
    except Exception as e:
        print(f"get_eth_addresses error: {e}")
        return []


def ethereum_tx_count(address: str) -> int:
    """Đếm số transaction trên Ethereum"""
    try:
        addr = Web3.to_checksum_address(address)
        return w3_eth.eth.get_transaction_count(addr)
    except Exception as e:
        print(f"ethereum_tx_count error: {e}")
        return 0


def base_tx_count(address: str) -> int:
    """Đếm số transaction trên Base"""
    try:
        addr = Web3.to_checksum_address(address)
        return w3_base.eth.get_transaction_count(addr)
    except Exception as e:
        print(f"base_tx_count error: {e}")
        return 0


def get_primary_wallet(fid: int) -> Optional[str]:
    """
    Xác định Primary Wallet từ FID
    Logic:
    - Nếu có ví chưa có ETH txn → chọn ví có nhiều Base txn nhất
    - Nếu tất cả ví đều có ETH txn → chọn ví có ít ETH txn nhất (signing wallet)
    """
    eth_addresses = get_eth_addresses(fid)
    if not eth_addresses:
        return None

    if len(eth_addresses) == 1:
        return eth_addresses[0]

    # Lấy số transaction Ethereum
    eth_tx_map = {a: ethereum_tx_count(a) for a in eth_addresses}
    
    # Lọc ra các ví Ethereum chưa có txn
    zero_eth_addresses = [a for a, tx in eth_tx_map.items() if tx == 0]

    if zero_eth_addresses:
        # Trong số ví chưa có Ethereum txn, check Base txn
        base_tx_map = {a: base_tx_count(a) for a in zero_eth_addresses}
        primary = max(base_tx_map, key=lambda a: base_tx_map[a])
        return primary
    else:
        # Nếu tất cả ví đều có Ethereum txn > 0, chọn ví có ETH txn thấp nhất
        primary = min(eth_tx_map, key=lambda a: eth_tx_map[a])
        return primary


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Lấy thông tin user từ Neynar API (display_name, pfp_url)"""
    try:
        url = f"https://api.neynar.com/v2/farcaster/user/by_username?username={username}"
        headers = {
            "accept": "application/json",
            "x-api-key": NEYNAR_API_KEY
        }
        
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return None
        
        data = r.json()
        user = data.get("user")
        
        if user:
            # Neynar có thể trả về pfp_url hoặc pfp.url (nested)
            if not user.get("pfp_url") and user.get("pfp"):
                user["pfp_url"] = user.get("pfp", {}).get("url")
        
        return user
    except Exception as e:
        print(f"get_user_by_username error: {e}")
        return None


def get_user_by_fid(fid: int) -> Optional[Dict[str, Any]]:
    """Lấy thông tin user từ Neynar API bằng FID"""
    try:
        url = f"https://api.neynar.com/v2/farcaster/user/bulk?fids={fid}"
        headers = {
            "accept": "application/json",
            "x-api-key": NEYNAR_API_KEY
        }
        
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return None
        
        data = r.json()
        users = data.get("users", [])
        
        if users:
            user = users[0]
            # Neynar có thể trả về pfp_url hoặc pfp.url (nested)
            if not user.get("pfp_url") and user.get("pfp"):
                user["pfp_url"] = user.get("pfp", {}).get("url")
            return user
        
        return None
    except Exception as e:
        print(f"get_user_by_fid error: {e}")
        return None


# ============= PHẦN 4: BASESCAN FUNCTIONS =============

def get_eth_price() -> float:
    """Lấy giá Ethereum hiện tại từ CoinGecko"""
    try:
        url = 'https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd'
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('ethereum', {}).get('usd', 3500.0)
    except Exception as e:
        print(f"get_eth_price error: {e}")
    
    # Giá dự phòng
    return 3500.0


def get_transactions(wallet_address: str) -> List[Dict]:
    """Lấy danh sách transactions từ BaseScan (Etherscan API V2)"""
    try:
        params = {
            'chainid': BASE_CHAIN_ID,
            'module': 'account',
            'action': 'txlist',
            'address': wallet_address,
            'startblock': 0,
            'endblock': 99999999,
            'page': 1,
            'offset': 10000,
            'sort': 'asc',
            'apikey': BASESCAN_API_KEY
        }
        
        response = requests.get(BASESCAN_API_URL, params=params, timeout=30)
        
        if response.status_code != 200:
            print(f"get_transactions HTTP error: {response.status_code}")
            return []
        
        data = response.json()
        
        if data.get('status') == '1':
            return data.get('result', [])
        else:
            message = data.get('message', '')
            if 'No transactions found' not in message:
                print(f"get_transactions error: {message}")
            return []
            
    except Exception as e:
        print(f"get_transactions error: {e}")
        return []


def calculate_volume_for_method(wallet_address: str, method_id: str = METHOD_ID) -> Dict[str, Any]:
    """
    Tính tổng volume của method cụ thể
    
    Returns:
        Dict với:
        - total_transactions: số lượng transactions
        - total_volume_eth: tổng volume (ETH)
        - total_gas_eth: 1% của volume (ETH)
        - total_gas_usd: 1% của volume × giá ETH
        - eth_price: giá ETH hiện tại
    """
    # Lấy giá ETH
    eth_price = get_eth_price()
    
    transactions = get_transactions(wallet_address)
    
    if not transactions:
        return {
            'wallet_address': wallet_address,
            'total_transactions': 0,
            'total_volume_eth': 0.0,
            'total_gas_eth': 0.0,
            'total_gas_usd': 0.0,
            'eth_price': eth_price
        }
    
    # Lọc transactions có method ID matching
    filtered_txs = [
        tx for tx in transactions 
        if tx.get('input', '')[:10].lower() == method_id.lower()
    ]
    
    if not filtered_txs:
        return {
            'wallet_address': wallet_address,
            'total_transactions': 0,
            'total_volume_eth': 0.0,
            'total_gas_eth': 0.0,
            'total_gas_usd': 0.0,
            'eth_price': eth_price
        }
    
    # Tính tổng volume (tính bằng ETH)
    total_volume = Decimal('0')
    for tx in filtered_txs:
        value_in_eth = Decimal(tx.get('value', '0')) / Decimal('1e18')
        total_volume += value_in_eth
    
    # Tính 1% của tổng volume (gọi là "total gas")
    total_gas = total_volume * Decimal('0.01')
    
    # Tính USD
    total_gas_usd = float(total_gas) * eth_price
    
    return {
        'wallet_address': wallet_address,
        'total_transactions': len(filtered_txs),
        'total_volume_eth': float(total_volume),
        'total_gas_eth': float(total_gas),
        'total_gas_usd': round(total_gas_usd, 2),
        'eth_price': eth_price
    }


# ============= PHẦN 5: MAIN FUNCTION =============

def get_user_gas_info(username: str) -> GasResult:
    """
    Main function: Lấy thông tin gas cho Farcaster user
    
    Flow: Username → FID → Primary Wallet → Volume/Gas
    """
    # Clean username
    username = username.strip().lower()
    if username.startswith("@"):
        username = username[1:]
    
    # Bước 1: Lấy thông tin user từ Neynar (bao gồm FID, display_name, pfp_url)
    user_data = get_user_by_username(username)
    
    display_name = None
    pfp_url = None
    fid = None
    
    if user_data:
        fid = user_data.get("fid")
        display_name = user_data.get("display_name")
        pfp_url = user_data.get("pfp_url")
        
        # Debug log
        print(f"[DEBUG] User data from Neynar:")
        print(f"  - FID: {fid}")
        print(f"  - Display Name: {display_name}")
        print(f"  - PFP URL: {pfp_url}")
    else:
        # Fallback: thử tìm FID bằng fname/ENS
        fid = username_to_fid(username)
        print(f"[DEBUG] FID from fname/ENS: {fid}")
        
        # Nếu có FID, thử lấy user info bằng FID
        if fid:
            user_data = get_user_by_fid(fid)
            if user_data:
                display_name = user_data.get("display_name")
                pfp_url = user_data.get("pfp_url")
                print(f"[DEBUG] User data from FID lookup:")
                print(f"  - Display Name: {display_name}")
                print(f"  - PFP URL: {pfp_url}")
    
    if not fid:
        return GasResult(
            success=False,
            username=username,
            fid=None,
            display_name=None,
            pfp_url=None,
            primary_wallet=None,
            total_transactions=0,
            total_volume_eth=0.0,
            total_gas_eth=0.0,
            total_gas_usd=0.0,
            eth_price=get_eth_price(),
            error="User not found - Cannot find FID for this username"
        )
    
    # Bước 2: Tìm Primary Wallet
    primary_wallet = get_primary_wallet(fid)
    
    if not primary_wallet:
        return GasResult(
            success=False,
            username=username,
            fid=fid,
            display_name=display_name,
            pfp_url=pfp_url,
            primary_wallet=None,
            total_transactions=0,
            total_volume_eth=0.0,
            total_gas_eth=0.0,
            total_gas_usd=0.0,
            eth_price=get_eth_price(),
            error="No verified wallet found for this user"
        )
    
    # Bước 3: Tính volume/gas
    volume_result = calculate_volume_for_method(primary_wallet)
    
    return GasResult(
        success=True,
        username=username,
        fid=fid,
        display_name=display_name,
        pfp_url=pfp_url,
        primary_wallet=primary_wallet,
        total_transactions=volume_result['total_transactions'],
        total_volume_eth=volume_result['total_volume_eth'],
        total_gas_eth=volume_result['total_gas_eth'],
        total_gas_usd=volume_result['total_gas_usd'],
        eth_price=volume_result['eth_price'],
        error=None
    )


# ============= PHẦN 6: CLI TEST =============

if __name__ == '__main__':
    import sys
    
    print("=" * 50)
    print("🚀 FARCASTER GAS CHECKER")
    print("=" * 50)
    
    # Get username from args or input
    if len(sys.argv) > 1:
        username = sys.argv[1]
    else:
        username = input("\n📝 Nhập Farcaster username (fname hoặc ENS): ").strip()
    
    if not username:
        print("✗ Vui lòng nhập username!")
        exit()
    
    print(f"\n🔎 Đang xử lý: {username}")
    
    # Get gas info
    result = get_user_gas_info(username)
    
    print(f"\n{'=' * 50}")
    print("📊 KẾT QUẢ")
    print(f"{'=' * 50}")
    
    if result.success:
        print(f"✔ Username: {result.username}")
        print(f"✔ FID: {result.fid}")
        print(f"✔ Primary Wallet: {result.primary_wallet}")
        print(f"✔ Total Transactions: {result.total_transactions}")
        print(f"✔ Total Volume: {result.total_volume_eth:.6f} ETH")
        print(f"✔ Total Gas (1%): {result.total_gas_eth:.6f} ETH")
        print(f"✔ Total Gas USD: ${result.total_gas_usd:.2f}")
        print(f"✔ ETH Price: ${result.eth_price:.2f}")
    else:
        print(f"✗ Error: {result.error}")
        print(f"  Username: {result.username}")
        print(f"  FID: {result.fid}")
        print(f"  Primary Wallet: {result.primary_wallet}")
    
    print(f"{'=' * 50}")
