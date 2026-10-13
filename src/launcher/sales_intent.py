"""V1.4 one-shot Sheets assembly; no browser, inquiry worker or consent flow."""
from pathlib import Path

from src.core.app_paths import resolve_app_path
from src.sheets import WorksheetIdentity
from src.sheets.google_oauth import build_read_write_google_sheets_service
from src.sheets.google_reader import GoogleSheetsRowReader
from src.sheets.google_writer import GoogleSheetsIntentStatusWriter
from src.sheets.intent_status import IntentLine, IntentResult, update_intent_statuses


def mark_sales_intent(order, *, production, root):
    lines = tuple(dict.fromkeys(IntentLine(line.part_number, line.quantity) for line in order.lines))
    try:
        titles = production['worksheet_titles']
        if (not isinstance(titles, list) or len(titles) != 2
                or any(not isinstance(title, str) or not title for title in titles)):
            raise ValueError("WORKSHEETS_UNCONFIRMED")
        worksheets = tuple(WorksheetIdentity(production['spreadsheet_id'], title) for title in titles)
        client = resolve_app_path(Path(production['client_secret_file']), root=Path(root))
        service = build_read_write_google_sheets_service(client, allow_interactive=False)
        return update_intent_statuses(GoogleSheetsRowReader(service),
            GoogleSheetsIntentStatusWriter(service), worksheets, lines)
    except Exception:  # noqa: BLE001 - missing/invalid grant must not open another browser
        return tuple(IntentResult(line, False, 'SHEETS_UNAVAILABLE') for line in lines)


def intent_report(results):
    failed = [result for result in results if not result.success]
    if not failed:
        return 'Google 表格对应行已确认“意向订单”（已是该状态的行未重复修改）。'
    labels = {'MATCH_NOT_UNIQUE': '未找到唯一匹配行', 'SOURCE_CHANGED': '源行已变化',
        'WRITE_UNCONFIRMED': '写入未确认', 'SHEETS_UNAVAILABLE': '表格或写入授权不可用',
        'CONFIGURATION_UNCONFIRMED': '工作表配置无法确认', 'LINE_UNCONFIRMED': '型号数量无法确认'}
    rows = '\n'.join(f'• {result.line.model}（数量 {result.line.quantity}）：{labels[result.reason]}' for result in failed)
    return ('需要手动补表的型号：\n' + rows + '\n请核对对应行并改为“意向订单”。'
        '\nINSO 已填写完成并记录已处理；请保留当前页面人工核对，不要为补表重新录单。')
