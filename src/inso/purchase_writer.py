"""Purchase draft preparation using the existing INSO action boundary.

The Save Data path is durable-before-dispatch and remains closed by
``ProductionWriteGate``. There is deliberately no Save-and-Send or Send path.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from urllib.parse import urlsplit

from .session import OperationPage, SecurityViolation
from .write_safety import (
    ControlCandidate,
    ControlSemantics,
    FeatureGate,
    InsoDraftActions,
    ProductionWriteGate,
    SelectorRegistry,
    WriteAction,
)

AI_ENTRY_PATH = "/skins/etaoerp/product/Import_ai.aspx"
_QUOTATION_TYPES = frozenset({"需要问全价格", "普通询价"})
_CUSTOMERS = frozenset({"Win Source Elec. Tech. Ltd"})
_PURCHASERS = frozenset({"颜浩坚", "陈熙"})


@dataclass(frozen=True, slots=True)
class AiRecognitionResult:
    """Read-only value shape from the verified single-row AI result area."""

    model: str
    brand: str
    quantity: int
    ready: bool


class AiResultReader(Protocol):
    def read(self) -> AiRecognitionResult | None: ...


class ParentProductFields(Protocol):
    """Narrow parent-form product-field seam; selectors are injected by runtime."""

    def set_model(self, value: str) -> None: ...

    def set_brand(self, value: str) -> None: ...

    def set_quantity(self, value: int) -> None: ...

    def read_model(self) -> str | None: ...

    def read_brand(self) -> str | None: ...

    def read_quantity(self) -> int | None: ...


class SaveDispatchStore(Protocol):
    """Narrow Workflow persistence seam; the INSO module owns no state rules."""

    def begin_save_dispatch(self, inquiry_id: str, *, at: datetime) -> None: ...


class PlaywrightAiResultReader:
    """Read the verified one-row AI preview and ready button state."""

    def __init__(self, ai_page: OperationPage) -> None:
        self._ai_page = ai_page

    def read(self) -> AiRecognitionResult | None:
        page = self._ai_page.page
        _require_ai_page(page.url)
        ready = page.locator("button#ai-recognize")
        if ready.count() != 1 or ready.inner_text().strip() != "重新识别":
            return None
        rows = page.locator("#preview-body > tr")
        if rows.count() != 1:
            return None
        row = rows.nth(0)
        fields = {
            name: row.locator(f'input[data-f="{field}"]')
            for name, field in (
                ("model", "PartNo"),
                ("brand", "Brand"),
                ("quantity", "Qty"),
            )
        }
        if any(locator.count() != 1 for locator in fields.values()):
            return None
        model = fields["model"].input_value()
        brand = fields["brand"].input_value()
        quantity_text = fields["quantity"].input_value()
        if not model or not brand or not quantity_text.isdecimal():
            return None
        quantity = int(quantity_text)
        if quantity <= 0:
            return None
        return AiRecognitionResult(model, brand, quantity, ready=True)


@dataclass(frozen=True, slots=True)
class _Binding:
    selector_id: str
    scope_id: str
    selector: str
    semantics: ControlSemantics
    frame: str


_BINDINGS: dict[WriteAction, _Binding] = {
    WriteAction.NEW_DRAFT: _Binding(
        "product_add_control",
        "inquiry-list",
        "button#product_add_",
        ControlSemantics(
            "button", "新增", "新增", (("id", "product_add_"), ("type", "button"))
        ),
        "list",
    ),
    WriteAction.SET_CUSTOMER: _Binding(
        "customer-name-input",
        "purchase-form",
        "input#CompanyName",
        ControlSemantics(
            "textbox",
            "",
            "",
            (("id", "CompanyName"), ("type", "text")),
        ),
        "form",
    ),
    WriteAction.SET_PURCHASER: _Binding(
        "purchaser-input",
        "purchase-form",
        "input#UserName_text",
        ControlSemantics(
            "textbox",
            "",
            "",
            (("id", "UserName_text"), ("type", "text")),
        ),
        "form",
    ),
    WriteAction.SET_QUOTATION_TYPE: _Binding(
        "quotation-routing-input",
        "purchase-form",
        "input#ImpValueF",
        ControlSemantics(
            "textbox",
            "",
            "",
            (("id", "ImpValueF"), ("type", "text")),
        ),
        "form",
    ),
    WriteAction.SET_AI_INPUT: _Binding(
        "ai-input",
        "ai-entry",
        "textarea#paste-area",
        ControlSemantics(
            "textbox",
            "",
            "",
            (("id", "paste-area"), ("type", "textarea")),
        ),
        "ai",
    ),
    WriteAction.RUN_AI_RECOGNITION: _Binding(
        "ai-recognition-button",
        "ai-entry",
        "button#ai-recognize",
        ControlSemantics(
            "button",
            "AI 智能识别",
            "AI 智能识别",
            (("id", "ai-recognize"), ("type", "button")),
        ),
        "ai",
    ),
    WriteAction.SAVE_DATA: _Binding(
        "save-data-control",
        "purchase-form",
        "button#btnSave",
        ControlSemantics(
            "button", "保存", "保存", (("id", "btnSave"),)
        ),
        "form",
    ),
}


class _PlaywrightActionPort:
    """Private exact-selector bridge; callers only receive business methods."""

    def __init__(self, form_page: OperationPage, ai_page: OperationPage) -> None:
        self._form_page = form_page
        self._ai_page = ai_page

    def _locator(self, binding: _Binding) -> Any:
        if binding.frame == "list":
            _require_inso_origin(self._form_page.page.url)
            return self._form_page.page.frame_locator(
                "iframe#iframe_YeWuXJ_frame"
            ).locator(binding.selector)
        if binding.frame == "form":
            _require_inso_origin(self._form_page.page.url)
            return self._form_page.page.frame_locator(
                "iframe#winIframealert_enquiry"
            ).locator(binding.selector)
        if binding.frame == "ai":
            page = self._ai_page.page
            _require_ai_page(page.url)
            return page.locator(binding.selector)
        raise SecurityViolation("unknown INSO selector scope")

    def _ai_page_is_ready(self) -> bool:
        try:
            _require_ai_page(self._ai_page.page.url)
        except SecurityViolation:
            return False
        return True

    def _candidate(self, action: WriteAction) -> tuple[ControlCandidate, ...]:
        binding = _BINDINGS[action]
        locator = self._locator(binding)
        metadata = locator.evaluate_all(
            """elements => elements.map(e => {
                const tag = e.tagName.toLowerCase();
                const text = tag === 'button' ? (e.innerText || '').trim() : '';
                const labels = e.labels ? [...e.labels].map(l => (l.innerText || '').trim()) : [];
                const label = labels.find(Boolean) || '';
                const labelledBy = (e.getAttribute('aria-labelledby') || '')
                    .split(/\\s+/).filter(Boolean)
                    .map(id => e.ownerDocument.getElementById(id)?.innerText?.trim() || '')
                    .filter(Boolean).join(' ');
                const role = tag === 'button' ? 'button' : 'textbox';
                return {
                    role,
                    accessibleName: e.getAttribute('aria-label') || labelledBy || label || text,
                    visibleText: text,
                    id: e.id || '',
                    type: e.type || tag,
                    enabled: !e.disabled,
                    visible: !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length)
                        && getComputedStyle(e).visibility !== 'hidden'
                        && getComputedStyle(e).display !== 'none'
                };
            })"""
        )
        return tuple(
            ControlCandidate(
                binding.selector_id,
                binding.scope_id,
                ControlSemantics(
                    item["role"],
                    item["accessibleName"],
                    item["visibleText"],
                    (("id", item["id"]),)
                    if action is WriteAction.SAVE_DATA
                    else (("id", item["id"]), ("type", item["type"])),
                ),
                enabled=item["enabled"],
                visible=item["visible"],
            )
            for item in metadata
        )

    def candidates(self) -> tuple[ControlCandidate, ...]:
        return tuple(
            candidate
            for action in _BINDINGS
            if _BINDINGS[action].frame != "ai" or self._ai_page_is_ready()
            for candidate in self._candidate(action)
        )

    def dispatch_validated(
        self, action: WriteAction, control: ControlCandidate, value: str | None
    ) -> None:
        binding = _BINDINGS.get(action)
        if binding is None:
            raise SecurityViolation("action has no live INSO dispatch binding")
        current = self._candidate(action)
        if len(current) != 1 or current[0] != control:
            raise SecurityViolation("INSO control changed before dispatch")
        locator = self._locator(binding)

        if action is WriteAction.NEW_DRAFT:
            locator.click()
            return
        if action in {
            WriteAction.SET_CUSTOMER,
            WriteAction.SET_PURCHASER,
            WriteAction.SET_AI_INPUT,
        }:
            if value is None:
                raise SecurityViolation("field value is required")
            locator.fill(value)
            if locator.input_value() != value:
                raise SecurityViolation("field read-back did not match input")
            if action is WriteAction.SET_PURCHASER:
                purchaser_id = self._form_page.page.frame_locator(
                    "iframe#winIframealert_enquiry"
                ).locator("input#UserName")
                if purchaser_id.count() != 1 or not purchaser_id.input_value():
                    raise SecurityViolation("purchaser selection was not confirmed")
            return
        if action is WriteAction.SET_QUOTATION_TYPE:
            if value not in _QUOTATION_TYPES:
                raise SecurityViolation("quotation type is not allowlisted")
            locator.click()
            menu = self._form_page.page.frame_locator(
                "iframe#winIframealert_enquiry"
            ).locator(".select-menu-modal .select-menu-item")
            matches = [item for item in menu.all() if item.inner_text().strip() == value]
            if len(matches) != 1:
                raise SecurityViolation("quotation option is missing or ambiguous")
            matches[0].click()
            if locator.input_value() != value:
                raise SecurityViolation("quotation type read-back did not match")
            return
        if action is WriteAction.RUN_AI_RECOGNITION:
            locator.click()
            return
        if action is WriteAction.SAVE_DATA:
            locator.click()
            return
        raise SecurityViolation("action is not available in the purchase writer")


class InsoPurchaseWriter:
    """Draft actions and one closed, durable-before-dispatch Save Data path."""

    def __init__(
        self,
        *,
        form_page: OperationPage,
        ai_page: OperationPage,
        gate: FeatureGate | None = None,
        ai_result_reader: AiResultReader | None = None,
    ) -> None:
        self._gate = gate or ProductionWriteGate()
        self._form_page = form_page
        self._ai_page = ai_page
        self._ai_result_reader = ai_result_reader or PlaywrightAiResultReader(ai_page)
        self._port = _PlaywrightActionPort(form_page, ai_page)
        self._registry = SelectorRegistry()
        for action, binding in _BINDINGS.items():
            self._registry.register(
                action,
                binding.selector_id,
                binding.scope_id,
                binding.semantics,
            )
        # Save-and-Send and Send have no action binding or dispatch path.
        for denied in ("#btnSave2", "#bcSend"):
            self._registry.deny(denied)
        self._actions = InsoDraftActions(
            gate=self._gate,
            registry=self._registry,
            candidate_source=self._port,
            dispatcher=self._port,
        )

    def new_draft(self) -> None:
        self._actions.new_draft()

    def set_customer(self, value: str) -> None:
        if value not in _CUSTOMERS:
            raise SecurityViolation("customer is not allowlisted")
        self._actions.set_customer(value)

    def set_purchaser(self, value: str) -> None:
        if value not in _PURCHASERS:
            raise SecurityViolation("purchaser is not allowlisted")
        purchaser_id = self._form_page.page.frame_locator(
            "iframe#winIframealert_enquiry"
        ).locator("input#UserName")
        if purchaser_id.count() != 1 or purchaser_id.input_value():
            raise SecurityViolation("purchaser field is not blank and unique")
        self._actions.set_purchaser(value)

    def set_quotation_type(self, _value: str) -> None:
        if _value not in _QUOTATION_TYPES:
            raise SecurityViolation("quotation type is not allowlisted")
        self._actions.set_quotation_type(_value)

    def open_ai_entry(self) -> None:
        self._gate.require_open()
        current = urlsplit(self._form_page.page.url)
        if (
            current.scheme != "https"
            or current.hostname != "yingsuo.alperp.cn"
            or current.username
            or current.password
        ):
            raise SecurityViolation("INSO origin is not verified")
        self._ai_page.page.goto(f"{current.scheme}://{current.netloc}{AI_ENTRY_PATH}")

    def set_ai_input(self, value: str) -> None:
        self._actions.set_ai_input(value)

    def run_ai_recognition(self) -> None:
        self._actions.run_ai_recognition()

    def read_ai_result(self) -> AiRecognitionResult:
        if self._ai_result_reader is None:
            raise SecurityViolation("AI result selectors are not verified")
        result = self._ai_result_reader.read()
        if result is None or not result.ready:
            raise SecurityViolation("AI recognition is not ready")
        return result

    def save_data(
        self, store: SaveDispatchStore, inquiry_id: str, *, at: datetime
    ) -> None:
        """Dispatch only after durable AI_RECOGNIZED state and exact Save control.

        ``begin_save_dispatch`` persists UNKNOWN before the final semantic
        re-check and private click. Any failure after that boundary stays
        UNKNOWN and must be reconciled; this method never retries.
        """

        self._gate.require_open()
        self._registry.resolve(WriteAction.SAVE_DATA, self._port.candidates())
        # The store rejects every state except AI_RECOGNIZED, including a
        # previous UNKNOWN outcome, before the private dispatcher can click.
        store.begin_save_dispatch(inquiry_id, at=at)
        self._actions.save_data()


def _require_inso_origin(url: str) -> None:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "yingsuo.alperp.cn"
        or parsed.username
        or parsed.password
    ):
        raise SecurityViolation("INSO origin is not verified")


def _require_ai_page(url: str) -> None:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "yingsuo.alperp.cn"
        or parsed.path != AI_ENTRY_PATH
        or parsed.username
        or parsed.password
        or parsed.fragment
        or parsed.query not in {"", "BillPage=Enquiry&VendorID=&h=510"}
    ):
        raise SecurityViolation("AI page identity is not verified")
