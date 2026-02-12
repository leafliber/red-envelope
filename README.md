# ⚠️ 重要声明（请务必阅读）

> 本项目**仅供学习与技术研究用途**，严禁用于任何违反平台规则、法律法规或他人权益的场景。  
> 请在下载/克隆后 **24 小时内删除**，请勿用于生产或实际牟利环境。  
> 因使用本项目造成的任何直接或间接后果（包括但不限于账号异常、封禁、数据损失、法律风险等），均由使用者本人承担，项目作者与贡献者**不承担任何责任**。

# QQ红包自动点击系统

基于 Python 开发的跨平台 QQ 红包自动点击工具，通过图像识别检测屏幕上的红包并自动点击，支持 Windows 和 macOS 双平台。

## 功能特性

- **窗口检测** — 自动扫描所有 QQ 程序窗口，支持后台检测
- **图像识别** — 使用 OpenCV 模板匹配检测红包图片
- **窗口激活** — 检测到红包后自动将窗口拉到最前
- **自动操作** — 点击红包、按 ESC 关闭窗口
- **仿人机制** — 鼠标移动轨迹模拟、点击位置随机偏移、操作间随机等待时间
- **全局快捷键** — Ctrl+Shift+P 暂停/继续监控，无需切换窗口
- **跨平台** — Windows (pywin32) 和 macOS (pyobjc) 双平台兼容
- **完善日志** — 同时输出到命令行和日志文件，支持日志轮转

## 目录结构

```
red-envelope-qq/
├── img/
│   └── redbag.png              # 红包模板图片
├── config/
│   └── config.yaml             # 配置文件
├── src/
│   ├── __init__.py             # 包初始化
│   ├── __main__.py             # 命令行入口
│   ├── main.py                 # 主控制器
│   ├── window_manager.py       # 窗口管理模块
│   ├── image_detector.py       # 图像识别模块
│   ├── humanizer.py            # 人类化操作模块
│   └── platform/               # 平台实现
│       ├── __init__.py         # 平台自动检测
│       ├── base.py             # 平台抽象基类
│       ├── windows.py          # Windows 平台实现
│       └── macos.py            # macOS 平台实现
├── tests/                      # 单元测试
├── requirements.txt            # Python 依赖
├── .gitignore                  # Git 忽略规则
└── README.md                   # 项目说明
```

## 系统要求

- Python 3.8+
- Windows 10+ 或 macOS 10.14+

## 安装

### 1. 克隆项目

```bash
git clone <repository-url>
cd red-envelope-qq
```

### 2. 创建虚拟环境

```bash
python -m venv .venv
source .venv/bin/activate    # macOS/Linux
# .venv\Scripts\activate     # Windows
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

#### 平台特定依赖

**Windows:**
```bash
pip install pywin32>=300
```

**macOS:**
```bash
pip install pyobjc-framework-Quartz>=8.0 pyobjc-framework-Cocoa>=8.0
```

> macOS 还需要在「系统偏好设置 → 安全性与隐私 → 辅助功能」中授权终端/IDE 的屏幕录制和辅助功能权限。

### 4. 准备模板图片

将 QQ 红包的截图放到 `img/redbag.png`，建议截取红包图标的特征区域。

## 使用方法

### 基础运行

```bash
python -m src
```

### 指定配置文件

```bash
python -m src -c /path/to/config.yaml
```

### 开启详细日志

```bash
python -m src -v
```

### 暂停/继续监控

运行期间按 `Ctrl+Shift+P` 即可切换暂停/继续（全局快捷键，无需切换窗口）。

### 停止运行

按 `Ctrl+C` 安全退出。

## 配置说明

编辑 `config/config.yaml` 调整参数：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `window.title_keywords` | 窗口标题匹配关键词 | `["QQ"]` |
| `window.scan_interval_min/max` | 扫描间隔范围（秒） | `1.0 ~ 3.0` |
| `detection.match_threshold` | 图像匹配阈值 | `0.8` |
| `detection.grayscale` | 灰度匹配（提升速度） | `true` |
| `humanizer.click_offset_x/y` | 点击随机偏移（像素） | `5` |
| `humanizer.move_duration_min/max` | 鼠标移动时长（秒） | `0.2 ~ 0.5` |
| `hotkey.pause_resume` | 暂停/继续快捷键 | `<ctrl>+<shift>+p` |
| `logging.level` | 日志级别 | `INFO` |

## 工作原理

```
扫描QQ窗口列表 → 后台截图 → 图像匹配红包
       ↓ (检测到红包)
窗口置顶激活 → 人类化鼠标移动 → 随机偏移点击 → 随机延时 → 按ESC关闭
```

### 技术细节

- **后台截图**：Windows 使用 `PrintWindow()` API，macOS 使用 `CGWindowListCreateImage()`，均可在窗口被遮挡时截取内容
- **模板匹配**：使用 OpenCV `TM_CCOEFF_NORMED` 算法，阈值可配置
- **人类化操作**：PyAutoGUI 的 `tween` 参数实现贝塞尔曲线鼠标轨迹，所有操作带随机偏移和延时

## 测试

```bash
pytest tests/ -v
```

## 注意事项

- 首次运行 macOS 版本时，系统会弹出权限请求对话框，请授予辅助功能和屏幕录制权限
- 运行期间请勿将鼠标移动到屏幕左上角（PyAutoGUI FailSafe 机制）
- 建议在非生产环境测试后再正式使用
- 模板图片的质量直接影响识别准确率，建议使用清晰的红包特征截图

## 许可证

MIT License
