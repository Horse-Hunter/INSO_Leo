# Core 模块

- Core 拥有 Credential Provider 公共能力边界。
- 业务模块通过稳定的 provider 能力请求已授权凭据。
- 业务模块不得依赖 DPAPI、文件路径、PowerShell 或其他底层实现细节。
- 真实 Secret 不得进入 Git、Task、log、fixture 或 evidence；调用方同时遵守 `BOUNDARIES.md`。

Vault 尚未进入 canonical `main`；具体实现状态待正式合并后另行同步。
