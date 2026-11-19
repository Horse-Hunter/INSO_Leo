"""Owner-readable projection of one runtime fault.

The product must explain a failure where the Owner already looks: the
"异常与通知" page.  Everything here is derived from evidence the runtime already
owns -- the site-outage clock, the stop reason, the exception class name and the
existing incident row -- so the page can never invent a second truth.

Two rules are absolute:

* Nothing but a stable ``reason_code`` and a Python exception *class name* is
  projected from an exception.  Messages can carry URLs, sheet titles or customer
  text, so they are never read here.
* A fault that was not confirmed stays ``UNCONFIRMED`` in the wording.  The page
  says "原因未确认" instead of guessing a cause.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime

UNCONFIRMED = "尚未确认"

# code -> (标题, 具体原因（可安全展示）, 建议操作)
_CATALOGUE: dict[str, tuple[str, str, str]] = {
    "SHEETS_READ_UNAVAILABLE": (
        "Google Sheets 数据读取失败",
        "读取源表格时连接中断或返回无效响应，程序已按上限重试仍未成功。",
        "1) 确认本机能直接打开该 Google 表格；2) 检查网络/VPN 是否稳定；3) 恢复后重新开始。",
    ),
    "SHEETS_SCHEMA_UNAVAILABLE": (
        "Google Sheets 表格结构无法确认",
        "源表格的表头块与约定不一致，程序拒绝按猜测的列读取。",
        "1) 核对表头行是否仍为 STATUS/WHAT/CLASS/WHO/MPN/MFR/Qty；2) 不要改动其他列顺序；3) 改好后重新开始。",
    ),
    "GOOGLE_SHEETS_UNAVAILABLE": (
        "Google Sheets 不可用",
        "表格读取或写入未能确认，可能是网络、授权或服务端问题。",
        "1) 确认能打开表格；2) 确认服务账号仍被授权；3) 恢复后重新开始，不要重复提交。",
    ),
    "GOOGLE_AUTHENTICATION_REQUIRED": (
        "Google 授权被拒绝",
        "Google 拒绝了当前凭据，程序停止业务以免反复失败。",
        "1) 检查服务账号是否还有该表格的访问权；2) 重新授权后重新开始。",
    ),
    "GOOGLE_READ_RETRY_EXHAUSTED": (
        "Google 表格读取重试用尽",
        "本轮读取已到重试上限，程序等待下一轮，不会永久停摆。",
        "可先观察下一轮是否自行恢复；连续多轮仍失败再检查网络与授权。",
    ),
    "GOOGLE_OUTAGE_THREE_HOURS": (
        "Google 表格连续三小时未恢复",
        "同一读取故障连续三小时未恢复，已按规则停止共享业务。",
        "1) 先确认网络与表格可访问；2) 确认后再重新开始；3) 不要重复提交采购。",
    ),
    "GOOGLE_WAITING_RECOVERY": (
        "Google 表格等待恢复",
        ("表格读取失败，程序等待下一轮自动重试。注意：浏览器能打开表格，不等于本程序能连上——"
         "程序读取表格走的是 Google 接口，需要系统代理/VPN 可用（已按系统代理设置连接）。"),
        ("1) 确认 Clash/iKuuu 等代理或 VPN 处于开启状态（浏览器能开表格即可对照）；"
         "2) 程序会自动按系统代理重试，无需重启；3) 若代理已开仍持续失败，把本页故障码与日志交给技术处理。"),
    ),
    "GOOGLE_PAGE_UNRESPONSIVE": (
        "表格页面通道没有回应（不是表格不可用）",
        ("程序向共享 Chrome 的表格页面发出操作后没有收到任何回答：Chrome 与表格本身通常是好的，"
         "失效的是程序自己持有的那条页面连接，常见于 Chrome 窗口被关闭、标签页被重建或会话被回收之后。"),
        ("通常无需操作：程序已自动断开并重连自己的浏览器连接，下一轮会继续读取。"
         "若同一故障连续多轮出现，重启程序即可恢复；Chrome 与已保存数据不受影响，不要新建登录环境。"),
    ),
    "BROWSER_WAITING_RECOVERY": (
        "浏览器（CDP）连接未就绪",
        "程序无法连接到已授权的 Chrome 会话，本轮业务推迟到下一轮。",
        "1) 确认授权 Chrome 仍在运行；2) 关闭无响应标签页；3) 不要关闭该 Chrome 或换用新配置。",
    ),
    "CDP_RECONNECT_EXHAUSTED": (
        "浏览器（CDP）重连失败",
        "多次尝试连接已授权的 Chrome 均失败，业务已停止。",
        "1) 确认 Chrome 仍在运行且不是无响应状态；2) 关闭卡住的标签页；3) 重新开始。",
    ),
    "CDP_SESSION_UNAVAILABLE": (
        "浏览器（CDP）会话不可用",
        "共享浏览器会话不可用，涉及浏览器的业务无法开始。",
        "确认授权 Chrome 正常后重新开始；不要另开新的登录环境。",
    ),
    "CDP_PAGE_OWNERSHIP_UNCONFIRMED": (
        "Chrome 页面归属无法确认",
        ("程序在操作某个标签页前重新核对它的身份（targetId）没有通过：可能是该标签页已被关闭或重建、"
         "CDP 会话中途断开，或协议查询超时。为避免操作到不属于程序的页面，程序已停止。"),
        ("1) 保留当前 Chrome，不要新建登录环境，也不要关闭程序不认识的标签页；"
         "2) 确认该 Chrome 仍能正常打开网页；3) 重新开始，程序会重建专属页面并重新核对身份；"
         "若反复出现，把本页故障码与日志交给技术处理。"),
    ),
    "CDP_PAGE_CREATION_UNCONFIRMED": (
        "Chrome 页面创建结果无法确认",
        "程序请求新建标签页后没有拿到可用的 targetId，无法确认页面是否已创建。",
        "不要手工补开页面；重新开始会让程序重新创建并核对；反复出现请保留日志。",
    ),
    "CDP_PAGE_CLEANUP_UNCONFIRMED": (
        "Chrome 页面释放失败",
        "程序关闭或释放专属标签页时失败，无法确认页面资源已归还。",
        "保留当前 Chrome 现场，重新开始；不要手工关闭未知用途的标签页。",
    ),
    "INSO_AUTHENTICATION_REQUIRED": (
        "INSO 需要人工登录/验证",
        "ERP 会话失效或需要验证码，只有本人能完成。",
        "1) 在已授权的 Chrome 中完成 INSO 登录/验证；2) 回到程序重新开始。",
    ),
    "INSO_WAITING_RECOVERY": (
        "INSO 等待恢复",
        "本轮 INSO 操作未成功，程序等待下一轮。",
        "若需要验证码请先完成登录；程序不会自动重复提交。",
    ),
    "INSO_OUTAGE_THREE_HOURS": (
        "INSO 连续三小时未恢复",
        "INSO 相关操作连续三小时未恢复，已停止共享业务。",
        "先恢复 INSO 登录与网站可用性，再重新开始。",
    ),
    "IC_NET_UNAVAILABLE": (
        "IC.net 不可用",
        "IC.net 查询失败，相关调研无法继续。",
        "确认站点可访问后重新开始；不要重复提交。",
    ),
    "IC_NET_WAITING_RECOVERY": (
        "IC.net 等待恢复",
        "本轮 IC.net 未成功，程序等待下一轮。",
        "若持续失败，先确认站点可正常打开。",
    ),
    "IC_NET_OUTAGE_THREE_HOURS": (
        "IC.net 连续三小时未恢复",
        "IC.net 连续三小时不可用，已停止共享业务。",
        "确认站点恢复后重新开始。",
    ),
    "WORKFLOW_LEDGER_UNAVAILABLE": (
        "本地订单台账不可用",
        "程序无法读写本地业务台账，为避免误操作已停止。",
        "1) 检查磁盘是否可写、文件是否被占用；2) 不要删除台账文件；3) 处理后再重新开始。",
    ),
    "PROGRAM_OPERATION_STALLED": (
        "业务长时间没有进展",
        "程序检测到业务停滞，没有可用的进展证据，已安全停止。",
        "查看运行记录确认停在哪一步；保留现场后重新开始。",
    ),
    "GOOGLE_WRITE_SETTLEMENT_UNCONFIRMED": (
        "Google 写入结果未确认",
        "写入请求可能已送达但回执不可读，程序不会自动重试，以免重复写。",
        "先人工核对该行当前内容，再决定是否重做；不要直接重发。",
    ),
    "PROGRAM_SAFETY_PAUSED": (
        "自动业务安全暂停",
        "运行过程中出现未预期的内部故障，程序已停止自动业务以避免错误操作。",
        "按下方“具体原因”的故障代码排查；无法确认时保留现场并交给技术处理。",
    ),
    "V12_INTERNAL_FAILURE": (
        "程序内部故障",
        "内部操作未能正常完成，具体原因未能归类。",
        "保留现场（数据库与日志）后交给技术处理；不要重复提交采购或报价。",
    ),
}

# Modules that are paused only because a shared dependency stopped.  They must
# never be presented as separate faults.
SHARED_DEPENDENT_MODULES = {
    "Google Sheets": ("询价采购", "报价跟进", "目标价调研"),
    "INSO": ("询价采购", "报价跟进"),
    "Browser/CDP": ("询价采购", "报价跟进", "目标价调研"),
    "IC.net": ("目标价调研",),
    "汇率网站": ("目标价调研",),
}


def describe(reason: str) -> tuple[str, str, str]:
    """Return (title, confirmed cause, next action) for a stable reason code."""

    known = _CATALOGUE.get(reason)
    if known is not None:
        return known
    return (
        f"未分类故障（{reason or 'UNKNOWN'}）",
        f"程序记录到故障代码 {reason or 'UNKNOWN'}，但该代码没有已确认的中文说明。",
        "保留现场（日志与数据库）后交给技术处理；不要重复提交采购或报价。",
    )


@dataclass(frozen=True, slots=True)
class FaultDiagnostic:
    """One Owner-facing fault record.  Stable, JSON-safe and secret-free."""

    code: str
    title: str
    cause: str
    action: str
    first_seen: str | None = None
    last_seen: str | None = None
    occurrences: int = 1
    site: str | None = None
    stage: str | None = None
    cause_class: str | None = None
    phase: str = UNCONFIRMED
    impact: str = ""
    knock_on: tuple[str, ...] = ()
    related_modules: tuple[str, ...] = ()
    escalation: str = ""
    next_retry_at: str | None = None
    recovered_at: str | None = None
    evidence: str = ""
    uncertainty: str = ""
    external_effect: str = UNCONFIRMED
    extra: dict = field(default_factory=dict)

    @property
    def active(self) -> bool:
        return self.recovered_at is None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["knock_on"] = list(self.knock_on)
        data["related_modules"] = list(self.related_modules)
        return data

    @classmethod
    def from_dict(cls, data) -> FaultDiagnostic:
        if not isinstance(data, dict):
            raise TypeError("FAULT_DIAGNOSTIC_UNCONFIRMED")
        allowed = {f for f in cls.__dataclass_fields__}
        clean = {k: v for k, v in data.items() if k in allowed}
        clean["knock_on"] = tuple(clean.get("knock_on") or ())
        clean["related_modules"] = tuple(clean.get("related_modules") or ())
        clean["code"] = str(clean.get("code") or "UNKNOWN")
        title, cause, action = describe(clean["code"])
        stored_title = str(clean.get("title") or "")
        if not stored_title or stored_title.startswith("未分类故障"):
            # A record written before the catalogue learned this code keeps the
            # old placeholder. Re-derive the wording; everything else is kept.
            clean["title"], clean["cause"], clean["action"] = title, cause, action
        else:
            clean["title"] = stored_title
            clean["cause"] = str(clean.get("cause") or cause)
            clean["action"] = str(clean.get("action") or action)
        return cls(**clean)


def _iso(value) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str) and value:
        return value
    return None


def build_diagnostic(
    reason: str,
    *,
    site: str | None = None,
    stage: str | None = None,
    cause_class: str | None = None,
    first_seen=None,
    last_seen=None,
    occurrences: int = 1,
    escalation: str = "",
    next_retry_at=None,
    recovered_at=None,
    event_id: str = "",
    external_effect: str = UNCONFIRMED,
    uncertainty: str = "",
    impact: str = "",
    deferred: bool = False,
    log_hint: str = "runtime/logs/INSO_V1.3.log",
) -> FaultDiagnostic:
    """Build the record from the values the runtime actually measured.

    ``deferred`` marks a fault that only postponed work: nothing was stopped, so
    it must not claim the dependent modules were paused.
    """

    title, cause, action = describe(reason)
    knock_on = () if deferred else SHARED_DEPENDENT_MODULES.get(site or "", ())
    if deferred:
        impact = impact or "本轮只推迟了这一步，没有停止任何模块；其他任务照常运行。"
        phase = escalation or f"{site or '依赖'}等待下一轮"
    elif site and knock_on:
        impact = impact or f"本次停止了 {('、'.join(knock_on))}；三者的暂停由 {site} 同一原因引起。"
        phase = escalation or f"{site}未恢复，业务已停止"
    else:
        impact = impact or ("本次停止了自动业务；具体范围以下方模块状态为准。"
                           if not site else f"本次停止了与 {site} 相关的业务。")
        phase = escalation or ("已停止共享业务" if not site else f"{site}未恢复")
    if cause_class:
        cause = f"{cause}（异常类型 {cause_class}）"
    return FaultDiagnostic(
        code=reason or "UNKNOWN",
        title=title,
        cause=cause,
        action=action,
        first_seen=_iso(first_seen),
        last_seen=_iso(last_seen),
        occurrences=max(1, int(occurrences)),
        site=site,
        stage=stage,
        cause_class=cause_class,
        phase=phase,
        impact=impact,
        knock_on=tuple(knock_on),
        related_modules=tuple(knock_on) or ((site,) if site else ()),
        escalation=escalation,
        next_retry_at=_iso(next_retry_at),
        recovered_at=_iso(recovered_at),
        evidence="；".join(part for part in (event_id, log_hint) if part),
        uncertainty=uncertainty,
        external_effect=external_effect,
    )
