# V1.4 Phase 3 / RFQ-011 CEO 报告

状态：REVIEW_REQUIRED。基于 REVIEWED_DONE
`b1a11820bff01e939b63dba0cf0072318787ce1f`，继续开发分支
`codex/v1-4-order-mail-inspection`。未部署，等待 CEO 独立 Review。

1. **明细行数：** 10月7日样本2为1行；10月9日样本1为4行。每次 GUI 点击仅
   读取/处理当前选择的一封邮件，另一封只可能读取候选头部，不读取正文/附件。
2. **字段解析：** 两份的 PART NUMBER、L/T、BRAND、DC、QTY(PCS)、
   UNIT PRICE(￥) 均稳定读取，表头唯一。PI 唯一有效；缺失、公式、歧义和非法
   数值停止。QTY 为正整数，价格为原 Excel 正数直接填写未税单价，不换汇/除税。
3. **交期：** 同一次开始时捕获一个 Asia/Shanghai today，所有行共用。
   两份真实样本均按1-3 DAYS得到+7天；离线验证2-4 WEEKS为+35、
   3-6 WEEKS为+49，其他格式停止。填写格式 YYYY-MM-DD。
4. **ICNET 封装：** 两份所有明细均取得有效封装。直接统计页面展示顺序的前
   20条（不足则实际条数），忽略空值、选最高频，并列取最先出现；不再匹配型号。
   同订单完全相同型号缓存一次，查询串行执行，保留原有查询间隔。
5. **既有代码复用：** 使用 CoreResearchCredentials、CdpIcNetClient 的既有
   登录/搜索/CDP 和 HTML 可见性解析基础，只增加 result_pakaging 读取能力。
   Research 品牌/库存/匹配规则未改，没有第二套登录/搜索。
6. **精确新增：** 1行样本没有新增；Owner 检查并回复已返回列表后才运行4行
   样本，增加3行且每次验证+1。最终行数4；在内存比较确认 XS 编号未变。
   超出合同行数停止，未删除任何明细。Phase2 开发期复用策略与再次选择 RMB
   行为保留，没有提前设计生产 tab 生命周期。
7. **读回：** 两次各行型号、订单量、未税单价、品牌、批号、封装、交期、
   包装情况、开发人、湿敏等级、是否拆包，即时/逐行/整表全部一致；头部也一致。
   当前原生明细编辑器为普通输入框，通过 fill + Tab/blur 触发页面逻辑，未用
   JS 强改值；控件类型不明即停止。
8. **异常通知：** 接入现有1069 SMTP/V1.2 notification outbox/worker，收件人
   229/shawn 独立发送重试，同一 invocation 异常去重，正文仅必要业务句子。
   离线覆盖合同、L/T、ICNET、读回异常及独立失败重试，没有故意发真实邮件。
   本次两份真实运行成功，没有自然异常或真实异常邮件。持久化使用 Git ignored
   独立开发通知 DB，沿用旧 schema/枚举；外键使用仅通知的 MANUAL_REVIEW
   锚点，不创建采购/报价状态、不修改生产 DB。
9. **总金额：** 未填写 AMOUNT/总金额；由页面原生逻辑计算。CONDITION未映射。
10. **禁止项：** 没有 PDF 上传、Save、提交审核、自动删除、Sheets 写入、
    采购/报价状态修改、15分钟邮件轮询或部署；没有同时处理两封邮件。
11. **页面保留：** 当前4行样本仍在同一个 V1.4 未保存页面供 Owner 查看。
    GUI 显示等待 Owner 复核，worker 已释放；独立 owned tab 与询价 run state
    保护继续通过回归。未主动关闭销售页面，未导航/关闭 V1.2/V1.3 页面。
12. **检查：** focused **319 passed**；full safe/offline **1806 passed / 1 skipped**；
    Ruff、diff check 通过，完整 V1.2/V1.3 与 Research ICNET 回归通过。

限制/UNKNOWN：仅两份授权版式；没有执行带真实采购/报价/通知副作用的并行业务
混跑，也未宣称旧冻结 V1.3 EXE 与未部署 V1.4 同时运行已验收。异常 SMTP 路径
本次仅 fake transport 验证。未来生产独立订单 tab/authentication/Save 闭环仍待
后续 Owner 授权，本阶段不进入 Phase4。

Git/报告不含真实 PI、客户、型号、价格、合同正文、原始邮件/页面或附件。
真实附件仅内存解析，所需值只填入授权的未保存页面。
