"""Bounded local presentation and the CustomTkinter workbench shell.

No business modules, files, websites, timers or threads are accessed here.
"""

from datetime import datetime, timezone
from math import ceil
from time import monotonic
from tkinter import ttk

import customtkinter as ctk

from src.core.app_paths import application_name

from .contracts import OrderStatus, RunState

BG, NAV, CARD, LINE = "#141b23", "#10161e", "#1c2733", "#2b3949"
TEXT, MUTED, BLUE = "#e7edf4", "#9baabd", "#557fae"
GREEN, AMBER, RED = "#8bc9ac", "#e5bb7b", "#ed9b9b"
NAMES = {"inquiry": "询价采购", "quotation": "报价跟进", "tp": "目标价调研"}
SITES = {
    "ic.net": "IC.net",
    "findchips": "Findchips",
    "hqew": "华强",
    "lcsc": "立创",
    "bom.ai": "正能量",
    "inso": "INSO",
}
MAIL_UNKNOWN = "邮件发送结果尚未确认，请人工核对；系统不会自动重复发送。"


def unknown_mail(order, state=None):
    return order.delivery_status == "UNKNOWN" or bool(
        state
        and any(
            a.reason_code.value == "NOTIFICATION_UNKNOWN" for a in state.active_alerts
        )
    )


def stamp(value):
    return value.astimezone().strftime("%m-%d %H:%M:%S") if value else "暂无记录"


def elapsed(module, now=None):
    seconds = module.elapsed_seconds
    if module.started_monotonic is not None:
        seconds += max(
            0, (monotonic() if now is None else now) - module.started_monotonic
        )
    seconds = int(seconds)
    return f"{seconds // 3600:02d}:{seconds // 60 % 60:02d}:{seconds % 60:02d}"


def scheduling(snapshot, now=None, tick=None):
    session = snapshot.session
    if session.state is RunState.STOPPING_AFTER_CYCLE:
        return "正在安全结束本轮，未确认操作不会重做"
    if session.state not in {RunState.RUNNING, RunState.QUOTATION_RUNNING}:
        return (
            "已停止"
            if session.state is RunState.STOPPED
            else "已暂停 · 请检查异常与通知"
        )
    if (
        snapshot.cycle_started_monotonic is not None
        and snapshot.cycle_finished_at is None
    ):
        seconds = max(
            0,
            int(
                (monotonic() if tick is None else tick)
                - snapshot.cycle_started_monotonic
            ),
        )
        return f"本轮进行中 · 已耗时 {seconds // 60:02d}:{seconds % 60:02d}"
    if session.row_cooldown_until is not None:
        return "订单间安全等待"
    active = next(
        (m for m in snapshot.modules if m.started_monotonic is not None), None
    )
    if active:
        return "任务进行中 · " + active.name + " / " + active.stage
    planned = snapshot.planned_check_at
    if planned is None and snapshot.cycle_started_at is None:
        planned = session.next_poll_at  # legacy/mock snapshots without observed rounds
    if planned is None:
        return "等待调度确认 · 暂无下次检查时间"
    seconds = max(
        0,
        ceil(
            (planned - (now or datetime.now(timezone.utc))).total_seconds()
        ),
    )
    return (f"等待{snapshot.recovery_site}恢复 · " if snapshot.recovery_site else "") + (
        f"下次检查 {seconds // 60:02d}:{seconds % 60:02d}"
        if seconds
        else "计划时间已到 · 等待工作流确认"
    )


def order_status(order):
    if order.delivery_status == "UNKNOWN":
        return "邮件结果待核对"
    if order.delivery_status in {"PENDING", "SENDING", "RETRYABLE_FAILURE"}:
        return "邮件待确认"
    if order.delivery_status == "PERMANENT_FAILURE":
        return "邮件发送失败"
    if order.delivery_status == "SENT":
        return "调研邮件已发送"
    return (
        order.business_status
        or {
            OrderStatus.COMPLETED: "调研已完成",
            OrderStatus.PARTIAL: "调研部分完成",
            OrderStatus.PENDING: "待处理",
            OrderStatus.ERROR: "异常待核对",
            OrderStatus.UNKNOWN: "状态未确认",
        }[order.status]
    )


