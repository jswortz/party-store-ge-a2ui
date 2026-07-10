# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Deterministic Party Store A2A executor for Gemini Enterprise (GE).

Instead of relying on the LLM to call `send_a2ui_json_to_client` (unreliable), this routes each
request to the BigQuery-backed tools and assembles the A2UI screen in Python, then emits each A2UI
command as a DataPart tagged `mimeType=application/json+a2ui`. This mirrors the proven pattern in
rag_pg_ip/pg_razor_agent/agent_executor.py, which renders A2UI in GE end-to-end over Cloud Run.

GE cannot invoke A2A agents on Vertex Agent Runtime, so this executor is served over HTTP on Cloud
Run (see app/fast_api_app.py). Without the `application/json+a2ui` DataPart tag GE silently drops the UI.
"""
import re

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import DataPart, Part, Task, TextPart, UnsupportedOperationError
from a2a.utils import new_task
from a2a.utils.errors import ServerError

from app import tools

A2UI_MIMETYPE = "application/json+a2ui"

# Known BigQuery product ids (party_store dataset). Used to resolve free-text product names.
KNOWN_PRODUCTS = [
    "halloween_costume",
    "halloween_skeleton",
    "party_balloons",
    "birthday_candles",
]


def _ui_parts(text: str, ui_messages: list) -> list:
    """Leading conversational TextPart + A2UI DataParts (tagged for GE rendering)."""
    parts = [Part(root=TextPart(text=text))]
    for msg in ui_messages:
        parts.append(Part(root=DataPart(data=msg, metadata={"mimeType": A2UI_MIMETYPE})))
    return parts


def _normalize_product(raw: str) -> str:
    """Map free text like 'birthday candles' / 'Halloween Costumes' to a product_id."""
    if not raw:
        return ""
    s = raw.strip().lower()
    s = re.sub(r"[^a-z0-9\s_]", " ", s)
    s = re.sub(r"\s+", "_", s).strip("_")
    if not s:
        return ""
    # Exact match first, then singular/plural and substring fallbacks against known products.
    if s in KNOWN_PRODUCTS:
        return s
    candidates = {s, s.rstrip("s"), s + "s"}
    for p in KNOWN_PRODUCTS:
        if p in candidates or s in p or p.rstrip("s") in candidates:
            return p
    return s


class PartyStoreExecutor(AgentExecutor):
    """Routes A2A requests to the supply-chain tools and renders A2UI deterministically."""

    # --- request parsing ---------------------------------------------------
    def _parse(self, context: RequestContext):
        action, ctx, text = None, {}, ""
        if context.message and context.message.parts:
            for part in context.message.parts:
                root = part.root
                if isinstance(root, DataPart) and isinstance(root.data, dict) and "userAction" in root.data:
                    ua = root.data["userAction"] or {}
                    action = ua.get("name")
                    ctx = ua.get("context", {}) or {}
                elif isinstance(root, TextPart) and root.text:
                    text = root.text
        if not text:
            try:
                text = context.get_user_input() or ""
            except Exception:  # noqa: BLE001
                text = ""
        return action, ctx, text

    @staticmethod
    def _ctx_val(ctx, key: str) -> str:
        """Read a value from a button-action context (dict, list-of-{key,value}, or scalar shapes)."""
        v = ""
        if isinstance(ctx, dict):
            v = ctx.get(key, "")
        elif isinstance(ctx, list):
            for e in ctx:
                if isinstance(e, dict):
                    if e.get("key") == key:
                        v = e.get("value", ""); break
                    if key in e:
                        v = e[key]; break
        if isinstance(v, dict):
            v = v.get("literalString") or v.get("path") or ""
        if isinstance(v, list):
            v = v[0] if v else ""
        return str(v) if v is not None else ""

    # --- screen builders ---------------------------------------------------
    def _inventory(self) -> list:
        res = tools.query_inventory_status()
        if res.get("status") != "success":
            return [Part(root=TextPart(text=f"Sorry, I couldn't load inventory: {res.get('message')}"))]
        inv = res.get("inventory", [])
        low = [i for i in inv if "Low" in i.get("status", "")]
        if low:
            names = ", ".join(i["product_id"] for i in low)
            summary = (f"Here's your current inventory ({len(inv)} products). "
                       f"⚠️ {len(low)} need attention: {names}.")
        else:
            summary = f"Here's your current inventory ({len(inv)} products). All stock levels look healthy."
        return _ui_parts(summary, res["a2ui_payload"])

    def _forecast(self, product_id: str) -> list:
        product_id = product_id or "halloween_costume"
        res = tools.get_sales_forecast(product_id)
        if res.get("status") != "success":
            return [Part(root=TextPart(text=f"Sorry, I couldn't build a forecast: {res.get('message')}"))]
        fc = res.get("forecast", [])
        peak = max(fc, key=lambda r: r["sales"]) if fc else None
        peak_note = f" Projected peak is {peak['sales']} units in {peak['date']}." if peak else ""
        summary = f"Here's the Jul–Dec 2026 sales forecast for {product_id}.{peak_note}"
        return _ui_parts(summary, res["a2ui_payload"])

    def _purchase_order(self, product_id: str, quantity: int) -> list:
        product_id = product_id or "halloween_costume"
        res = tools.create_purchase_order(product_id, quantity)
        if res.get("status") != "success":
            return [Part(root=TextPart(text=f"Sorry, I couldn't create the purchase order: {res.get('message')}"))]
        summary = (f"✅ Purchase order {res['po_id']} created for {quantity} × {product_id}. "
                   f"Estimated delivery {res['estimated_delivery']}.")
        return _ui_parts(summary, res["a2ui_payload"])

    # --- main --------------------------------------------------------------
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        action, ctx, text = self._parse(context)
        # Echo requested extensions so clients (e.g. Gemini Enterprise) accept the response.
        for ext in (context.requested_extensions or []):
            try:
                context.add_activated_extension(ext)
            except Exception:  # noqa: BLE001
                pass

        print(f"--- PartyStoreExecutor: action={action} text={text!r} ctx={ctx} ---")
        low = (text or "").lower().strip()

        try:
            if action == "view_forecast" or low.startswith(("forecast", "sales forecast", "show sales forecast", "show forecast")):
                product = self._ctx_val(ctx, "product_id")
                if not product:
                    m = re.search(r"forecast(?:\s+for)?\s+(.+)", low)
                    product = _normalize_product(m.group(1)) if m else ""
                parts = self._forecast(product)
            elif action == "order_more" or low.startswith(("order", "purchase", "reorder", "buy")):
                product = self._ctx_val(ctx, "product_id")
                qty_raw = self._ctx_val(ctx, "quantity")
                if not product or not qty_raw:
                    m = re.search(r"(?:order|purchase|reorder|buy)\s+(\d+)\s+(.+)", low)
                    if m:
                        qty_raw = qty_raw or m.group(1)
                        product = product or _normalize_product(m.group(2))
                try:
                    quantity = int(qty_raw) if qty_raw else 500
                except (TypeError, ValueError):
                    quantity = 500
                parts = self._purchase_order(product, quantity)
            elif action in ("go_home", "view_inventory") or any(
                w in low for w in ("inventory", "dashboard", "stock", "home", "status", "overview")
            ) or not low:
                parts = self._inventory()
            else:
                parts = self._inventory()
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            parts = [Part(root=TextPart(text=f"Sorry, I hit an error: {e}"))]

        task = context.current_task
        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue, task.id, task.context_id)
        await updater.start_work()
        await updater.add_artifact(parts, name="response")
        await updater.complete()

    async def cancel(self, request: RequestContext, event_queue: EventQueue) -> Task | None:
        raise ServerError(error=UnsupportedOperationError())
