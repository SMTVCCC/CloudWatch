import time
import psutil
import platform
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import ctypes
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

# 获取系统启动时间
boot_time = datetime.fromtimestamp(psutil.boot_time())

# 状态存储
state = {
    "last_net_io": psutil.net_io_counters(),
    "last_time": time.time(),
    "auto_clean_enabled": False,
    "clean_threshold": 65,         # 默认阈值 65%
    "last_clean_time": 0,
    "clean_cooldown": 300,         # 初始 CD 延长至 300 秒 (5 分钟)
    "consecutive_fails": 0,        # 连续清理后仍处于高负载的次数
    "max_cooldown": 1800,          # 最大 CD 限制为 1800 秒 (30 分钟)
    "last_proc_check_time": 0,     # 上次检查进程的时间
    "cached_top_procs": [],        # 缓存的进程列表
    "static_info": {  # 缓存静态信息，减少重复计算
        "os": f"{platform.system()} {platform.release()}",
        "cpu_count": psutil.cpu_count(logical=True),
        "total_memory": f"{round(psutil.virtual_memory().total / (1024**3), 2)} GB",
        "boot_time": boot_time.strftime("%Y-%m-%d %H:%M:%S")
    }
}

class Settings(BaseModel):
    auto_clean_enabled: bool
    threshold: Optional[int] = 65

def get_top_processes():
    """获取内存占用最高的前 5 个进程"""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
        try:
            processes.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    # 按内存占用排序
    top_5 = sorted(processes, key=lambda x: x['memory_percent'], reverse=True)[:5]
    return top_5

def clean_memory():
    """调用 Windows Native API 清理内存 (类似 Mem Reduct)"""
    if platform.system() != "Windows":
        return 0
    
    cleaned_count = 0
    # PROCESS_QUERY_INFORMATION (0x0400) | PROCESS_SET_QUOTA (0x0100)
    flags = 0x0400 | 0x0100
    
    for pid in psutil.pids():
        try:
            # 这里的权限足以执行 EmptyWorkingSet
            handle = ctypes.windll.kernel32.OpenProcess(flags, False, pid)
            if handle:
                ctypes.windll.psapi.EmptyWorkingSet(handle)
                ctypes.windll.kernel32.CloseHandle(handle)
                cleaned_count += 1
        except Exception:
            continue
    return cleaned_count

# 允许跨域请求，方便前端调试
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/settings")
async def get_settings():
    return {
        "auto_clean_enabled": state["auto_clean_enabled"],
        "threshold": state["clean_threshold"]
    }

@app.post("/api/settings")
async def update_settings(settings: Settings):
    state["auto_clean_enabled"] = settings.auto_clean_enabled
    if settings.threshold is not None:
        state["clean_threshold"] = settings.threshold
    return {
        "status": "ok",
        "auto_clean_enabled": state["auto_clean_enabled"],
        "threshold": state["clean_threshold"]
    }

@app.post("/api/clean")
async def manual_clean():
    count = clean_memory()
    state["last_clean_time"] = time.time()
    return {"status": "ok", "cleaned_processes": count}

@app.get("/api/info")
async def get_info():
    """获取缓存的静态系统信息，减少性能损耗"""
    info = state["static_info"]
    return {
        "os": info["os"],
        "cpu_count": info["cpu_count"],
        "cpu_freq": f"{psutil.cpu_freq().max if psutil.cpu_freq() else 'N/A'} MHz",
        "total_memory": info["total_memory"],
        "boot_time": info["boot_time"]
    }

@app.get("/api/stats")
async def get_stats():
    global state
    
    # 获取 CPU 使用率 (非阻塞模式)
    cpu_usage = psutil.cpu_percent(interval=None)
    
    # 获取当前网络流量
    current_net_io = psutil.net_io_counters()
    current_time = time.time()
    
    # 计算时间差
    time_delta = current_time - state["last_time"]
    if time_delta <= 0:
        time_delta = 0.1 # 避免除以零
    
    # 计算上传和下载速度 (字节/秒)
    bytes_sent = current_net_io.bytes_sent - state["last_net_io"].bytes_sent
    bytes_recv = current_net_io.bytes_recv - state["last_net_io"].bytes_recv
    
    upload_speed = bytes_sent / time_delta
    download_speed = bytes_recv / time_delta
    
    # 更新状态
    state["last_net_io"] = current_net_io
    state["last_time"] = current_time
    
    # 获取内存使用情况
    memory = psutil.virtual_memory()
    mem_percent = memory.percent

    # 自动清理逻辑 (带有自适应冷却保护)
    was_cleaned = False
    if state["auto_clean_enabled"]:
        mem_percent = psutil.virtual_memory().percent
        current_time = time.time()
        
        # 计算当前实际需要的 CD (根据失败次数倍增)
        # 1次失败: 300s, 2次: 600s, 3次: 1200s, 最高 1800s
        dynamic_cd = min(state["clean_cooldown"] * (2 ** state["consecutive_fails"]), state["max_cooldown"])
        
        if mem_percent >= state["clean_threshold"] and (current_time - state["last_clean_time"]) > dynamic_cd:
            print(f"检测到内存占用 {mem_percent}%, 触发自动清理 (当前 CD: {dynamic_cd}s)...")
            clean_memory()
            state["last_clean_time"] = current_time
            was_cleaned = True
            
            # 预判：如果清理后内存依然很高，则增加失败计数，拉长下次清理间隔
            time.sleep(1) # 稍等片刻让 API 生效
            new_mem_percent = psutil.virtual_memory().percent
            if new_mem_percent >= state["clean_threshold"]:
                state["consecutive_fails"] += 1
                print(f"清理效果不佳，内存仍为 {new_mem_percent}%, 延长冷却时间至下次倍增")
            else:
                state["consecutive_fails"] = 0 # 清理成功，重置计数
                print("清理成功，内存已降至阈值以下")
            
            # 更新 mem_percent 以反映变化
            mem_percent = new_mem_percent
    
    # 获取磁盘使用情况
    disk = psutil.disk_usage('/')
    
    # 降低进程检查频率 (每 5 秒检查一次)
    if (current_time - state["last_proc_check_time"]) > 5:
        state["cached_top_procs"] = get_top_processes()
        state["last_proc_check_time"] = current_time
    
    top_procs = state["cached_top_procs"]
    
    # 计算运行时间 (Uptime)
    uptime_delta = datetime.now() - boot_time
    days = uptime_delta.days
    hours, remainder = divmod(uptime_delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"
    
    return {
        "cpu": cpu_usage,
        "memory": mem_percent,
        "disk": disk.percent,
        "upload_speed": round(upload_speed, 2), # bytes/s
        "download_speed": round(download_speed, 2), # bytes/s
        "uptime": uptime_str,
        "timestamp": current_time,
        "auto_clean": state["auto_clean_enabled"],
        "was_cleaned": was_cleaned,
        "top_processes": top_procs
    }

# 静态文件服务 (将前端页面放在 static 目录下)
if not os.path.exists("static"):
    os.makedirs("static")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse("static/index.html")

if __name__ == "__main__":
    import uvicorn
    # access_log=False 禁用常规访问日志（如 GET / 200 OK），仅保留错误日志
    uvicorn.run(app, host="0.0.0.0", port=8000, access_log=False)
