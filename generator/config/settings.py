from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DatasetSizes:
    raw_materials: int = 25
    finished_goods: int = 100
    suppliers: int = 10
    customers: int = 20
    plants: int = 2
    warehouses: int = 3


@dataclass(frozen=True)
class GeneratorConfig:
    seed: int = 42
    company_name: str = "FlexiPack Industries Ltd."
    sizes: DatasetSizes = DatasetSizes()
    output_dir: Path = Path("output")

    @property
    def erp_output_dir(self) -> Path:
        return self.output_dir / "erp"
