"""One existing stored test-model anchor; canonical exact-row native read/bind.
No discovery iteration, workflow, writes or durable application initialization.
Underlying approved transport uses transient full TSV; only one row is consumed
by business binding, and transport deletes download in its own finally block.
"""
import hashlib
import json
import logging
import re
import sqlite3
import sys
import time
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,'C:/Users/Leo/.codex/worktrees/v1-5-tp-research/INSO_Leo')
logging.disable(logging.CRITICAL)
from playwright.sync_api import sync_playwright
from src.launcher.google_web import build_google_web_service
from src.research.cdp_pages import page_owner
from src.sheets.google_reader import _to_worksheet_rows,execute_google_read
from src.sheets.tp_brief import bind_tp_order

OUT=Path(__file__).resolve().parent
dbpath=Path('D:/Program_Leo/INSO_Leo/.worktrees/v1-2-design/dist/INSO_V1.1/runtime/production/workflow.sqlite3')
result=dict(status='NOT_VERIFIED',tested_mpn='STM32G0B0CET6',one_anchor_only=True,
 transport='Unmodified guarded native TSV; transient full download, exact selected row returned',
 underlying_full_tsv_retained=False,current_rfq_brief_rechecked=False)
diagnostics=[]
class SafeDiagnostics(logging.Handler):
 def emit(self,record):
  facts={}
  for key in ('runtime_reason','runtime_cause','inso_step','inso_cause'):
   value=getattr(record,key,None)
   if isinstance(value,str) and re.fullmatch('[A-Za-z_0-9-]{1,80}',value):facts[key]=value
  if facts:diagnostics.append(facts)
logging.disable(logging.NOTSET)
logging.getLogger().handlers=[logging.NullHandler()]
logger=logging.getLogger('inso.diagnostics');logger.handlers=[SafeDiagnostics()];logger.propagate=False;logger.setLevel(logging.DEBUG)
def safe_code(exc):
 text=str(exc)
 return text if re.fullmatch('[A-Z_0-9]+',text) else type(exc).__name__
try:
 assert not any(Path(str(dbpath)+s).exists() and Path(str(dbpath)+s).stat().st_size for s in ('-wal','-journal')),'BUSY_LEDGER_ABORT'
 before=hashlib.sha256(dbpath.read_bytes()).hexdigest()
 db=sqlite3.connect(dbpath.as_uri()+'?mode=ro&immutable=1',uri=True)
 try:
  db.execute('pragma query_only=ON')
  row=db.execute("select order_json from workflow_requirements where kind='target_price' and json_extract(order_json,'$.mpn')=? limit 1",('STM32G0B0CET6',)).fetchone()
 finally:db.close()
 assert row is not None,'NO_STORED_AUTHORIZED_SAMPLE'
 old=json.loads(row[0])
 assert old['sheet'] in {'2026','SHAHAB'} and isinstance(old['row'],int) and old['row']>0
 cfg=json.loads(Path('D:/Program_Leo/INSO_Leo/dist/INSO_V1.4/runtime/production.json').read_text(encoding='utf-8'))
 assert old['spreadsheet']==cfg['spreadsheet_id'],'STORED_SPREADSHEET_CONFLICT'
 with sync_playwright() as p:
  browser=p.chromium.connect_over_cdp('http://127.0.0.1:9222',timeout=10000)
  assert len(browser.contexts)==1,'CDP_CONTEXT_AMBIGUOUS'
  context=browser.contexts[0];original=tuple(context.pages)
  assert not any(page_owner(pg) for pg in original),'OWNED_TAB_CONFLICT'
  web=build_google_web_service(provider=lambda:(p,browser))
  def forbidden(*a,**kw):raise AssertionError('GOOGLE_WRITE_FORBIDDEN')
  web.update=forbidden
  attempts=[]
  def read():
   attempts.append(len(attempts)+1)
   return web.get(spreadsheetId=old['spreadsheet'],range=f"'{old['sheet']}'!A{old['row']}:G{old['row']}").execute()
  response=execute_google_read(read,retry_wait=lambda seconds:time.sleep(seconds) or False)
  source_rows=_to_worksheet_rows(response['values'],first_row=old['row'])
  assert len(source_rows)==1,'TARGET_ROW_CARDINALITY_CONFLICT'
  line={'sheet':old['sheet'],'sheet_row':str(old['row']),'mpn':old['mpn'],
   'qty':str(old['quantity']),'mfr':old['brand'] or '',
   'rfq_date':old['rfq_date'],'target_price':old['target_raw']}
  bound=bind_tp_order(SimpleNamespace(get=line.get),old['spreadsheet'],source_rows)
  result.update(status='SOURCE_ANCHOR_VERIFIED',source_sheet=old['sheet'],source_row=old['row'],
   matched_fields=['spreadsheet','sheet','physical_row','full_mpn','positive_integer_quantity','available_brand'],
   date_checked=old['sheet']=='SHAHAB',business_rows_validated=1,
   original_pages_preserved=all(not pg.is_closed() for pg in original),
   new_pages_remaining=len([pg for pg in context.pages if pg not in original]))
 result['production_database_unchanged']=before==hashlib.sha256(dbpath.read_bytes()).hexdigest()
except Exception as exc:
 result.update(reason=safe_code(exc))
 chain=[];seen=set();current=exc
 while current is not None and id(current) not in seen:
  seen.add(id(current));chain.append({'type':type(current).__name__,'closed_code':safe_code(current)})
  current=current.__cause__ or current.__context__
 result['exception_chain']=chain
finally:
 result['read_diagnostics']=diagnostics
 result['attempts']=len(locals().get('attempts',[]))
 if 'before' in locals():result['production_database_unchanged']=before==hashlib.sha256(dbpath.read_bytes()).hexdigest()
(OUT/'google-anchor-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
