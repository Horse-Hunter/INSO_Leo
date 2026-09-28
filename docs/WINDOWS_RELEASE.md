# Windows release

## Build

安装 `requirements-windows-release.lock`，运行：

`scripts/build_windows_release.ps1`

产物：`dist/INSO_V1.1/INSO_V1.1.exe`。构建脚本会运行 frozen `--self-check`；Tcl/Tk 不可用时直接失败。

## Runtime files

Release 不包含生产数据。部署时在 release root 下提供 Git-ignored：
- `runtime/research.json`
- `runtime/production.json`

Chrome bootstrap 只使用显式 approved 配置：

```json
{
  "browser_bootstrap": {
    "executable": "C:/Approved/Chrome/Application/chrome.exe",
    "profile_dir": "C:/Approved/INSO-CDP-Profile",
    "debug_port": 9222,
    "ready_timeout_seconds": 30
  }
}
```

Profile 必须已存在；程序不猜路径、不创建替代 profile。CDP 已可用时复用；否则只启动配置中的 approved Chrome。Reused Chrome 不关闭，app-owned Chrome 按 runtime lifecycle 清理。

INSO ordinary authentication 使用共享 runtime helper + Core Vault 自动恢复；只有 CAPTCHA / OTP / device verification 等人工安全挑战需要 Owner。

## Secrets / diagnostics

不要把 runtime config、OAuth client/grant、browser profile、SQLite、Excel 或 credential 放进 release artifact。

Launcher 日志位于 `runtime/logs/INSO_V1.1.log`，只允许 sanitized diagnostics。Vault readiness 可用：

`INSO_V1.1.exe --diagnose-vault`

报告只能包含 site/config readiness 与安全错误类型，不包含 credential value。
