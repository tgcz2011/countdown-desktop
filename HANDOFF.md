# HANDOFF.md — Countdown Desktop 项目交接文档

> 最后更新: 2026-08-10

## 项目概述

Windows 动态壁纸软件，将网页设为壁纸/屏保。Go 语言开发，WebView2 渲染，NSIS 安装。

## 环境与工具链

| 工具 | 版本/路径 | 用途 |
|------|-----------|------|
| Go | 1.26.5, `C:\Program Files\Go\bin` | 编译 |
| Git | 2.55.0, `C:\Program Files\Git\bin` | 版本管理 |
| NSIS | 3.12, `C:\Program Files (x86)\NSIS` | 安装包 |
| Inno Setup | 7, `C:\Program Files\Inno Setup 7` | 备选安装包 |
| GitHub CLI | `C:\Program Files\GitHub CLI` | Release 发布 |
| Go Module Proxy | `https://goproxy.cn,direct` | 国内代理 |

## 项目结构

```
D:\countdown-desktop\
├── main.go                    # 入口：单实例检查、消息循环、动作分发
├── version/version.go         # 版本号 + 构建时间（ldflags 注入）
├── go.mod / go.sum
├── internal/
│   ├── webview/webview.go     # WebView2 COM 封装（核心）
│   ├── wallpaper/wallpaper.go # WorkerW 壁纸引擎
│   ├── screensaver/screensaver.go # 全屏屏保引擎
│   ├── tray/tray.go           # 系统托盘（Shell_NotifyIcon）
│   ├── settings/settings.go   # Win32 原生设置窗口
│   ├── config/config.go       # JSON 配置读写
│   └── win32/win32.go         # Win32 API 类型/常量/函数
├── installer/setup.nsi        # NSIS 安装脚本
├── assets/icon.ico            # 应用图标（32x32 BGRA）
├── README.md
├── HANDOFF.md
└── .github/workflows/release.yml
```

## 核心架构

### 壁纸引擎 (wallpaper)

1. 找到桌面 `Progman` 窗口
2. 发送 `0x052C` 消息触发 WorkerW 创建
3. 枚举 WorkerW 窗口，找到包含 `SHELLDLL_DefView` 子窗口的那个
4. 创建 WebView2 子窗口，用 `SetParent` 嵌入到 WorkerW
5. 设置 `WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE` 扩展样式
6. 用 `SetWindowPos(HWND_BOTTOM)` 置底

### 屏保引擎 (screensaver)

1. 创建全屏 WebView2 窗口
2. `SetWindowPos(HWND_TOPMOST)` 置顶
3. 隐藏鼠标光标
4. 后台 goroutine 监听 `GetLastInputInfo` + `GetAsyncKeyState`
5. 检测到用户输入立即关闭

### WebView2 COM 封装 (webview)

- 纯 Go + `syscall` 实现，无需 CGo
- 加载 `WebView2Loader.dll` 动态调用
- COM vtable 分发通过 `syscall.NewCallback` 实现
- 关键接口：`ICoreWebView2Environment` → `ICoreWebView2Controller` → `ICoreWebView2`

### 系统托盘 (tray)

- `Shell_NotifyIcon` + 隐藏消息窗口
- 右键弹出菜单（`CreatePopupMenu` + `TrackPopupMenu`）
- 左键打开设置

### 设置窗口 (settings)

- 纯 Win32 API，无第三方 GUI 库
- 控件：STATIC 标签、EDIT 文本框、BUTTON 按钮、CHECKBOX
- 配置即时生效，Save 持久化到 `config.json`

## 构建命令

```powershell
# 设置环境
$env:PATH = "C:\Program Files\Go\bin;C:\Program Files\Git\bin;$env:PATH"
$env:GOPROXY = "https://goproxy.cn,direct"

# 构建
go build -ldflags "-H windowsgui -X github.com/tgcz2011/countdown-desktop/version.Version=1.0.0.0" -o countdown-desktop.exe .

# 安装包
makensis installer\setup.nsi
```

## 曾经犯过的错误

### 2026-08-10
1. **import 路径问题**: Go module 路径是 `github.com/tgcz2011/countdown-desktop`，内部 import 必须用完整路径，不能用短名 `countdown-desktop/...`
2. **golang.org/x/sys/windows 缺少 API**: `WNDCLASSEXW`、`RegisterClassEx`、`CS_HREDRAW` 等不在该包中，需自行在 win32 包定义
3. **HWND_TOPMOST 类型**: 作为 `const` 定义时是 untyped constant，不能直接传给 `HWND` 类型参数，需用 `var` 定义类型化变量
4. **GetAsyncKeyState 返回值**: `int16` 类型的 `0x8000` 溢出，需先转 `uint16` 再比较
5. **PowerShell heredoc 中的换行符**: `@'...'@` 内容中的 `\`n` 会被当作字面文本，不要在 heredoc 里使用 `-replace`

### 注意事项
- `CreateCoreWebView2EnvironmentWithOptions` 的 browserExecutableFolder 传 NULL（空字符串）使用系统安装的 Runtime
- userDataFolder 不能共享，每个 WebView2 实例需独立目录或传空
- WebView2 初始化是异步的，必须等 `CompletedHandler` 回调才能使用 controller
- 设置窗口必须在创建它的线程上运行消息循环

## 发布流程

1. 更新 `version/version.go` 中的版本号
2. 推送到 GitHub
3. GitHub Actions 自动构建 + Release
4. 构建产物：`countdown-desktop.exe` + `CountdownDesktop_Setup_*.exe`

## 需求清单

- [x] 网页壁纸（WorkerW 嵌入 WebView2）
- [x] 网页屏保（全屏置顶窗口）
- [x] 壁纸/屏保独立 URL 配置
- [x] 屏保超时可调（默认 600s）
- [x] 自定义全屏窗口屏保（非系统屏保）
- [x] 系统托盘图标 + 右键菜单
- [x] 设置界面（壁纸 URL、屏保 URL、超时、启用开关）
- [x] NSIS 安装包
- [x] 单实例锁（CreateMutex）
- [x] 开机自启（注册表 Run 键）
- [ ] 应用图标嵌入 EXE（需 windres 编译 .rc → .syso）
- [ ] 托盘图标从 EXE 资源加载
- [ ] 多显示器支持
- [ ] 壁纸全屏应用时暂停
- [ ] Inno Setup 安装包备选
- [ ] 自动更新
