"""Offline verification of the deterministic Party Store A2UI path (no BigQuery required).

Checks:
1. build_*_payload output validates against the augmented a2ui catalog (incl. VegaChart).
2. PartyStoreExecutor screen builders emit a leading TextPart + DataParts tagged
   metadata.mimeType == "application/json+a2ui".
3. fast_api_app builds a card advertising the A2UI extension with url + JSONRPC transport.
"""
import sys
from unittest import mock

from a2a.types import DataPart, TextPart

from app import tools
from app.a2ui_config import catalog

FAKE_INVENTORY = [
    {"product_id": "halloween_costume", "received": 900, "sold": 800, "current_stock": 100, "status": "Low Stock (Season Coming)"},
    {"product_id": "party_balloons", "received": 500, "sold": 120, "current_stock": 380, "status": "Good"},
]
FAKE_HISTORY = [{"date": "2025-10", "sales": 800, "type": "actual"}]
FAKE_FORECAST = [{"date": "2026-10", "sales": 880, "type": "forecast"}]


def _validate(name, payload):
    catalog.validator.validate(payload)
    print(f"  ✓ {name}: {len(payload)} commands validate against catalog")


def test_payload_validation():
    print("[1] Payload validation against augmented catalog (VegaChart)")
    _validate("inventory", tools.build_inventory_payload(FAKE_INVENTORY))
    _validate("forecast", tools.build_forecast_payload("halloween_costume", FAKE_HISTORY, FAKE_FORECAST))
    _validate("purchase_order", tools.build_po_payload("PO-TEST1234", "birthday_candles", 500, "2026-07-09", "2026-07-23"))


def _assert_ui_parts(name, parts):
    assert parts, f"{name}: no parts"
    assert isinstance(parts[0].root, TextPart), f"{name}: first part is not TextPart"
    dataparts = [p for p in parts[1:] if isinstance(p.root, DataPart)]
    assert dataparts, f"{name}: no DataParts emitted"
    for p in dataparts:
        mt = (p.root.metadata or {}).get("mimeType")
        assert mt == "application/json+a2ui", f"{name}: bad mimeType {mt!r}"
    print(f"  ✓ {name}: TextPart + {len(dataparts)} DataParts tagged application/json+a2ui | text={parts[0].root.text[:70]!r}")


def test_executor_screens():
    print("[2] Executor screen builders emit tagged DataParts")
    from app.agent_executor import PartyStoreExecutor
    ex = PartyStoreExecutor()
    with mock.patch.object(tools, "_fetch_inventory", return_value=FAKE_INVENTORY):
        _assert_ui_parts("inventory", ex._inventory())
    with mock.patch.object(tools, "_fetch_forecast", return_value=(FAKE_HISTORY, FAKE_FORECAST)):
        _assert_ui_parts("forecast", ex._forecast("halloween_costume"))
    _assert_ui_parts("purchase_order", ex._purchase_order("birthday_candles", 500))


def test_product_normalization():
    print("[3] Product normalization")
    from app.agent_executor import _normalize_product
    cases = {
        "birthday candles": "birthday_candles",
        "Halloween Costumes": "halloween_costume",
        "party balloons": "party_balloons",
        "halloween_skeleton": "halloween_skeleton",
    }
    for raw, expect in cases.items():
        got = _normalize_product(raw)
        assert got == expect, f"normalize {raw!r} -> {got!r}, expected {expect!r}"
        print(f"  ✓ {raw!r} -> {got!r}")


def test_card():
    print("[4] fast_api_app agent card")
    from app import fast_api_app as f
    card = f._agent_card
    assert card.url.endswith("/a2a/app"), f"bad url {card.url}"
    assert str(card.preferred_transport) in ("JSONRPC", "TransportProtocol.jsonrpc", "jsonrpc"), f"transport {card.preferred_transport}"
    exts = card.capabilities.extensions or []
    assert any("a2ui" in (e.uri or "") for e in exts), "no a2ui extension on card"
    assert f.app is not None
    print(f"  ✓ url={card.url} transport={card.preferred_transport} extensions={[e.uri for e in exts]}")


if __name__ == "__main__":
    try:
        test_payload_validation()
        test_executor_screens()
        test_product_normalization()
        test_card()
        print("\nALL OFFLINE CHECKS PASSED ✅")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\nFAILED ❌: {e}")
        sys.exit(1)
