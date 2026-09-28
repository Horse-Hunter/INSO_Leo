# 汇报规则

默认 **Main Programmer 直接向 Owner 汇报阶段结果**；普通开发失败不得通过汇报把诊断工作转交给 Owner。

阶段完成时只报：

```text
状态：DONE / BLOCKED
完成：<关键结果>
验证：<测试 + live>
需要 Owner：NONE / 一个真正必须由 Owner 完成的动作
阻塞：NONE / 唯一真实 blocker
说人话：<仅在有问题/阻塞时填写：用 1-3 句话解释现在到底出了什么问题、影响什么、接下来谁处理>
Commit：<SHA + push 状态>
```

只有业务规则、Safety/Write Gate、重大架构或 release/merge 节点才升级 CEO。

规则：
- 不贴长篇过程日志，不重复背景。
- `NOT_LIVE_VERIFIED` 不等于 `FAIL`。
- 普通技术失败先自行诊断、修复、重试验证，不以 `PARTIAL` / `BLOCKED` / `NEEDS_ONE_CLICK` 代替解决。
- selector/parser、browser/CDP、普通 session/认证恢复、timeout、测试错误不得列为“需要 Owner”；先由 Main Programmer 负责到底。
- **普通技术问题禁止发送“责任说明/失误复盘”代替继续工作。** 只有在问题已经修复或确实命中升级条件时才汇报；否则继续执行。
- **汇报不算进度，验收结果才算。** 没有 READY/PASS/live/commit/push 的过程描述，不得包装成阶段成果。
- 只有 CAPTCHA / OTP / 设备验证等明确人工安全挑战，或业务/Safety/Git/release 决策，才可要求 Owner 动作。
- 不得要求 Owner 提供账号、密码、cookie、token 或其他 secret。
- **有问题时，技术描述下面必须紧跟“说人话”。** 不得只给错误码、类名、函数名、selector、堆栈或内部缩写。直白解释必须回答三件事：哪里出了问题；对当前功能有什么影响；下一步由谁处理。Owner 不需要自己翻译技术报告。
- **Owner 不负责翻译、搬运或逐步指导普通调试。** 如果下一步仍由 Main Programmer 自己完成，则“需要 Owner”必须是 `NONE`。
- 一个答复最多要求 Owner 做一个明确动作。
