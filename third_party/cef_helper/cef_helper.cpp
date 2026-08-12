// CEF wallpaper renderer helper (Lively-style architecture)
// Usage: cef_helper.exe --url=<url> --width=<w> --height=<h> [--x --y]
// Prints "HWND:<value>" to stdout when the window is created.
#include "include/cef_app.h"
#include "include/cef_browser.h"
#include "include/cef_client.h"
#include "include/cef_command_line.h"
#include "include/cef_sandbox_win.h"
#include <windows.h>
#include <iostream>
#include <sstream>
#include <string>

namespace {

bool g_quit = false;

class HelperApp : public CefApp, public CefBrowserProcessHandler {
 public:
  HelperApp() {}

  CefRefPtr<CefBrowserProcessHandler> GetBrowserProcessHandler() override {
    return this;
  }

  void OnBeforeCommandLineProcessing(
      const CefString& process_type,
      CefRefPtr<CefCommandLine> command_line) override {
    command_line->AppendSwitch("no-sandbox");
    command_line->AppendSwitch("disable-gpu");
    command_line->AppendSwitch("disable-gpu-compositing");
    command_line->AppendSwitch("autoplay-policy=no-user-gesture-required");
  }

  IMPLEMENT_REFCOUNTING(HelperApp);
};

class HelperClient : public CefClient, public CefLifeSpanHandler,
                     public CefLoadHandler {
 public:
  HelperClient() {}

  CefRefPtr<CefLifeSpanHandler> GetLifeSpanHandler() override { return this; }
  CefRefPtr<CefLoadHandler> GetLoadHandler() override { return this; }

  void OnLoadEnd(CefRefPtr<CefBrowser> browser, CefRefPtr<CefFrame> frame,
                 int httpStatusCode) override {
    if (frame->IsMain()) {
      std::cout << "LOADED:" << httpStatusCode << std::endl;
      browser_ = browser;
    }
  }

  CefRefPtr<CefBrowser> GetBrowser() { return browser_; }

  IMPLEMENT_REFCOUNTING(HelperClient);

 private:
  CefRefPtr<CefBrowser> browser_;
};

std::string GetArg(int argc, char** argv, const std::string& key,
                   const std::string& def = "") {
  std::string prefix = "--" + key + "=";
  for (int i = 1; i < argc; ++i) {
    std::string a = argv[i];
    if (a.rfind(prefix, 0) == 0) {
      return a.substr(prefix.size());
    }
  }
  return def;
}

}  // namespace

int main(int argc, char** argv) {
  HINSTANCE hInstance = GetModuleHandle(NULL);
  CefMainArgs main_args(hInstance);

  CefSettings settings;
  settings.no_sandbox = true;
  settings.log_severity = LOGSEVERITY_DISABLE;

  // Resolve resource paths relative to the executable
  {
    wchar_t buf[MAX_PATH] = {0};
    GetModuleFileNameW(NULL, buf, MAX_PATH);
    std::wstring exe_dir = buf;
    size_t pos = exe_dir.find_last_of(L"\\");
    if (pos != std::wstring::npos) {
      exe_dir = exe_dir.substr(0, pos);
      std::wstring res = exe_dir + L"\\Resources";
      CefString(&settings.resources_dir_path) = res;
      CefString(&settings.locales_dir_path) = res + L"\\locales";
    }
  }

  CefRefPtr<HelperApp> app(new HelperApp());

  // Execute sub-processes
  int exit_code = CefExecuteProcess(main_args, app.get(), nullptr);
  if (exit_code >= 0) {
    return exit_code;
  }

  if (!CefInitialize(main_args, settings, app.get(), nullptr)) {
    std::cerr << "CEF initialize failed" << std::endl;
    return 1;
  }

  // Parse args
  std::string url = "https://zztool.free.nf/countdown";
  int width = 1920, height = 1080, x = 0, y = 0;
  for (int i = 1; i < argc; ++i) {
    std::string a = argv[i];
    auto get = [&](const std::string& key, std::string* out) {
      std::string p = "--" + key + "=";
      if (a.rfind(p, 0) == 0) *out = a.substr(p.size());
    };
    std::string v;
    get("url", &v); if (!v.empty()) url = v;
    get("width", &v); if (!v.empty()) width = atoi(v.c_str());
    get("height", &v); if (!v.empty()) height = atoi(v.c_str());
    get("x", &v); if (!v.empty()) x = atoi(v.c_str());
    get("y", &v); if (!v.empty()) y = atoi(v.c_str());
  }
  bool visible = false;
  for (int i = 1; i < argc; ++i) {
    if (std::string(argv[i]) == "--visible") visible = true;
  }

  // Register window class
  const wchar_t kClassName[] = L"CountdownCEFHost";
  WNDCLASSEXW wc = {};
  wc.cbSize = sizeof(wc);
  wc.lpfnWndProc = DefWindowProcW;
  wc.hInstance = hInstance;
  wc.lpszClassName = kClassName;
  RegisterClassExW(&wc);

  // Create window (top-level; the Python controller reparents it)
  // Hidden at creation (Lively-style): the controller embeds the window
  // into the desktop and then shows it, so CEF initializes rendering on a
  // visible embedded window.
  HWND hwnd = CreateWindowExW(WS_EX_TOOLWINDOW, kClassName, L"Countdown",
                              WS_OVERLAPPED, x, y, width, height,
                              nullptr, nullptr, hInstance, nullptr);
  if (!hwnd) {
    std::cerr << "CreateWindow failed" << std::endl;
    return 2;
  }
  if (visible) {
    ShowWindow(hwnd, SW_SHOWNA);
  } else {
    // Lively-style: minimized + off-screen before embedding
    ShowWindow(hwnd, SW_SHOWMINIMIZED);
    SetWindowPos(hwnd, nullptr, -9999, 0, 0, 0,
                 SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE);
  }

  // Create browser as child of our window
  CefWindowInfo win_info;
  RECT child_rect = {0, 0, width, height};
  win_info.SetAsChild(hwnd, child_rect);

  CefBrowserSettings browser_settings;
  browser_settings.background_color = CefColorSetARGB(255, 30, 30, 30);

  CefRefPtr<HelperClient> client(new HelperClient());

  if (!CefBrowserHost::CreateBrowser(win_info, client.get(), url,
                                     browser_settings, nullptr)) {
    std::cerr << "CreateBrowser failed" << std::endl;
    return 3;
  }

  // Tell the controller the window handle
  std::cout << "HWND:" << std::hex << (uintptr_t)hwnd << std::dec << std::endl;
  std::cout.flush();

  // Custom message loop: dispatch window messages (WM_PAINT etc) + CEF work.
  // Without GetMessage/DispatchMessage the window never repaints on screen.
  {
    CefRefPtr<CefBrowser> browser = client->GetBrowser();
    DWORD lastNotify = 0;
    MSG msg;
    while (!g_quit) {
      while (PeekMessage(&msg, NULL, 0, 0, PM_REMOVE)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
      }
      CefDoMessageLoopWork();
      DWORD now = GetTickCount();
      if (browser && now - lastNotify > 500) {
        lastNotify = now;
        CefRefPtr<CefBrowserHost> host = browser->GetHost();
        if (host) {
          host->NotifyMoveOrResizeStarted();
        }
      }
      Sleep(10);
    }
  }
  CefShutdown();
  return 0;
}
