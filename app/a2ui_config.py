import os
import a2ui
from a2ui.schema.catalog import CatalogConfig
from a2ui.schema.manager import A2uiSchemaManager
from a2ui.schema.common_modifiers import remove_strict_validation

# A2UI Catalog setup with VegaChart support
def add_vega_chart(schema: dict) -> dict:
    if "components" in schema:
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

a2ui_path = list(a2ui.__path__)[0]
standard_catalog_path = os.path.join(
    a2ui_path, "assets", "0.8", "standard_catalog_definition.json"
)
catalog_config = CatalogConfig.from_path("standard", standard_catalog_path)
schema_manager = A2uiSchemaManager(
    "0.8",
    catalogs=[catalog_config],
    schema_modifiers=[add_vega_chart, remove_strict_validation]
)
catalog = schema_manager.get_selected_catalog()

# Examples directory
UI_EXAMPLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui_examples")
examples_str = catalog.load_examples(UI_EXAMPLES_DIR, validate=True)
