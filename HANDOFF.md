# HANDOFF.md — Countdown Desktop 项目交接文档

> 最后更新: 2026-08-12

## 项目概述

Windows 动态壁纸/屏保软件：将任意网页设为壁纸（WorkerW/Progman 嵌入）和全屏屏保。
Go 语言，WebView2 渲染，NSIS 安装包，GitHub Actions 发布。

## 环境与工具链

| 工具 | 版本/路径 | 用途 |
|------|-----------|------|
| Go | 1.26.5, `C:\Program Files\Go\bin` | 编译 |
| Git | 2.55.0, `C:\Program Files\Git\bin` | 版本管理 |
| NSIS | 3.12, `C:\Program Files (x86)\NSIS` | 安装包 |
| Inno Setup | 7, `C:\Program Files\Inno Setup 7` | 备选 |
| GitHub CLI | `C:\Program Files\GitHub CLI` | 发布 |
| Go Proxy | `https://goproxy.cn,direct` | 国内代理 |
| WebView2Loader.dll | NuGet `Microsoft.Web.WebView2` 包提取，随仓库分发 | WebView2 加载 |

## 项目结构

```
D:\countdown-desktop\
├── main.go                        # DPI 初始化 → 单实例 → 测试模式 → 托盘/消息循环
├── version/version.go             # 版本 a.b.c.d
├── internal/
│   ├── webview/webview.go         # WebView2 COM 封装（核心，~700 行）
│   ├── wallpaper/wallpaper.go     # 壁纸引擎
│   ├── screensaver/screensaver.go # 屏保引擎
│   ├── tray/tray.go               # 托盘
│   ├── settings/settings.go       # 设置窗口
│   ├── config/config.go           # JSON 配置
│   ├── logutil/log.go             # log.txt
│   └── win32/win32.go             # Win32 封装
├── installer/setup.nsi
├── WebView2Loader.dll             # 必须随 exe 分发（System32 里没有）
├── assets/icon.ico
└── .github/workflows/release.yml
```

## 核心架构

### WebView2 封装（webview.go）

- 纯 Go + syscall 手写 COM vtable（零 CGo）
- 加载 WebView2Loader.dll：exe 目录 → 注册表定位 Runtime 目录 → System32
- 关键接口 vtable 索引（从 WebView2.h 1.0.4129.50 验证）：
  - ICoreWebView2Controller: put_IsVisible=4, put_Bounds=6, NotifyParentWindowPositionChanged=23, Close=24, get_CoreWebView2=25
  - ICoreWebView2: Navigate=5, get_Settings=3, Reload=31
- **所有 WebView2 方法必须从创建线程调用**（"This method can only be called from the thread that created the object"）→ 通过 opCh channel 投递到窗口线程（消息循环内 drain）
- COM 回调对象必须用全局 map 持有（防 GC），回调触发后 releaseHandler
- 收到的 COM 接口指针必须 AddRef 持有（WebView2 在 Invoke 返回后释放临时引用）
- 消息循环必须用 GetMessage(0)（全窗口），GetMessage(hwnd) 会过滤掉 WebView2 初始化需要的消息
- WaitReady 有 30s 超时保护

### 壁纸引擎（wallpaper.go）

1. 检测 Win11 raised desktop：Progman 是否有 WS_EX_NOREDIRECTIONBITMAP (0x00200000)
2. **SendMessageTimeout(progman, 0x052C, 0xD, 0x1, ..., 1000)** —— 传 0,0 不会创建正确的 WorkerW
3. 定位 SHELLDLL_DefView：Progman 子窗口 或 顶层 WorkerW 子窗口
4. **先手动设 WS_CHILD 样式再 SetParent**（SetParent 不修改 WS_CHILD/WS_POPUP！不设则 SetParent 无效）
5. SetParent 目标：raised→Progman；classic→含 DefView 的 WorkerW
6. SetWindowPos(HWND_BOTTOM) 置底（图标层之上显示壁纸）
7. **所有窗口操作必须通过 wv.Exec() 投递到窗口线程**（跨线程 SetParent/SetWindowPos 静默失败！）
8. reparent 后重新 put_Bounds/put_IsVisible/NotifyParentWindowPositionChanged/Reload（渲染可能冻结）
9. raised 分支需要 WS_EX_LAYERED + SetLayeredWindowAttributes(bAlpha=0xFF)（微软官方要求）

### 屏保引擎（screensaver.go）

- 全屏置顶窗口（HWND_TOPMOST）+ WebView2
- GetLastInputInfo + GetAsyncKeyState 监听，任意输入退出
- 空闲检测 goroutine：5s 轮询，IdleTime >= ScreensaverTime 启动

### 线程模型（重要）

- 每个 WebView2 实例 = 独立 goroutine + runtime.LockOSThread
- 该 goroutine：创建窗口 → 发环境创建 → 跑消息循环（GetMessage(0) + drain opCh）
- WebView2 回调（env/controller completed）在 WebView2 线程触发，但 controller 创建线程 = 回调线程
- opCh 在消息循环线程执行 = 创建线程 → 所有 controller/webview 方法通过 opCh 调用

## 构建命令

