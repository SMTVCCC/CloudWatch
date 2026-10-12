<p align="center">
  <h1 align="center">☁️ CloudWatch</h1>
  <p align="center">轻量、高颜值的云服务器实时监控面板 · v2.0</p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-v0.100+-05998b.svg?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Tailwind_CSS-3.0+-38B2AC.svg?style=for-the-badge&logo=tailwind-css&logoColor=white" alt="Tailwind">
  <img src="https://img.shields.io/badge/ECharts-5.0+-AA344D.svg?style=for-the-badge&logo=apache-echarts&logoColor=white" alt="ECharts">
</p>

---

## 🌟 项目简介

**CloudWatch** 是一款专为云服务器打造的**极简、轻量、高颜值**实时监控工具。一个 Python 文件 + 一个静态页面，即可在浏览器里看清 CPU / 内存 / 磁盘 / 网络与高占用进程，并在 Windows 上一键释放冗余内存。

> "监控不仅是观察，更是掌控。"

---

## ✨ v2.0 更新点

本版本在原版基础上做了一轮完整的性能与工程化优化：

### 🚀 后端性能
- **事件循环不再被阻塞**：原 `time.sleep(1)` 与同步的进程扫描 / 内存清理全部改用 `asyncio.to_thread` 丢线程池，`await asyncio.sleep(1)` 等待清理生效。高并发轮询时后端响应不再卡顿。
- **静态信息真正缓存**：`cpu_freq` 等恒定值在启动时取一次，不再每个请求重算。
- **进程扫描仍保持 5 秒异步节流**，但扫描过程不阻塞 API。
- **磁盘路径跨平台自适应**：Windows 自动取系统盘（`C:\`），Linux / macOS 用 `/`，也可通过环境变量覆盖。
- **启动路径无关**：基于 `__file__` 定位 `static/`，从任何目录启动都能找到前端。

### 💾 设置持久化
- 自动清理开关与阈值会写入 `settings.json`，重启服务后自动恢复，不再每次手动开。

### 🔒 安全加固
- 新增**可选访问令牌**（环境变量 `CLOUDWATCH_TOKEN`）。开启后所有 `/api/*` 请求需要 `Authorization: Bearer <token>`，前端首次访问会弹窗输入并记住。
- 前端对进程名做 **HTML 转义**，杜绝恶意进程名导致的 XSS。
- `host` / `port` / 磁盘根路径均可通过环境变量配置。

### 🎨 前端体验
- 新增**下次自动清理倒计时**显示。
- Toast 通知改用原生 CSS transition，不再依赖 Tailwind 动画插件。
- 断连状态保持，恢复后自动继续轮询。

### 📦 工程化
- 新增 `requirements.txt`、`.gitignore`、`start.sh`（Linux/macOS）与升级后的 `start.bat`（Windows），首次运行自动建虚拟环境并装依赖。

---

## 🚀 快速开始

### Windows
```bat
start.bat
```

### Linux / macOS
```bash
chmod +x start.sh
./start.sh
```

### 手动方式
```bash
pip install -r requirements.txt
python main.py
```

启动后浏览器访问：
- 本机：`http://localhost:8000`
- 公网：`http://<服务器IP>:8000`

---

## ⚙️ 环境变量（可选）

| 变量 | 默认值 | 说明 |
|---|---|---|
| `CLOUDWATCH_HOST` | `0.0.0.0` | 监听地址 |
| `CLOUDWATCH_PORT` | `8000` | 监听端口 |
| `CLOUDWATCH_TOKEN` | 空（关闭） | 设置后启用 Bearer Token 鉴权 |
| `CLOUDWATCH_DISK` | 系统盘 / `/` | 监控的磁盘根路径 |

示例（Linux）：
```bash
CLOUDWATCH_PORT=9000 CLOUDWATCH_TOKEN=my-secret python main.py
```

---

## 🧠 核心功能

### 深度进程洞察
- 实时追踪内存占用最高的 **Top 5** 进程，超过 10% 内存占用红色高亮。
- 5 秒异步轮询，CPU 开销远低于秒级全量扫描。

### 智能内存优化（Windows）
- 调用 Windows Native API `EmptyWorkingSet`，一键释放各进程工作集。
- **自适应冷却**：基础 300 秒；若清理后内存仍高于阈值，按 `300s → 600s → 1200s` 倍增，上限 30 分钟；负载回落到阈值以下自动复位。
- Linux / macOS 上该功能自动跳过（接口仍可用，返回清理 0 个进程）。

### 负载视觉警示
- CPU 或内存 ≥ 70% 时数值变红并呼吸闪烁。

---

## 📂 目录结构

```text
CloudWatch/
├── main.py            # 核心引擎（API、采集、Windows Native、异步缓存、持久化）
├── requirements.txt   # Python 依赖
├── start.bat          # Windows 一键启动
├── start.sh           # Linux / macOS 一键启动
├── .gitignore
├── README.md
└── static/
    └── index.html     # 极客可视化仪表盘
```

---

## ⚠️ 安全提示

- 该面板默认绑定 `0.0.0.0` 且**内存清理接口可直接清空进程工作集**。如果要暴露到公网，**强烈建议**：
  1. 设置 `CLOUDWATCH_TOKEN`；
  2. 或放在 Nginx / Caddy 反代后并加 Basic Auth；
  3. 不要在不可信网络中裸奔。

---

<p align="center">
  <b>Designed with ❤️ by Your Pair Programmer</b><br>
  <i>Empowering your server monitoring experience.</i>
</p>
