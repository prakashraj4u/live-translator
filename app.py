"""
Live Translator - launcher
Chalane ke liye:  python app.py
"""
import threading
import time
import webbrowser

import uvicorn

from main import app  # FastAPI app (main.py me hai)

HOST = "127.0.0.1"
PORT = 8000


def open_browser():
    time.sleep(1.5)  # server start hone ka wait
    webbrowser.open(f"http://localhost:{PORT}")


if __name__ == "__main__":
    threading.Thread(target=open_browser, daemon=True).start()
    print(f"Server chal raha hai: http://localhost:{PORT}  (band karne ke liye Ctrl+C)")
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
