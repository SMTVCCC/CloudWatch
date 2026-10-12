"""
CloudWatch - 轻量级云服务器实时监控面板
核心引擎: API、数据采集、Windows Native 内存清理、异步缓存与持久化设置
"""
import os
import time
import json
import asyncio
import logging
import ctypes
import platform
from datetime import datetime
from typing import Optional

import psutil
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# --------------------------------------------------------------------------- #
# 基础配置
# --------------------------------------------------------------------------- #
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")

HOST = os.environ.get("CLOUDWATCH_HOST", "0.0.0.0")
PORT = int(os.environ.get("CLOUDWATCH_PORT", "8000"))
AUTH_TOKEN = os.environ.get("CLOUDWATCH_TOKEN", "").strip()

# 磁盘根路径: Windows 默认取系统盘, 其他系统默认 /
if platform.system() == "Windows":
    DEFAULT_DISK_ROOT = os.environ.get("SystemDrive", "C:") + "\\"
else:
    DEFAULT_DISK_ROOT = "/"
DISK_ROOT = os.environ.get("CLOUDWATCH_DISK", DEFAULT_DISK_ROOT)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("cloudwatch")

app = FastAPI(title="CloudWatch", version="2.0.0")

# --------------------------------------------------------------------------- #
# 状态存储
# --------------------------------------------------------------------------- #
boot_time = datetime.fromtimestamp(psutil.boot_time())

# cpu_freq 在大多数系统上是恒定值, 启动时取一次即可
_cpu_freq = psutil.cpu_freq()
_cpu_freq_max = f"{round(_cpu_freq.max)} MHz" if _cpu_freq else "N/A"

state = {
    "last_net_io": psutil.net_io_counters(),
    "last_time": time.time(),
    "auto_clean_enabled": False,
    "clean_threshold": 65,          # 默认阈值 65%
    "last_clean_time": 0.0,
    "clean_cooldown": 300,          # 初始 CD 300 秒 (5 分钟)
    "consecutive_fails": 0,          # 连续清理后仍高负载的次数
    "max_cooldown": 1800,           # 最大 CD 30 分钟
    "last_proc_check_time": 0.0,
    "cached_top_procs": [],
    "static_info": {
        "os": f"{platform.system()} {platform.release()}",
        "cpu_count": psutil.cpu_count(logical=True),
        "cpu_freq": _cpu_freq_max,
        "total_memory": f"{round(psutil.virtual_memory().total / (1024 ** 3), 2)} GB",
        "boot_time": boot_time.strftime("%Y-%m-%d %H:%M:%S"),
    },
}


# --------------------------------------------------------------------------- #
# 设置持久化
# --------------------------------------------------------------------------- #
def load_settings() -> None:
    """启动时从 settings.json 恢复上次的自动清理配置。"""
    if not os.path.exists(SETTINGS_FILE):
        return
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        state["auto_clean_enabled"] = bool(data.get("auto_clean_enabled", False))
        state["clean_threshold"] = int(data.get("clean_threshold", 65))
        logger.info("已加载持久化设置: auto_clean=%s, threshold=%s%%",
                    state["auto_clean_enabled"], state["clean_threshold"])
    except Exception as e:  # 文件损坏时不阻塞启动
        logger.warning("settings.json 读取失败, 使用默认设置: %s", e)


def save_settings() -> None:
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "auto_clean_enabled": state["auto_clean_enabled"],
                    "clean_threshold": state["clean_threshold"],
                },
                f,
                indent=2,
            )
    except Exception as e:
        logger.warning("settings.json 写入失败: %s", e)


load_settings()


# --------------------------------------------------------------------------- #
# 数据采集
# --------------------------------------------------------------------------- #
class Settings(BaseModel):
    auto_clean_enabled: bool
    threshold: Optional[int] = 65


def _get_top_processes_sync() -> list:
    """同步版本: 取内存占用最高的前 5 个进程 (在线程池中执行)。"""
    processes = []
    for proc in psutil.process_iter(["pid", "name", "memory_percent"]):
        try:
            info = proc.info
            # memory_percent 可能在进程消失瞬间为 None
            if info.get("memory_percent") is not None:
                processes.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    processes.sort(key=lambda x: x["memory_percent"], reverse=True)
    return processes[:5]


def _clean_memory_sync() -> int:
    """调用 Windows Native API 清空进程工作集 (类似 Mem Reduct)。非 Windows 返回 0。"""
    if platform.system() != "Windows":
        return 0

    cleaned = 0
    # PROCESS_QUERY_INFORMATION (0x0400) | PROCESS_SET_QUOTA (0x0100)
    flags = 0x0400 | 0x0100
    for pid in psutil.pids():
        try:
            handle = ctypes.windll.kernel32.OpenProcess(flags, False, pid)
            if handle:
                ctypes.windll.psapi.EmptyWorkingSet(handle)
                ctypes.windll.kernel32.CloseHandle(handle)
                cleaned += 1
        except Exception:
            continue
    return cleaned


def _safe_disk_percent() -> float:
    try:
        return psutil.disk_usage(DISK_ROOT).percent
    except Exception as e:
        logger.debug("磁盘 %s 读取失败: %s", DISK_ROOT, e)
        return 0.0


