# V1.2 Safety Review

Status: **Production Write Gate CLOSED**

本文件只保留当前有效安全结论；历史 discovery/旧 blocker 不在此保留。

## 当前允许

Main Programmer 可自主：
- 代码/文档/测试；
- read-only INSO discovery；
- synthetic/fake 数据；
- AI preview / recognition；
- 本轮创建且未保存的临时草稿；
- 开发分支 commit/push。

以上操作不得产生真实业务副作用。

## 需要 Gate 的动作

以下必须先由 Owner + CEO/Safety 明确授权：
- INSO `保存数据`；
- 真实 SMTP 到业务收件人；
- Google Sheets 真实写入；
- 任何真实订单/客户记录修改；
- 数据迁移/恢复中可能覆盖真实数据的动作。

授权只覆盖明确环境、动作和范围；风险或范围变化需重新授权。

## 永久禁止

- `保存并发送`、`发送`；
- 绕过 CAPTCHA / OTP / device verification；
- 猜测页面、订单、控件或写入目标；
- unknown write outcome 后自动再点一次 Save；
- 将 password/secret/token/cookie/Vault value 写入 Git、日志、fixture、SQLite、evidence；
- force push `main`、reset/clean/delete 未知 Owner 工作。

## 首次真实 Save 的最低条件

必须全部满足：

1. Chrome production baseline 与 session lease 身份明确；
2. 当前 inquiry 唯一；
3. Save Data 控件唯一、可见、语义确认；
4. Save-and-Send / Send 在 API 与 selector 层均不可达；
5. AI preview 与 parent read-back：MPN / Brand / Qty 全部 exact；
6. customer / quotation type / purchaser read-back 正确；
7. Save 前 durable state 已记录；
8. Save 后可取得唯一 BillID/record identity 并 read-back；
9. timeout/未知结果进入 `UNKNOWN_WRITE_OUTCOME`，禁止自动重试；
10. evidence 只保存已证明可安全裁剪/脱敏的内容；否则不截图。

任一项不满足 → fail closed。

## 通知安全

- sender/recipients 是非秘密配置；
- SMTP credential 只从 Core Vault `smtp.qq.com` 读取；
- per-recipient ledger，已 SENT 不重发；
- transient 才重试；auth/config/permanent 不重试；
- UNKNOWN transport result 在 reconciliation/manual review 前不重发；
- notification failure 不阻塞 purchase。

## 数据与日志

允许持久化：sanitized reason code、状态、时间、attempt、非敏感 identity。

禁止持久化：raw external exception/body/header、cookie、credential、完整客户行、任意页面文本、未脱敏截图。

SQLite migration：additive + verified pre-migration backup；不自动 downgrade/drop。

## Gate 状态

- Read-only discovery：**允许，按明确范围执行**
- Synthetic AI / unsaved draft：**允许**
- Production Save Data：**CLOSED**
- Real SMTP：**CLOSED**
- Sheets real write：**CLOSED**
- Save-and-Send / Send：**永久禁止**

首次真实写入前由 CEO/Safety 做一次 Gate Review；普通开发问题不升级 Safety。
