# Farcaster Gas Checker - Backend API

Backend API thật để check gas usage cho Farcaster users.

## 🚀 Features

- ✅ **Username → FID**: Chuyển đổi fname hoặc ENS sang Farcaster ID
- ✅ **FID → Wallets**: Lấy tất cả verified ETH addresses
- ✅ **Primary Wallet Detection**: Xác định ví chính dựa trên transaction activity
- ✅ **Gas Usage**: Tính toán tổng gas đã sử dụng (cần Etherscan API key)
- ✅ **Multi-chain**: Hỗ trợ Ethereum mainnet và Base

## 📦 Installation

```bash
# Clone và vào thư mục
cd farcaster-gas-backend

# Tạo virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Copy và edit .env
cp .env.example .env
# Edit .env với API keys của bạn

# Run server
uvicorn main:app --reload --port 8000
```

## 🔑 API Keys cần thiết

| Key | Bắt buộc | Nguồn |
|-----|----------|-------|
| `NEYNAR_API_KEY` | ✅ Yes | [neynar.com](https://neynar.com) |
| `ETHEREUM_RPC` | ✅ Yes | [alchemy.com](https://alchemy.com) hoặc [infura.io](https://infura.io) |
| `ETHERSCAN_API_KEY` | ❌ Optional | [etherscan.io/apis](https://etherscan.io/apis) |
| `BASESCAN_API_KEY` | ❌ Optional | [basescan.org/apis](https://basescan.org/apis) |

## 📡 API Endpoints

### Health Check
```
GET /
GET /api/health
```

### Full Gas Check
```
GET /api/gas?username=vitalik.eth

Response:
{
  "success": true,
  "username": "vitalik.eth",
  "fid": 5650,
  "display_name": "Vitalik Buterin",
  "pfp_url": "https://...",
  "wallets": [...],
  "primary_wallet": "0x...",
  "total_gas_used_eth": 1.234,
  "total_gas_used_base": 0.001,
  "total_gas_usd": 4319.00
}
```

### Quick Check (faster)
```
GET /api/quick?username=dwr.eth

Response:
{
  "success": true,
  "username": "dwr.eth",
  "fid": 3,
  "display_name": "Dan Romero",
  "primary_wallet": "0x...",
  "wallet_count": 4
}
```

### Get FID only
```
GET /api/fid/vitalik.eth
```

### Get Wallets
```
GET /api/wallets/dwr.eth
```

## 🔗 Connect to Frontend (Next.js)

Tạo file `frontend/src/app/api/gas/route.ts`:

```typescript
import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const username = searchParams.get('username');

  if (!username) {
    return NextResponse.json(
      { success: false, error: 'Username is required' },
      { status: 400 }
    );
  }

  try {
    const response = await fetch(
      `${BACKEND_URL}/api/gas?username=${encodeURIComponent(username)}`,
      { next: { revalidate: 60 } } // Cache 60 seconds
    );

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { success: false, error: 'Failed to fetch from backend' },
      { status: 500 }
    );
  }
}
```

## 🐳 Deploy with Docker

```bash
# Build
docker build -t farcaster-gas-api .

# Run
docker run -d -p 8000:8000 --env-file .env farcaster-gas-api
```

## 🚀 Deploy to Railway/Render

1. Push code to GitHub
2. Connect repository to Railway/Render
3. Set environment variables
4. Deploy!

## 📝 Architecture

```
Username (fname/ENS)
        ↓
   [fname_to_fid]  ←→  fnames.farcaster.xyz
   [ens_to_fid]    ←→  ENS + Neynar API
        ↓
      FID
        ↓
   [get_user_info] ←→  Neynar API
        ↓
   Verified Addresses
        ↓
   [determine_primary_wallet]
        ↓
   Transaction Counts (ETH + Base RPC)
        ↓
   Gas Usage (Etherscan/Basescan API)
        ↓
   Final Response
```

## 📄 License

MIT
