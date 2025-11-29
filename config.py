import os
from dotenv import load_dotenv

load_dotenv()

# RPC Endpoints
ETHEREUM_RPC = os.getenv("ETHEREUM_RPC", "https://eth-mainnet.g.alchemy.com/v2/demo")
BASE_RPC = os.getenv("BASE_RPC", "https://mainnet.base.org")
OPTIMISM_RPC = os.getenv("OPTIMISM_RPC", "https://mainnet.optimism.io")

# API Keys
NEYNAR_API_KEY = os.getenv("NEYNAR_API_KEY", "")
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "")
BASESCAN_API_KEY = os.getenv("BASESCAN_API_KEY", "")

# CORS
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001").split(",")
