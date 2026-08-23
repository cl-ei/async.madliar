import asyncio
import logging
import time
import traceback
import sys
from src.config import LOG_FILE
from multiprocessing import Process, Queue
from queue import Empty
from .generator import generate, upload_to_oss


_global_communication = []  # task and control queue


_process = []


def worker_wrapper(index: int, q: Queue):
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s]: %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(sys.stdout),
        ],
    )

    logging.getLogger("asyncio").setLevel(logging.INFO)

    logging.info(f"\t worker {index} started.")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    while True:
        try:
            task = q.get_nowait()
        except Empty:
            time.sleep(1)
            continue

        try:
            act = task["act"]
            if act == "stop":
                q.put_nowait(task)
                logging.info(f"worker {index} received stop cmd, exit")
                return

            if act == "generate":
                coro = generate()
            elif act == "upload":
                coro = upload_to_oss()
            else:
                logging.info(f"error act: {act}, task args: {task}, skip...")
                continue

            logging.info(f"worker {index} received task: {act}, args: {task}")
            loop.run_until_complete(coro)
            pending_tasks = asyncio.all_tasks(loop)
            if pending_tasks:
                loop.run_until_complete(asyncio.gather(*pending_tasks, return_exceptions=True))
            logging.info(f"worker {index} generate static site complete, args: {task}")

        except Exception as e:
            logging.error(f"error happened in worker {index}: {e}\n{traceback.format_exc()}")


def start(count: int = 2):
    global _global_communication

    q = Queue()
    _global_communication.append(q)

    for i in range(count):
        p = Process(target=worker_wrapper, args=(i, q))
        p.start()
        _process.append(p)
    logging.info(f"worker started, total: {count}")


def stop():
    global _global_communication
    global _process

    q = _global_communication[0]
    q.put_nowait({"act": "stop"})
    p: Process
    for p in _process:
        p.join()
    _process = []
    logging.info("worker stopped.")


def create_task(act: str) -> bool:
    if act not in ("generate", "upload"):
        return False

    global _global_communication

    if not _global_communication:
        return False

    q = _global_communication[0]
    try:
        q.put_nowait({"act": act, "email": "xxx"})
        logging.info(f"current queue length: {q.qsize()}")
        return True

    except Exception as e:
        logging.error(f"error happened in create_task_publish_blog: {e}\n{traceback.format_exc()}")
    return False
