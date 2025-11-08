"""
Entry point for the Speech Coach API.
Run this file to start the server.
"""
from app.main import app
import uvicorn

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
