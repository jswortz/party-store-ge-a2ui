import datetime
import logging
import json
from google.cloud import bigquery
from google.adk.tools import ToolContext

from app import ui_builder

PROJECT_ID = "wortz-project-352116"
DATASET_ID = "party_store"

logger = logging.getLogger(__name__)

def get_bq_client():
    return bigquery.Client(project=PROJECT_ID)


# --- A2UI component helpers ------------------------------------------------
def _ctx(key: str, literal: str) -> dict:
    """A button-action context entry: {"key": K, "value": {"literalString": V}}."""
    return {"key": key, "value": {"literalString": str(literal)}}


def _button(eid: str, label: str, action: str, context: list = None, primary: bool = False) -> list:
    """Native A2UI Button + its child Text. Returns [button_component, text_component].

    The click round-trips to the executor as a DataPart whose data has a "userAction"
    {name: action, context: [...]}. Mirrors rag_pg_ip/pg_razor_agent/ui_builder._button.
    """
    tid = f"txt_{eid}"
    act = {"name": action}
    if context:
        act["context"] = context
    return [
        {"id": eid, "component": {"Button": {"child": tid, "primary": primary, "action": act}}},
        {"id": tid, "component": {"Text": {"text": {"literalString": label}, "usageHint": "body"}}},
    ]


def _screen(surface: str, panel_html: str, height: int, buttons: list) -> list:
    """Assemble a screen: a branded WebFrameSrcdoc panel + native buttons underneath.

    buttons: list of (eid, label, action, context, primary) tuples.
    """
    btn_ids = [b[0] for b in buttons]
    btn_components = []
    for eid, label, action, context, primary in buttons:
        btn_components += _button(eid, label, action, context=context, primary=primary)
    components = [
        {"id": "root-layout", "component": {"Column": {"children": {"explicitList": ["panel"] + btn_ids}}}},
        ui_builder._webframe("panel", panel_html, height),
        *btn_components,
    ]
    return [
        {"beginRendering": {"surfaceId": surface, "root": "root-layout"}},
        {"surfaceUpdate": {"surfaceId": surface, "components": components}},
    ]


# --- Inventory -------------------------------------------------------------
def _fetch_inventory() -> list:
    """Query current inventory (received shipments minus sold orders) from BigQuery."""
    client = get_bq_client()
    query = f"""
        WITH received AS (
          SELECT product_id, SUM(quantity) as total_received
          FROM `{PROJECT_ID}.{DATASET_ID}.shipments`
          WHERE receive_date IS NOT NULL
          GROUP BY product_id
        ),
        sold AS (
          SELECT product_id, SUM(quantity) as total_sold
          FROM `{PROJECT_ID}.{DATASET_ID}.orders`
          GROUP BY product_id
        )
        SELECT
          p.product_id,
          COALESCE(r.total_received, 0) as received,
          COALESCE(s.total_sold, 0) as sold,
          (COALESCE(r.total_received, 0) - COALESCE(s.total_sold, 0)) as current_stock
        FROM (
          SELECT DISTINCT product_id FROM `{PROJECT_ID}.{DATASET_ID}.shipments`
          UNION DISTINCT
          SELECT DISTINCT product_id FROM `{PROJECT_ID}.{DATASET_ID}.orders`
        ) p
        LEFT JOIN received r ON p.product_id = r.product_id
        LEFT JOIN sold s ON p.product_id = s.product_id
    """
    query_job = client.query(query)
    results = query_job.result()
    inventory = []
    for row in results:
        # Simple threshold for low stock alert
        status = "Good"
        if row.product_id in ["halloween_costume", "halloween_skeleton"]:
            # For seasonal items, warn early if stock is low before the season ramps.
            if row.current_stock < 200:
                status = "Low Stock (Season Coming)"
        else:
            if row.current_stock < 50:
                status = "Low Stock"

        inventory.append({
            "product_id": row.product_id,
            "received": row.received,
            "sold": row.sold,
            "current_stock": row.current_stock,
            "status": status
        })
    return inventory