# --------------------------------------------------------------------------- #
# 鉴权 (可选, 通过环境变量 CLOUDWATCH_TOKEN 开启)
# --------------------------------------------------------------------------- #
async def verify_token(request: Request):
    if not AUTH_TOKEN:
        return
    if request.headers.get("authorization", "") != f"Bearer {AUTH_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")


# --------------------------------------------------------------------------- #
# 中间件
# --------------------------------------------------------------------------- #
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------- #
# API 路由
# --------------------------------------------------------------------------- #
@app.get("/api/settings", dependencies=[Depends(verify_token)])
async def get_settings():
    return {
        "auto_clean_enabled": state["auto_clean_enabled"],
        "threshold": state["clean_threshold"],
    }


@app.post("/api/settings", dependencies=[Depends(verify_token)])
async def update_settings(settings: Settings):
    state["auto_clean_enabled"] = settings.auto_clean_enabled
    if settings.threshold is not None:
        state["clean_threshold"] = max(1, min(int(settings.threshold), 99))
    save_settings()
    return {
        "status": "ok",
        "auto_clean_enabled": state["auto_clean_enabled"],
        "threshold": state["clean_threshold"],
    }


@app.post("/api/clean", dependencies=[Depends(verify_token)])
async def manual_clean():
    count = await asyncio.to_thread(_clean_memory_sync)
    state["last_clean_time"] = time.time()
    return {"status": "ok", "cleaned_processes": count}


@app.get("/api/info", dependencies=[Depends(verify_token)])
async def get_info():
    info = state["static_info"]
    return {
        "os": info["os"],
        "cpu_count": info["cpu_count"],
        "cpu_freq": info["cpu_freq"],
        "total_memory": info["total_memory"],
        "boot_time": info["boot_time"],
    }


@app.get("/api/stats", dependencies=[Depends(verify_token)])
async def get_stats():
    cpu_usage = psutil.cpu_percent(interval=None)

    # ---- 网络速率 ----
    current_net_io = psutil.net_io_counters()
    current_time = time.time()
    time_delta = max(current_time - state["last_time"], 0.001)
    upload_speed = (current_net_io.bytes_sent - state["last_net_io"].bytes_sent) / time_delta
    download_speed = (current_net_io.bytes_recv - state["last_net_io"].bytes_recv) / time_delta
    state["last_net_io"] = current_net_io
    state["last_time"] = current_time

    # ---- 内存 & 自动清理 (自适应冷却) ----
    memory = psutil.virtual_memory()
    mem_percent = memory.percent
    was_cleaned = False
    next_clean_in = 0

    if state["auto_clean_enabled"]:
        # 300s -> 600s -> 1200s, 上限 1800s
        dynamic_cd = min(
            state["clean_cooldown"] * (2 ** state["consecutive_fails"]),
            state["max_cooldown"],
        )
        elapsed = current_time - state["last_clean_time"]
        next_clean_in = max(0, round(dynamic_cd - elapsed))

        if mem_percent >= state["clean_threshold"] and elapsed > dynamic_cd:
            logger.info("检测到内存 %.1f%%, 触发自动清理 (CD=%ds)...", mem_percent, dynamic_cd)
            await asyncio.to_thread(_clean_memory_sync)
            state["last_clean_time"] = time.time()
            was_cleaned = True

            # 不阻塞事件循环地等 1 秒让 EmptyWorkingSet 生效
            await asyncio.sleep(1)
            new_mem = psutil.virtual_memory().percent
            if new_mem >= state["clean_threshold"]:
                state["consecutive_fails"] += 1
                logger.info("清理效果不佳, 内存仍为 %.1f%%, 下次冷却时间倍增", new_mem)
            else:
                state["consecutive_fails"] = 0
                logger.info("清理成功, 内存已降至阈值以下")
            mem_percent = new_mem

    # ---- 磁盘 ----
    disk_percent = _safe_disk_percent()

    # ---- 进程排行 (5 秒缓存, 丢线程池避免阻塞) ----
    if (current_time - state["last_proc_check_time"]) > 5:
        state["cached_top_procs"] = await asyncio.to_thread(_get_top_processes_sync)
        state["last_proc_check_time"] = current_time

    # ---- Uptime ----
    uptime_delta = datetime.now() - boot_time
    d = uptime_delta.days
    h, rem = divmod(uptime_delta.seconds, 3600)
    m, s = divmod(rem, 60)
    uptime_str = f"{d}d {h}h {m}m {s}s"

    return {
        "cpu": cpu_usage,
        "memory": mem_percent,
        "disk": disk_percent,
        "upload_speed": round(upload_speed, 2),
        "download_speed": round(download_speed, 2),
        "uptime": uptime_str,
        "timestamp": current_time,
        "auto_clean": state["auto_clean_enabled"],
        "was_cleaned": was_cleaned,
        "next_clean_in": next_clean_in,
        "top_processes": state["cached_top_procs"],
    }


# --------------------------------------------------------------------------- #
# 静态文件
# --------------------------------------------------------------------------- #
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def read_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


if __name__ == "__main__":
    import uvicorn
    logger.info("CloudWatch v2.0 启动: http://%s:%d (鉴权: %s)",
                HOST, PORT, "开启" if AUTH_TOKEN else "关闭")
    uvicorn.run(app, host=HOST, port=PORT, access_log=False)
