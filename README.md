# Countdown Desktop

Windows 动态壁纸软件：把任意网页设置为**动态壁纸**和**屏幕保护**，内置高考/中考倒计时切换（高考为原默认链接 `https://zztool.free.nf/countdown`，中考为 `https://zztool.free.nf/countdown-junior`），也支持自定义任意地址。

- 倒计时类型：设置里一键切换 **高考倒计时 / 中考倒计时 / 自定义地址**；高考/中考时壁纸与屏保统一使用对应倒计时页，自定义时两者可分别设置。
- 动态壁纸：网页窗口嵌入桌面壁纸层（桌面图标之下、原壁纸之上），桌面图标正常可点；退出软件或关闭壁纸自动恢复原壁纸。
- 源类型：壁纸/屏保源支持 **网页、视频（mp4/webm/mkv/mov）、图片、动图（gif）**；可用远程地址或本地文件（设置里「浏览…」选择）；视频循环播放（可关）；图片/视频画幅可选铺满裁剪/黑边/拉伸；网页与视频声音默认静音、可开。
- 屏幕保护：**自绘全屏置顶窗口，不使用系统屏保**；空闲达到设定时长自动触发，任意键鼠输入立即退出，默认 600 秒。
- 壁纸与屏保的源 **分开设置、均可修改**，互不影响。
- 命令行参数：全部设置均可通过启动参数单次覆盖（不写入长期配置），详见下文「命令行参数」。
- 托盘图标：单击弹出设置（通用页）；右键菜单含设置、立即启动屏保、刷新壁纸、开机自启、退出。
  托盘图标随系统主题自适应：深色任务栏用白色描边时钟（assets/icon-tray.ico），浅色任务栏用彩色主图标，切换实时生效。

## 运行环境

- Windows 10 / 11（x64 / ARM64）。
- 依赖 **WebView2 Runtime**（Chromium 内核，保证任意 Win10/11 机器渲染一致）：Win11 与多数 Win10 已预装；若缺失，安装包自动静默安装（内置微软官方 Bootstrapper），无需手动操作。

## 安装与使用

