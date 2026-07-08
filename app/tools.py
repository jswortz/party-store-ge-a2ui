import datetime
import logging
import json
from google.cloud import bigquery
from google.adk.tools import ToolContext

PROJECT_ID = "wortz-project-352116"
DATASET_ID = "party_store"

logger = logging.getLogger(__name__)

def get_bq_client():
    return bigquery.Client(project=PROJECT_ID)

def query_inventory_status() -> dict:
    """Queries the current inventory status for all products from BigQuery.
    
    Calculates current stock as received shipments minus sold orders.
    
    Returns:
        A dict containing a list of products with their current stock, received, and sold quantities.
    """
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
    try:
        query_job = client.query(query)
        results = query_job.result()
        inventory = []
        for row in results:
            # Simple threshold for low stock alert
            status = "Good"
            if row.product_id in ["halloween_costume", "halloween_skeleton"]:
                # For seasonal, if we are in July and stock is low compared to last year's sales, warn
                # Last year's sales was around 800 for costumes, so if stock < 200, it's low
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
            
        # Construct A2UI payload
        items = []
        for i, item in enumerate(inventory):
             icon_name = "warning" if "Low" in item["status"] else "check"
             items.append({
                 "key": f"item{i}",
                 "valueMap": [
                     {"key": "product_id", "valueString": item["product_id"]},
                     {"key": "stock_display", "valueString": f"Stock: {item['current_stock']}"},
                     {"key": "status", "valueString": item["status"]},
                     {"key": "status_icon", "valueString": icon_name}
                 ]
             })
        
        a2ui_payload = [
          {
            "beginRendering": {
              "surfaceId": "inventory-status",
              "root": "root-layout"
            }
          },
          {
            "surfaceUpdate": {
              "surfaceId": "inventory-status",
              "components": [
                {
                  "id": "root-layout",
                  "component": {
                    "Column": {
                      "children": {
                        "explicitList": [
                          "header-text",
                          "inventory-card"
                        ]
                      }
                    }
                  }
                },
                {
                  "id": "header-text",
                  "component": {
                    "Text": {
                      "usageHint": "h1",
                      "text": {
                        "literalString": "Current Inventory Status"
                      }
                    }
                  }
                },
                {
                  "id": "inventory-card",
                  "component": {
                    "Card": {
                      "child": "inventory-list"
                    }
                  }
                },
                {
                  "id": "inventory-list",
                  "component": {
                    "List": {
                      "direction": "vertical",
                      "children": {
                        "template": {
                          "componentId": "item-layout",
                          "dataBinding": "items"
                        }
                      }
                    }
                  }
                },
                {
                  "id": "item-layout",
                  "component": {
                    "Column": {
                      "children": {
                        "explicitList": [
                          "item-row",
                          "item-divider"
                        ]
                      }
                    }
                  }
                },
                {
                  "id": "item-row",
                  "component": {
                    "Row": {
                      "children": {
                        "explicitList": [
                          "item-icon",
                          "item-name",
                          "item-stock",
                          "item-status"
                        ]
                      },
                      "distribution": "spaceBetween",
                      "alignment": "center"
                    }
                  }
                },
                {
                  "id": "item-icon",
                  "component": {
                    "Icon": {
                      "name": {
                        "path": "status_icon"
                      }
                    }
                  }
                },
                {
                  "id": "item-name",
                  "component": {
                    "Text": {
                      "usageHint": "body",
                      "text": {
                        "path": "product_id"
                      }
                    }
                  }
                },
                {
                  "id": "item-stock",
                  "component": {
                    "Text": {
                      "text": {
                        "path": "stock_display"
                      }
                    }
                  }
                },
                {
                  "id": "item-status",
                  "component": {
                    "Text": {
                      "text": {
                        "path": "status"
                      }
                    }
                  }
                },
                {
                  "id": "item-divider",
                  "component": {
                    "Divider": {
                      "axis": "horizontal"
                    }
                  }
                }
              ]
            }
          },
          {
            "dataModelUpdate": {
              "surfaceId": "inventory-status",
              "contents": [
                {
                  "key": "items",
                  "valueMap": items
                }
              ]
            }
          }
        ]
        
        a2ui_str = json.dumps(a2ui_payload)
        
        return {
            "status": "success",
            "inventory": inventory,
            "a2ui_payload_str": a2ui_str
        }
    except Exception as e:
        logger.exception("Failed to query inventory")
        return {"status": "error", "message": str(e)}

