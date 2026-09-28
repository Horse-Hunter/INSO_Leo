# 汇报规则

默认 **Main Programmer 直接向 Owner 汇报阶段结果**；普通开发失败不得通过汇报把诊断工作转交给 Owner。

阶段完成时只报：

```text
状态：DONE / BLOCKED
完成：<关键结果>
验证：<测试 + live>
需要 Owner：NONE / 一个真正必须由 Owner 完成的动作
阻塞：NONE / 唯一真实 blocker
Commit：<SHA + push 状态>
```

只有业务规则、Safety/Write Gate、重大架构或 release/merge 节点才升级 CEO。

规则：
- 不贴长篇过程日志，不重复背景。
- `NOT_LIVE_VERIFIED` 不等于 `FAIL`。
- 普通技术失败先自行诊断、修复、重试验证，不以 `PARTIAL` / `BLOCKED` / `NEEDS_ONE_CLICK` 代替解决。
- selector/parser、browser/CDP、普通 session/认证恢复、timeout、测试错误不得列为“需要 Owner”；先由 Main Programmer 负责到底。
- 只有 CAPTCHA / OTP / 设备验证等明确人工安全挑战，或业务/Safety/Git/release 决策，才可要求 Owner 动作。
- 不得要求 Owner 提供账号、密码、cookie、token 或其他 secret。
- 一个答复最多要求 Owner 做一个明确动作。
