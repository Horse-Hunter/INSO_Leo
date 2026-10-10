"""Bounded IMAP discovery. Raw data never leaves this module or touches disk."""
from __future__ import annotations

import imaplib
import re
import ssl
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from io import BytesIO
from zipfile import ZipFile

from src.core import CredentialError, get_login

ACCOUNT = "linan229@qq.com"
HOST = "imap.qq.com"
PREFIX = "订单录单"
MAX_BYTES = 20 * 1024 * 1024
MAX_CELLS = 100_000
LABELS = frozenset({
    "合同号", "合同编号", "订单号", "客户", "客户名称", "客户信息", "客户编号",
    "公司名称", "地址", "电话", "联系人", "型号", "品牌", "数量", "价格",
    "单价", "金额", "总价", "交期", "交货日期", "交货期", "产品名称",
    "序号", "规格", "单位", "备注", "含税单价", "税率", "销售合同",
    "购销合同", "采购合同", "产品型号", "物料编码", "料号", "签订日期",
    "买方", "卖方", "需方", "供方", "购方", "销方", "品名", "厂牌",
    "规格型号", "交货时间", "付款方式", "收货地址", "含税", "小计", "合计",
})
ENGLISH_LABELS = frozenset({"SALES CONTRACT", "PURCHASE ORDER", "CONTRACT NO", "CONTRACT NUMBER", "CONTRACT", "DATE", "BUYER", "SELLER", "CUSTOMER", "ADDRESS", "TEL", "PHONE", "CONTACT", "ITEM", "DESCRIPTION", "PART NO", "PART NUMBER", "PART", "MODEL", "BRAND", "MANUFACTURER", "MFG", "QTY", "QUANTITY", "UNIT PRICE", "PRICE", "AMOUNT", "TOTAL", "DELIVERY", "LEAD TIME", "L/T", "PAYMENT", "TERMS", "PRODUCT", "CURRENCY", "USD", "REMARK", "REMARKS", "SHIP TO", "SHIPPING", "UNIT", "P/N", "NO.", "NO", "MPN", "CONDITION", "PACKING", "PACKAGING", "PACKAGE", "D/C", "DC", "COUNTRY OF ORIGIN", "SALES", "S/C", "P/O"})
MIMES = frozenset({"application/pdf", "application/octet-stream",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"})


@dataclass(frozen=True)
class InspectionReport:
    """Only sanitized, bounded display text crosses the public boundary."""
    status: str
    text: str
    matched: int = 0
    connected: bool = False
    flags_unchanged: bool | None = None


def subject_shape(subject: str) -> str:
    # No customer/contract token is copied, even Chinese or arbitrary suffixes.
    tail = subject[len(PREFIX):]
    parts = re.split(r"([\s:：_\-—/()（）\[\]【】]+)", tail[:200])
    return PREFIX + "".join(
        part if re.fullmatch(r"[\s:：_\-—/()（）\[\]【】]+", part or "x")
        else "[文本/编号]" if part else "" for part in parts
    )


def _date(value):
    try:
        return parsedate_to_datetime(str(value)).isoformat()
    except (ValueError, TypeError, OverflowError):
        return "UNKNOWN"


def _ok(response):
    status, data = response
    if status != "OK":
        raise ValueError("IMAP_OPERATION_FAILED")
    return data


def _fetch(client, uid, fields):
    data = _ok(client.uid("fetch", uid, fields))
    metadata = b" ".join(item[0] if isinstance(item, tuple) else item
                         for item in data if isinstance(item, (tuple, bytes)))
    returned = re.search(rb"\bUID (\d+)\b", metadata)
    flags = re.search(rb"\bFLAGS \(([^)]*)\)", metadata)
    if returned is None or returned[1] != uid or flags is None:
        raise ValueError("IMAP_METADATA_UNCONFIRMED")
    flag_set = frozenset(flags[1].split())
    literals = [item[1] for item in data if isinstance(item, tuple)]
    return metadata, flag_set, b"".join(literals)


def _excel(payload, suffix):
    if suffix == ".xls":
        return ["Excel：xls；当前没有旧格式解析器，sheet/字段/特殊结构 UNKNOWN。"]
    from openpyxl import load_workbook
    with ZipFile(BytesIO(payload)) as archive:
        if sum(i.file_size for i in archive.infolist()) > MAX_BYTES * 4:
            return ["Excel：解压大小超出检查上限，结构 UNKNOWN。"]
    workbook = load_workbook(BytesIO(payload), data_only=False, keep_links=False)
    try:
        lines = [f"Excel：{suffix}；{len(workbook.worksheets)} 个 sheet。"]
        for number, sheet in enumerate(workbook.worksheets, 1):
            safe_name = sheet.title if re.fullmatch(r"Sheet\d*|工作表\d*", sheet.title) else sheet.title if sheet.title in LABELS or sheet.title.upper() in ENGLISH_LABELS else "[名称已脱敏]"
            lines.append(f"sheet {number} {safe_name}：区域 {sheet.calculate_dimension()}；状态 {sheet.sheet_state}。")
            if sheet.max_row * sheet.max_column > MAX_CELLS:
                lines.append("区域超出检查上限，字段/公式 UNKNOWN。")
                continue
            labels, occupied_rows, formulas = [], [], 0
            for row in sheet.iter_rows():
                if any(cell.value is not None for cell in row):
                    occupied_rows.append(row[0].row)
                for cell in row:
                    formulas += cell.data_type == "f"
                    if isinstance(cell.value, str):
                        compact = re.sub(r"\s+", "", cell.value)
                        # Label vocabulary only, never copy values/combined customer text.
                        found = sorted(label for label in LABELS if label in compact)
                        labels.extend(f"{label}@{cell.coordinate}" for label in found)
                        normalized = re.sub(r"[._:：]+", " ", cell.value.upper())
                        normalized = re.sub(r"\s+", " ", normalized).strip()
                        found_en = sorted(label for label in ENGLISH_LABELS
                                          if re.search(r"(?<![A-Z])" + re.escape(label) + r"(?![A-Z])", normalized))
                        labels.extend(f"{label}@{cell.coordinate}" for label in found_en)
            lines.append("有值单元格：" + ", ".join(
                cell.coordinate + ("(公式)" if cell.data_type == "f" else "(文本)" if isinstance(cell.value, str) else "(数值/日期)")
                for row in sheet.iter_rows() for cell in row if cell.value is not None
            )[:3000])
            lines.append("字段标题线索（词汇命中，不代表字段映射）：" + ("、".join(labels[:80]) or "未识别标准标题，UNKNOWN"))
            lines.append(f"有值行数 {len(occupied_rows)}；公式 {formulas}；合并区域 "
                         + (", ".join(str(r) for r in list(sheet.merged_cells.ranges)[:30]) or "无")
                         + f"；隐藏行 {sum(bool(d.hidden) for d in sheet.row_dimensions.values())}"
                         + f"；隐藏列 {sum(bool(d.hidden) for d in sheet.column_dimensions.values())}。")
        lines.append("一订单/多料号：需结合数据区域人工确认；尚未建立业务字段映射。")
        return lines
    finally:
        workbook.close()


def _pdf(payload):
    if not payload.startswith(b"%PDF-"):
        return ["PDF：文件签名异常，正常性/页数/加密 UNKNOWN。"]
    try:
        from pypdf import PdfReader
    except ImportError:
        return ["PDF：签名正常；本机未配置页数解析器，完整正常性/页数/加密 UNKNOWN。"]
    reader = PdfReader(BytesIO(payload), strict=True)
    encrypted = reader.is_encrypted
    pages = "UNKNOWN" if encrypted else str(len(reader.pages))
    terms = set()
    if not encrypted:
        for page in reader.pages[:2]:
            text = (page.extract_text() or "").upper()
            terms.update(term for term in ("CONTRACT", "BUYER", "SELLER", "UNIT PRICE", "合同", "买方", "卖方") if term in text)
    contract = "有合同结构线索（不是法律有效性判断）" if len(terms) >= 2 else "UNKNOWN（未发现足够文本线索）"
    return [f"PDF：解析正常；页数 {pages}；加密 {'是' if encrypted else '否'}；{contract}。"]


def describe_message(message, metadata):
    subject = str(message.get("Subject", ""))
    internal = re.search(rb'INTERNALDATE "([^"]*)"', metadata)
    received = _date(internal[1].decode("ascii") if internal else None)
    body_types = sorted({part.get_content_type() for part in message.walk()
                         if not part.get_filename() and part.get_content_type() in {"text/plain", "text/html"}})
    attachments = [part for part in message.walk() if not part.is_multipart()
                   and (part.get_filename() or part.get_content_disposition() == "attachment")]
    stems = [str(part.get_filename() or "").rsplit(".", 1)[0] for part in attachments]
    lines = [f"标题结构：{subject_shape(subject)}",
             "合同号稳定提取：UNKNOWN（仅观察结构，未定义提取规则）。",
             f"发件时间 {_date(message.get('Date'))}；收件时间 {received}（IMAP INTERNALDATE）。",
             (f"发件人 {'存在，已脱敏' if message.get('From') else 'UNKNOWN'}；"
             f"Message-ID {'存在，已脱敏' if message.get('Message-ID') else 'UNKNOWN'}；IMAP UID 已确认，已脱敏。"),
             f"正文类型：{', '.join(body_types) or 'UNKNOWN'}；附件 {len(attachments)} 个。"]
    if len(stems) == 2:
        lines.append("两附件文件名主体" + ("相同" if stems[0] == stems[1] else "不同") + "（具体文件名已脱敏）。")
    candidates = re.findall(r"(?<![A-Za-z0-9])[A-Za-z]{1,10}[-_]?\d{4,}[A-Za-z0-9_-]*", subject)
    lines.append(f"标题中字母+数字编号候选 {len(candidates)} 个；具体编号已脱敏。")
    for number, part in enumerate(attachments[:20], 1):
        filename = str(part.get_filename() or "")
        suffix = next((s for s in (".xlsx", ".xls", ".pdf", ".xlsm") if filename.lower().endswith(s)), "其他")
        mime = part.get_content_type()
        safe_mime = mime if mime in MIMES else "其他（已脱敏）"
        payload = part.get_payload(decode=True) or b""
        lines.append(f"附件 {number}：[文件名已脱敏]{suffix}；MIME {safe_mime}；大小 {len(payload)} bytes。")
        try:
            if suffix in {".xlsx", ".xls", ".xlsm"}:
                lines.extend(_excel(payload, suffix))
                if suffix != ".xls" and candidates:
                    from openpyxl import load_workbook
                    wb = load_workbook(BytesIO(payload), data_only=False, keep_links=False)
                    try:
                        locations = [f"sheet {i} {cell.coordinate}" for i, ws in enumerate(wb.worksheets, 1)
                                     if ws.max_row * ws.max_column <= MAX_CELLS
                                     for row in ws.iter_rows() for cell in row
                                     if isinstance(cell.value, str) and any(token in cell.value for token in candidates)]
                        name_match = any(token in filename for token in candidates)
                        sheet_match = any(token in ws.title for token in candidates for ws in wb.worksheets)
                        lines.append("标题编号候选在 Excel 的位置：" + (", ".join(locations[:20]) or "未找到")
                                     + f"；附件文件名包含候选 {'是' if name_match else '否'}；sheet 名包含候选 {'是' if sheet_match else '否'}。")
                    finally:
                        wb.close()
            elif suffix == ".pdf":
                lines.extend(_pdf(payload))
        except Exception:  # noqa: BLE001 - untrusted data errors must never expose contents
            lines.append("附件结构解析失败，结构 UNKNOWN；未输出原始错误或内容。")
    if len(attachments) > 20:
        lines.append("附件超过 20 个，剩余结构未检查。")
    return lines


def inspect_order_mail(*, credential_getter=get_login, client_factory=imaplib.IMAP4_SSL, now=None, _message_consumer=None, selected_date=None):
    """One explicit call, no scheduler, storage, SMTP or other production services."""
    client = None
    connected = False
    try:
        login = credential_getter(HOST)
        if login.username.strip().lower() != ACCOUNT:
            return InspectionReport("ACCOUNT_MISMATCH", "Vault 邮箱账号不匹配，请配置 229 邮箱。")
        try:
            client = client_factory(HOST, 993, ssl_context=ssl.create_default_context(), timeout=20)
            _ok(client.login(login.username, login.password))
            connected = True
        finally:
            del login
        total = int(_ok(client.select("INBOX", readonly=True))[0])
        if not client.is_readonly:
            raise ValueError("READ_ONLY_NOT_CONFIRMED")
        since = (now or datetime.now(timezone.utc)) - timedelta(days=30)
        # Explicit numeric English month avoids machine-locale IMAP date errors.
        months = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
        date = f"{since.day:02d}-{months[since.month-1]}-{since.year}"
        if total:
            data = _ok(client.uid("search", "CHARSET", "UTF-8", "SINCE", date,
                                 "SUBJECT", ('"' + PREFIX + '"').encode("utf8"),
                                 f"{max(1, total-199)}:{total}"))
            uids = sorted(set(data[0].split()), key=int)[-5:][::-1]
        else:
            uids = []
        lines = ["检查范围：INBOX 最近30天、末尾最多200封范围内，最近最多5封候选。",
                 "只读查看；邮件和附件仅在内存中分析，未保存原始内容。"]
        before = {}
        matched = 0
        for uid in uids:
            metadata, flags, header = _fetch(client, uid, "(UID FLAGS INTERNALDATE RFC822.SIZE BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE MESSAGE-ID)])")
            before[uid] = flags
            message = BytesParser(policy=policy.default).parsebytes(header)
            if not str(message.get("Subject", "")).startswith(PREFIX):
                continue
            if selected_date is not None:
                from email.utils import parsedate_to_datetime
                try:
                    if parsedate_to_datetime(str(message.get("Date", ""))).isoformat() != selected_date:
                        continue
                except (ValueError, TypeError):
                    continue
            matched += 1
            lines.append(f"\n邮件 {matched}：")
            size = re.search(rb"RFC822.SIZE (\d+)", metadata)
            if size is None or int(size[1]) > MAX_BYTES:
                lines.append("大小未知或超过20MB，正文/附件未读取，结构 UNKNOWN。")
                continue
            _, _, raw = _fetch(client, uid, "(UID FLAGS BODY.PEEK[])")
            if len(raw) > MAX_BYTES:
                raise ValueError("MESSAGE_SIZE_LIMIT")
            message = BytesParser(policy=policy.default).parsebytes(raw)
            if not str(message.get("Subject", "")).startswith(PREFIX):
                raise ValueError("SUBJECT_CHANGED")
            lines.extend(describe_message(message, metadata))
            if _message_consumer is not None:
                _message_consumer(message)
        unchanged = all(_fetch(client, uid, "(UID FLAGS)")[1] == flags for uid, flags in before.items())
        lines.append(f"\n找到 {matched} 封标题以订单录单开头的邮件（不是整个邮箱总数）。")
        lines.append("读取前后候选邮件 FLAGS 一致。" if unchanged else "读取前后 FLAGS 有差异；不能确认状态未变，未执行任何修复写入。")
        return InspectionReport("SUCCESS" if unchanged else "FLAGS_DIFFER", "\n".join(lines), matched, connected, unchanged)
    except CredentialError:
        return InspectionReport("CREDENTIAL_REQUIRED", "需要在现有 Credential Vault 配置 imap.qq.com：229 邮箱账号和 IMAP 授权码。")
    except Exception:  # noqa: BLE001 - untrusted data errors must never expose contents
        return InspectionReport("CHECK_FAILED", "邮箱检查未完成，请检查 IMAP 开启状态、Vault 授权码和网络。未输出原始错误或客户数据；邮件状态一致性 UNKNOWN。", connected=connected)
    finally:
        if client is not None:
            try:
                client.logout()  # no CLOSE, which could expunge a writable mailbox
            except Exception:  # noqa: BLE001, S110 - never log raw provider errors
                pass
