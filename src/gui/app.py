"""INSO_V1.0 single-page Dashboard implemented with customtkinter.

The app owns no automation logic; it consumes a GuiBackend implementation and
updates its widgets from the main thread via tkinter.after.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from tkinter import ttk
from typing import Any

import customtkinter as ctk

from .contracts import GuiBackend, LogEntry, Order, RunSession, RunState

logger = logging.getLogger(__name__)

# Colour palette
_BG = "#121212"
_CARD_BG = "#1E1E1E"
_CARD_BG_HOVER = "#262626"
_TEXT = "#FFFFFF"
_TEXT_SECONDARY = "#9CA3AF"
_GREEN = "#10B981"
_YELLOW = "#F59E0B"
_RED = "#EF4444"
_BLUE = "#3B82F6"
_GRAY = "#6B7280"
_BORDER = "#2E2E2E"

_FONT_TITLE = ("Microsoft YaHei UI", 22, "bold")
_FONT_LABEL = ("Microsoft YaHei UI", 12)
_FONT_SMALL = ("Microsoft YaHei UI", 10)
_FONT_NUMBER = ("Microsoft YaHei UI", 20, "bold")


def _format_time(value: datetime | None) -> str:
    if value is None:
        return "--"
    local = value.astimezone(timezone.utc).astimezone()
    return local.strftime("%H:%M:%S")


def _status_color(status: str) -> str:
    status_l = status.lower()
    if status_l in {"正常", "completed", "运行中", "success"}:
        return _GREEN
    if status_l in {"需要登录", "manual_review", "需要人工处理", "warning"}:
        return _YELLOW
    if status_l in {"异常", "failed", "error", "fault"}:
        return _RED
    return _TEXT_SECONDARY


class InsoDashboardApp:
    """Single-page INSO_V1.0 operator dashboard."""

    def __init__(self, backend: GuiBackend) -> None:
        self._backend = backend
        self._status: RunSession = backend.get_status()
        self._selected_order: Order | None = None

        self._root = ctk.CTk()
        self._root.title("INSO_V1.0")
        self._root.geometry("1200x800")
        self._root.configure(fg_color=_BG)
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self._build_ui()
        self._wire_backend()
        self._schedule_tick()

    def _build_ui(self) -> None:
        # Main container with padding
        self._root.grid_rowconfigure(1, weight=1)
        self._root.grid_columnconfigure(0, weight=1)

        self._header = self._build_header()
        self._header.grid(row=0, column=0, sticky="ew", padx=24, pady=(24, 12))

        content = ctk.CTkFrame(self._root, fg_color="transparent")
        content.grid(row=1, column=0, sticky="nsew", padx=24, pady=12)
        content.grid_columnconfigure(0, weight=2)
        content.grid_columnconfigure(1, weight=1)
        content.grid_rowconfigure(1, weight=1)

        self._build_action_card(content).grid(
            row=0, column=0, sticky="new", padx=(0, 12), pady=(0, 12)
        )
        self._build_run_info(content).grid(
            row=0, column=1, sticky="new", padx=(12, 0), pady=(0, 12)
        )
        self._build_results(content).grid(
            row=1, column=0, columnspan=2, sticky="nsew", pady=(12, 0)
        )

        self._build_health_bar().grid(row=2, column=0, sticky="ew", padx=24, pady=(12, 24))

    def _build_header(self) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self._root, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            frame,
            text="INSO_V1.0",
            font=_FONT_TITLE,
            text_color=_TEXT,
        )
        title.grid(row=0, column=0, sticky="w")

        self._status_badge = ctk.CTkLabel(
            frame,
            text="已停止",
            font=("Microsoft YaHei UI", 14, "bold"),
            text_color=_TEXT,
            fg_color=_GRAY,
            corner_radius=16,
            width=160,
        )
        self._status_badge.grid(row=0, column=1, sticky="e")

        return frame

    def _build_action_card(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        card = ctk.CTkFrame(parent, fg_color=_CARD_BG, corner_radius=16)
        card.grid_columnconfigure(0, weight=1)

        label = ctk.CTkLabel(
            card,
            text="核心操作",
            font=_FONT_LABEL,
            text_color=_TEXT_SECONDARY,
        )
        label.grid(row=0, column=0, sticky="w", padx=24, pady=(20, 8))

        self._action_button = ctk.CTkButton(
            card,
            text="启动自动调研",
            font=("Microsoft YaHei UI", 14, "bold"),
            fg_color=_GREEN,
            hover_color="#059669",
            text_color="white",
            height=52,
            corner_radius=12,
            command=self._on_action,
        )
        self._action_button.grid(row=1, column=0, sticky="ew", padx=24, pady=(8, 20))

        return card

    def _build_run_info(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        card = ctk.CTkFrame(parent, fg_color=_CARD_BG, corner_radius=16)
        card.grid_columnconfigure((0, 1, 2), weight=1)

        title = ctk.CTkLabel(
            card,
            text="运行信息",
            font=_FONT_LABEL,
            text_color=_TEXT_SECONDARY,
        )
        title.grid(row=0, column=0, columnspan=3, sticky="w", padx=20, pady=(16, 8))

        self._run_info_labels: dict[str, ctk.CTkLabel] = {}
        info_items = [
            ("本轮发现订单", "0"),
            ("已完成", "0"),
            ("正在处理", "0"),
            ("待处理", "0"),
            ("下次轮询时间", "--"),
        ]
        positions = [(1, 0), (1, 1), (1, 2), (2, 0), (2, 1)]
        for (label_text, value), (row, col) in zip(info_items, positions, strict=True):
            cell = ctk.CTkFrame(card, fg_color="transparent")
            cell.grid(row=row, column=col, sticky="nsew", padx=8, pady=8)
            lbl = ctk.CTkLabel(
                cell,
                text=label_text,
                font=_FONT_SMALL,
                text_color=_TEXT_SECONDARY,
            )
            lbl.pack(anchor="w")
            val = ctk.CTkLabel(
                cell,
                text=value,
                font=_FONT_NUMBER,
                text_color=_TEXT,
            )
            val.pack(anchor="w")
            self._run_info_labels[label_text] = val

        return card

    def _build_results(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=2)
        frame.grid_columnconfigure(1, weight=1)

        header = ctk.CTkLabel(
            frame,
            text="本次运行结果",
            font=_FONT_LABEL,
            text_color=_TEXT_SECONDARY,
        )
        header.grid(row=0, column=0, sticky="w", pady=(0, 8))

        toolbar = ctk.CTkFrame(frame, fg_color="transparent")
        toolbar.grid(row=0, column=1, sticky="e", pady=(0, 8))
        ctk.CTkButton(
            toolbar,
            text="打开 Excel",
            font=_FONT_SMALL,
            width=100,
            height=32,
            fg_color=_CARD_BG,
            hover_color=_CARD_BG_HOVER,
            text_color=_TEXT,
            command=self._backend.open_excel,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            toolbar,
            text="打开结果目录",
            font=_FONT_SMALL,
            width=110,
            height=32,
            fg_color=_CARD_BG,
            hover_color=_CARD_BG_HOVER,
            text_color=_TEXT,
            command=self._backend.open_results_dir,
        ).pack(side="left")

        table_card = ctk.CTkFrame(frame, fg_color=_CARD_BG, corner_radius=16)
        table_card.grid(row=1, column=0, sticky="nsew", padx=(0, 12))
        table_card.grid_rowconfigure(0, weight=1)
        table_card.grid_columnconfigure(0, weight=1)

        columns = ("model", "brand", "quantity", "stock", "min_price", "total", "status")
        self._tree = ttk.Treeview(
            table_card,
            columns=columns,
            show="headings",
            selectmode="browse",
        )
        self._tree.heading("model", text="型号")
        self._tree.heading("brand", text="品牌")
        self._tree.heading("quantity", text="数量")
        self._tree.heading("stock", text="货量")
        self._tree.heading("min_price", text="最低参考价")
        self._tree.heading("total", text="总价")
        self._tree.heading("status", text="状态")
        self._tree.column("model", width=160, anchor="w")
        self._tree.column("brand", width=80, anchor="w")
        self._tree.column("quantity", width=60, anchor="e")
        self._tree.column("stock", width=80, anchor="e")
        self._tree.column("min_price", width=100, anchor="e")
        self._tree.column("total", width=100, anchor="e")
        self._tree.column("status", width=100, anchor="center")
        self._tree.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)

        scrollbar = ttk.Scrollbar(
            table_card, orient="vertical", command=self._tree.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns", pady=12)
        self._tree.configure(yscrollcommand=scrollbar.set)

        style = ttk.Style(self._tree)
        style.theme_use("default")
        style.configure(
            "Treeview",
            background=_CARD_BG,
            foreground=_TEXT,
            fieldbackground=_CARD_BG,
            rowheight=28,
            borderwidth=0,
        )
        style.configure(
            "Treeview.Heading",
            background=_CARD_BG,
            foreground=_TEXT_SECONDARY,
            borderwidth=0,
            font=_FONT_SMALL,
        )
        style.map("Treeview", background=[("selected", _CARD_BG_HOVER)])
        style.configure(
            "Vertical.TScrollbar",
            background=_CARD_BG,
            troughcolor=_BG,
            bordercolor=_BG,
            arrowcolor=_TEXT_SECONDARY,
        )

        self._tree.bind("<<TreeviewSelect>>", self._on_row_select)

        detail_card = ctk.CTkFrame(frame, fg_color=_CARD_BG, corner_radius=16)
        detail_card.grid(row=1, column=1, sticky="nsew", padx=(12, 0))
        detail_card.grid_rowconfigure(1, weight=1)
        detail_card.grid_columnconfigure(0, weight=1)

        detail_title = ctk.CTkLabel(
            detail_card,
            text="订单详情",
            font=_FONT_LABEL,
            text_color=_TEXT_SECONDARY,
        )
        detail_title.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 8))

        self._detail_container = ctk.CTkFrame(detail_card, fg_color="transparent")
        self._detail_container.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self._detail_empty = ctk.CTkLabel(
            self._detail_container,
            text="点击左侧订单查看详情",
            font=_FONT_SMALL,
            text_color=_TEXT_SECONDARY,
        )
        self._detail_empty.pack(expand=True)

        return frame

    def _build_health_bar(self) -> ctk.CTkFrame:
        bar = ctk.CTkFrame(self._root, fg_color=_CARD_BG, corner_radius=16)
        bar.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        label = ctk.CTkLabel(
            bar,
            text="健康状态",
            font=_FONT_LABEL,
            text_color=_TEXT_SECONDARY,
        )
        label.grid(row=0, column=0, sticky="w", padx=16, pady=12)

        self._health_labels: dict[str, ctk.CTkLabel] = {}
        for idx, name in enumerate(
            ["Google Sheets", "Browser/CDP", "Credential", "Research"], start=1
        ):
            cell = ctk.CTkFrame(bar, fg_color="transparent")
            cell.grid(row=0, column=idx, sticky="nsew", padx=8, pady=8)
            name_lbl = ctk.CTkLabel(
                cell,
                text=name,
                font=_FONT_SMALL,
                text_color=_TEXT_SECONDARY,
            )
            name_lbl.pack(anchor="w")
            status_lbl = ctk.CTkLabel(
                cell,
                text="正常",
                font=("Microsoft YaHei UI", 12, "bold"),
                text_color=_GREEN,
            )
            status_lbl.pack(anchor="w")
            self._health_labels[name] = status_lbl

        return bar

    def _wire_backend(self) -> None:
        def on_status(status: RunSession) -> None:
            self._root.after(0, lambda: self._update_status(status))

        def on_log(entry: LogEntry) -> None:
            self._root.after(0, lambda: self._append_log(entry))

        self._backend.on_status_change(on_status)
        self._backend.on_log(on_log)

    def _schedule_tick(self) -> None:
        """Slow background poll to keep time labels fresh."""
        self._update_status(self._backend.get_status())
        self._root.after(1000, self._schedule_tick)

    def _on_action(self) -> None:
        if self._status.state == RunState.STOPPED:
            self._backend.start()
        elif self._status.state == RunState.RUNNING:
            self._backend.request_stop_after_cycle()
        else:
            logger.debug("忽略操作：当前状态 %s", self._status.state.value)

    def _update_status(self, status: RunSession) -> None:
        self._status = status

        # Header badge
        self._status_badge.configure(
            text=status.state.value,
            fg_color=_status_color(status.state.value),
        )

        # Action button
        if status.state == RunState.STOPPED:
            self._action_button.configure(
                text="启动自动调研",
                fg_color=_GREEN,
                hover_color="#059669",
                state="normal",
            )
        elif status.state == RunState.RUNNING:
            self._action_button.configure(
                text="本轮结束后停止",
                fg_color=_YELLOW,
                hover_color="#D97706",
                state="normal",
            )
        else:
            self._action_button.configure(
                text=status.state.value,
                fg_color=_GRAY,
                state="disabled",
            )

        # Run info
        self._run_info_labels["本轮发现订单"].configure(text=str(status.orders_found))
        self._run_info_labels["已完成"].configure(text=str(status.completed))
        self._run_info_labels["正在处理"].configure(text=str(status.in_progress))
        self._run_info_labels["待处理"].configure(text=str(status.pending))
        self._run_info_labels["下次轮询时间"].configure(text=_format_time(status.next_poll_at))

        # Refresh results
        self._refresh_results()

        # Health
        health = self._backend.get_health()
        for item in health.items:
            lbl = self._health_labels.get(item.component)
            if lbl is not None:
                lbl.configure(text=item.status, text_color=_status_color(item.status))

    def _refresh_results(self) -> None:
        orders = self._backend.get_current_run_results()
        # Avoid full redraw when possible, but keep it simple for V1.
        for item in self._tree.get_children():
            self._tree.delete(item)
        for order in orders:
            self._tree.insert(
                "",
                "end",
                iid=order.inquiry_id,
                values=(
                    order.model,
                    order.brand or "--",
                    order.quantity,
                    order.stock,
                    f"¥{order.min_reference_price:.2f}" if order.min_reference_price else "--",
                    f"¥{order.total_price:.2f}" if order.total_price else "--",
                    order.status.value,
                ),
                tags=(order.status.value,),
            )

    def _on_row_select(self, _event: Any) -> None:
        selection = self._tree.selection()
        if not selection:
            return
        inquiry_id = selection[0]
        order = next(
            (o for o in self._backend.get_current_run_results() if o.inquiry_id == inquiry_id),
            None,
        )
        if order is None:
            return
        self._selected_order = order
        self._render_detail(order)

    def _render_detail(self, order: Order) -> None:
        for widget in self._detail_container.winfo_children():
            widget.destroy()

        header = ctk.CTkLabel(
            self._detail_container,
            text=f"{order.model}",
            font=("Microsoft YaHei UI", 14, "bold"),
            text_color=_TEXT,
        )
        header.pack(anchor="w", pady=(0, 4))

        sub = ctk.CTkLabel(
            self._detail_container,
            text=f"品牌: {order.brand or '--'} | 数量: {order.quantity}",
            font=_FONT_SMALL,
            text_color=_TEXT_SECONDARY,
        )
        sub.pack(anchor="w", pady=(0, 12))

        for ev in order.evidence:
            row = ctk.CTkFrame(self._detail_container, fg_color="transparent")
            row.pack(fill="x", pady=4)
            source_color = _GREEN if ev.unit_price is not None else _YELLOW
            name = ctk.CTkLabel(
                row,
                text=ev.source,
                font=_FONT_SMALL,
                text_color=source_color,
                width=80,
            )
            name.pack(side="left")
            price_text = (
                f"¥{ev.unit_price:.2f}"
                if ev.unit_price is not None
                else (ev.remark or "无报价")
            )
            price = ctk.CTkLabel(
                row,
                text=price_text,
                font=_FONT_SMALL,
                text_color=_TEXT,
            )
            price.pack(side="left", padx=(8, 0))
            stock = ctk.CTkLabel(
                row,
                text=f"库存 {ev.stock}" if ev.stock is not None else "",
                font=_FONT_SMALL,
                text_color=_TEXT_SECONDARY,
            )
            stock.pack(side="right")

        if order.remark:
            remark = ctk.CTkLabel(
                self._detail_container,
                text=f"备注: {order.remark}",
                font=_FONT_SMALL,
                text_color=_YELLOW,
                wraplength=300,
            )
            remark.pack(anchor="w", pady=(12, 0))

    def _append_log(self, entry: LogEntry) -> None:
        # For V1, logs are collected but not displayed in a heavy console.
        # Future: stream to a collapsible log panel.
        logger.debug("%s %s", entry.level, entry.message)

    def run(self) -> None:
        self._root.mainloop()

    def _on_close(self) -> None:
        try:
            self._backend.shutdown()
        except Exception as exc:  # noqa: BLE001 - defensive close path
            logger.error("Backend shutdown error: %s", exc)
        self._root.destroy()
