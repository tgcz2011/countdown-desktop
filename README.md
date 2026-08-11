# Countdown Desktop

Windows 动态壁纸与屏保软件 —— 将任意网页设为桌面壁纸和屏保（默认 https://zztool.free.nf/countdown 高考倒计时页面）。

## 功能

| 功能 | 说明 |
|------|------|
| 网页壁纸 | 将任意 URL 设为桌面壁纸，嵌入桌面图标层之下（WorkerW/Progman 技术） |
| 网页屏保 | 自定义全屏置顶窗口屏保（非系统屏保机制），默认超时 600s 可调 |
| 独立配置 | 壁纸 URL 与屏保 URL 分开设置，互不干扰 |
| 系统托盘 | 托盘图标 + 右键菜单（切换壁纸/屏保、打开设置、退出） |
| 原生设置窗口 | 纯 Win32 控件（无第三方 GUI 库） |
| WebView2 渲染 | 基于系统内置 Microsoft Edge WebView2 Runtime，Win10/11 自带 |

## 系统要求

- Windows 10 1809+ 或 Windows 11（客户端版本，需要 DWM 桌面合成）
- Microsoft Edge WebView2 Runtime（Win10/11 系统自带，应用目录也内置了 WebView2Loader.dll）
- 无需其他运行时

> 注意：Windows Server（无 DWM 合成）上壁纸嵌入渲染不可用，屏保功能不受影响。

## 下载安装

从 [Releases](https://github.com/tgcz2011/countdown-desktop/releases) 下载：
`CountdownDesktop_Setup_1.0.0.5.exe`（NSIS 安装包，安装后自动开机启动）。

## 开发

### 构建

```bash
go build -ldflags "-H windowsgui -X github.com/tgcz2011/countdown-desktop/version.Version=1.0.0.5" -o countdown-desktop.exe .
```

### 测试模式（无需托盘交互）

```bash
countdown-desktop.exe --test-wallpaper    # 壁纸 25s 自动退出
countdown-desktop.exe --test-screensaver  # 屏保 15s 自动退出
countdown-desktop.exe --test-settings     # 设置窗口 15s 自动关闭
countdown-desktop.exe --test-standalone   # 独立 WebView2 窗口（调试渲染）
```

### 构建安装包

```bash
makensis installer\setup.nsi
```

### 版本号规则

格式 `a.b.c.d`：d=修复，c=小功能，b=重要功能，a=架构变更。去掉 "." 后必须递增。

### 项目结构

```
countdown-desktop/
├── main.go                        # 入口：DPI 初始化、单实例、测试模式、动作分发
├── version/version.go             # 版本号（ldflags 注入）
├── internal/
│   ├── webview/webview.go         # WebView2 COM 封装（纯 syscall，零 CGo）
│   ├── wallpaper/wallpaper.go     # 壁纸引擎（WorkerW/Progman 嵌入 + Z-order）
│   ├── screensaver/screensaver.go # 全屏屏保 + 空闲检测
│   ├── tray/tray.go               # 系统托盘（Shell_NotifyIcon）
│   ├── settings/settings.go       # Win32 原生设置窗口
│   ├── config/config.go           # JSON 配置
│   ├── logutil/log.go             # 文件日志（exe 同目录 log.txt）
│   └── win32/win32.go             # Win32 API 类型/常量/函数封装
├── installer/setup.nsi            # NSIS 安装脚本
├── WebView2Loader.dll             # WebView2 加载器（随包分发）
├── assets/icon.ico
├── README.md / HANDOFF.md
└── .github/workflows/release.yml  # tag 推送自动构建 + Release
```

## 技术要点

- 纯 Go + syscall，无 CGo，单二进制
- WebView2 COM vtable 手写封装（见 HANDOFF.md 的踩坑记录）
- 壁纸嵌入：检测 Win11 raised desktop（WS_EX_NOREDIRECTIONBITMAP）→ 0x052C wParam=0xD/lParam=0x1 创建 WorkerW → WS_CHILD + SetParent → Z-order 置于图标层之下
- 所有 Win32/WebView2 操作必须运行在窗口创建线程（opCh 调度）

## License

GPL-3.0（借鉴 Lively Wallpaper 架构，与上游许可证保持一致）
