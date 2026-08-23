import uvicorn
from src.worker.entry import start, stop

if __name__ == "__main__":
    start()
    uvicorn.run("src.main:app", host="0.0.0.0", port=10090, workers=1, server_header=False)
    stop()
