# Task: 任务中心默认新订单在前

status: complete
owner: Codex Executor
created: 2026-10-29

## problem / goal
Owner要求任务中心按新订单在前显示。当前默认保留本轮/TP/历史拼接顺序，未统一排序；1000条截断发生在排序前。

## scope / requirements
仅离线修改显示排序及必要的只读DTO接线。复用已有workflow_items.created_at，随原all_items查询返回，不新增数据库查询、字段或迁移。默认按首次入库时间倒序；重跑/状态变化不改订单新旧。无入库时刻的旧历史单在已知入库单之后按原处理时间倒序；完全无时间的独立TP/旧单末尾，固定ID稳定排序。不得用TP updated_at或来源行号伪造新旧。
统一合并后先排序再取最新1000；搜索/筛选/分页维持默认顺序，手动表头排序继续可用。

## non_scope
不修改业务处理顺序、权限/幂等、邮件、采购、报价、TP算法；不连接Chrome；初始仅离线修改。Owner随后明确授权：做完确认没问题直接打包覆盖运行。发布必须沿用原构建/安全停止正常退出/新鲜备份/仅程序文件替换/原CLI恢复，禁止Computer Use和强杀，不回滚账本。COMPUTER_USE_NOT_USED。

## acceptance / verification
- 新入库单在前；旧单重跑不前移；同时间稳定；缺失时间末尾。
- 混合模块及1000条截断保留最新单；筛选分页一致；手动排序保留。
- 只读入库时刻来自原持久数据，重启/状态更新不改变，无GUI线程数据库访问。
- 对应离线回归、ruff/diff；依据Owner追加授权完成受控构建安装，不宣布整体V1.6 PASS。

## reuse / execution
原WorkItem/WorkflowStateStore.all_items、Order、GUI纯state投影、WorkbenchView和Backend快照复用；唯一缺口是入库时间未进入显示DTO。追加可选只读时刻，原schema/业务调用不变。

## completion
complete — source and controlled release verified; original production business resumed.

## Owner release authorization
2026-10-29 Owner明确要求测试通过后直接打包覆盖运行，无额外源码复审门禁。Owner已确认本次从托盘正常退出；实际退出及锁仍须核验。旧生产59F1983...仅在最终完整回归通过后替换。

## Regression finding
首次最终全量3145PASS/1FAIL/1SKIP128.52秒，原7天规则bad-date测试发现新增WorkItem显示时间解析不能破坏原未知日期处理。复用原inquiry_intake_at的容错解析作为内部纯函数，未知日期仅显示None；新增三项回归，不弱化原7天保守跳过。

## Final exact-source verification / release
## 任务中心新订单优先：Owner授权发布（2026-10-29）

**BUSINESS_RUNNING。** Owner要求完成验证后直接打包覆盖运行；本次不新增CEO发布门禁，也不宣布整个V1.6 PASS。
应用源码`13ace48ad13ec43ea8b46698e3829af6620499b2`；src树`554906930b1b88ec424be534ca903137d8e22e67`；tests树`b1f586a710c1aece7c95812f238bfe708118d574`。
安装程序`D:/Program_Leo/INSO_Leo/dist/INSO_V1.6/INSO_V1.6.exe`，SHA256 **`00AD692EE9EB15969E0489D6D9D92CD30EE5492DC38E7DD159D48FEA1BEE3C79`**。

### 实际修改与验证
原任务中心将本轮/TP/Excel历史拼接且先截断再显示，未默认统一新旧。
复用原WorkItem/Store.all_items、原只读startup投影、Order、GUI纯state、原快照与差异刷新。
追加可选只读入库时刻，原已存在created_at随既有查询返回；无schema/迁移/N+1查询。
统一按首次入库倒序，重跑/状态更新不前移；同时间按固定身份稳定排序。
无入库时刻的旧历史按processed_at倒序放在已知入库之后；独立TP/旧行完全无时刻则末尾，不用updated_at或行号假造。
合并后先排再限1000；GUI默认、搜索、筛选和分页同序，手动表头排序继续可用。后台执行顺序/权限不改变。
源码及测试实际清单在新任务`tasks/2026-10-29-task-center-newest-first.md`；未重写业务、浏览器或调度。
首次全量3145PASS/1FAIL/1SKIP128.52秒，原坏日期测试发现显示读取不应使原未知年龄分支报账本错误；
抽取复用原inquiry_intake_at容错解析，新增坏/空/无时区日期回归，不弱化原年龄保守跳过。
最终专项**88PASS1.71秒**；最终完整**3149PASS/1SKIP128.26秒**；Ruff/diff通过。
只用合成数据/隔离数据库，原SMTP外发守卫有效；最终冻结模块117项全部等价，2875资产及RELEASE_SCAN_OK/self-check0通过。

### 真实替换和恢复
旧GUI88228由Owner安全停止/托盘退出，退出收据2026-10-29T07:02:55.501063+00:00 code0 normal。
原单实例锁独占备份/替换；新鲜59F1983程序2875文件回滚、自检及一致性SQLite备份通过：
`D:\Program_Leo\INSO_Leo\dist\release-backups\INSO_V1.6-task-center-sort-20261029T070809Z\program`。只换EXE/_internal，不恢复旧数据库。
替换后及原idle-self-check0后全部业务表一致；配置/Vault/runtime链接及目标不变，无迁移。
2026-10-29T07:09:03.3976885Z原CLI仅启动一次，GUI94416/原观察器96656；原锁存在、系统响应正常，15:09:07自然询价begin已确认。
历史121不可变命令、152SENT全文行、四TP任务/六TP-SENT不变；现有来源身份hold保留。
配置/900秒/120秒和三模块授权保持，仍单Owner+方案A，未开启双Actor；无测试订单、邮件或新CDP检查。
短测13点/121.813秒：主程序整机CPU0.27292%，RSS114.41～117.04MiB，
Private86.00～89.84MiB，句柄841～1058，线程12～18；GDI136/USER258。
不是长期无泄漏/整轮业务/真实指针GUI验收。当前业务继续；Google跨重启页累积属于既知独立缺口，本次不操作页面或临时修复。
自有stage已退休（2876文件/268032365字节）、五个本轮合成pytest目录及四个一次性CLI辅助脚本已退休；保留日志/清单/生产/新鲜回滚。
`COMPUTER_USE_NOT_USED`。仅CLI、原发布脚本、日志及原生进程计数器；无鼠标、键盘、截图控制。
