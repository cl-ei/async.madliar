# src/log_stream.py
import os
import subprocess
import time
from collections import deque
from fastapi.responses import StreamingResponse
from src.config import IS_PROD, LOG_FILE


def _get_inode(path: str) -> int:
    try:
        return os.stat(path).st_ino
    except FileNotFoundError:
        return 0


def _generate_linux():
    current_inode = _get_inode(LOG_FILE)
    proc = subprocess.Popen(
        ["tail", "-n", "200", "-f", LOG_FILE],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    try:
        for line in proc.stdout:
            new_inode = _get_inode(LOG_FILE)
            if new_inode != current_inode and new_inode != 0:
                yield "event: rotate\ndata: {}\n\n"
                break
            yield f"data: {line.rstrip()}\n\n"
    except GeneratorExit:
        proc.terminate()
        proc.wait(timeout=3)
    except Exception:
        proc.terminate()


def _get_file_meta(path: str):
    try:
        st = os.stat(path)
        return st.st_size, st.st_mtime
    except FileNotFoundError:
        return 0, 0


def _generate_windows():
    # ---- 首次加载最后 200 行 ----
    try:
        with open(LOG_FILE, "r", encoding="gbk", errors="replace") as f:
            for line in deque(f, maxlen=200):
                yield f"data: {line.rstrip()}\n\n"
    except FileNotFoundError:
        yield "data: (log file not found, waiting...)\n\n"

    # ---- 跟随模式 ----
    file_size, _ = _get_file_meta(LOG_FILE)
    if file_size == 0:
        return

    f = open(LOG_FILE, "r", encoding="gbk", errors="replace")
    f.seek(file_size)

    try:
        while True:
            line = f.readline()
            if line:
                yield f"data: {line.rstrip()}\n\n"
            else:
                time.sleep(0.5)
                new_size, _ = _get_file_meta(LOG_FILE)

                # 只检测文件被截断/重建（size 变小）
                if new_size < file_size:
                    f.close()
                    yield "event: rotate\ndata: {}\n\n"
                    break

                # 正常追加：更新 size（mtime 不再跟踪）
                if new_size > file_size:
                    file_size = new_size

    except GeneratorExit:
        f.close()
    except Exception:
        f.close()


def get_log_streaming_response():
    """根据 IS_PROD 选择实现，返回 StreamingResponse"""
    generator = _generate_linux() if IS_PROD else _generate_windows()

    headers = {"Cache-Control": "no-cache"}
    if IS_PROD:
        headers["X-Accel-Buffering"] = "no"

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers=headers,
    )