def get_sales_forecast(product_id: str) -> dict:
    """Generates sales forecast for a product for the next 6 months (Jul-Dec 2026).
    
    Uses historical sales data from BigQuery to project future sales,
    considering seasonality for seasonal products.
    
    Args:
        product_id: The ID of the product to forecast.
        
    Returns:
        A dict containing historical monthly sales and forecasted sales.
    """
    client = get_bq_client()
    # Query monthly sales
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
    try:
        query_job = client.query(query, job_config=job_config)
        results = query_job.result()
        
        history = {}
        for row in results:
            if row.year not in history:
                history[row.year] = {}
            history[row.year][row.month] = row.monthly_sales
            
        # Generate forecast for Jul-Dec 2026
        # Current date is assumed to be July 2026
        forecast = []
        
        # Determine seasonality
        is_seasonal = product_id in ["halloween_costume", "halloween_skeleton"]
        
        # Calculate average for non-seasonal
        total_sales = 0
        count = 0
        for y in history:
            for m in history[y]:
                # Exclude seasonal spikes from average if it is seasonal?
                # Actually, if we just want a simple model:
                total_sales += history[y][m]
                count += 1
        avg_sales = total_sales / count if count > 0 else 10
        
        for month in range(7, 13):
            date_str = f"2026-{month:02d}"
            if is_seasonal:
                # Use last year's (2025) value if available, otherwise estimate
                val_2025 = history.get(2025, {}).get(month, 0)
                if month == 10:
                    # October spike, add some growth
                    projected = int(val_2025 * 1.1) if val_2025 > 0 else 800
                elif month == 9:
                    projected = int(val_2025 * 1.1) if val_2025 > 0 else 200
                else:
                    projected = val_2025 if val_2025 > 0 else 5
            else:
                # Non-seasonal: use average with some minor random noise
                projected = int(avg_sales)
                
            forecast.append({
                "date": date_str,
                "sales": projected,
                "type": "forecast"
            })
            
        # Format history for return
        history_list = []
        for y in sorted(history.keys()):
            for m in sorted(history[y].keys()):
                history_list.append({
                    "date": f"{y}-{m:02d}",
                    "sales": history[y][m],
                    "type": "actual"
                })
                
        # Construct Vega data table
        combined_data = history_list + forecast
        value_maps = []
        for idx, entry in enumerate(combined_data):
            value_maps.append({
                "key": str(idx),
                "valueMap": [
                    {"key": "date", "valueString": entry["date"]},
                    {"key": "sales", "valueNumber": entry["sales"]},
                    {"key": "type", "valueString": entry["type"]}
                ]
            })
            
        a2ui_payload = [
          {
            "beginRendering": {
              "surfaceId": "sales-forecast",
              "root": "root-layout"
            }
          },
          {
            "surfaceUpdate": {
              "surfaceId": "sales-forecast",
              "components": [
                {
                  "id": "root-layout",
                  "component": {
                    "Column": {
                      "children": {
                        "explicitList": [
                          "header-text",
                          "forecast-chart"
                        ]
                      }
                    }
                  }
                },
                {
                  "id": "header-text",
                  "component": {
                    "Text": {
                      "usageHint": "h1",
                      "text": {
                        "literalString": f"Sales Forecast: {product_id}"
                      }
                    }
                  }
                },
                {
                  "id": "forecast-chart",
                  "component": {
                    "VegaChart": {
                      "spec": {
                        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                        "description": "Sales Forecast Chart",
                        "width": "container",
                        "height": 300,
                        "data": {
                          "name": "table"
                        },
                        "mark": {
                          "type": "line",
                          "point": {"filled": True, "size": 60},
                          "interpolate": "monotone",
                          "strokeWidth": 3
                        },
                        "encoding": {
                          "x": {
                            "field": "date",
                            "type": "temporal",
                            "title": "Month",
                            "axis": {
                              "format": "%b %Y",
                              "grid": True,
                              "labelAngle": -30
                            }
                          },
                          "y": {
                            "field": "sales",
                            "type": "quantitative",
                            "title": "Units Sold",
                            "axis": {
                              "grid": True
                            }
                          },
                          "color": {
                            "field": "type",
                            "type": "nominal",
                            "title": "Data Type",
                            "scale": {
                              "domain": ["actual", "forecast"],
                              "range": ["#1a73e8", "#f9ab00"]
                            }
                          },
                          "tooltip": [
                            {"field": "date", "type": "temporal", "title": "Month", "format": "%B %Y"},
                            {"field": "sales", "type": "quantitative", "title": "Sales"},
                            {"field": "type", "type": "nominal", "title": "Type"}
                          ]
                        }
                      }
                    }
                  }
                }
              ]
            }
          },
          {
            "dataModelUpdate": {
              "surfaceId": "sales-forecast",
              "contents": [
                {
                  "key": "table",
                  "valueMap": value_maps
                }
              ]
            }
          }
        ]
        
        a2ui_str = json.dumps(a2ui_payload)
        
        return {
            "status": "success",
            "product_id": product_id,
            "history": history_list,
            "forecast": forecast,
            "a2ui_payload_str": a2ui_str
        }
    except Exception as e:
        logger.exception("Failed to get sales forecast")
        return {"status": "error", "message": str(e)}