def build_inventory_payload(inventory: list) -> list:
    """A2UI: branded inventory dashboard panel + a context-aware 'view forecast' button."""
    height = min(320 + 64 * len(inventory), 1500)
    panel = ui_builder.inventory_panel_html(inventory)
    target = ui_builder.most_at_risk_seasonal(inventory)
    tname = ui_builder.product_meta(target)["name"]
    buttons = [
        ("view-forecast-btn", f"📈 View {tname} Forecast", "view_forecast",
         [_ctx("product_id", target)], True),
    ]
    return _screen("inventory-status", panel, height, buttons)


def query_inventory_status(tool_context: ToolContext = None) -> dict:
    """Queries the current inventory status for all products from BigQuery.

    Calculates current stock as received shipments minus sold orders.

    Returns:
        A dict containing a list of products with their current stock, received, and sold quantities.
    """
    try:
        inventory = _fetch_inventory()
        a2ui_payload = build_inventory_payload(inventory)
        if tool_context:
            tool_context.state["a2ui_payload_inventory"] = json.dumps(a2ui_payload)
        return {
            "status": "success",
            "inventory": inventory,
            "a2ui_payload": a2ui_payload,
            "a2ui_key": "inventory"
        }
    except Exception as e:
        logger.exception("Failed to query inventory")
        return {"status": "error", "message": str(e)}


