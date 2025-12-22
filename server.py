import http.server
import socketserver
import webbrowser
import os
import threading
import time
import traceback

PORT = int(os.getenv("PORT", 8000))
DIRECTORY = "web"

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def log_message(self, format, *args):
        # Silence server logs to keep terminal clean
        pass

def open_browser():
    # Only open browser if NOT in a cloud environment
    if not os.getenv("RAILWAY_STATIC_URL") and not os.getenv("RAILWAY_ENVIRONMENT"):
        time.sleep(1)
        webbrowser.open(f"http://localhost:{PORT}")

def run_server():
    try:
        # Change into the directory of this script to ensure relative paths work
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_dir)
        
        print(f"\n🌐 Starting Web Server on PORT {PORT}...")
        print(f"📁 Serving directory: {os.path.abspath(DIRECTORY)}")
        
        # Verify web directory exists
        if not os.path.exists(DIRECTORY):
            print(f"❌ ERROR: Directory '{DIRECTORY}' not found!")
            os.makedirs(DIRECTORY, exist_ok=True)
            print(f"✅ Created directory: {DIRECTORY}")
        
        # Listen on all interfaces (0.0.0.0) which is required for containers
        with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
            print(f"✅ BLIZZARD LOG SERVER ACTIVE: http://0.0.0.0:{PORT}")
            print(f"    Railway URL: https://blizzard.up.railway.app/")
            print(f"    (Server running in background thread)\n")
            httpd.serve_forever()
            
    except Exception as e:
        print(f"❌ SERVER CRASH: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        # Try to restart after a delay
        time.sleep(5)
        print("🔄 Attempting to restart server...")
        run_server()

if __name__ == "__main__":
    t = threading.Thread(target=open_browser)
    t.start()
    run_server()