1. 从 [Releases](https://github.com/tgcz2011/countdown-desktop/releases) 下载 `CountdownDesktop_Setup_<版本>.exe` 安装（默认按用户安装，免管理员权限）。
2. 软件常驻托盘。单击托盘或右键 →「设置」，设置窗口为左侧导航多页结构：
   - 「倒计时」：类型切换（高考倒计时 / 中考倒计时 / 自定义地址）。高考/中考时壁纸与屏保统一使用对应页面；自定义时在壁纸/屏保页分别设置地址。
   - 「动态壁纸」：启用开关 + 壁纸源 + 画幅（铺满裁剪/黑边/拉伸，图片视频源生效）+ 静音开关；
   - 「屏幕保护」：启用开关 + 屏保源 + 空闲触发时长（秒）+ 画幅 + 静音开关；
   - 「通用」：开机自启 + 视频循环开关；
   - 「关于」：版本信息、GitHub 仓库与反馈链接、开源许可说明、Lively Wallpaper 鸣谢、检查更新/一键更新/自动检查开关；
   - 底部「保存」后所有页设置一起生效，壁纸按新配置立即重启；右上角 × 等同取消不保存。
3. 退出软件或关闭动态壁纸后，桌面自动恢复原壁纸。
4. 「立即启动屏保」可当场预览；按任意键或移动鼠标退出。
5. 「开机自启」写入 HKCU 注册表，登录自动启动（卸载自动清理）。

## 命令行参数

程序支持带参数启动，**所有设置均可通过参数覆盖，仅本次运行有效，不写入长期配置**；未传的参数沿用已保存配置。

```
CountdownDesktop.exe [参数...]
```

| 参数 | 取值 | 说明 |
|------|------|------|
| `--exam` | `gaokao` \| `zhongkao` \| `custom` | 倒计时类型：高考（默认）/ 中考 / 自定义 |
| `--wallpaper-url` | URL 或本地文件路径 | 壁纸源地址 |
| `--wallpaper-enabled` | `on` \| `off` | 是否启用动态壁纸 |
| `--wallpaper-fit` | `cover` \| `contain` \| `fill` | 壁纸画幅（图片/视频源） |
| `--wallpaper-mute` | `on` \| `off` | 壁纸静音 |
| `--screensaver-url` | URL 或本地文件路径 | 屏保源地址 |
| `--screensaver-enabled` | `on` \| `off` | 是否启用屏保 |
| `--screensaver-timeout` | 秒 | 屏保空闲触发时长 |
| `--screensaver-fit` | `cover` \| `contain` \| `fill` | 屏保画幅（图片/视频源） |
| `--screensaver-mute` | `on` \| `off` | 屏保静音 |
| `--video-loop` | `on` \| `off` | 视频循环播放 |
| `--run-at-startup` | `on` \| `off` | 本次会话的「开机自启」显示状态（**不写注册表**） |
| `--auto-check-update` | `on` \| `off` | 本次会话是否自动检查更新 |
| `--help` / `-h` | — | 显示参数帮助 |

示例：

```powershell
# 本次用中考倒计时作为壁纸与屏保
CountdownDesktop.exe --exam zhongkao

# 自定义壁纸源（中考预设之外的地址），屏保保持配置
CountdownDesktop.exe --exam custom --wallpaper-url https://example.com/countdown

# 只改屏保触发时长与静音
CountdownDesktop.exe --screensaver-timeout 300 --screensaver-mute on
```

规则说明：

- 显式 `--wallpaper-url` / `--screensaver-url` 优先于 `--exam` 预设；只传地址、不传 `--exam` 时，倒计时类型自动视为「自定义」。
- 参数会同步生效于壁纸/屏保播放器子进程；也可以直接对播放器传参，如 `python run.py player wallpaper --exam zhongkao`。
- 覆盖只作用于内存；例外：本次会话中若手动打开设置并点「保存」，界面当前值会写入配置（所见即所得）。
- 程序已运行时，带参数启动会提示先退出当前实例。

## 开发与构建

技术栈：Python + PySide6（托盘/多页设置 UI）+ pywebview（WebView2 渲染）+ Inno Setup 安装包 + GitHub Actions 发布。

```powershell
# 本地一键构建
.\build.ps1 -Version 3.2.0.0

# 或分步
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm CountdownDesktop.spec
& "C:\Program Files\Inno Setup 7\ISCC.exe" /DVERSION=3.2.0.0 installer\setup.iss
```

发布：推送 tag `v<版本>`，GitHub Actions 自动构建安装包并创建 Release。

## 架构速览

```
CountdownDesktop.exe            主进程：托盘/设置/空闲检测/子进程管理
  ├─ run.py player wallpaper    壁纸播放器（WebView2 窗口嵌入 WorkerW/Progman）
  └─ run.py player screensaver  屏保播放器（全屏置顶 + 输入监听退出）
配置 %APPDATA%\CountdownDesktop\config.json；日志同目录 *.log
命令行覆盖 app/cli.py：主进程与播放器子进程共用同一套参数解析
```

壁纸嵌入参考 [Lively Wallpaper](https://github.com/rocksdanister/lively)：
`SendMessageTimeout(Progman, 0x052C, 0xD, 0x1)` → 定位壁纸宿主（含 `SHELLDLL_DefView` 的 WorkerW 的下一个 WorkerW 兄弟；Win11 raised desktop 时为 Progman 且窗口加 `WS_EX_LAYERED`）→ 转 `WS_CHILD` + `SetParent` → 铺满虚拟屏幕。

## 版本号规则

`a.b.c.d`：d=小改动/修复，c=小添加，b=大改，a=大添加；去掉点后数值严格递增。

## License

GPL-3.0，见 [LICENSE](LICENSE)（架构借鉴 Lively Wallpaper）。
