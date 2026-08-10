# Countdown Desktop

Windows 动态壁纸与屏保软件 —— 将任意网页设为桌面壁纸和屏保。

## 功能

| 功能 | 说明 |
|------|------|
| 🌐 网页壁纸 | 将任意 URL 设为 Windows 桌面壁纸，显示在桌面图标下方 |
| 🖥️ 网页屏保 | 自定义全屏网页屏保，支持独立 URL 和超时设置 |
| ⚙️ 独立配置 | 壁纸和屏保分别设置，互不干扰 |
| 📋 系统托盘 | 托盘图标右键菜单快速切换壁纸/屏保、打开设置 |
| 🔧 纯 Win32 设置界面 | 轻量原生设置窗口，无需额外运行时 |
| 🚀 WebView2 渲染 | 基于 Microsoft Edge WebView2 Runtime，Win10/11 内置 |

## 系统要求

- Windows 10 1809+ 或 Windows 11
- Microsoft Edge WebView2 Runtime（系统已预装）
- 无需额外依赖

## 下载安装

从 [Releases](https://github.com/tgcz2011/countdown-desktop/releases) 下载最新安装包：

- `CountdownDesktop_Setup_x.x.x.x.exe` — NSIS 安装包，安装后自动开机启动

## 开发

### 构建

```bash
# 安装 Go 1.21+
go build -ldflags "-H windowsgui -X countdown-desktop/version.Version=1.0.0.0" -o countdown-desktop.exe .
```

### 构建安装包

```bash
# 需要安装 NSIS 3.x
makensis installer\setup.nsi
```

### 版本号规则

格式：`a.b.c.d`
- **a**: 重大架构变更
- **b**: 重要功能添加
- **c**: 小功能添加
- **d**: Bug 修复和小改动

每个版本号去掉 "." 后必须比上一版本大。

### 项目结构

```
countdown-desktop/
├── main.go                    # 入口
├── version/version.go         # 版本信息
├── internal/
│   ├── webview/webview.go     # WebView2 COM 封装
│   ├── wallpaper/wallpaper.go # 壁纸引擎（WorkerW 嵌入）
│   ├── screensaver/screensaver.go # 屏保引擎
│   ├── tray/tray.go           # 系统托盘
│   ├── settings/settings.go   # 设置窗口（Win32 原生控件）
│   ├── config/config.go       # JSON 配置管理
│   └── win32/win32.go         # Win32 API 封装
├── installer/setup.nsi        # NSIS 安装脚本
├── assets/icon.ico            # 应用图标
├── README.md
└── HANDOFF.md
```

## 技术方案

- **语言**: Go（单二进制，零运行时依赖）
- **渲染**: Microsoft Edge WebView2（系统内置，无需打包浏览器）
- **壁纸嵌入**: WorkerW 窗口技术（参考 [Lively Wallpaper](https://github.com/rocksdanister/lively)）
- **屏保**: 全屏置顶窗口 + 输入监听（非系统屏保机制）
- **安装包**: NSIS，兼容 Win10/11
- **CI/CD**: GitHub Actions 自动构建 + Release

## License

MIT
