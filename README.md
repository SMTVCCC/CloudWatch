# <p align="center">☁️ CloudMonitor Pro</p>
<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-v0.100+-05998b.svg?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Tailwind_CSS-3.0+-38B2AC.svg?style=for-the-badge&logo=tailwind-css&logoColor=white" alt="Tailwind">
  <img src="https://img.shields.io/badge/ECharts-5.0+-AA344D.svg?style=for-the-badge&logo=apache-echarts&logoColor=white" alt="ECharts">
</p>

---

## 🌟 项目简介

**CloudMonitor Pro** 是一款专为云服务器打造的**极简、轻量、高颜值**实时监控工具。它不仅能提供深度性能透视，还集成了工业级内存优化与进程追踪功能，让你的服务器在监控中保持巅峰状态。

> [!TIP]
> **“监控不仅是观察，更是掌控。”** —— 全新进化版，性能开销更低，洞察力更强。

---

## ✨ 核心亮点

### � 深度进程洞察 (NEW!)
-   **高占用排行**：实时追踪内存占用最高的前 5 个进程，精准定位资源黑洞。
-   **极致节能算法**：进程扫描采用 **5 秒级异步轮询**，相比常规秒级采集，CPU 损耗降低 80% 以上。
-   **智能高亮**：对超过 10% 内存占用的进程进行红色标记，一眼揪出“罪魁祸首”。

### 🚀 智能内存优化
-   **Mem Reduct 核心集成**：调用 Windows Native API (`EmptyWorkingSet`)，一键释放各进程冗余内存。
-   **自适应冷却保护 (NEW!)**：
    -   **初始 CD 延长**：基础冷却时间为 300 秒（5 分钟），避免频繁操作。
    -   **高压退避算法**：若清理后内存仍高于 65%，系统将判定为“顽固负载”，自动倍增下一次清理的等待时间（300s -> 600s -> 1200s），最高延长至 30 分钟。
    -   **智能复位**：一旦负载降至阈值以下，冷却时间自动重置为基础值。
-   **手动加速**：控制面板一键触发，即刻感受内存占用的“断崖式”下降。

### 🚨 负载视觉警示
-   **高压红色预警**：当 CPU 或内存占用 ≥ 70% 时，数值自动切换为**鲜艳红色**并伴随**呼吸灯闪烁**。
-   **静默后端**：智能屏蔽常规 GET 请求日志，仅在发生错误时报错，保持后端输出清爽。

### 🎨 极客风 UI 设计
-   **暗黑沉浸式**：基于 Zinc 灰阶与 Emerald 翠绿配色，完美契合开发者审美。
-   **静态数据缓存**：系统信息（OS、CPU 核心等）采用缓存机制，消除重复计算开销。
-   **响应式适配**：无论是工作站还是手机端，都能获得极致的交互体验。

---

## 🚀 快速开始

### 1. 环境准备
确保你的服务器已安装 Python 3.8+，然后安装核心依赖：
```bash
pip install fastapi uvicorn psutil pydantic -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 2. 一键启动
在项目根目录下双击：
> `⚡ start.bat`

### 3. 访问面板
在浏览器输入：
- **本地访问**：`http://localhost:8000`
- **公网访问**：`http://你的服务器IP:8000`

---

## 📂 目录说明

```text
CloudMonitor/
├── 📄 main.py          # 核心引擎 (API、数据采集、Windows Native 接口、异步缓存)
├── 📄 start.bat        # Windows 快速启动入口
├── 📄 README.md        # 项目说明手册
└── 📁 static/          # 前端资源目录
    └── 📄 index.html   # 极客可视化仪表盘 (含自动清理逻辑 & 进程排行)
```

---

## 🤝 参与贡献

如果你有更好的想法或发现了 BUG，欢迎参与共建！
1. 提交 **Issues** 描述你的建议。
2. 提交 **Pull Requests** 贡献代码。
3. 或是点个 **Star** 支持这个项目！

---
<p align="center">
  <b>Designed with ❤️ by Your Pair Programmer</b><br>
  <i>Empowering your server monitoring experience.</i>
</p>
