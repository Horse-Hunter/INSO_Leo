"""Pure parsing of Owner-confirmed Google quotation update dialog semantics."""
import re
from enum import StrEnum


class UpdatePopupOutcome(StrEnum):
    INSERTED = "INSERTED"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    UNCONFIRMED = "UNCONFIRMED"


def parse_update_popup(display: str | None) -> UpdatePopupOutcome:
    if not isinstance(display, str):
        return UpdatePopupOutcome.UNCONFIRMED
    compact = re.sub(r"\s+", "", display)
    if not compact.startswith(("报价更新完成", "更新完成")):
        return UpdatePopupOutcome.UNCONFIRMED
    def count(label):
        found = re.findall(re.escape(label) + r"[:：]?(\d+)行", compact)
        return int(found[0]) if len(found) == 1 else None
    existing_labels = [label for label in ("已有报价", "已有价跳过") if label in compact]
    if len(existing_labels) > 1:
        return UpdatePopupOutcome.UNCONFIRMED
    existing_label = existing_labels[0] if existing_labels else "已有报价"
    inserted, existing = count("成功填入"), count(existing_label)
    if ("成功填入" in compact and inserted is None) or (existing_label in compact and existing is None):
        return UpdatePopupOutcome.UNCONFIRMED
    if inserted == 1 and existing in {None, 0}:
        return UpdatePopupOutcome.INSERTED
    if existing == 1 and inserted in {None, 0}:
        return UpdatePopupOutcome.ALREADY_EXISTS
    return UpdatePopupOutcome.UNCONFIRMED
