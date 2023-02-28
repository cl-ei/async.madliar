# shellcheck disable=SC1045
nohup python gen.py 2>&1 &;
uvicorn --host=0.0.0.0 --port=10090 src.main:app