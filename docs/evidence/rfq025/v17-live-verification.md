# RFQ-025 第二阶段 — V1.7 真实页面验证（2026-11-21）

用**已提交的生产代码路径**在真实 ERP 上跑通一次完整录单。不是临时探针脚本：调用的就是
`backend._prepare_on_page()` 同一个组合 —— `attach_inso_research_session` →
`access.operation_page()` → `InsoPurchaseWriter` → `CoordinatorPurchaseDraftWriter.prepare(command)`。

## 1. 执行条件

| 项 | 值 |
|---|---|
| V1.6 状态 | 业务停止（日志最后一条 10:59:11，无新 `cycle=` 行） |
| 代码 | `workbuddy/v17-native-paste` @ `38341aa5` |
| 浏览器 | 唯一 Chrome `127.0.0.1:9222`，原 profile，未新建环境 |
| 登录 | 走 `ensure_inso_authenticated`（生产同一入口），凭据取自 Core |
| Owner 授权 | 2026-11-21：允许在生产环境直接开发、调试与实机验证 |

## 2. 执行结果

```
attached: True
surface_cleared_before_order: True
paste_input: TRJC476K016RRJ|200|Kyocera AVX
outcome: AI_RECOGNIZED
reason: None
recognized: TRJC476K016RRJ  Kyocera AVX  200
non_get_requests: [... sys_login.ashx ×4, cus.ashx ×3, sys_code.ashx ×2,
                   services/product/import.ashx ×1]
ai_traffic: []
bill_id_after_prepare: (空)
VERDICT: PASS
surface_cleared_after_order: True
```

逐项对照 Owner 的验收要求：

| 要求 | 结果 |
|---|---|
| 新代码真实、稳定地操作 INSO 页面 | **是**，一次成功，无重试 |
| 数据顺序与内容准确 | **是**：`型号|数量|品牌`，回读 `TRJC476K016RRJ` / `Kyocera AVX` / `200` |
| ERP 原生解析及编码补充正常 | **是**：唯一一次 `POST /services/product/import.ashx`，父表单行含 ERP 生成的编码 |
| 父表单回填正确 | **是**：`wait_for_model` 命中，`read_model/brand/quantity` 与订单一致 |
| 正常路径未调用 AI 录单服务 | **是**：请求监听中 `Import_ai.aspx` / `ai_import` 命中数为 **0** |
| 草稿验证未创建或发送真实采购单据 | **是**：`#BillID` 为空；全程未点 `#btnSave` / `#btnSave2` |
| 异常时能给出准确诊断 | 单元层面已覆盖（见测试）；真实故障注入未做，见第 4 节 |

`AI_RECOGNIZED` 是**历史持久化值**（SQLite 与事件目录沿用），语义为"预览已核对通过"，
不是"AI 识别成功"。用户可见文案已改为"粘贴录单"。

## 3. 联网请求的实际构成

那次运行里唯一的业务 POST 是解析接口本身；其余 POST 全部来自页面自身的登录/客户/字典加载，
与本次改动无关。**没有任何一个请求指向 AI 端点**，这是"生产路径不再依赖 AI 录单"的直接证据。

## 4. 未覆盖的部分（如实）

- **没有真实发送**：`#btnSave` / `#btnSave2` 全程未点，未产生任何 ERP 单据。
  真实发送与完整业务结果验收按 Owner 指令放在候选安装试运行阶段。
- **没有做真实故障注入**：弹窗不出现、解析超时、预览多行等异常路径由单元测试覆盖
  （假件驱动），未在真实站点上故意制造故障。理由：那需要改动生产页面状态或反复登录，
  收益低于风险。
- **没有验证"数量为小数/异常品牌"在真实 ERP 上的表现**：同理，属于故意构造非法输入，
  由 `_strict_positive_int` 与 `build_paste_input` 的单元测试与源码契约保证。
