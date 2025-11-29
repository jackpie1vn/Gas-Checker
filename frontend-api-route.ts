/**
 * Next.js API Route - Connect to Python Backend
 * File: frontend/src/app/api/gas/route.ts
 */

import { NextResponse } from 'next/server';

// Backend URL - set in .env.local
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

// Types
interface WalletInfo {
  address: string;
  eth_tx_count: number;
  base_tx_count: number;
  eth_balance: number;
  is_primary: boolean;
}

interface GasCheckResponse {
  success: boolean;
  username: string;
  fid: number | null;
  display_name: string | null;
  pfp_url: string | null;
  wallets: WalletInfo[];
  primary_wallet: string | null;
  total_gas_used_eth: number;
  total_gas_used_base: number;
  total_gas_usd: number;
  error?: string;
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const username = searchParams.get('username');

  // Validate input
  if (!username || username.trim() === '') {
    return NextResponse.json(
      { 
        success: false, 
        error: 'Username is required',
        username: '',
        fid: null,
        display_name: null,
        pfp_url: null,
        wallets: [],
        primary_wallet: null,
        total_gas_used_eth: 0,
        total_gas_used_base: 0,
        total_gas_usd: 0
      } as GasCheckResponse,
      { status: 400 }
    );
  }

  try {
    // Call Python backend
    const response = await fetch(
      `${BACKEND_URL}/api/gas?username=${encodeURIComponent(username.trim())}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        // Cache for 60 seconds
        next: { revalidate: 60 }
      }
    );

    if (!response.ok) {
      throw new Error(`Backend responded with status ${response.status}`);
    }

    const data: GasCheckResponse = await response.json();
    
    return NextResponse.json(data);
    
  } catch (error) {
    console.error('Error fetching from backend:', error);
    
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to connect to backend',
        username: username,
        fid: null,
        display_name: null,
        pfp_url: null,
        wallets: [],
        primary_wallet: null,
        total_gas_used_eth: 0,
        total_gas_used_base: 0,
        total_gas_usd: 0
      } as GasCheckResponse,
      { status: 500 }
    );
  }
}

// Quick check endpoint (faster, less data)
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const username = body.username;

    if (!username || username.trim() === '') {
      return NextResponse.json(
        { success: false, error: 'Username is required' },
        { status: 400 }
      );
    }

    // Use quick endpoint for faster response
    const response = await fetch(
      `${BACKEND_URL}/api/quick?username=${encodeURIComponent(username.trim())}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    const data = await response.json();
    return NextResponse.json(data);
    
  } catch (error) {
    console.error('Error in quick check:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to process request' },
      { status: 500 }
    );
  }
}
