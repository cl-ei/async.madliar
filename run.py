import uvicorn


if __name__ == "__main__":
    uvicorn.run("src.main:app", port=8080, workers=8, reload=True)
