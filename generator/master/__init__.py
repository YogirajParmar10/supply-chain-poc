import importlib

__all__ = [
    "generate_customers",
    "generate_materials",
    "generate_plants",
    "generate_suppliers",
    "generate_warehouses",
]

_MODULE_EXPORTS = {
    "generate_customers": ("generator.master.customers", "generate_customers"),
    "generate_materials": ("generator.master.materials", "generate_materials"),
    "generate_plants": ("generator.master.plants", "generate_plants"),
    "generate_suppliers": ("generator.master.suppliers", "generate_suppliers"),
    "generate_warehouses": ("generator.master.warehouses", "generate_warehouses"),
}


def __getattr__(name: str):
    if name not in _MODULE_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attribute_name = _MODULE_EXPORTS[name]
    module = importlib.import_module(module_name)
    return getattr(module, attribute_name)
