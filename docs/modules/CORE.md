# Core 模块

- Core 拥有 Credential Provider 公共能力边界。
- 业务模块通过稳定的 provider 能力请求已授权凭据。
- 业务模块不得依赖 DPAPI、文件路径、PowerShell 或其他底层实现细节。
- 真实 Secret 不得进入 Git、Task、log、fixture 或 evidence；调用方同时遵守 `BOUNDARIES.md`。

Windows 本地 Credential Vault 的源码与 synthetic 测试已进入 canonical `main`。Secret 存储与源码分离，并使用 Windows 当前用户保护能力；具体存储位置和 PowerShell 脚本不是业务模块 Contract。

## Python application Credential Provider API

业务模块通过 `core` 包提供的稳定 Python Provider 访问已授权登录信息。

### 入口

```python
from core import get_login, default_provider, Login, CredentialError

login = get_login("example.com")  # raises CredentialError subclass on failure
```

`get_login` 是 `default_provider().get_login(site_id)` 的便捷封装。两者都是
进程级单例入口；业务模块不应直接 import 私有类（带下划线前缀的符号）。

### `Login` dataclass

不可变记录，包含：

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `site_id` | `str` | 业务模块使用的稳定 site key（与 Vault 中的 SiteId 对应） |
| `url` | `str` | 登录页 URL（可为空字符串） |
| `username` | `str` | 已授权用户名 |
| `password` | `str` | 已授权密码，仅在调用方持有期间存在于内存 |
| `company` | `Optional[str]` | 可选公司/主体标识；未配置时为 `None` |

`repr(Login)` 默认重写为脱敏形式，password 与 username 显示为 `***REDACTED***`。

### 异常

| 异常 | 触发场景 |
| --- | --- |
| `CredentialSiteNotFoundError` | 请求的 `site_id` 不在 Vault 中 |
| `CredentialNotConfiguredError` | site 存在但未配置 password |
| `CredentialVaultError` | Vault 文件缺失、不可读或结构损坏 |
| `CredentialProviderUnavailableError` | 后端不可达（PowerShell 缺失、DPAPI 不可用等） |
| `CredentialError` | 上述异常的基类；也用于非法 `site_id` |

所有异常只携带 `site_id` 与人类可读消息；`str(exc)` 中绝不包含 password 或
username 任何取值。Provider 失败时绝不返回空 / 占位 `Login`。

### 失效策略

- 缺失 site / 未配置 credential / Vault 损坏 / 后端不可用 → 抛出对应类型异常。
- 不允许 `plaintext` / `env` / repo-file fallback。
- 不建立第二份 Credential Store；唯一真实来源仍是现有 Windows Vault。
- PowerShell 可执行文件、`.psm1` 模块路径、Vault JSON 路径均属于 Core 私有
  实现细节，业务模块不可依赖。

### 业务模块用法示例

```python
# research module
from core import get_login, CredentialError

try:
    login = get_login("findchips")
except CredentialError as exc:
    # fail closed; never proceed with a fake/empty credential
    raise SystemExit(f"credential unavailable: {exc.site_id}")

# pass login.username / login.password to the authenticated HTTP client
# delete or scope-limit the login object as soon as possible
```

### 文档化环境变量

| 变量 | 用途 | 默认 |
| --- | --- | --- |
| `INSO_CREDENTIAL_PWSH` | 指定 PowerShell 可执行文件 | 在 PATH 上自动发现 `pwsh` / `powershell` |
| `INSO_CREDENTIAL_VAULT_PATH` | 指定 Vault JSON 文件路径 | 由现有 PowerShell 模块决定（默认 `%LOCALAPPDATA%\INSO_Leo\credential-vault.json`） |

业务模块不应读取或依赖这两个变量；它们仅供测试与运维脚本使用。

### 兼容性

- Python 3.8+ 标准库；不引入第三方依赖。
- Provider 接口在 Windows + Windows DPAPI 主机上保证可用；在其他主机上
  `default_provider()` 会以 `CredentialProviderUnavailableError` 失败。
- 跨平台抽象不在 V1 范围内。
