"""One report layout and price formatter for TP and target-free detailed mail."""
from .source_contracts import money_text


def render_market_report(order, result, *, target=True, context=()):
    from datetime import timedelta, timezone
    from html import escape

    from .detailed import distinct_two

    names = {"ic.net": "IC.net", "findchips": "Findchips", "hqew": "华强",
             "lcsc": "立创", "bom.ai": "正能量", "inso": "INSO"}
    def source_name(q):
        return names[q.offer.source.value]
    def valid(q):
        return (q is not None and q.rmb.is_finite() and q.rmb > 0
                and q.offer.price.is_finite() and q.offer.price > 0
                and q.offer.currency in {"USD", "HKD", "RMB", "CNY"}
                and (q.offer.current or q.offer.quoted_at is not None
                     and q.offer.quoted_at.tzinfo is not None))
    def quote(q, *, include_source=False):
        o = q.offer
        price = f"{money_text(o.price)} {o.currency}"
        if o.currency not in {"RMB", "CNY"}:
            price += f" ≈ {money_text(q.rmb)} RMB"
        # Quote history is limited to the current12 months; Shanghai is UTC+8.
        # Match the existing BOM date parser without a tzdata runtime dependency.
        when = "现价" if o.current else o.quoted_at.astimezone(timezone(timedelta(hours=8))).date().isoformat()
        if not target and o.current:
            captured = next((s.evidence.captured_at for s in result.sources if s.source is o.source), None)
            if captured is not None and captured.tzinfo is not None:
                when += "（采集 " + captured.astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M") + "）"
        parts = [price]
        if include_source:
            parts.append(source_name(q))
        parts.append(when)
        if not o.stocked:
            parts.append("无库存")
        return " · ".join(parts)
    lowest = result.lowest if valid(result.lowest) else None
    second = result.second if valid(result.second) else None
    if lowest is None:
        opening = "请人工加急跟进：暂无有效报价。" if target else "未取得有效报价。"
    elif not target:
        opening = "市场参考调研（非客户正式报价）。"
    elif lowest.rmb < result.target_rmb:
        opening = "请人工加急跟进：最低价低于 TP。"
    elif lowest.rmb == result.target_rmb:
        opening = "最低价等于 TP。"
    else:
        opening = "最低价高于 TP。"
    identity = []
    if order.customer:
        identity.append(f"客户：{order.customer}")
    identity.append(f"型号：{order.mpn}")
    if getattr(order, "brand", None):
        identity.append(f"品牌：{order.brand}")
    identity.append(f"数量：{order.quantity:,}" if order.quantity is not None else "询价数量：未匹配，不计算订单总价")
    if getattr(order, "rfq_date", None):
        identity.append(f"{getattr(order, 'date_source', None) or '原询价日期'}：{order.rfq_date.split('T')[0].split(' ')[0]}")
    if getattr(order, "sheet", None):
        identity.append(f"订单：{order.sheet} 第{order.row}行")
    identity.extend(context)
    summary = [f"货量：{result.stock_label}"]
    if target:
        target_text = f"TP：{order.target_raw}"
        if order.currency not in {"RMB", "CNY"}:
            target_text += f" ≈ {money_text(result.target_rmb)} RMB"
        summary.insert(0, target_text)
    if lowest is not None:
        summary.append("最低：" + quote(lowest, include_source=True))
        if second is not None:
            summary.append("次低：" + quote(second, include_source=True))
        if result.estimated_total is not None and result.estimated_total.is_finite() and result.estimated_total > 0:
            summary.append(("预计订单总价：" if target else "市场参考估算订单总价（非正式报价）：") + f"{money_text(result.estimated_total)} RMB")
    if result.fallback:
        summary.append("仅无库存报价，需人工核实。")
    source_lines, table_rows = [], []
    for source in result.sources:
        available = [q for q in source.quotes if valid(q)]
        pool = [q for q in available if q.offer.stocked] or available
        pair = distinct_two(pool)
        if target and not pair:
            continue
        label = names[source.source.value]
        missing = {"SOURCE_UNAVAILABLE": "来源暂不可用或资料不足", "NO_STRICT_MPN_MATCH": "未匹配完整型号",
                   "NO_VALID_PRICE": "价格或报价日期不适用", "SUCCESS": "未取得可信价格"}
        values = [quote(q) for q in pair] or ["未取得有效报价（" + missing[source.outcome.value] + "）"]
        source_lines.append(label + "：" + values[0]
                            + ("；次低 " + values[1] if len(values) == 2 else ""))
        table_rows.append((label, values))
    paragraphs = [opening, "\n".join(identity), "\n".join(summary)]
    if source_lines:
        paragraphs.append("各来源报价\n" + "\n".join(source_lines))
    html = ('<div style="max-width:760px;font:14px/1.8 Arial,Microsoft YaHei,sans-serif;color:#20252b">'
        + '<p style="font-size:17px;font-weight:bold;margin:0 0 20px">' + escape(opening) + '</p>'
        + '<p style="margin:0 0 18px">' + "<br>".join(map(escape, identity)) + '</p>'
        + '<p style="padding:14px 16px;background:#f5f7fa;margin:0 0 20px">'
        + "<br>".join(map(escape, summary)) + '</p>')
    if table_rows:
        has_second = any(len(values) == 2 for _, values in table_rows)
        rows = []
        for label, values in table_rows:
            cells = [label, *values, *([""] if has_second and len(values) == 1 else [])]
            rows.append("<tr>" + "".join(
                '<td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;vertical-align:top">'
                + escape(value) + "</td>" for value in cells) + "</tr>")
        html += ('<table style="border-collapse:collapse;width:100%;font-size:13px;text-align:left">'
            '<tr style="background:#f5f7fa"><th style="padding:10px 12px">来源</th>'
            '<th style="padding:10px 12px">最低</th>'
            + ('<th style="padding:10px 12px">次低</th>' if has_second else '') + '</tr>'
            + "".join(rows) + '</table>')
    html += '</div>'
    return "\n\n".join(paragraphs), html