# --- Forecast --------------------------------------------------------------
def _fetch_forecast(product_id: str) -> tuple:
    """Return (history_list, forecast) for a product using BigQuery order history.

    Forecasts Jul-Dec 2026 with seasonality for Halloween items.
    """
    client = get_bq_client()
    query = f"""
        SELECT
          EXTRACT(YEAR FROM order_date) as year,
          EXTRACT(MONTH FROM order_date) as month,
          SUM(quantity) as monthly_sales
        FROM `{PROJECT_ID}.{DATASET_ID}.orders`
        WHERE product_id = @product_id
        GROUP BY 1, 2
        ORDER BY 1, 2
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("product_id", "STRING", product_id)
        ]
    )
    query_job = client.query(query, job_config=job_config)
    results = query_job.result()

    history = {}
    for row in results:
        if row.year not in history:
            history[row.year] = {}
        history[row.year][row.month] = row.monthly_sales

    # Generate forecast for Jul-Dec 2026 (current date assumed July 2026).
    forecast = []
    is_seasonal = product_id in ["halloween_costume", "halloween_skeleton"]

    total_sales = 0
    count = 0
    for y in history:
        for m in history[y]:
            total_sales += history[y][m]
            count += 1
    avg_sales = total_sales / count if count > 0 else 10

    for month in range(7, 13):
        date_str = f"2026-{month:02d}"
        if is_seasonal:
            val_2025 = history.get(2025, {}).get(month, 0)
            if month == 10:
                projected = int(val_2025 * 1.1) if val_2025 > 0 else 800
            elif month == 9:
                projected = int(val_2025 * 1.1) if val_2025 > 0 else 200
            else:
                projected = val_2025 if val_2025 > 0 else 5
        else:
            projected = int(avg_sales)

        forecast.append({
            "date": date_str,
            "sales": projected,
            "type": "forecast"
        })

    history_list = []
    for y in sorted(history.keys()):
        for m in sorted(history[y].keys()):
            history_list.append({
                "date": f"{y}-{m:02d}",
                "sales": history[y][m],
                "type": "actual"
            })
    return history_list, forecast


def build_forecast_payload(product_id: str, history_list: list, forecast: list) -> list:
    """A2UI: branded forecast panel (inline-SVG chart + KPIs) + order/back buttons."""
    panel = ui_builder.forecast_panel_html(product_id, history_list, forecast)
    name = ui_builder.product_meta(product_id)["name"]
    buttons = [
        ("order-more-btn", f"🛒 Order 500 more {name}", "order_more",
         [_ctx("product_id", product_id), _ctx("quantity", "500")], True),
        ("back-home-btn", "🏠 Back to Inventory", "go_home", None, False),
    ]
    return _screen("sales-forecast", panel, 640, buttons)


def get_sales_forecast(product_id: str, tool_context: ToolContext = None) -> dict:
    """Generates sales forecast for a product for the next 6 months (Jul-Dec 2026).

    Uses historical sales data from BigQuery to project future sales,
    considering seasonality for seasonal products.

    Args:
        product_id: The ID of the product to forecast.

    Returns:
        A dict containing historical monthly sales and forecasted sales.
    """
    try:
        history_list, forecast = _fetch_forecast(product_id)
        a2ui_payload = build_forecast_payload(product_id, history_list, forecast)
        if tool_context:
            tool_context.state["a2ui_payload_forecast"] = json.dumps(a2ui_payload)
        return {
            "status": "success",
            "product_id": product_id,
            "history": history_list,
            "forecast": forecast,
            "a2ui_payload": a2ui_payload,
            "a2ui_key": "forecast"
        }
    except Exception as e:
        logger.exception("Failed to get sales forecast")
        return {"status": "error", "message": str(e)}


# --- Purchase order --------------------------------------------------------
def build_po_payload(po_id: str, product_id: str, quantity: int, order_date: str,
                     estimated_delivery: str) -> list:
    """A2UI: branded purchase-order receipt panel + a home button."""
    po = {
        "po_id": po_id, "product_id": product_id, "quantity": quantity,
        "order_date": order_date, "estimated_delivery": estimated_delivery,
    }
    panel = ui_builder.po_panel_html(po)
    buttons = [("po-home-btn", "🏠 Back to Inventory", "go_home", None, True)]
    return _screen("po-confirmation", panel, 560, buttons)


def create_purchase_order(product_id: str, quantity: int, tool_context: ToolContext = None) -> dict:
    """Creates a purchase order for a product. (Simulated)

    Args:
        product_id: The ID of the product to order.
        quantity: The quantity to order.

    Returns:
        A dict containing the purchase order details and status.
    """
    import uuid
    po_id = f"PO-{str(uuid.uuid4())[:8].upper()}"
    order_date = datetime.date.today().isoformat()
    estimated_delivery = (datetime.date.today() + datetime.timedelta(days=14)).isoformat()

    a2ui_payload = build_po_payload(po_id, product_id, quantity, order_date, estimated_delivery)
    if tool_context:
        tool_context.state["a2ui_payload_po"] = json.dumps(a2ui_payload)

    return {
        "status": "success",
        "po_id": po_id,
        "product_id": product_id,
        "quantity": quantity,
        "order_date": order_date,
        "estimated_delivery": estimated_delivery,
        "a2ui_payload": a2ui_payload,
        "a2ui_key": "po"
    }

def send_a2ui_json_to_client(a2ui_json: str, tool_context: ToolContext = None) -> dict:
    """Sends A2UI JSON to the client to render rich UI for the user.

    Args:
        a2ui_json: Either the raw A2UI JSON string, or a lookup key ('inventory', 'forecast', 'po')
                  representing a pre-generated payload.
    """
    from a2ui.parser.payload_fixer import parse_and_fix
    from app.a2ui_config import catalog

    # 1. Resolve key if it's a lookup key
    if a2ui_json in ["inventory", "forecast", "po"]:
        state_key = f"a2ui_payload_{a2ui_json}"
        actual_json = tool_context.state.get(state_key) if tool_context else None
        if not actual_json:
            return {"error": f"Payload for key '{a2ui_json}' not found in session state."}
        a2ui_json = actual_json

    try:
        # 2. Parse and Validate
        a2ui_json_payload = parse_and_fix(a2ui_json)
        catalog.validator.validate(a2ui_json_payload)

        if tool_context:
            tool_context.actions.skip_summarization = True

        return {"validated_a2ui_json": a2ui_json_payload}
    except Exception as e:
        logger.exception("Failed to validate A2UI JSON in custom tool")
        return {"error": f"Failed to validate A2UI: {e}"}
