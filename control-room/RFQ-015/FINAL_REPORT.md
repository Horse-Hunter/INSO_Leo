# V1.4 已授权部署报告

Owner于2026-10-10确认Review完成，明确授权打包部署。
已审核业务来源：7a5728388fc14cd685521d520e23fbfa19536988。
分支：codex/v1-4-order-mail-inspection。
本次仅补齐打包版本、运行依赖与冻结诊断；src业务代码没有新增修改。

正式路径：D:/Program_Leo/INSO_Leo/dist/INSO_V1.4/INSO_V1.4.exe
桌面入口：C:/Users/Leo/Desktop/INSO_V1.4.lnk
EXE SHA256：1e3c70979410adc3ddd1e6207234bba3440f1b7b43eccd13740782c0179eb751
完整源码/发布记录HEAD由本任务完成消息提供（本文所在提交）。

## 打包与验证

- 复用canonical PyInstaller spec/build script/entry，扩展1.4版本。
- 在隔离build venv复用原发布依赖，并加入开发环境已用的pypdf6.10.0、tzdata2026.4。
  原其他worktree环境未修改；锁定依赖匹配，pip check PASS，没有新增业务依赖路径。
- 122项发布/GUI专项通过；完整safe/offline1848通过、1跳过；Ruff/diff PASS。
- generic staging package扫描PASS，不包含本机配置、DB、客户附件或Vault数据。
- 部署2875个资产逐一核对SHA256，均与候选相同。
- frozen --self-check PASS：GUI/Tcl、PDF解析、Asia/Shanghai时区。
- frozen --idle-self-check PASS：INSO_V1.4，已停止，询价/录单线程均未启动。
- frozen --diagnose-vault PASS：canonical Vault/PowerShell及IMAP凭据就绪。
- frozen --cdp-self-check PASS：已有唯一9222会话，单context；没有业务启动、tab清理。
- 正式程序已打开待命，没有代Owner点击询价或录单按钮。

## 运行数据与回退

- V1.4是独立正式目录；旧V1.3/V1.2 EXE及_internal保留，不覆盖。
- 本机复制现有配置，台账/client-secret/Research输出的相对路径解析为原位置，
  因此保留现有业务历史，不创建或迁移新的生产workflow台账。
- Credential Vault/OAuth缓存及固定Chrome profile继续使用原位置。
- V1.4本机完成记录/隔离通知outbox以SQLite只读backup快照保留；完成记录数量一致。
- 4396项受保护旧资产/配置/台账/缓存文件SHA256核对，0变化。
- 旧正式版本和桌面入口保留作回退；共享单实例guard避免两版本同时占用台账。
  回退需要先退出V1.4再打开旧V1.3，不能同时运行两个版本。
- 候选及部署manifest保存在本机ignored build/.tmp；未把客户数据或runtime提交Git。

没有生产workflowDB/GoogleSheets写入、真实SMTP、销售订单保存/审核、采购/报价业务重跑。
部署只验证冻结环境、idle GUI和连接/凭据就绪；业务验收仍由Owner按钮触发，
不把这些自检描述成新一轮真实订单或询价全部成功。