```powershell
$env:PATH = "C:\Program Files\Go\bin;C:\Program Files\Git\bin;$env:PATH"
$env:GOPROXY = "https://goproxy.cn,direct"
go build -ldflags "-H windowsgui -X github.com/tgcz2011/countdown-desktop/version.Version=1.0.0.4" -o countdown-desktop.exe .
makensis installer\setup.nsi
```

## 曾经犯过的错误（血泪史）

### 1. GetTickCount 放错 DLL（崩溃根因）
`GetTickCount` 是 kernel32 的 API，误放 user32 → 启动 5 秒后 panic，托盘消失。
**教训**：Win32 函数归属 DLL 要核对 MSDN。

### 2. WebView2Loader.dll 不在 System32
新版 WebView2 Runtime 不包含 WebView2Loader.dll（是开发者组件）。
**解决**：从 NuGet `Microsoft.Web.WebView2` 包提取，随应用分发；查找顺序 exe 目录 → 注册表 Runtime 路径 → System32。

### 3. Go GC 回收 COM 回调对象
`syscall.NewCallback` 生成的函数指针安全，但传入 WebView2 的 handler 结构体指针无 Go 引用 → GC 回收 → 回调不触发（死锁）。
**解决**：全局 `sync.Map` 持有 handler，回调后释放。

### 4. 缺少 COM AddRef
WebView2 在 CompletedHandler Invoke 返回后释放临时引用 → 25 秒后 controller 悬空 → Close() 崩溃（0xffffffffffffffff）。
**解决**：回调里对 controller/webView/settings 调 AddRef，Close 时 Release。
**注意**：脚本 patch 常因格式不匹配静默失败——每次 patch 后必须 grep 验证代码真的进去了！

### 5. WebView2 需要消息循环
CreateCoreWebView2Controller 的完成依赖宿主窗口消息泵。GetMessage(hwnd) 只取该窗口消息会漏掉 WebView2 需要处理的消息 → **必须 GetMessage(0)**。
消息循环必须与窗口创建在同一 OS 线程（LockOSThread）。

### 6. WebView2 方法线程绑定
put_IsVisible/put_Bounds/Close/Reload 全部报 "only be called from the thread that created the object"。
**解决**：opCh channel 投递到消息循环线程执行。

### 7. SetParent 跨线程静默失败
窗口创建在专用 goroutine 线程，main goroutine 调 SetParent → 返回旧父窗口（伪成功）但 GetParent 仍为 0。
**解决**：所有窗口操作（SetParent/SetWindowPos/ShowWindow/SetWindowLong）通过 wv.Exec() 投递。

### 8. SetParent 不修改 WS_CHILD 样式
顶层样式窗口直接 SetParent → 无效。**必须先 SetWindowLongPtr(GWL_STYLE, WS_CHILD|WS_VISIBLE) 再去掉 WS_POPUP/WS_OVERLAPPEDWINDOW**。

### 9. 0x052C 参数
传 (0,0) 不会创建 raised desktop 的壁纸 WorkerW。**必须 wParam=0xD, lParam=0x1**（微软内部规范，Lively 源码确认）。

### 10. DPI 虚拟化
未声明 DPI awareness → 窗口被系统缩放（3840→1920→960），嵌入 Explorer 的 DPI-aware WorkerW 后缩得更严重。
**解决**：main() 第一行 SetProcessDpiAwarenessContext(PerMonitorV2)，fallback SetProcessDPIAware。

### 11. WS_EX_LAYERED 必须配 SetLayeredWindowAttributes
设了 LAYERED 不调 SetLayeredWindowAttributes → 窗口完全透明不绘制。
Win11 raised desktop 下微软官方要求 LAYERED + bAlpha=0xFF；classic 布局不需要 LAYERED。

### 12. 无 DWM 环境（Server）嵌入渲染不可用
Windows Server（无 DWM 桌面合成）上 WebView2 顶层窗口正常，**嵌入 WorkerW/Progman 子窗口后内容不渲染**（浅色空白）。--disable-gpu 无效。
**影响**：壁纸嵌入在客户端 Win10/11（有 DWM）正常（Lively 同机制验证过）；Server 上壁纸不可用，屏保正常。
**测试环境限制**：本开发机是 Server 2022 无 DWM，壁纸嵌入的最终渲染效果需在客户端 Windows 验证。

### 13. 免费域名反爬
zztool.free.nf 有 JS 验证（slowAES cookie + 跳转），WebView2 能正常通过（有 cookie 存储）。curl 测试时需带 cookie 流程。

## 已知限制

- Server/无 DWM 环境：壁纸嵌入不渲染（见错误 12）
- 托盘图标从 EXE 资源加载未实现（LoadIcon 用系统图标 fallback）
- 未实现：多显示器壁纸、全屏应用暂停、自动更新

## 发布流程

1. 更新 version/version.go（a.b.c.d 递增）
2. 更新 README.md + HANDOFF.md（强制）
3. git add/commit/push
4. git tag vX.X.X.X && git push origin vX.X.X.X → GitHub Actions 构建 + Release
5. Actions 用 choco install nsis（makensis-action 在 windows runner 找不到 NSIS，已修复）

## GitHub 仓库注意事项

- 默认分支是 **main**（之前代码推到了 master，用户看不到 → 已合并）
- 发布前确认 main 是最新代码
