
import threading
import sys
import os

# Import the existing modules
# We need to ensure we can run them as threads or sub-processes
import server
import main

if __name__ == "__main__":
    print("❄️  INITIALIZING BLIZZARD PROTOCOL FOR RAILWAY ❄️")
    
    # 1. Start the Web Server (Daemon thread)
    t_server = threading.Thread(target=server.run_server, daemon=True)
    t_server.start()
    
    # 2. Run the Main Bot (Blocking-ish, but has its own threads)
    # We call main.main() which enters a while True loop
    try:
        main.main()
    except KeyboardInterrupt:
        print("Shutting down...")
