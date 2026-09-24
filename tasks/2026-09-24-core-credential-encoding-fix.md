# Task Packet — Core Python Credential Provider 编码缺陷修复

## 概要

| 字段 | 值 |
| --- | --- |
| Stage | Core Python Credential Provider 缺陷修复 |
| 角色 | Utility Codex |
| 执行器 | CodeBuddy |
| 直属上级 | CEO / Architecture Chat |
| Module | core |
| Execution Mode | FAST_V1 |
| Status | complete |
| Branch | `buddy/core-credential-encoding-fix` |
| Worktree | `D:/Program_Leo/INSO_Leo/.worktrees/core-credential-encoding-fix` |
| Base | `origin/main` @ `73520c170f12a5c5054211c3e6f38da119ad3fbf` |
| 触发 | Research RESEARCH-007 真实复现 |

## Public Contract

**不变**：`from src.core import get_login, Login, CredentialError` 完全保持。
本任务不修改 Core Python Provider Public Contract；只修复底层编码管线。

## 根因（已稳定复现）

`_vault_backend.py` 调用 PowerShell 5.1 时使用：

```python
subprocess.run(..., capture_output=True, text=True)
```

`text=True` 让 Python 用 `locale.getpreferredencoding(False)`（中文 Windows
上为 `cp936` / `gbk`）来解码子进程的 stdout / stderr。

但 PowerShell 5.1 通过 `[Console]::Out.WriteLine(...)` 输出的字节序列遵循
`[Console]::OutputEncoding`：

* 当输出包含非 ASCII 字符时，PowerShell 默认会按 UTF-8 写出字节
  （这是 .NET `Console` 在 Windows 上的实际行为，与系统代码页无关）。
* Python 端用 `cp936` 去解码这些 UTF-8 字节，命中无效多字节序列时直接抛
  `UnicodeDecodeError: 'gbk' codec can't decode byte 0xad ...`。

`UnicodeDecodeError` 由 `subprocess._readerthread` 抛出，stdout buffer
未被填充，主线程拿到的 `CompletedProcess.stdout` 为 `None`；
`_vault_backend.py` 后续对 `completed.stdout.strip()` / `completed.stderr` 的
访问触发 `AttributeError`，从 Provider 中以非 typed 异常形式冒出，
Research 观察到的就是这条逃逸。

## 诊断证据（synthetic 数据）

- 测试桩 fixture：
  - `powershell.exe -Command "[Console]::Out.WriteLine('中Ω🎉')"`
- Python `subprocess.run(text=True)`：
  - `returncode: 0`，但 `stdout: None`
  - reader thread 异常：`UnicodeDecodeError: 'gbk' codec can't decode byte 0xad in position 2`
- Python `subprocess.run(text=False)` + 读 raw bytes：
  - stdout bytes hex: `e4b8adcea9f09f8e89 0d0a`
  - 该序列为 `中Ω🎉\r\n` 的 UTF-8 编码（已 strict 验证）。

修复后必须使相同输入 → Python 拿到 `中Ω🎉\r\n` 字符串而非 None / 异常。

## 修复策略

最小且确定性的进程间文本编码协议：

1. **PowerShell 端**：embedded script 头部显式设置
   ```powershell
   [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
   ```
   包裹在 `try/catch` 中，失败映射为 `_BackendUnavailableError`
   （exit code 33）。
2. **Python 端**：`subprocess.run` 改为 `text=False` 拿原始 bytes，
   显式按 `'utf-8', errors='strict'` 解码 `stdout` / `stderr`：
   - stdout 解码失败 → `_VaultMalformedError`（PowerShell 发送了非 UTF-8 字节，
     等价于 Vault payload 损坏）。
   - stderr 解码失败 → `_BackendUnavailableError`（PowerShell 自身的
     错误输出也非 UTF-8，视为 backend 故障）。
3. 保持其余逻辑（exit code 映射、typed exception 转换、JSON 解析、
   payload 校验）完全不变。

不引入任何第三方依赖；继续使用 Python 3.8+ 标准库。

## Write Scope

允许：

- `src/core/_vault_backend.py`
- `src/core/credential_provider.py`（仅当确有必要，目前预计无需改动）
- `tests/core/test_credential_provider.py`
- `tests/core/test_vault_backend_smoke.py`
- `tests/core/test_vault_backend_encoding.py`（新增）
- `docs/modules/CORE.md`（仅当确有必要；Public Contract 不应改变）
- `tasks/2026-09-24-core-credential-encoding-fix.md`（本 Packet）

禁止：

- `src/research/**`
- `src/workflow/**`
- `src/sheets/**`
- Research Task Packet
- governance docs
- 其它任何模块

## 测试要求

新增 `tests/core/test_vault_backend_encoding.py`（synthetic、非 Secret）：

