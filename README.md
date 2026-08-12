# Countdown Desktop

Windows 动态壁纸与屏保软件：将任意网页设为桌面壁纸与屏保（默认 https://zztool.free.nf/countdown 高考倒计时页面）。

## 功能

| 功能 | 说明 |
|------|------|
| 网页壁纸 | 任意 URL 嵌入桌面（CEF 渲染 + WorkerW 嵌入，Lively 同构方案） |
| 网页屏保 | CEF 全屏置顶窗口 + 输入监听退出（非系统屏保），默认超时 600s 可调 |
| 独立配置 | 壁纸 URL / 屏保 URL 分开设置，互不干扰 |
| 系统托盘 | Qt 原生托盘（QSystemTrayIcon），右键菜单：切换壁纸/屏保、设置、退出 |
| 设置窗口 | Qt 对话框：URL、超时、启用开关、测试按钮 |
| 自带浏览器 | 打包 CEF（Chromium 内核），**不依赖系统 WebView/Edge** |

## 技术栈

- **Python 3.13** + PySide6（QtWidgets 托盘/设置，不含 QtWebEngine）
- **CEF 3.2704**（Chromium）独立渲染进程 `cef_helper.exe`（C++，MinGW 编译，随包分发）
- 壁纸嵌入：CEF 窗口最小化创建 → WS_CHILD → SetParent 到壁纸 WorkerW → 恢复显示（与 Lively 完全同构）
- 打包：PyInstaller onedir + NSIS 安装包
- CI：GitHub Actions（下载 CEF + 编译 helper + PyInstaller + NSIS）

## 系统要求

- Windows 10/11（客户端版本）
- 无其他运行时依赖（Chromium 已打包，约 225MB 安装）

## 下载

Releases: <https://github.com/tgcz2011/countdown-desktop/releases>

`CountdownDesktop_Setup_x.x.x.x.exe`（NSIS 安装包，自动开机启动）。

## 开发

```bash
# 依赖（仅主程序；helper 已预编译）
pip install PySide6

# 运行（开发模式）
python run.py                          # 托盘模式
python run.py --test-screensaver       # 屏保 15s
python run.py --test-wallpaper         # 壁纸 25s
python run.py --test-settings          # 设置窗口
python run.py --test-standalone        # 独立 CEF 窗口

# 重新编译 CEF helper（需要下载 CEF 104MB + MinGW 61MB）
python third_party/build_cef_helper.py

# 打包
python -m PyInstaller --noconfirm --onedir --windowed --name CountdownDesktop run.py
makensis installer\setup.nsi
```

## 项目结构

```
countdown-desktop/
├── run.py                     # 入口
├── app/
│   ├── main.py                # 应用主逻辑（托盘/调度/测试模式）
│   ├── cef.py                 # CEF helper 进程管理（嵌入/全屏）
│   ├── desktop.py             # Win32 桌面嵌入（WorkerW/Progman）
│   ├── screensaver.py         # 屏保引擎（输入监听）
│   ├── wallpaper.py           # 壁纸引擎
│   ├── settings.py            # 设置对话框
│   ├── tray.py                # 系统托盘
│   └── config.py              # JSON 配置
├── third_party/
│   ├── cef_helper/            # CEF 渲染进程（C++ 源码 + 编译产物）
│   └── build_cef_helper.py    # helper 构建脚本（本地 + CI）
├── installer/setup.nsi        # NSIS 安装脚本
└── .github/workflows/release.yml
```

## License

GPL-3.0（架构借鉴 Lively Wallpaper）