def create_purchase_order(product_id: str, quantity: int) -> dict:
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
    
    a2ui_payload = [
      {
        "beginRendering": {
          "surfaceId": "po-confirmation",
          "root": "root-layout"
        }
      },
      {
        "surfaceUpdate": {
          "surfaceId": "po-confirmation",
          "components": [
            {
              "id": "root-layout",
              "component": {
                "Card": {
                  "child": "receipt-container"
                }
              }
            },
            {
              "id": "receipt-container",
              "component": {
                "Column": {
                  "children": {
                    "explicitList": [
                      "receipt-header-row",
                      "divider-1",
                      "po-details-text",
                      "po-delivery-text"
                    ]
                  }
                }
              }
            },
            {
              "id": "receipt-header-row",
              "component": {
                "Row": {
                  "children": {
                    "explicitList": [
                      "receipt-success-icon",
                      "receipt-title-text"
                    ]
                  },
                  "alignment": "center",
                  "distribution": "start"
                }
              }
            },
            {
              "id": "receipt-success-icon",
              "component": {
                "Icon": {
                  "name": {
                    "literalString": "check"
                  }
                }
              }
            },
            {
              "id": "receipt-title-text",
              "component": {
                "Text": {
                  "usageHint": "h2",
                  "text": {
                    "literalString": "Order Confirmation"
                  }
                }
              }
            },
            {
              "id": "divider-1",
              "component": {
                "Divider": {
                  "axis": "horizontal"
                }
              }
            },
            {
              "id": "po-details-text",
              "component": {
                "Text": {
                  "usageHint": "body",
                  "text": {
                    "path": "po_details_text"
                  }
                }
              }
            },
            {
              "id": "po-delivery-text",
              "component": {
                "Text": {
                  "usageHint": "body",
                  "text": {
                    "path": "delivery_text"
                  }
                }
              }
            }
          ]
        }
      },
      {
        "dataModelUpdate": {
          "surfaceId": "po-confirmation",
          "contents": [
            {
              "key": "po_details_text",
              "valueString": f"**Purchase Order ID:** {po_id}\n\n**Product Ordered:** {product_id}\n\n**Quantity:** {quantity}\n\n**Order Date:** {order_date}"
            },
            {
              "key": "delivery_text",
              "valueString": f"**Estimated Delivery:** {estimated_delivery}"
            }
          ]
        }
      }
    ]
    
    a2ui_str = json.dumps(a2ui_payload)
    
    return {
        "status": "success",
        "po_id": po_id,
        "product_id": product_id,
        "quantity": quantity,
        "order_date": order_date,
        "estimated_delivery": estimated_delivery,
        "a2ui_payload_str": a2ui_str
    }
