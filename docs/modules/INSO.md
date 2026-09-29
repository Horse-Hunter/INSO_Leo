# INSO 模块

本文件只保存当前有效的 INSO runtime、重复检查、采购草稿和 Save 边界；历史 discovery 已由 Git 保存，不在这里重复。

## Shared runtime

- Production browser：Chrome only；launcher 使用 approved dedicated profile + CDP `127.0.0.1:9222`。
- Credential：只通过 Core Vault，Site ID = `yingsuo.alperp.cn`。
- `ensure_inso_authenticated()` 是共享 ordinary recovery 能力。所有 INSO 功能复用它，不自行重写浏览器步骤。
- 已有唯一 authenticated shell 时直接复用；普通 `/login.aspx` 时在同一明确页面完成一次恢复。
- 已验证 ordinary controls：
  - account：`input#personname:visible`
  - password：`input#password:visible`
  - submit：精确 `get_by_text("登录", exact=True)`
- account/password 都必须 fill 后 read-back 确认非空，才允许单次 submit；不得记录或输出 secret value。
- 成功只以唯一 authenticated shell 为准：INSO HTTPS origin + list frame `/InnerEnquiry/YeWuXJ/List.aspx` + `#DetailFieldValue`、`button#select_btns`、`#_id_dg`。
- CAPTCHA / OTP / device verification → `MANUAL_VERIFICATION_REQUIRED`；不得绕过。
- reused Owner browser/page 不关闭；app-owned 资源只按既有 ownership lifecycle 清理。

普通 Chrome/CDP/session/ordinary recovery 问题属于共享 runtime 技术问题，不是 Owner blocker。

## Duplicate history

- `PlaywrightDuplicateHistoryPage` 复用 authenticated shell 的 native search/serializer，使用 exact query settlement contract；不另造第二套请求协议。
- 业务窗口：rolling 168h，Asia/Shanghai，下界 inclusive。
- MPN：`dup-mpn-v1` = NFKC + outer trim + ASCII uppercase；内部标点、分隔符、空格保留；禁止 fuzzy。
- 只比较同型号最新记录；数量只比较/展示，不参与 MPN 匹配。
- 同 timestamp 无已证明稳定排序时 → `AMBIGUOUS`。
- BillID 是稳定 list→detail identity。
- creator 当前业务结论：`CREATOR_NOT_EXPOSED_BY_INSO`；采购员/业务员不能替代 creator。
- quote/currency contract 已确认；具体选价业务仍归 Research。

## Purchase draft

业务动作使用明确 frame/control：

- list frame：`iframe#iframe_YeWuXJ_frame`
- 新增：`button#product_add_`
- parent form：`iframe#winIframealert_enquiry`
- customer：`input#CompanyName`
- quotation type：`input#ImpValueF`
- purchaser：`input#UserName_text`
- AI input：`textarea#paste-area`
- AI recognition：`button#ai-recognize`
- parent PartNo：唯一 `#_id_dg td[data-field="PartNo"]` cell
- parent Brand：唯一 `#_id_dg td[data-field="Brand"]` cell
- parent Qty：唯一 `#_id_dg td[data-field="Qty"]` cell

每个 parent field 必须先双击唯一 cell，随后只接受唯一、可见、enabled 的 transient `input` editor；fill 后立即从 editor 或已提交 cell read-back。AI preview 只接受唯一 row；MPN 按 `ai-mpn-v1` exact、Brand trim-only exact、Qty positive integer exact。缺失、多重、不可见、不可用、错误 frame/origin 或 mismatch 一律 fail closed。

## Save / reconciliation

- 唯一可能授权的最终动作：`button#btnSave`（保存数据）。
- `#btnSave2`（保存并发送）和 `#bcSend`（发送）没有允许的 dispatch path，永久禁止。
- Production Write Gate 默认 CLOSED。
- Save 前必须先持久化 `UNKNOWN_WRITE_OUTCOME`；Save 结果未知时绝不自动再次点击。
- `PlaywrightReadOnlySaveReconciler` 复用 exact history + BillID/PENO/detail read-back；在确认结果前必须证明 candidate set 完整：native response、cache、DOM 一致，分页总数等于 response row count，且为首页单页结果。不能证明完整性时为 `UNKNOWN`：
  - 唯一候选 + stable id + MPN/Brand/Qty exact → `CONFIRMED_SAVED`
  - authoritative settled query + 0 candidate → `CONFIRMED_NOT_SAVED`
  - 多候选 → `AMBIGUOUS`
  - 其余 → `UNKNOWN`
- 当前阶段与 Gate 状态只看 `control-room/COORDINATION.md` 与对应 RFQ Task Spec。
