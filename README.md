# Project Flux (Automated Liquidity & Treasury Protocol)

Project Flux is a self-sustaining DeFi protocol designed to actively manage its own liquidity via high-frequency volatility trading and automate cross-promotion through treasury diversification.

## Executive Summary

Unlike static tokens, this protocol utilizes an "Active Treasury" system. The system monitors the Protocol Treasury Wallet and when fees accumulate, it executes a split strategy.

## Key Features

### The Core Mechanic ("The Hybrid Loop")

Triggered when the wallet balance hits a configurable threshold (e.g., 0.5 SOL).

1.  **Likquidity Provisioning (The Engine) - 80%**
    *   Buys the Native Token ($FLUX).
    *   Holds for a set interval or price target.
    *   Sells back to SOL to compound the treasury.
    *   **Goal:** Price support and volume generation.

2.  **Treasury Diversification (The Marketing Layer) - 20%**
    *   Buys a "Target Asset" (e.g., the #1 Trending Token on Solana).
    *   Holds the asset for visibility.
    *   **Goal:** "Billboard Marketing" via on-chain visibility.

## Technical Stack

*   **Language:** Python 3.10+
*   **APIs:** PumpPortal (Trading), DexScreener (Market Data)
*   **Libraries:** `solana-py`, `solders`, `requests`
*   **Infrastructure:** Designed for execution on a VPS/Server (e.g., Railway).

## Setup

1.  Clone the repository.
    ```bash
    git clone https://github.com/nullxnothing/blizzard2.0.git
    cd blizzard2.0
    ```

2.  Install dependencies.
    ```bash
    pip install -r requirements.txt
    ```

3.  Configure Environment Variables.
    *   Rename `.env.example` to `.env`.
    *   Fill in your `PRIVATE_KEY`, `RPC_URL`, etc.

4.  Run the Application.
    ```bash
    python main.py
    ```

## Disclaimer

This project is for educational purposes only. Use at your own risk.
