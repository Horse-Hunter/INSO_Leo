# RFQ-025 — 页面嗅探证据（脱敏，2026-11-21）

分两段采集，务必分清：

- **第 1–6 节：只读采集**（V1.6 运行中）。在 Executor 自建的临时标签页内完成，采集后立即关闭；
  未登录、未提交任何表单、未点击 `导入`、未点击 `保存数据`、未发送任何采购。
- **第 7–8 节：真实链路实测**（Owner 停机并授权后）。用真实生产业务流程完整跑通一遍，
  包括 `导入` 与 `保存数据`；**始终未点 `保存` / `保存并发送`**，未产生任何服务端单据。

**脱敏规则：** 不记录 Cookie、`__VIEWSTATE`、`__VIEWSTATEGENERATOR`、`erp_token`、认证码、客户资料。
下文只保留结构标识与客户端源码。

## 1. 生产现场（采集时点）

| 项 | 值 |
|---|---|
| EXE SHA256 | `9a0cb3d3d2101745deb014d4fa0f4c66072dc0da295923aa927f0e0387db2710` |
| 进程 | PID 56032 / 75380，2026-11-20 14:50:55 启动，采集期间未重启 |
| CDP | `127.0.0.1:9222`，Chrome/156.0.8078.81，单 profile |
| 业务 | 10:43:07–10:43:10 inquiry 轮次 `completed`，3.4 s；`fatal.log` 0 字节 |
| 采集期新增故障 | 无（日志内唯一 `runtime fault` 仍是 2026-11-20 14:29 已修的那条） |

## 2. 会话边界（决定了本轮只做到"静态 + 只读 DOM"）

- 共享 profile 内仍有 `erp_token` / `erp_current_login_v1` / `erp_identity_context_v1` 等 Cookie。
- 但**新建文档的认证能力不等同于业务外壳**：
  - `GET /` → `login.aspx?t=reset`
  - `GET /skins/etaoerp//InnerEnquiry/YeWuXJ/List.aspx` → 200，标题 `1.业务询价`（已认证）
  - `GET /skins/etaoerp/product/Import.aspx`、`/skins/etaoerp/sale/Enquiry/Bill.aspx` → 200，正常渲染
- 也就是说：**弹窗页与单据页可直接只读加载，但 `windows()` / `main_alertbox()` 外壳只在登录后的首页存在**。
  实测：在独立列表页点 `#product_add_`（`AddBill()`）与 `#product_import_`（`product_import()`）都无任何反应，
  原因是这两页上的 `windows()` 定义为 `function windows(a,b,c,d,e,f,g){parent.windows(...)}`，
  页顶时 `parent === window` 自调用，栈溢出被吞掉，弹窗永不产生。
- 结论（第 1 轮）：要真正点通"粘贴 → 导入 → 预览 → 保存数据"，必须先登录建立外壳。
  第 1 轮**未登录**（V1.6 正在运行，登录会覆盖共享 profile 的 `erp_token`，属干扰生产登录状态）。
  **第 2 轮在 Owner 停机并明确授权后已完成登录与全链路实测，见第 7 节。**

## 3. 粘贴按钮（步骤 1）

表单页 `GET /skins/etaoerp/sale/Enquiry/Bill.aspx` → 标题 `客临时询价`，`BillID` 为空（仅 GET，未建单）。

工具栏（同一 `iframe#winIframealert_enquiry` 内、同一按钮行）实际控件：

| id | 文本 | onclick |
|---|---|---|
| `btnAdd` | 新增 | `bill_add()` |
| `btnSave` | 保存 | `bill_save_auto()` |
| `btnSave2` | 保存并发送 | `bill_save_send()` |
| `btnSave3` | 智能分配 | `bill_save_gonghai()` |
| `btnCancel` | 取消 | `bill_cancel()` |
| **`product_import_`** | **粘贴** | **`product_import()`** |
| **`ai_import_`** | **AI录单** | **`ai_import()`** |

- 目标控件：`iframe#winIframealert_enquiry` → `button#product_import_`，文本恰为 `粘贴`，唯一、可见、可用。
- 相邻的 `button#ai_import_`（`AI录单`）是**要替换掉的旧入口**，两者 id 不同、不会误点。
- 注意：`#product_import_` 这个 id 在**列表页**上文本是"导入"（批量导入），在**单据页**上文本是"粘贴"。
  同名不同语义，靠所属 frame 区分，不能只按 id 找。

