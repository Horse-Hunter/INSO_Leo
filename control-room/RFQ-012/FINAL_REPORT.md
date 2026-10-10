# RFQ-012 Owner 单次按钮调整

REVIEW_REQUIRED。基于671ef59770cbcb5202f9d2f918c5688d2ca6f451，
沿用 codex/v1-4-order-mail-inspection，未部署、未进入自动保存/审核。

- 一次点击只运行一次；最先恢复/最大化唯一 CDP Chrome 窗口并读回确认，
  然后选择 INBOX 最旧的未处理“订单录单”邮件，以 INTERNALDATE 收件时间
  排序（相同时间以UID稳定排序），不按未读状态或发件日期判断。
- 服务端搜索订单候选，只读其必要元数据，最多2000个候选，超过上限停止。
  只对选中的一封 PEEK 正文/Excel；候选读取前后 FLAGS 审核一致才继续。
  未删除/移动/设置 flag/回复；没有邮箱定时轮询。
- 每张订单新建独立保护的 V1.4 tab，复用现有唯一9222/profile/登录 guard，
  完成合同/ICNET preflight 后才认证进入销售订单。旧待复核页不导航、不关闭，
  并可在旧页仍打开时处理下一张订单。询价/采购 run state 不被暂停或改写。
- 头部与明细仍使用已有严格解析、封装查询和即时/逐行/最终读回。全部确认后
  在本机 runtime/v14-filled.sqlite3 记录成功填写，仅哈希邮件身份和时间。
  邮件 UIDVALIDITY+UID 和 Message-ID 别名用单向哈希，不存 PI/正文/附件。
  失败不记录成功，下次点击仍选最旧未完成订单；本机记录损坏/写入失败停止。
- 填完释放 worker，按钮恢复“自动订单录单”。页面保留供 Owner 人工核对、
  提交审核并关闭。程序不填总金额/CONDITION、不传 PDF、不保存、不提交审核。
  没有采购/报价/Sheets/生产 workflow DB 修改。异常通知沿用既有1069路径。
- 两封旧样本仅当作测试，未预先标记、未代 Owner 运行本轮真实填写。Owner
  将用新按钮验证：第一封成功后再点击应选下一封，旧标签页仍可保留。

验证：focused299 passed；full safe/offline1814 passed/1 skipped；Ruff/diff PASS。
本轮没有真实业务/异常 SMTP 测试。源码验收完成，Owner 实际按钮测试和 CEO
独立 Review 待进行。被冻结旧 V1.3 EXE 与源代码开发GUI混跑仍为 UNKNOWN，
未声称部署或对旧EXE做修改。Message-ID被复用/修订的业务规则未自行扩展。
