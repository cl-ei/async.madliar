import uvicorn


if __name__ == "__main__":
    uvicorn.run("src.main:app", port=10090, workers=2, reload=False, server_header=False)
