#!/usr/bin/env python3
"""
MQTT File Sync Agent — 基于MAS持久化的文件同步Worker

用法:
    # 启动Worker（监听文件同步任务）
    python tools/file_sync_agent.py

    # Master发布同步任务
    master.post_task("sync", {"src": "D:/data/src/", "dst": "D:/data/bak/", "pattern": "*.csv"})

Worker能力: file_sync
"""

import sys, os, time, json, hashlib, threading, glob, shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from mqtt_bbs import WorkerAgentWithPersistence
from mqtt_bbs.bbs import TaskOutput, TaskStatus


class FileSyncWorker(WorkerAgentWithPersistence):
    """文件同步Worker — 接收sync任务后执行文件拷贝"""

    def __init__(self, agent_id="sync_worker"):
        super().__init__(agent_id,
                         capabilities=["file_sync", "sync"],
                         description="文件同步Worker，支持rsync/copy模式")
        self._running = False

    def start(self):
        self._running = True
        super().start()

    def stop(self):
        self._running = False

    def execute_task(self, task_id, task_type, task_input):
        """执行文件同步任务"""
        src = task_input.get("src", "")
        dst = task_input.get("dst", "")
        pattern = task_input.get("pattern", "*")
        mode = task_input.get("mode", "copy")  # copy / move / rsync
        recursive = task_input.get("recursive", True)

        if not src or not dst:
            return {"error": "src and dst required"}

        results = []
        total_size = 0
        errors = []

        # 查找文件
        if recursive:
            matched = glob.glob(os.path.join(src, "**", pattern), recursive=True)
        else:
            matched = glob.glob(os.path.join(src, pattern))

        os.makedirs(dst, exist_ok=True)

        for src_path in matched:
            if os.path.isfile(src_path):
                rel = os.path.relpath(src_path, src)
                dst_path = os.path.join(dst, rel)
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)

                try:
                    if mode == "move":
                        shutil.move(src_path, dst_path)
                    else:
                        shutil.copy2(src_path, dst_path)

                    fsize = os.path.getsize(dst_path)
                    total_size += fsize
                    results.append({
                        "file": rel,
                        "size": fsize,
                        "md5": self._md5_file(dst_path),
                        "status": "ok"
                    })
                except Exception as e:
                    errors.append({"file": rel, "error": str(e)})

        return {
            "src": src,
            "dst": dst,
            "total_files": len(results),
            "total_size": total_size,
            "files": results[:50],  # 限制返回条数
            "errors": errors[:10],
            "duration": time.time() - task_input.get("_start_time", time.time()),
        }

    def _md5_file(self, path, chunk=8192):
        h = hashlib.md5()
        with open(path, "rb") as f:
            while True:
                d = f.read(chunk)
                if not d:
                    break
                h.update(d)
        return h.hexdigest()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="MQTT File Sync Agent")
    parser.add_argument("--id", default="sync_worker", help="Worker agent ID")
    args = parser.parse_args()

    worker = FileSyncWorker(args.id)
    worker.start()
    print(f"✅ FileSyncWorker [{args.id}] 已启动, 等待 sync 任务...")
    try:
        while worker.is_connected:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n停止...")
        worker.stop()


if __name__ == "__main__":
    main()