### 两个入口的真实差异（本轮最重要的一条）

单据页 `product_import()`：

```js
function product_import(){
  if(!isDetailAdd()) return;
  returnSet('');
  windows('粘贴导入', 1050, 600,
          'product/Import.aspx?BillPage=' + BillPage + '&VendorID=' + $('#VendorID').val(),
          [ {'title':'导入','mtd':'pasteImport(0)','icon':'icon-save'},
            {'title':'保存数据','mtd':'pasteImport(1)','icon':'icon-save','disabled':'true'} ],
          function(){ appendRow() });
}
```

对照 `ai_import()`：

```js
function ai_import(){
  if(!isDetailAdd()) return;
  returnSet('');
  windows('AI智能录单', 1050, 600,
          'product/Import_ai.aspx?BillPage=' + BillPage + '&VendorID=' + $('#VendorID').val(),
          [ {'title':'保存数据','mtd':'pasteImport(0)','icon':'icon-save'} ],
          function(){ ai_appendRow() });
}
```

两者结构完全一致：同一个 `windows()`、同一尺寸、同一 `BillPage/VendorID` 查询、同一套"关窗回调把行交给父表单"
的模式。差别只有：内容页、按钮组、关窗回调（`appendRow` vs `ai_appendRow`）。

## 4. 粘贴页结构（步骤 2、3）

`GET /skins/etaoerp/product/Import.aspx?BillPage=Enquiry&VendorID=` → 标题 `粘贴导入`。

| 元素 | 值 |
|---|---|
| 标签页 | `ul#tabs` → `li#tabs_li1` 数据粘贴（默认选中）、`li#tabs_li2` 数据预览 |
| 面板 | `div#tabs_1`（粘贴）、`div#tabs_2`（预览） |
| 文本框 | `textarea#pasteData`（`name="pasteData"`） |
| 列分隔符 | `input#combox101` 值 `3`，显示 `竖线('|')` —— **默认已是竖线，无需每次设置** |
| 字段映射 | `input#cmb0..cmb24` + `#cmbN_text` 显示名 |
| 预览表格容器 | `div#dg_div`、`div#import_div`；`div#tabs_2` 内 `button#detail_add`(`dg_add()`)、`button#detail_del`(`dg_delete()`) |

字段映射默认值（列序即粘贴列序，前三位正是 Owner 要求）：

| 序 | 字段 | 中文 |
|---|---|---|
| 0 | `PartNo` | 型号 |
| 1 | `Qty` | 数量 |
| 2 | `Brand` | 品牌 |
| 3 | `Type` | 品名 |
| 4 | `ProductID` | 编码/型号 |
| 5 | `CusPartNo` | 客户型号 |
| 6 | `Pack` | 封装 |
| 7 | `DC` | 批号 |
| 8 | `MaterialNO` | 客户料号 |
| 9 | `StockQty` | 库存数量 |
| 10 | `realStockQty` | 实时库存 |
| 11 | `OfferPrice` | 未税报价 |
| 12 | `UPIncludeTax` | 含税报价 |
| 13 | `TargetPrice` | 客接受价 |
| 14 | `Amount` | 总金额 |
| 15–24 | `SPQ`/`SPQLow`/`MOQ`/`LT`/`NewOld`/`CusFeedBack`/`Descr2`/`bjMaterialNO`/`bjType`/`bjPartNo` | 标准包装/最小包装/起订量/货期/新旧程度/客户要求/备注/报价料号/报价品名/报价型号 |

→ `型号|数量|品牌` 与默认映射**同位同序**，不用改任何下拉，也不用改分隔符。
这同时说明：粘贴文本必须**严格三列**，第四列起会被当成品名/编码等字段。

## 5. 两个按钮的真实语义（步骤 3、4）

`product/Import.aspx` 内的 `pasteImport(imp, fun)`：

