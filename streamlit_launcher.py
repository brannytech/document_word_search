import subprocess
import sys
import os
import webbrowser
import time
import socket
from pathlib import Path

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

def get_streamlit_script():
    if getattr(sys, 'frozen', False):
        bundle_dir = sys._MEIPASS
    else:
        bundle_dir = Path(__file__).parent
    
    # IMPORTANT: Change 'app.py' to YOUR Streamlit script name
    return os.path.join(bundle_dir, 'app.py')

def main():
    port = find_free_port()
    streamlit_script = get_streamlit_script()
    
    print(f"Starting Streamlit app on port {port}...")
    
    process = subprocess.Popen([
        sys.executable,
        "-m", "streamlit", "run",
        streamlit_script,
        f"--server.port={port}",
        "--server.headless=true",
        "--browser.serverAddress=localhost",
        "--browser.gatherUsageStats=false",
        "--server.fileWatcherType=none"
    ])
    
    time.sleep(3)
    
    url = f"http://localhost:{port}"
    print(f"Opening browser at {url}")
    webbrowser.open(url)
    
    try:
        process.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        process.terminate()
        process.wait()

if __name__ == "__main__":
    main()