"""Owner-authorized visible demo; canonical gui.main, app, mock and mutex.
No production Backend instance, network, database, credentials or business send.
"""
import json
import logging
import os
import platform
import smtplib
import socket
import sqlite3
import subprocess
import sys
import time
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from logging.handlers import RotatingFileHandler
from pathlib import Path

SOURCE = Path('C:/Users/Leo/.codex/worktrees/v1-5-tp-research/INSO_Leo')
OUT = Path(__file__).resolve().parent
sys.path[:0] = [str(SOURCE), str(SOURCE / 'scripts')]
platform.uname()
os.environ['INSO_RUNTIME_ROOT'] = str(OUT)
(OUT / 'runtime').mkdir(exist_ok=True)
(OUT / 'runtime/production.json').write_text('{"tp_enabled":false}', encoding='utf-8')
def denied(*args, **kwargs):
    with (OUT / 'guards.log').open('a', encoding='utf-8') as stream:
        stream.write('BLOCKED_EXTERNAL_OR_DATABASE_CALL\n')
    raise RuntimeError('MOCK acceptance: external operations disabled')
socket.socket.connect = socket.socket.connect_ex = denied
socket.create_connection = denied
smtplib.SMTP = smtplib.SMTP_SSL = denied
sqlite3.connect = denied

from src.gui import main as entry
from src.gui.contracts import ModuleSnapshot, Order, OrderStatus, SourceDetail, WorkbenchSnapshot
from src.gui.mock_backend import MockBackend
from measure_workbench import process_sample
from verify_workbench_ui import capture

handler = RotatingFileHandler(OUT / 'mock-events.log', maxBytes=200000, backupCount=2, encoding='utf-8')
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
logging.getLogger('src.gui.mock_backend').addHandler(handler)
logging.getLogger('src.gui.mock_backend').setLevel(logging.INFO)
started = time.monotonic()

class VisibleMock(MockBackend):
    def __init__(self, **unused):
        super().__init__(cycle_seconds=900)
        now = datetime.now(UTC)
        self._history = [Order(f'demo-{i:04}', f'DEMO-STM32-{i:04}', '合成品牌', 100+i,
            '待验证', Decimal('12.30') if i%4 else None, Decimal('1230') if i%4 else None,
            (OrderStatus.PENDING, OrderStatus.COMPLETED, OrderStatus.ERROR)[i%3],
            sources=tuple(SourceDetail(name, '合成报价 RMB 12.30' if i%4 else '暂无可核实价格')
                for name in ('IC.net','Findchips','华强','立创','BOM.AI','INSO')),
            remark='纯合成演示；操作仅拒绝，不会采购/写表/发邮件', processed_at=now-timedelta(days=i%30),
            source_sheet=('2026','SHAHAB')[i%2], source_row=i+2,
            module_id=('inquiry','quotation','tp')[i%3],
            business_status='MAIL_QUEUED' if i%3==2 else None,
            delivery_status='UNKNOWN' if i==2 else 'SENT' if i%3==2 else None)
            for i in range(250)]
        self._log('最新源码 b2b4936 可见 MOCK 验收；TP关闭；无生产服务')
        self._log('合成异常：网站等待恢复；邮件UNKNOWN禁止重复发送', 'WARNING')
    def get_workbench_snapshot(self):
        session = self.get_status()
        active = self._cycle_active
        stage = '合成调研执行中' if active else '合成本轮完成，等待下一轮'
        modules = (ModuleSnapshot('inquiry','询价采购','运行中' if active else '等待',stage,
            site='findchips' if active else None, order_ref='demo-0000' if active else None,
            next_check_at=session.next_poll_at, waiting_reason=None if active else '合成15分钟等待'),
            ModuleSnapshot('quotation','报价跟进','空闲','合成历史结果可查看'),
            ModuleSnapshot('tp','目标价调研','未启用','本次显式关闭TP，列表仅合成历史'))
        logs = self.get_logs()[-300:]
        revision = hash((session.state, session.next_poll_at, len(self._orders), logs[-1].timestamp if logs else None))
        return WorkbenchSnapshot(revision, session, self.get_health(), tuple(self._orders+self._history),
            modules=modules, logs=logs, total_orders=len(self._orders)+len(self._history),
            planned_check_at=session.next_poll_at)
    def order_action_hint(self, key, action):
        return (key=='demo-0000' and action in {'purchase','quotation'}) or (key=='demo-0005' and action=='tp')
    def can_order_action(self, key, action):
        return self.order_action_hint(key,action)
    def request_order_action(self, key, action, **kwargs):
        self._log(f'合成人工重跑安全拒绝：{key} / {action}')
        return '模拟验收：没有接入生产操作，本次请求已安全拒绝。'
    def open_excel(self):
        self._log('模拟：没有真实Research文件，不打开生产文件')
    def open_results_dir(self):
        self._log('模拟：日志仅保存在独立验收目录，不打开生产目录')

OriginalApp = entry.InsoDashboardApp
class VisibleApp(OriginalApp):
    def __init__(self, backend):
        super().__init__(backend)
        self._root.title('INSO V1.5 最新源码 b2b4936 | MOCK 合成验收（无生产操作）')
        self._root.geometry('1400x760+10+10')
        original_page = self._view.show_page
        def page(name):
            backend._log('合成菜单切换：'+name)
            return original_page(name)
        self._view.show_page = page
        original_tray = self._on_tray_command
        def tray(command):
            backend._log('真实托盘命令：'+command)
            return original_tray(command)
        self._on_tray_command = tray
        self._sample_last = (time.monotonic(), time.process_time())
        def sample():
            wall, cpu = time.monotonic(), time.process_time()
            last_wall, last_cpu = self._sample_last
            row = dict(seconds=wall-started, hidden=self._hidden,
                cpu_one_core_percent=(cpu-last_cpu)/max(.001,wall-last_wall)*100,
                cpu_host_percent=(cpu-last_cpu)/max(.001,wall-last_wall)*100/(os.cpu_count() or 1),
                after_callbacks=len(self._root.tk.call('after','info')),
                event_queue=len(self._events._queue)+len(self._events._latest), **process_sample())
            with (OUT/'resources.jsonl').open('a',encoding='utf-8') as stream: stream.write(json.dumps(row)+'\n')
            self._sample_last = (wall,cpu)
            self._root.after(30000,sample)
        self._root.after(30000,sample)
        # Save only this synthetic window on demand; command file is local diagnostic input.
        def diagnostic():
            command = OUT/'capture.request'
            if command.exists():
                tag = command.read_text(encoding='utf-8').strip()
                command.unlink()
                if tag.isascii() and tag.replace('-','').isalnum(): capture(self._root,OUT/f'{tag}.png')
            self._root.after(1000,diagnostic)
        self._root.after(1000,diagnostic)

entry.MockBackend = VisibleMock
entry.InsoDashboardApp = VisibleApp
subprocess.Popen = denied
sys.argv = ['src.gui.main','--mock','--start-inquiry']
(OUT/'environment.json').write_text(json.dumps(dict(pid=os.getpid(), source_sha='b2b4936770aad4a8cda53e5ecaf6fbee8475d17b',
    synthetic_only=True, production_backend=False, runtime_root=str(OUT), tp_enabled=False,
    started_at=datetime.now(UTC).isoformat()),indent=2),encoding='utf-8')
try:
    result = entry.main()
finally:
    (OUT/'exited.json').write_text(json.dumps(dict(closed_at=datetime.now(UTC).isoformat())),encoding='utf-8')
raise SystemExit(result)