```js
function pasteImport(imp, fun) {
    var data = $("#pasteData").val();
    if (data.length == 0) { alert_warning('<b>警告：</b> 数据为空!'); return; }

    //保存
    if (imp == 1) {
        if (!importPreviewReady) {
            alert_warning('请先成功导入并预览数据，再保存数据。');
            return;
        }
        var DetailData = { "total": 0, "rows": table.cache['dg'] };
        returnSet(DetailData);
        windowsClose();
        return;
    }

    var fields = "";  for (var i = 0; i < fieldArray.length; i++) { fields += $("#cmb"+i).val() + ","; }
    ...
    var FenGeFu = $("#combox101").val();
    var TitleConfig = { data: data, fields: fields, fieldsText: fieldsText, FenGeFu: FenGeFu, imp: imp };

    importPreviewReady = false;
    windowsBtn_disab(2, true);
    $('#dg_div').empty();  $('#import_div').empty();
    $('#tabs').PageTab('add', '{"index":"1"}');

    //显示预处理区
    $.post("/services/product/import.ashx?action=PasteImport&VendorID=" + VendorID
           + "&BillPage=" + BillPage, { ... }, ...);
}
```

关窗回调：

```js
function appendRow() {
    var rows = returnGet();
    if (rows) { var that = layui.table.getThat('dg');
        for (var i = 0; i < rows.length; i++) {
            jQuery.each(rows[i], function (key, val) { that.updatecellVal(key, val, i); });
        } }
}
```

判定：

- **`保存数据`（`pasteImport(1)`）= 纯客户端。** 只有 `returnSet()` + `windowsClose()`，
  行数据来自 `table.cache['dg']`；随后关窗回调 `appendRow()` 把行写进父表单的 layui 表。
  没有 `$.post`、没有 AJAX、不返回 `BillID`、不发采购。与 `AI录单` 弹窗的"保存数据"属**同一语义类别**。
- **`导入`（`pasteImport(0)`）= 服务端解析。** `$.post('/services/product/import.ashx?action=PasteImport&...')`。
  这是"显示预处理区"的解析调用：它返回预览行、置 `importPreviewReady=true`、启用"保存数据"、切到"数据预览"标签。
  **数据预览不是本地算出来的**：`#dg_div` 初始为空，行来自这个 POST 的响应。
- **硬约束：** `保存数据` 有 `importPreviewReady` 闸门。没先跑过 `导入` 就点，只会弹
  "请先成功导入并预览数据，再保存数据。"，不会写入任何东西。这天然保证了"预览核对"不可能被绕过。

### 名称相同但语义不同的另一个弹窗（必须避开）

**列表页**的批量导入是另一个实现，`保存数据` 绑的是 `Import()`：

```js
function Import() {
    ...
    $.post(importService + "?action=Import", { ImportRequestId: importRequestId,
           DetailData: DetailData, ... }, function (data) {
        ...
        if (!data.BillID || data.isLogin == 'false') { alert_warning('未确认导入成功...'); return; }
        importCompleted = true;
        if (data.MsgUserID) parent.send_msg(...);
        windowsClose();
    }, "JSON") ...
}
```

它 `$.post()` 到 `action=Import`，要求服务端返回 `BillID`，并向同事发 IM 提醒 —— **会在服务端创建单据**。
本轮从未打开、从未点击该路径；V1.7 也不得使用它。区分依据：所属页 `innerenquiry/yewuxj/Import.aspx`
（列表批量，服务端建单）vs `product/Import.aspx`（单据内粘贴，纯客户端回填）。

## 6. 预览表格的读取方式（步骤 3 结论）

- 预览列 = `#cmbN_text` 的显示名顺序（型号、数量、品牌、品名、编码/型号、…）。
  这一列序与 `fieldsText` 一起随 POST 上送，服务端据此回渲染 `data.dg` 与行数据。
- `编码/型号` 由服务端按型号解析后回填（Owner 截图里 `TRJC476K016RRJ` → `P1463619` 即此）。
- **视觉截断 ≠ 数据截断**：Owner 截图 3 的 `TRJC476K01...` 是 layui 单元格宽度省略（CSS ellipsis），
  真实值在 `table.cache['dg'][i].PartNo` 与单元格数据里。程序核对必须读数据源，不能读渲染文本。
  本轮未能在真实弹窗内验证该 cache 的字段名（需登录，见第 2 节）。

## 7. 真实链路实测（2026-11-21 11:05 前后，Owner 停机并授权）

Owner 停止 V1.6 后，用真实生产业务流程完整跑了一遍，由程序写脚本执行、逐项记录。

