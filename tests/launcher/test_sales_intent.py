from types import SimpleNamespace

from src.launcher import sales_intent
from src.sheets.intent_status import IntentLine, IntentResult


def test_no_interactive_google_consent_and_both_configured_sheets(monkeypatch, tmp_path):
    service = object()
    def build(*, browser_handle):
        assert browser_handle is None
        return service
    monkeypatch.setattr(sales_intent, 'build_google_web_service', build)
    monkeypatch.setattr(sales_intent, 'GoogleSheetsRowReader', lambda value: value)
    monkeypatch.setattr(sales_intent, 'GoogleSheetsIntentStatusWriter', lambda value: value)
    def update(reader, writer, worksheets, lines):
        assert reader is writer is service
        assert [ws.worksheet for ws in worksheets] == ['2026', 'SHAHAB']
        return tuple(IntentResult(line, True, 'UPDATED') for line in lines)
    monkeypatch.setattr(sales_intent, 'update_intent_statuses', update)
    order = SimpleNamespace(lines=[SimpleNamespace(part_number='TEST-A', quantity=2)])
    result, = sales_intent.mark_sales_intent(order, production={'client_secret_file': 'client.json',
        'spreadsheet_id': 'test', 'worksheet_titles': ['2026', 'SHAHAB']}, root=tmp_path)
    assert result.success


def test_auth_failure_reports_all_models_without_provider_content(monkeypatch, tmp_path):
    def fail(*args, **kwargs):
        raise RuntimeError('PRIVATE_TOKEN_URL')
    monkeypatch.setattr(sales_intent, 'build_google_web_service', fail)
    order = SimpleNamespace(lines=[SimpleNamespace(part_number='TEST-A', quantity=2),
        SimpleNamespace(part_number='TEST-B', quantity=3)])
    results = sales_intent.mark_sales_intent(order, production={'client_secret_file': 'client.json',
        'spreadsheet_id': 'test', 'worksheet_titles': ['2026', 'SHAHAB']}, root=tmp_path)
    text = sales_intent.intent_report(results)
    assert 'TEST-A' in text and 'TEST-B' in text and '手动补表' in text
    assert '不要为补表重新录单' in text and 'PRIVATE' not in text


def test_already_intent_report_is_success():
    assert '已确认' in sales_intent.intent_report([IntentResult(IntentLine('TEST-A', 2), True, 'ALREADY_INTENT')])
