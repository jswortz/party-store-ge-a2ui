import os
import json
import a2ui
from a2ui.schema.catalog import CatalogConfig
from a2ui.schema.manager import A2uiSchemaManager

a2ui_path = list(a2ui.__path__)[0]
standard_catalog_path = os.path.join(
    a2ui_path, "assets", "0.8", "standard_catalog_definition.json"
)

from a2ui.schema.common_modifiers import remove_strict_validation

config = CatalogConfig.from_path("standard", standard_catalog_path)
mgr = A2uiSchemaManager("0.8", catalogs=[config], schema_modifiers=[remove_strict_validation])
catalog = mgr.get_selected_catalog()

example = [
  {
    "dataModelUpdate": {
      "surfaceId": "default",
      "path": "/",
      "contents": [
        {
          "key": "items",
          "valueMap": [
            {
              "key": "item1",
              "valueMap": [
                {
                  "key": "name",
                  "valueString": "The Fancy Place"
                }
              ]
            }
          ]
        }
      ]
    }
  }
]

try:
    catalog.validator.validate(example)
    print("Nested valueMap validation SUCCESS!")
except Exception as e:
    print(f"Nested valueMap validation FAILED: {e}")