一次会话内完成：`login.aspx?t=islogin` → 普通登录 → 首页外壳 → 业务询价菜单 →
`新增`（空草稿）→ 工具栏 `粘贴` → 弹窗 → 写入示例 → `导入` → 读预览 → `保存数据` → 读父表单行 →
`返回列表`（`goback()`）关闭，**全程未点 `保存` / `保存并发送`**。

### 7.1 弹窗与按钮的真实标识

| 元素 | 实测 |
|---|---|
| 弹窗 iframe | `#winIframe_dialog1` → `product/Import.aspx?BillPage=Enquiry&VendorID=&h=510` |
| `导入` | **`#win_btn__dialog11`**，初始可用 |
| `保存数据` | **`#win_btn__dialog12`**，**初始 `disabled=true`**，解析成功后变为可用 |
| `取消` | 无 id，`onclick="alertbox._close('_dialog1', 1)"` |
| 关窗 | 只把 dialog 置为隐藏；iframe 仍留在 DOM（与既有约定一致：判断"关了"要看可见性，不看存在） |

### 7.2 逐项实测结果

| 项 | 实测 |
|---|---|
| `新增` 是否建单 | **否**。`#BillID` 打开前后都为空，`BillNo` 为空；列表最新单号仍是 `XJ-261119-150055`，无 11-21 新单 |
| 输入回读 | `TRJC476K016RRJ\|200\|Kyocera AVX` 原样回读，未变形 |
| 分隔符 | `#combox101` = `3` / `竖线('|')`，默认即正确 |
| 字段映射 | `cmb0=型号`、`cmb1=数量`、`cmb2=品牌`、`cmb3=品名`、`cmb4=编码/型号` |
| `导入` 的网络行为 | **恰好一次 POST**：`/services/product/import.ashx?action=PasteImport&VendorID=0&BillPage=Enquiry` |
| 预览列（20 列） | 型号、数量、品牌、品名、编码/型号、客户型号、封装、批号、客户料号、库存数量、实时库存、未税报价、含税报价、客接受价、总金额、标准包装、最小包装、起订量、货期、新旧程度 |
| 预览数据（`layui.table.cache['dg']`） | `{"PartNo":"TRJC476K016RRJ","Qty":"200","Brand":"Kyocera AVX","ProductID":"P1463619", …}` |
| 型号是否逐字节保持 | **是**。cache 里 `PartNo` 与输入完全一致 |
| ERP 自动补充 | **是**。`ProductID` 由服务端解析为 `P1463619`（输入里没有这个值） |
| **`保存数据` 的网络行为** | **零个非 GET 请求**（实测，不是推断） |
| `保存数据` 后父表单 | 明细行已写入：cache 同上一行，界面单元格顺序 `P1463619`、`TRJC476K016RRJ`、`Kyocera AVX`、`200` |
| `保存数据` 后 `#BillID` | 仍为空 → 没有产生任何服务端单据 |
| 关窗 | `btnBack`（`goback()`）后表单不可见；未保存、未发送 |

### 7.3 对 V1.7 实现有影响的三个细节

1. **`Qty` 在缓存里是字符串** `"200"`，不是整数。核对时必须显式转 `int` 并校验 `> 0`，
   不能直接 `isinstance(..., int)`。
2. **可靠的等待条件**不要用固定睡眠：`导入` 之后应同时满足
   (a) `layui.table.cache['dg']` 行数 == 1（本流程一行）
   (b) `#win_btn__dialog12` 不再 `disabled`
   再读数据。任一不成立即 fail-closed，不点 `保存数据`。
3. **`保存数据` 前必须有 `importPreviewReady`**。ERP 自己会挡（"请先成功导入并预览数据，再保存数据。"），
   程序侧仍要自己先核对，不要把闸门当唯一下限。

## 8. 首轮未验证项 —— 已全部补齐

首轮因未登录而标记的六项，本轮实测结果：

| 首轮未验证项 | 现状态 |
|---|---|
| 真实 5 步点击链路 | **已验证**（完整跑通） |
| 弹窗按钮 DOM id 与禁用态 | **已验证**（`dialog11` / `dialog12`，后者初始禁用） |
| 预览取值路径 | **已验证**（`layui.table.cache['dg']`） |
| 型号是否逐字节保持 | **已验证**（是） |
| `appendRow()` 后父表单行值 | **已验证** |
| `import.ashx` 响应结构与副作用 | **已验证**：一次 POST，只做解析，不建单 |