def select_orders(
    orders,
    *,
    query="",
    module="全部模块",
    status="全部状态",
    source="全部来源",
    scope="全部记录",
):
    query = query.strip().casefold()

    def keep(o):
        modules = getattr(o, "modules", ()) or (o.module_id,)
        return (
            (not query or query in o.model.casefold())
            and (module == "全部模块" or module in [NAMES.get(m, m) for m in modules])
            and (
                status == "全部状态"
                or (
                    status == "需核对"
                    and (
                        o.status in {OrderStatus.ERROR, OrderStatus.UNKNOWN}
                        or o.delivery_status in {"UNKNOWN", "PERMANENT_FAILURE"}
                    )
                )
                or (status == "待处理" and o.status is OrderStatus.PENDING)
                or (
                    status == "已完成"
                    and o.status in {OrderStatus.COMPLETED, OrderStatus.PARTIAL}
                    and o.delivery_status
                    not in {
                        "UNKNOWN",
                        "PENDING",
                        "SENDING",
                        "RETRYABLE_FAILURE",
                        "PERMANENT_FAILURE",
                    }
                )
            )
            and (source == "全部来源" or (o.source_sheet or "来源未载入") == source)
            and (
                scope == "全部记录"
                or (scope == "当前任务" and bool(o.run_id))
                or (scope == "历史记录" and not o.run_id)
            )
        )

    return tuple(o for o in orders if keep(o))


def sort_orders(orders, key, *, reverse=False):
    """Keep missing values last and compare numbers/dates in their own types."""
    if key in {"price", "quantity", "processed"}:
        field = {
            "price": "min_reference_price",
            "quantity": "quantity",
            "processed": "processed_at",
        }[key]
        present = [o for o in orders if getattr(o, field) is not None]
        missing = [o for o in orders if getattr(o, field) is None]

        def value(order):
            current = getattr(order, field)
            return current.timestamp() if key == "processed" else current

        return tuple(sorted(present, key=value, reverse=reverse) + missing)

    def value(order):
        return str(
            {
                "status": order_status(order),
                "source": order.source_sheet or "",
                "module": NAMES.get(order.module_id, ""),
            }.get(key, getattr(order, key, ""))
            or ""
        ).casefold()

    return tuple(sorted(orders, key=value, reverse=reverse))


