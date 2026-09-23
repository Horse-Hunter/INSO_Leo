# Core 模块

- Core 拥有 Credential Provider 公共能力边界。
- 业务模块通过稳定的 provider 能力请求已授权凭据。
- 业务模块不得依赖 DPAPI、文件路径、PowerShell 或其他底层实现细节。
- 真实 Secret 不得进入 Git、Task、log、fixture 或 evidence；调用方同时遵守 `BOUNDARIES.md`。

Windows 本地 Credential Vault 的源码与 synthetic 测试已进入 canonical `main`。Secret 存储与源码分离，并使用 Windows 当前用户保护能力；具体存储位置和 PowerShell 脚本不是业务模块 Contract。

语言中立或 Python application Credential Provider API：`UNKNOWN`。本次不为其预先设计 bridge。
