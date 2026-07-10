import subprocess
import webbrowser
import time
import sys
import os

def main():
    print("--------------------------------------------------")
    print("Starting WhatsApp Automation Web Dashboard Server...")
    print("--------------------------------------------------")
    
    # Path to flask app and virtual environment python
    current_dir = os.path.dirname(os.path.abspath(__file__))
    python_path = os.path.join(current_dir, 'venv', 'Scripts', 'python.exe')
    
    if not os.path.exists(python_path):
        python_path = sys.executable  # fallback to system python
        
    app_path = os.path.join(current_dir, 'app.py')
    
    # Start app.py as a subprocess
    # Run in unbuffered mode to see output
    process = subprocess.Popen([python_path, "-u", app_path], cwd=current_dir)
    
    # Wait a few seconds for the Flask server to initialize
    time.sleep(3)
    
    # Open dashboard in default web browser
    dashboard_url = "http://127.0.0.1:5000"
    print(f"Opening dashboard in your web browser: {dashboard_url}")
    webbrowser.open(dashboard_url)
    
    print("\nKeep this console window open to keep the server running.")
    print("Press Ctrl+C here or close this window to stop the server.\n")
    
    try:
        # Wait for the process to exit
        process.wait()
    except KeyboardInterrupt:
        print("\nStopping dashboard server...")
        process.terminate()
        process.wait()
        print("Server stopped.")

if __name__ == '__main__':
    main()
