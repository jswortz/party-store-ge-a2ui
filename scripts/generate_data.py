import datetime
import random
import uuid
from google.cloud import bigquery

PROJECT_ID = "wortz-project-352116"
DATASET_ID = "party_store"

def generate_data():
    client = bigquery.Client(project=PROJECT_ID)
    dataset_ref = client.dataset(DATASET_ID)

    # 1. Define schemas
    orders_schema = [
        bigquery.SchemaField("order_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("product_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("order_date", "DATE", mode="REQUIRED"),
        bigquery.SchemaField("quantity", "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField("customer_id", "STRING", mode="REQUIRED"),
    ]

    shipments_schema = [
        bigquery.SchemaField("shipment_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("product_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("ship_date", "DATE", mode="REQUIRED"),
        bigquery.SchemaField("receive_date", "DATE", mode="REQUIRED"),
        bigquery.SchemaField("quantity", "INTEGER", mode="REQUIRED"),
    ]

    # Products
    products = {
        "halloween_costume": {"seasonal": True, "season_month": 10, "avg_qty": 5},
        "halloween_skeleton": {"seasonal": True, "season_month": 10, "avg_qty": 3},
        "party_balloons": {"seasonal": False, "avg_qty": 10},
        "birthday_candles": {"seasonal": False, "avg_qty": 2},
    }

    # Generate Orders (Historical: 2025-01-01 to 2026-06-30)
    orders_data = []
    start_date = datetime.date(2025, 1, 1)
    end_date = datetime.date(2026, 6, 30)
    curr_date = start_date

    while curr_date <= end_date:
        for prod_id, info in products.items():
            # Determine if we sell today
            if info["seasonal"]:
                # Higher probability in September and October
                if curr_date.month == 10:
                    prob = 0.8
                elif curr_date.month == 9:
                    prob = 0.3
                else:
                    prob = 0.01  # Very rare off-season
            else:
                prob = 0.5  # Regular product sells often

            if random.random() < prob:
                num_orders = random.randint(1, 5) if info["seasonal"] and curr_date.month == 10 else random.randint(1, 2)
                for _ in range(num_orders):
                    qty = random.randint(1, info["avg_qty"] * 2)
                    orders_data.append({
                        "order_id": str(uuid.uuid4()),
                        "product_id": prod_id,
                        "order_date": curr_date.isoformat(),
                        "quantity": qty,
                        "customer_id": f"cust_{random.randint(100, 999)}"
                    })
        curr_date += datetime.timedelta(days=1)

    # Generate Shipments
    # We want to stock up before selling.
    # For seasonal: Large shipments in August/September.
    # For non-seasonal: Regular shipments.
    shipments_data = []
    
    # 2025 Shipments
    # Halloween
    shipments_data.append({
        "shipment_id": "ship_hal_2025_1",
        "product_id": "halloween_costume",
        "ship_date": "2025-08-15",
        "receive_date": "2025-08-20",
        "quantity": 1000
    })
    shipments_data.append({
        "shipment_id": "ship_hal_2025_2",
        "product_id": "halloween_skeleton",
        "ship_date": "2025-08-15",
        "receive_date": "2025-08-22",
        "quantity": 500
    })
    
    # Balloons (regular shipments)
    for month in range(1, 13):
        shipments_data.append({
            "shipment_id": f"ship_bal_2025_{month}",
            "product_id": "party_balloons",
            "ship_date": f"2025-{month:02d}-01",
            "receive_date": f"2025-{month:02d}-05",
            "quantity": 300
        })
    # Candles (regular shipments, but maybe we didn't order enough)
    for month in range(1, 13):
        shipments_data.append({
            "shipment_id": f"ship_can_2025_{month}",
            "product_id": "birthday_candles",
            "ship_date": f"2025-{month:02d}-01",
            "receive_date": f"2025-{month:02d}-05",
            "quantity": 50
        })

    # 2026 Shipments (up to June)
    # Balloons
    for month in range(1, 7):
        shipments_data.append({
            "shipment_id": f"ship_bal_2026_{month}",
            "product_id": "party_balloons",
            "ship_date": f"2026-{month:02d}-01",
            "receive_date": f"2026-{month:02d}-05",
            "quantity": 300
        })
    # Candles (only for Jan-Apr, running out of stock now in July)
    for month in range(1, 5):
        shipments_data.append({
            "shipment_id": f"ship_can_2026_{month}",
            "product_id": "birthday_candles",
            "ship_date": f"2026-{month:02d}-01",
            "receive_date": f"2026-{month:02d}-05",
            "quantity": 50
        })

    # Halloween 2026 (No shipments yet! This will trigger need to reorder because stock is low and season is coming)
    # Actually, let's see current stock.
    # Costumes: sold ~700-900 in 2025. Leftover ~100-300.
    # Skeletons: sold ~300-400. Leftover ~100.
    # Current date is July 2026. We need to forecast and see we need more.

    # Load to BigQuery
    load_table(client, dataset_ref.table("orders"), orders_data, orders_schema)
    load_table(client, dataset_ref.table("shipments"), shipments_data, shipments_schema)

def load_table(client, table_ref, data, schema):
    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition="WRITE_TRUNCATE",
    )
    job = client.load_table_from_json(data, table_ref, job_config=job_config)
    job.result()  # Wait for the job to complete.
    print(f"Loaded {len(data)} rows into {table_ref.table_id}")

if __name__ == "__main__":
    generate_data()
