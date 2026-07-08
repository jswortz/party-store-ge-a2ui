import os
import json
import a2ui
from a2ui.schema.catalog import CatalogConfig
from a2ui.schema.manager import A2uiSchemaManager

a2ui_path = list(a2ui.__path__)[0]
standard_catalog_path = os.path.join(
    a2ui_path, "assets", "0.8", "standard_catalog_definition.json"
)

def add_vega_chart(schema: dict) -> dict:
    if "components" in schema:
        print("Modifying catalog schema to add VegaChart")
        schema["components"]["VegaChart"] = {
            "type": "object",
            "properties": {
                "spec": {
                    "type": "object",
                    "description": "The Vega-Lite specification for the chart."
                }
            },
            "required": ["spec"]
        }
    return schema

config = CatalogConfig.from_path("standard", standard_catalog_path)
mgr = A2uiSchemaManager("0.8", catalogs=[config], schema_modifiers=[add_vega_chart])

# Test validation
example_data = [
  {
    "beginRendering": {
      "surfaceId": "chart-surface",
      "root": "chart-comp"
    }
  },
  {
    "surfaceUpdate": {
      "surfaceId": "chart-surface",
      "components": [
        {
          "id": "chart-comp",
          "component": {
            "VegaChart": {
              "spec": {
                "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                "mark": "line",
                "encoding": {}
              }
            }
          }
        }
      ]
    }
  }
]

catalog = mgr.get_selected_catalog()
try:
    catalog.validator.validate(example_data)
    print("Validation SUCCESS!")
except Exception as e:
    print(f"Validation FAILED: {e}")
