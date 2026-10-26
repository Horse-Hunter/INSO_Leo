"""Finite existing-client read probe. No Backend, credentials, DB or write API."""
import json
import re
import sys
import time
from pathlib import Path
from datetime import UTC,datetime
from urllib.parse import urlsplit
sys.path.insert(0,'C:/Users/Leo/.codex/worktrees/v1-5-tp-research/INSO_Leo')
from playwright.sync_api import sync_playwright
from src.research.cdp_pages import shared_playwright_factory,page_owner
from src.research.icnet import CdpIcNetClient,parse_icnet_reference_price,parse_icnet_rows
from src.research.findchips import CdpFindchipsClient,parse_findchips_offers
from src.research.hqew import CdpHqewClient,parse_hqew_offers
from src.research.lcsc import CdpLcscClient
from src.research.bom_ai import CdpBomAiAuthenticatedBrowser,parse_bom_ai_price_records
from src.research.runtime import load_runtime_config

OUT=Path(__file__).resolve().parent
results=[]
def record(value):
    results.append(value)
    (OUT/'readonly-results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps(value),flush=True)
def code(exc):
    text=getattr(exc,'code',None) or getattr(exc,'reason_code',None)
    return text if isinstance(text,str) and re.fullmatch('[A-Z_0-9]+',text) else type(exc).__name__

mpn='STM32G0B0CET6'  # existing Owner-authorized test model, no customer orders
with sync_playwright() as p:
    browser=p.chromium.connect_over_cdp('http://127.0.0.1:9222',timeout=10000)
    assert len(browser.contexts)==1,'CDP_CONTEXT_AMBIGUOUS'
    context=browser.contexts[0]
    original=tuple(context.pages)
    # Do not claim/reuse any existing owned tab, and stop for active business owners.
    owners=[page_owner(page) for page in original]
    if any(owners):
        record(dict(surface='CDP',status='NOT_VERIFIED',reason='EXISTING_OWNED_TAB_SESSION_CONFLICT',existing_pages=len(original)))
        raise SystemExit(2)
    record(dict(surface='CDP',status='ATTACHED_EXISTING_ONLY',contexts=1,original_pages=len(original)))
    factory=shared_playwright_factory(lambda:(p,browser))
    config=load_runtime_config('D:/Program_Leo/INSO_Leo/dist/INSO_V1.4/runtime/research.json')
    cases=[
        ('IC.net',lambda:CdpIcNetClient(timeout_ms=20000,playwright_factory=factory).fetch_first_page(mpn),
            lambda v:dict(parsed_rows=len(parse_icnet_rows(v.html)),valid_reference_price=parse_icnet_reference_price(v.html)>0,currencies=['RMB'])),
        ('Findchips',lambda:CdpFindchipsClient(timeout_ms=20000,playwright_factory=factory).fetch_first_page(mpn),
            lambda v:dict(parsed_offers=len(parse_findchips_offers(v.html,mpn)),currencies=['USD'])),
        ('HQEW',lambda:CdpHqewClient(timeout_ms=20000,playwright_factory=factory).fetch_first_page(mpn),
            lambda v:dict(parsed_offers=len(parse_hqew_offers(v.html,reference_at=v.captured_at)),currencies=['RMB'])),
        ('LCSC',lambda:CdpLcscClient(timeout_ms=20000,playwright_factory=factory).fetch_product_page(mpn),
            lambda v:dict(parsed_product=v.product is not None,tiers=len(v.product.tiers) if v.product else 0,currencies=['RMB'])),
        ('BOM.AI',lambda:CdpBomAiAuthenticatedBrowser(config.bom_ai,timeout_ms=20000,playwright_factory=factory).fetch_price_page(mpn,None),
            lambda v:dict(parsed_offers=len(parse_bom_ai_price_records(v.html,mpn,captured_at=v.captured_at)),
                currencies=sorted({r.currency for r in parse_bom_ai_price_records(v.html,mpn,captured_at=v.captured_at)})))
    ]
    for name,fetch,parse in cases:
        start=time.monotonic()
        try:
            page=fetch()
            facts=parse(page)
            record(dict(surface=name,status='READ_PARSED',mpn=mpn,seconds=round(time.monotonic()-start,3),**facts))
        except Exception as exc:
            record(dict(surface=name,status='NOT_VERIFIED',mpn=mpn,reason=code(exc),seconds=round(time.monotonic()-start,3)))
    record(dict(surface='INSO',status='NOT_VERIFIED',reason='GUARDED_OPERATION_LEASE_REQUIRED_NO_PRODUCTION_BACKEND_INITIALIZED'))
    record(dict(surface='Google_Sheets',status='NOT_VERIFIED',reason='NATIVE_TSV_DOWNLOAD_READS_WHOLE_SHEET_NOT_USED_FOR_SMALL_PROBE'))
    record(dict(surface='CDP_FINAL',original_pages_preserved=all(not pg.is_closed() for pg in original),new_pages_remaining=len([pg for pg in context.pages if pg not in original])))
    # Exit disconnects only this Playwright client; never browser.close().