1. 非 ASCII username 正常往返。
2. 非 ASCII company 正常往返。
3. 非 ASCII password 正常往返。
4. JSON round-trip 与 Python `json.loads` 一致。
5. `repr(Login)` 仍不泄露 password / username。
6. 异常消息不泄露 credential value。
7. Malformed output（注入非 UTF-8 bytes）→ `_VaultMalformedError`，
   在 Provider 层映射为 `CredentialVaultError`。
8. PowerShell backend error（exit code 33）→ typed Core exception
   (`CredentialProviderUnavailableError`)。

真实 Vault readiness（手动 / 一次性）：

只允许报告：`bom.ai configured login retrieval: PASS / FAIL`。
禁止打印 username / password / company / URL / Vault 内容。
禁止真实网站登录。

## 安全约束

- 任何新增 fixture / 测试数据必须为 synthetic、非 Secret。
- 禁止把真实 username / URL / password / token / cookie 写入 Git。
- 严禁把 Secret 写入 log / Task / exception message / repr。
- 严禁把真实 Vault 内容写入测试 fixture。

## 执行步骤

diagnosis（已在本 Packet 完成）
→ implementation
→ tests
→ bounded smoke
→ self-review
→ commit
→ push

## 最终验证清单

- [x] Core Python tests
- [x] PowerShell CredentialVault tests
- [x] full pytest
- [x] Ruff
- [x] non-ASCII synthetic regression
- [x] bounded real-vault readiness (bom.ai: PASS)
- [x] secret scan
- [x] git diff review

## Final Result / Verification

**根因**：`_vault_backend.py` 用 `subprocess.run(text=True)`，Python 端用
`locale.getpreferredencoding()`（zh-CN 上 cp936/gbk）解码；PowerShell 5.1
`[Console]::Out.WriteLine` 实际按 UTF-8 写出字节，两侧编码不一致 →
`subprocess._readerthread` 抛 `UnicodeDecodeError` → `CompletedProcess.stdout`
被留为 `None` → `completed.stdout.strip()` 抛 `AttributeError`，从 Provider 中
以非 typed 异常逃逸。

**修复**（最小且确定性的进程间文本编码协议）：

- PowerShell 端：`[Console]::OutputEncoding = [System.Text.Encoding]::UTF8`，
  try/catch 包裹，失败映射为 exit code 33 (`_BackendUnavailableError`)。
- Python 端：`subprocess.run(text=False)`，新增 `_decode_strict_utf8`
  helper，按 `'utf-8', errors='strict'` 解码 stdout/stderr；
  解码失败 → typed Core exception
  （stdout → `_VaultMalformedError`，stderr → `_BackendUnavailableError`）。
  Provider 不再见到 `UnicodeDecodeError` / `AttributeError`。

**Public Contract**：完全不变。`from src.core import get_login, Login,
CredentialError` 与 v1 完全相同；`docs/modules/CORE.md` 无需改动。

**验证证据**：

| 项 | 结果 |
| --- | --- |
| `py -3.12 -m pytest -q` | **257 passed in 7.34s**（v1: 240；新增 17 个编码相关测试） |
| `py -3.12 -m ruff check src/core tests/core` | **All checks passed** |
| `tests\core\CredentialVault.Tests.ps1` | **PASS**（既有 PowerShell Vault 行为不回归） |
| `tests/core/test_vault_backend_encoding.py` | **17 / 17 PASS**：非 ASCII username / company / password / URL round-trip，`repr(Login)` 仍 redact，exception 不泄露 credential value，malformed stream → typed exception，embedded script 显式 `[Console]::OutputEncoding = UTF8` |
| 真实 Vault readiness | **bom.ai configured login retrieval: PASS**（仅报告 PASS/FAIL；未打印 username / password / company / URL / Vault 内容；未进行真实网站登录） |
| Secret scan (`git diff`) | **clean**（无真实 username / URL / password / token / cookie；测试值 100% synthetic） |

**Commit / Push**：

- Branch: `buddy/core-credential-encoding-fix`
- Commit: `9001f86d22c25f6cf08a04847d1cad5a46c11689`
- Subject: `CORE: fix UTF-8 encoding protocol for non-ASCII credential data`
- Author: `Horse-Hunter <86754027+Horse-Hunter@users.noreply.github.com>`
- Diff scope: `src/core/_vault_backend.py` (+90/-5) +
  `tests/core/test_vault_backend_encoding.py` (新增, +402) +
  本 Task Packet
- Base: `origin/main` @ `73520c170f12a5c5054211c3e6f38da119ad3fbf`
- Tracking: `origin/buddy/core-credential-encoding-fix`
- Status: pushed

**Remaining**：NONE in task scope。

合入 canonical main 是独立后续 Task；Research / Workflow V1 production
runtime 切到消费 `from src.core import get_login` 是独立后续 Task；
本 Task scope 已完全结束。

## STOP 条件

- 必须改变 Core Public Contract → STOP / 升级 CEO。
- 必须引入新依赖 → STOP / 升级 CEO。
- 必须修改禁止模块（research / workflow / sheets / governance）→ STOP / 升级 CEO。
- 真实 Secret 有泄露风险 → STOP / 升级 CEO。