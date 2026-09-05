import os
import sys
import json
import subprocess
from src.config import DEBUG
from pathlib import Path


def covert_to_html(content, toc: bool = True):
    """起子进程 → 写 stdin → 读 stdout。一次调用处理整批文章。"""
    kwargs = {
        "cwd": os.getcwd(),
        "input": json.dumps({
            "content": content,
            "options": {
                "toc": toc,
            },
        }).encode("utf-8"),
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "timeout": 10,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    node_exe = r"C:\_PRIVATE_ROOT\programs\node\node.exe" if DEBUG else "node"

    js_entry = (Path(__file__).resolve().parent / "render.js").as_posix()
    proc = subprocess.run([node_exe, js_entry], **kwargs)

    out = proc.stdout.decode("utf-8", errors="replace")
    err = proc.stderr.decode("utf-8", errors="replace")
    if proc.returncode != 0 and not out.strip():
        raise ValueError(
            f"node 退出码 {proc.returncode}\nstderr: {err[:2000]}"
        )
    try:
        data = json.loads(out)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"node 输出不是合法 JSON（多半被管道截断）: {e}\n"
            f"stdout 前 300 字符: {out[:300]}\nstderr: {err[:1000]}"
        ) from e
    if not data.get("ok"):
        raise ValueError(f"render.js 返回失败: {data.get('error')}\nstderr: {err[:1000]}")
    return data


def test():
    with open("test.md", "r", encoding="utf-8") as f:
        content = f.read()

    result = covert_to_html(content)
    print(result)


if __name__ == "__main__":
    test()
