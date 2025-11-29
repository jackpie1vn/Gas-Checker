"""
Farcaster Gas Checker API
FastAPI backend for checking gas usage by Farcaster username
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from services import get_user_gas_info, get_eth_price

app = FastAPI(
    title="Farcaster Gas Checker API",
    description="Check gas usage for Farcaster users by username",
    version="2.0.0"
)

# CORS - Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# Response Models
# ============================================

class GasCheckResponse(BaseModel):
    success: bool
    username: str
    fid: Optional[int]
    display_name: Optional[str]
    pfp_url: Optional[str]
    primary_wallet: Optional[str]
    total_transactions: int
    total_volume_eth: float
    total_gas_eth: float  # 1% của volume
    total_gas_usd: float  # total_gas_eth × ETH price
    eth_price: float
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    eth_price: float


# ============================================
# Endpoints
# ============================================

@app.get("/", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="ok",
        eth_price=get_eth_price()
    )


@app.get("/api/health", response_model=HealthResponse)
async def api_health():
    """API health check"""
    return await health_check()


@app.get("/api/gas", response_model=GasCheckResponse)
async def check_gas(
    username: str = Query(..., description="Farcaster username (fname or ENS)")
):
    """
    Get gas info for a Farcaster user.
    
    Flow: Username → FID → Primary Wallet → Volume/Gas
    
    Returns:
    - total_transactions: Number of transactions with specific method
    - total_volume_eth: Total volume in ETH
    - total_gas_eth: 1% of volume in ETH
    - total_gas_usd: 1% of volume × current ETH price
    """
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")
    
    result = get_user_gas_info(username)
    
    return GasCheckResponse(
        success=result.success,
        username=result.username,
        fid=result.fid,
        display_name=result.display_name,
        pfp_url=result.pfp_url,
        primary_wallet=result.primary_wallet,
        total_transactions=result.total_transactions,
        total_volume_eth=result.total_volume_eth,
        total_gas_eth=result.total_gas_eth,
        total_gas_usd=result.total_gas_usd,
        eth_price=result.eth_price,
        error=result.error
    )


# ============================================
# Run with: uvicorn main:app --reload --port 8000
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