class WorkbenchView:
    pages = ("总览", "任务中心", "调研结果", "异常与通知", "运行记录", "设置")

    def __init__(self, app):
        self.app, self.root = app, app._root
        self.page, self.orders, self.states = "总览", (), {}
        self._manual_counts = dict.fromkeys(NAMES, 0)
        self.snapshot = None
        self.page_index, self.page_size, self.sort_desc = 0, 200, False
        self._filter_after = None
        self._detail_signature = self._notice_signature = self._log_signature = None
        self._values = {}
        self._row_values = {}
        self._layout_mode = None
        self.root.configure(fg_color=BG)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(1, weight=1)
        self.nav = ctk.CTkFrame(self.root, fg_color=NAV, corner_radius=0, width=158)
        self.nav.grid(row=0, column=0, rowspan=3, sticky="nsew")
        self.nav.grid_propagate(False)
        self.nav.grid_columnconfigure(0, weight=1)
        self.label(self.nav, "INSO LEO", 20).grid(
            row=0, column=0, padx=18, pady=(26, 0), sticky="w"
        )
        self.label(self.nav, "采购自动化工作站", 11, MUTED).grid(
            row=1, column=0, padx=18, pady=(4, 28), sticky="w"
        )
        self.nav_buttons = {}
        for i, name in enumerate(self.pages, 2):
            button = self.button(
                self.nav,
                name,
                lambda n=name: self.show_page(n),
                fg_color="transparent",
                anchor="w",
            )
            button.grid(row=i, column=0, sticky="ew", padx=10, pady=4)
            self.nav_buttons[name] = button
        self.nav.grid_rowconfigure(9, weight=1)
        self.label(self.nav, "稳定执行 · 有据可查", 11, MUTED).grid(
            row=10, column=0, pady=20
        )
        header = ctk.CTkFrame(self.root, fg_color="transparent")
        header.grid(row=0, column=1, sticky="ew", padx=22, pady=(20, 12))
        header.grid_columnconfigure(0, weight=1)
        self.page_title = self.label(header, "业务总览", 23)
        self.page_title.grid(row=0, column=0, sticky="w")
        self.label(header, "Procurement Automation Control Center", 11, MUTED).grid(
            row=1, column=0, sticky="w", pady=(3, 0)
        )
        app._status_badge = self.label(header, "已停止", 12, MUTED)
        app._status_badge.grid(row=0, column=1, padx=15)
        app._action_button = self.button(header, "开始运行", app._on_action, width=145)
        app._action_button.grid(row=0, column=2, rowspan=2)
        self.body = ctk.CTkFrame(self.root, fg_color="transparent")
        self.body.grid(row=1, column=1, sticky="nsew", padx=22, pady=(0, 12))
        self.body.grid_rowconfigure(0, weight=1)
        self.body.grid_columnconfigure(0, weight=1)
        self.frames = {}
        self._build_overview()
        self._build_tasks()
        self._build_text_page("异常与通知")
        self._build_text_page("运行记录")
        self._build_settings()
        self.footer = self.label(self.root, "等待运行 · 尚无执行记录", 12, MUTED)
        self.footer.grid(row=2, column=1, sticky="ew", padx=22, pady=(0, 12))
        self.show_page("总览")

    @staticmethod
    def label(parent, text, size=13, color=TEXT, **kw):
        return ctk.CTkLabel(
            parent, text=text, font=("Microsoft YaHei UI", size), text_color=color, **kw
        )

    @staticmethod
    def button(parent, text, command, **kw):
        return ctk.CTkButton(
            parent,
            text=text,
            command=command,
            font=("Microsoft YaHei UI", 12),
            height=36,
            corner_radius=7,
            fg_color=kw.pop("fg_color", BLUE),
            hover_color="#33485f",
            **kw,
        )

    def configure(self, widget, **values):
        # CTk configure invokes drawing even for equal values. Avoid those calls.
        key = id(widget)
        old = self._values.setdefault(key, {})
        changed = {k: v for k, v in values.items() if old.get(k) != v}
        if changed:
            widget.configure(**changed)
            old.update(changed)

    def frame(self, name, *, scroll=False):
        frame = ctk.CTkFrame(self.body, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew")
        self.frames[name] = frame
        if scroll:
            frame.grid_columnconfigure(0, weight=1)
            frame.grid_rowconfigure(0, weight=1)
            content = ctk.CTkScrollableFrame(frame, fg_color="transparent")
            content.grid(row=0, column=0, sticky="nsew")
            return content
        return frame

    def _build_overview(self):
        frame = self.frame("总览", scroll=True)
        frame.grid_columnconfigure((0, 1, 2), weight=1, uniform="modules")
        frame.grid_rowconfigure(2, weight=1)
        self.cards = {}
        self.module_cards = []
        for column, (key, name) in enumerate(NAMES.items()):
            card = ctk.CTkFrame(
                frame,
                fg_color=CARD,
                corner_radius=10,
                border_width=1,
                border_color=LINE,
            )
            card.grid(
                row=0,
                column=column,
                sticky="nsew",
                padx=(0, 10 if column < 2 else 0),
                pady=(0, 16),
            )
            self.module_cards.append(card)
            self.label(card, name, 15).pack(anchor="w", padx=16, pady=(16, 8))
            status = self.label(
                card, "未启用" if key != "inquiry" else "空闲", 21, MUTED
            )
            status.pack(anchor="w", padx=16)
            detail = self.label(
                card,
                "尚无执行记录",
                12,
                MUTED,
                justify="left",
                anchor="w",
                wraplength=270,
            )
            detail.pack(fill="x", padx=16, pady=(8, 16))
            self.cards[key] = (status, detail)
        active = ctk.CTkFrame(
            frame, fg_color=CARD, corner_radius=10, border_width=1, border_color=LINE
        )
        self.active_panel = active
        active.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 16))
        self.label(active, "当前执行任务", 12, MUTED).pack(
            anchor="w", padx=20, pady=(18, 8)
        )
        self.active_title = self.label(
            active, "工作流尚未启动", 20, anchor="w", wraplength=850
        )
        self.active_title.pack(fill="x", padx=20)
        self.active_detail = self.label(
            active,
            "开始运行后，仅展示实际观测到的阶段。",
            13,
            MUTED,
            justify="left",
            anchor="w",
        )
        self.active_detail.pack(fill="x", padx=20, pady=(12, 20))
        bottom = ctk.CTkFrame(frame, fg_color=CARD, corner_radius=10)
        bottom.grid(row=2, column=0, columnspan=3, sticky="nsew")
        self.label(bottom, "本轮与待办", 14).pack(anchor="w", padx=20, pady=(16, 8))
        self.counts = self.label(
            bottom, "暂无可靠统计", 13, MUTED, justify="left", anchor="w"
        )
        self.counts.pack(fill="x", padx=20, pady=8)
        self.health = self.label(
            bottom,
            "健康状态尚未检查",
            12,
            MUTED,
            justify="left",
            anchor="w",
            wraplength=850,
        )
        self.health.pack(fill="x", padx=20, pady=8)
        self.button(
            bottom, "查看任务中心", lambda: self.show_page("任务中心"), width=145
        ).pack(anchor="w", padx=20, pady=(8, 18))

    def _build_tasks(self):
        frame = self.frame("任务中心")
        self.frames["调研结果"] = frame
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        filters = ctk.CTkFrame(frame, fg_color="transparent")
        self.filter_bar = filters
        filters.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        filters.grid_columnconfigure(0, weight=1)
        self.search = ctk.CTkEntry(
            filters, placeholder_text="搜索已加载的本地型号", height=34
        )
        self.search.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.search.bind("<KeyRelease>", lambda _: self.filter_changed())
        self.filters = {}
        choices = (
            ("module", ["全部模块", *NAMES.values()]),
            ("status", ["全部状态", "待处理", "需核对", "已完成"]),
            ("source", ["全部来源", "2026", "SHAHAB", "来源未载入"]),
            ("scope", ["全部记录", "当前任务", "历史记录"]),
        )
        for column, (key, values) in enumerate(choices, 1):
            menu = ctk.CTkOptionMenu(
                filters,
                values=values,
                width=115,
                height=34,
                fg_color=CARD,
                button_color=LINE,
                command=lambda _: self.filter_changed(),
            )
            menu.grid(row=0, column=column, padx=4)
            self.filters[key] = menu
        table = ctk.CTkFrame(frame, fg_color=CARD, corner_radius=9)
        table.grid(row=1, column=0, sticky="nsew")
        table.grid_rowconfigure(0, weight=1)
        table.grid_columnconfigure(0, weight=1)
        columns = (
            "model",
            "brand",
            "quantity",
            "source",
            "module",
            "status",
            "processed",
            "price",
        )
        tree = ttk.Treeview(
            table, columns=columns, show="headings", selectmode="browse"
        )
        for key, title, width in zip(
            columns,
            (
                "型号",
                "品牌",
                "数量",
                "来源",
                "业务模块",
                "状态",
                "最近处理",
                "已有参考价",
            ),
            (225, 90, 70, 110, 145, 170, 130, 100),
            strict=True,
        ):
            tree.heading(key, text=title, command=lambda k=key: self.sort(k))
            tree.column(
                key, width=width, minwidth=55, stretch=key in {"model", "status"}
            )
        tree.configure(displaycolumns=columns[:-1])
        tree.grid(row=0, column=0, sticky="nsew", padx=(10, 0), pady=(10, 0))
        vertical = ttk.Scrollbar(table, orient="vertical", command=tree.yview)
        vertical.grid(row=0, column=1, sticky="ns", pady=(10, 0))
        horizontal = ttk.Scrollbar(table, orient="horizontal", command=tree.xview)
        horizontal.grid(row=1, column=0, sticky="ew", padx=10)
        tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        style = ttk.Style(tree)
        style.theme_use("default")
        style.configure(
            "Treeview",
            background=CARD,
            fieldbackground=CARD,
            foreground=TEXT,
            rowheight=34,
            borderwidth=0,
            font=("Microsoft YaHei UI", 11),
        )
        style.configure(
            "Treeview.Heading",
            background=LINE,
            foreground=MUTED,
            borderwidth=0,
            padding=(8, 10),
            font=("Microsoft YaHei UI", 11),
        )
        style.map(
            "Treeview",
            background=[("selected", "#344e68")],
            foreground=[("selected", "#ffffff")],
        )
        for name, color in (
            ("completed", GREEN),
            ("recent", TEXT),
            ("legacy", MUTED),
            ("warning", AMBER),
            ("error", RED),
        ):
            tree.tag_configure(name, background=CARD, foreground=color)
        self.app._tree = tree
        self.app._column_fields = {
            "#1": ("型号", "model"),
            "#2": ("品牌", "brand"),
            "#3": ("数量", "quantity"),
        }
        tree.bind("<<TreeviewSelect>>", self.app._on_row_select)
        tree.bind("<Button-3>", self.app._on_order_context)
        tree.bind("<Double-1>", self.app._on_order_edit)
        self.detail = ctk.CTkFrame(frame, fg_color=CARD, width=300, corner_radius=9)
        self.detail.grid(row=1, column=1, sticky="nsew", padx=(12, 0))
        self.detail.grid_propagate(False)
        self.detail.grid_rowconfigure(1, weight=1)
        self.detail.grid_columnconfigure(0, weight=1)
        self.button(
            self.detail, "订单详情   ×", self.hide_detail, fg_color="transparent"
        ).grid(row=0, column=0, sticky="ew", padx=8, pady=5)
        self.app._detail_container = ctk.CTkScrollableFrame(
            self.detail, fg_color="transparent"
        )
        self.app._detail_container.grid(
            row=1, column=0, sticky="nsew", padx=8, pady=(0, 8)
        )
        pager = ctk.CTkFrame(frame, fg_color="transparent")
        pager.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self.pager_text = self.label(pager, "暂无记录", 11, MUTED)
        self.pager_text.pack(side="left")
        self.button(
            pager, "下一页", lambda: self.page_by(1), width=70, fg_color=CARD
        ).pack(side="right", padx=4)
        self.button(
            pager, "上一页", lambda: self.page_by(-1), width=70, fg_color=CARD
        ).pack(side="right", padx=4)
        self.button(pager, "详情", self.show_detail, width=60, fg_color=CARD).pack(
            side="right", padx=4
        )
        self.hide_detail()

    def _build_text_page(self, name):
        frame = self.frame(name)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        box = ctk.CTkTextbox(
            frame,
            fg_color=CARD,
            text_color=TEXT,
            font=("Microsoft YaHei UI", 13),
            wrap="word",
        )
        box.grid(row=0, column=0, sticky="nsew")
        box.configure(state="disabled")
        if name == "异常与通知":
            self.notices = box
        else:
            self.logs = box

    def _build_settings(self):
        frame = self.frame("设置", scroll=True)
        frame.grid_columnconfigure(0, weight=1)
        self.label(frame, "工作站与安全操作", 18).grid(
            row=0, column=0, sticky="w", pady=(10, 12)
        )
        self.settings = self.label(
            frame, "业务配置状态尚未载入", 13, MUTED, justify="left", anchor="w"
        )
        self.settings.grid(row=1, column=0, sticky="ew", pady=12)
        actions = ctk.CTkFrame(frame, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="ew", pady=8)
        actions.grid_columnconfigure((0, 1), weight=1, uniform="existing-actions")
        self.app._login_all_button = self.button(
            actions, "一键登录所有网站", self.app._on_login_all, width=220
        )
        self.app._login_all_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.app._order_mail_button = self.button(
            actions, "自动订单录单", self.app._on_order_mail, width=220
        )
        self.app._order_mail_button.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        self.button(
            frame, "打开已有 Research 表格", self.app._backend.open_excel, width=220
        ).grid(row=4, column=0, sticky="w", pady=8)
        self.button(
            frame, "打开结果目录", self.app._backend.open_results_dir, width=220
        ).grid(row=5, column=0, sticky="w", pady=8)
        self.label(
            frame, "关于 · " + application_name() + " / V1.5-B 源码候选", 12, MUTED
        ).grid(row=6, column=0, sticky="w", pady=(25, 8))
        self.label(
            frame,
            "人工操作沿用原有安全校验；未确认的发送结果需要先人工核对。",
            12,
            MUTED,
            wraplength=650,
            justify="left",
        ).grid(row=7, column=0, sticky="w")

    def show_page(self, name):
        if name not in self.pages:
            return
        self.page = name
        self.frames[name].tkraise()
        self.configure(self.page_title, text="业务总览" if name == "总览" else name)
        for key, button in self.nav_buttons.items():
            self.configure(button, fg_color=LINE if key == name else "transparent")
        if name in {"任务中心", "调研结果"}:
            self.app._tree.configure(
                displaycolumns=(
                    "model",
                    "brand",
                    "quantity",
                    "source",
                    "module",
                    "status",
                    "processed",
                )
                + (("price",) if name == "调研结果" else ())
            )
            self.render_orders()
        if self.snapshot is not None:
            self.render(self.snapshot, force=True)

    def filter_changed(self):
        if self._filter_after is not None:
            self.root.after_cancel(self._filter_after)
        self._filter_after = self.root.after(180, self._apply_filter)

    def _apply_filter(self):
        self._filter_after = None
        self.page_index = 0
        self.render_orders()

    def set_orders(self, orders, states=None):
        orders = tuple(orders[:1000])
        states = states or {}
        if (orders, states) == (self.orders, self.states):
            return
        self.orders, self.states = orders, states
        self._manual_counts = {
            key: sum(
                key in (o.modules or (o.module_id,))
                and (
                    o.status in {OrderStatus.ERROR, OrderStatus.UNKNOWN}
                    or unknown_mail(o, states.get(o.inquiry_id))
                )
                for o in orders
            )
            for key in NAMES
        }
        if self.page in {"任务中心", "调研结果"}:
            self.render_orders()

    def sort(self, key):
        self.sort_desc = not self.sort_desc
        self.sort_key = key
        self.render_orders()

    def page_by(self, delta):
        self.page_index = max(0, self.page_index + delta)
        self.render_orders()

    def render_orders(self):
        selected = select_orders(
            self.orders,
            query=self.search.get(),
            **{k: v.get() for k, v in self.filters.items()},
        )
        key = getattr(self, "sort_key", None)
        if key:
            selected = sort_orders(selected, key, reverse=self.sort_desc)
        pages = max(1, (len(selected) + self.page_size - 1) // self.page_size)
        self.page_index = min(self.page_index, pages - 1)
        visible = selected[
            self.page_index * self.page_size : (self.page_index + 1) * self.page_size
        ]
        ids = {o.inquiry_id for o in visible}
        tree = self.app._tree
        for iid in tuple(self._row_values):
            if iid not in ids:
                tree.delete(iid)
                del self._row_values[iid]
        for position, o in enumerate(visible):
            source = (
                f"{o.source_sheet} · {o.source_row}"
                if o.source_sheet and o.source_row
                else "来源未载入"
            )
            modules = getattr(o, "modules", ()) or (o.module_id,)
            values = (
                o.model,
                o.brand or "—",
                o.quantity,
                source,
                " · ".join(NAMES.get(m, m) for m in modules),
                order_status(o),
                stamp(o.processed_at),
                str(o.min_reference_price)
                if o.min_reference_price is not None
                else "暂无价格",
            )
            tag = (
                "error"
                if o.status is OrderStatus.ERROR
                or o.delivery_status in {"UNKNOWN", "PERMANENT_FAILURE"}
                else "recent"
            )
            if self._row_values.get(o.inquiry_id) != (values, tag):
                if tree.exists(o.inquiry_id):
                    tree.item(o.inquiry_id, values=values, tags=(tag,))
                else:
                    tree.insert("", "end", iid=o.inquiry_id, values=values, tags=(tag,))
                self._row_values[o.inquiry_id] = (values, tag)
            tree.move(o.inquiry_id, "", position)
        self.app._displayed_orders = {o.inquiry_id: o for o in visible}
        self.configure(
            self.pager_text,
            text=f"{len(selected)} 条匹配 / 已加载 {len(self.orders)} 条 · 第 {self.page_index + 1}/{pages} 页",
        )

    def show_detail(self):
        self.detail.grid()
        if self.app._selected_order is not None:
            self.render_detail(self.app._selected_order)

    def hide_detail(self):
        self.detail.grid_remove()

    def render_detail(self, order):
        state = self.states.get(order.inquiry_id)
        session = self.snapshot.session if self.snapshot is not None else None
        signature = (
            order,
            state,
            session.state if session else None,
            session.next_poll_at if session else None,
            tuple(t for t in self.snapshot.timings if t.order_ref == order.inquiry_id)[
                -10:
            ]
            if self.snapshot
            else (),
        )
        self.show_detail_frame()
        if signature == self._detail_signature:
            return
        self._detail_signature = signature
        box = self.app._detail_container
        for widget in box.winfo_children():
            widget.destroy()

        def line(text, color=TEXT):
            self.label(
                box, text, 12, color, wraplength=255, justify="left", anchor="w"
            ).pack(fill="x", pady=5)

        line(order.model)
        line(f"品牌：{order.brand or '暂无记录'}\n数量：{order.quantity}", MUTED)
        line(
            f"库存判断：{order.stock_label or '待验证'}\n重要程度：{order.importance or '暂无记录'}",
            MUTED,
        )
        line(
            "已有参考价："
            + self.app._format_money(order.min_reference_price)
            + "\n预计总价："
            + self.app._format_money(order.total_price),
            MUTED,
        )
        line(
            f"来源：{order.source_sheet or '未载入'} / {order.source_row or '行号未载入'}",
            MUTED,
        )
        line("业务状态：" + order_status(order))
        if unknown_mail(order, state):
            line(MAIL_UNKNOWN, AMBER)
        if order.module_id == "tp" and not order.sources:
            line(
                "历史每源报价明细未持久化，当前无法展示。重跑需通过原有安全校验。",
                MUTED,
            )
        for source in order.sources:
            line(
                source.source
                + "："
                + source.display_value
                + (f"（{source.remark}）" if source.remark else "")
            )
        if order.remark:
            line(order.remark, AMBER)
        if self.snapshot:
            active = next(
                (
                    m
                    for m in self.snapshot.modules
                    if m.order_ref == order.inquiry_id
                    and m.started_monotonic is not None
                ),
                None,
            )
            if active:
                line("当前阶段：" + active.stage, MUTED)
            measured = [
                t for t in self.snapshot.timings if t.order_ref == order.inquiry_id
            ][-10:]
            for t in measured:
                site = SITES.get(t.site, t.site) or "本地阶段"
                line(
                    f"{stamp(t.started_at)} → {stamp(t.finished_at)}\n{site} · {t.stage} · {t.elapsed_seconds:.1f} 秒",
                    MUTED,
                )
        line("执行记录", MUTED)
        if state and state.event_history:
            from .app import _event_display_text

            for event in state.event_history[-30:]:
                line(
                    stamp(event.occurred_at) + "  " + _event_display_text(event), MUTED
                )
        else:
            line("暂无可核实的历史阶段时间线", MUTED)
        for title, action in (
            ("重跑采购流程", "purchase"),
            ("重跑报价流程", "quotation"),
            ("重跑 TP 价格", "tp"),
        ):
            enabled = self.app._backend.order_action_hint(order.inquiry_id, action)
            button = self.button(
                box,
                title,
                lambda a=action: self.app._request_order_action(order.inquiry_id, a),
                width=245,
            )
            button.pack(fill="x", pady=4)
            button.configure(state="normal" if enabled else "disabled")
        edit = self.button(
            box,
            "编辑重要程度",
            lambda: self.app._edit_order_field(order, "重要程度", "importance"),
            width=245,
        )
        edit.pack(fill="x", pady=4)
        edit.configure(
            state="normal"
            if self.app._backend.order_action_hint(order.inquiry_id, "edit")
            else "disabled"
        )

        line("操作请求仍须实时核验订单权限，结果不明的订单不能盲目重发。", MUTED)

    def show_detail_frame(self):
        self.detail.grid()

    @staticmethod
    def write_box(box, text):
        box.configure(state="normal")
        box.delete("1.0", "end")
        box.insert("1.0", text)
        box.configure(state="disabled")

    def render(self, snapshot, *, force=False):
        changed = (
            force
            or self.snapshot is None
            or snapshot.revision != self.snapshot.revision
        )
        self.snapshot = snapshot
        if changed:
            self.set_orders(
                snapshot.orders, {s.inquiry_id: s for s in snapshot.order_states}
            )
            selected = self.app._selected_order
            if selected is not None and self.detail.winfo_ismapped():
                current = next(
                    (o for o in self.orders if o.inquiry_id == selected.inquiry_id),
                    None,
                )
                if current is not None:
                    self.app._selected_order = current
                    self.render_detail(current)
        self.configure(self.footer, text=scheduling(snapshot))
        self.configure(
            self.app._status_badge,
            text=snapshot.session.state.value.replace(
                "V1.2暂停 / V1.3正常", "采购暂停 · 报价跟进继续"
            ),
        )
        width = self.root.winfo_width()
        scale = ctk.ScalingTracker.get_widget_scaling(self.root)
        logical_width = width / scale
        mode = (
            logical_width < 1100,
            logical_width < 1350,
            self.root.winfo_height() / scale < 600,
        )
        layout = (
            mode,
            int(logical_width),
            int(self.root.winfo_height() / scale),
            scale,
        )
        if layout != self._layout_mode:
            self._layout_mode = layout
            if mode[0]:
                self.hide_detail()
            self.active_panel.grid(
                row=0 if mode[2] else 1,
                column=0,
                columnspan=3,
                sticky="ew",
                pady=(0, 16),
            )
            for column, card in enumerate(self.module_cards):
                card.grid(
                    row=1 if mode[2] else 0,
                    column=column,
                    sticky="nsew",
                    padx=(0, 10 if column < 2 else 0),
                    pady=(0, 16),
                )
            self.search.grid(
                row=0,
                column=0,
                sticky="ew",
                padx=(0, 10),
                columnspan=4 if mode[1] else 1,
                pady=(0, 6) if mode[1] else 0,
            )
            for column, menu in enumerate(self.filters.values()):
                menu.grid(
                    row=1 if mode[1] else 0,
                    column=column if mode[1] else column + 1,
                    padx=4,
                )
            for column in range(5):
                self.filter_bar.grid_columnconfigure(
                    column, weight=int(column < 4) if mode[1] else int(column == 0)
                )
            for _, detail in self.cards.values():
                detail.configure(wraplength=max(100, (logical_width - 230) // 3 - 40))
            for label in (
                self.active_title,
                self.active_detail,
                self.counts,
                self.health,
            ):
                label.configure(wraplength=max(300, logical_width - 290))
        if self.page == "总览":
            for module in snapshot.modules:
                if module.module_id not in self.cards:
                    continue
                status, detail = self.cards[module.module_id]
                color = (
                    GREEN
                    if module.status == "运行中"
                    else AMBER
                    if module.status in {"需要人工处理", "已暂停"}
                    else MUTED
                )
                self.configure(status, text=module.status, text_color=color)
                timing = (
                    "已耗时 " + elapsed(module)
                    if module.started_monotonic is not None
                    else "待人工已耗时 " + elapsed(module)
                    if module.status in {"已暂停", "需要人工处理"}
                    else "最近阶段结束 " + stamp(module.last_finished_at)
                )
                self.configure(
                    detail,
                    text=module.stage
                    + "\n"
                    + timing
                    + "\n"
                    + (
                        (f"等待{snapshot.recovery_site}恢复 · " if snapshot.recovery_site else "")
                        + "计划 " + stamp(module.next_check_at)
                        if module.next_check_at
                        else module.waiting_reason or "暂无计划时间"
                    )
                    + "\n已加载待核对："
                    + str(self._manual_counts[module.module_id]),
                )
            active = next(
                (m for m in snapshot.modules if m.started_monotonic is not None), None
            )
            if active:
                self.configure(
                    self.active_title, text=active.name + " / " + active.stage
                )
                ref = (
                    ("任务 " + active.order_ref[-12:])
                    if active.order_ref
                    else "暂无当前订单标识"
                )
                site = (
                    "当前网站：" + SITES.get(active.site, active.site)
                    if active.site
                    else "当前网站：尚无可靠观测"
                )
                self.configure(
                    self.active_detail,
                    text=f"{ref}　·　{site}\n开始 {stamp(active.started_at)}　·　已耗时 {elapsed(active)}\n最近变化 {stamp(active.changed_at)}",
                )
            else:
                self.configure(self.active_title, text=scheduling(snapshot))
                self.configure(
                    self.active_detail,
                    text="没有正在执行的已观测任务。等待原因与异常请查看对应模块。",
                )
            s = snapshot.session
            self.configure(
                self.counts,
                text="　　".join(
                    label + "：" + ("暂无统计" if value is None else str(value))
                    for label, value in (
                        ("新订单", s.new_orders),
                        ("采购未报价", s.awaiting_quotation),
                        ("采购超时未报价", s.overdue_quotation),
                    )
                )
                + "\n本轮已记录阶段耗时："
                + (
                    "　".join(
                        f"{NAMES[k]} {v:.1f} 秒" for k, v in snapshot.cycle_durations
                    )
                    if snapshot.cycle_started_at
                    else "暂无记录"
                )
                + ("\n本地历史载入中" if snapshot.local_loading else ""),
            )
            self.configure(
                self.health,
                text="　·　".join(
                    i.component + " " + i.status for i in snapshot.health.items
                ),
            )
        elif self.page == "异常与通知" and changed:
            entries = []
            for m in snapshot.modules:
                if m.status in {"需要人工处理", "已暂停"}:
                    entries.append(
                        f"{m.name}｜{stamp(m.changed_at)}｜{m.status}\n{m.waiting_reason or '请人工核对'}"
                    )
            for o in snapshot.orders:
                state = self.states.get(o.inquiry_id)
                if unknown_mail(o, state):
                    entries.append(
                        f"{NAMES.get(o.module_id)}｜任务 {o.inquiry_id[-12:]}\n"
                        + MAIL_UNKNOWN
                    )
                elif o.status in {OrderStatus.ERROR, OrderStatus.UNKNOWN} or (
                    state and state.active_alerts
                ):
                    entries.append(
                        f"{NAMES.get(o.module_id)}｜{o.model}｜{order_status(o)}\n"
                        + ("请按已记录状态人工核对；本页不会重新发送或提交。")
                    )
                if state:
                    for alert in state.active_alerts:
                        entries.append(
                            f"{NAMES.get(o.module_id)}｜任务 {o.inquiry_id[-12:]}｜需人工核对\n"
                            f"{stamp(alert.raised_at)} · {alert.alert_type.value} / {alert.reason_code.value}\n"
                            + (
                                MAIL_UNKNOWN
                                if alert.reason_code.value == "NOTIFICATION_UNKNOWN"
                                else "请核对已记录异常；本页不推断未证实的原因。"
                            )
                        )
            text = (
                "\n\n".join(entries[:200])
                or "当前已加载记录中没有待展示异常；未加载的数据不作判断。"
            )
            if text != self._notice_signature:
                self.write_box(self.notices, text)
                self._notice_signature = text
        elif self.page == "运行记录" and changed:
            text = (
                "\n".join(
                    stamp(e.timestamp) + "  " + e.level + "  " + e.message
                    for e in snapshot.logs[-300:]
                )
                or "暂无运行记录"
            )
            if text != self._log_signature:
                self.write_box(self.logs, text)
                self._log_signature = text
        elif self.page == "设置" and changed:
            self.configure(
                self.settings,
                text="\n".join(m.name + "：" + m.status for m in snapshot.modules)
                + "\n\n业务使用既有串行工作流；界面仅提供本地查看与已支持的安全操作。",
            )

    def close(self):
        if self._filter_after is not None:
            self.root.after_cancel(self._filter_after)
            self._filter_after = None
