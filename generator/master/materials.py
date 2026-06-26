import numpy as np
import pandas as pd

from generator.config.settings import DatasetSizes
from generator.utils.ids import format_id

RAW_MATERIAL_NAMES: tuple[str, ...] = (
    "PET Resin Grade A",
    "PET Resin Grade B",
    "HDPE Resin Natural",
    "HDPE Resin Coloured",
    "PP Homopolymer Resin",
    "PP Copolymer Resin",
    "LDPE Resin",
    "LLDPE Resin",
    "Black Masterbatch",
    "White Masterbatch",
    "Blue Masterbatch",
    "Green Masterbatch",
    "UV Stabilizer Additive",
    "Antioxidant Additive",
    "Slip Agent Additive",
    "Anti-Block Additive",
    "28mm PP Screw Cap",
    "38mm HDPE Screw Cap",
    "Snap-On Cap 33mm",
    "Child-Resistant Cap 38mm",
    "Pressure-Sensitive Label Roll",
    "Shrink Sleeve Film Roll",
    "Corrugated Shipper Carton",
    "Pallet Wrap Film",
    "Silica Gel Desiccant Pack",
    "Hot Melt Adhesive Pellets",
    "Printing Ink Cyan",
    "Printing Ink Magenta",
    "Printing Ink Yellow",
    "Printing Ink Black",
)

FINISHED_GOOD_BASES: tuple[str, ...] = (
    "PET Bottle",
    "HDPE Bottle",
    "PP Jar",
    "PET Preform",
    "Trigger Spray Bottle",
    "Pump Dispenser Bottle",
    "Squeeze Tube",
    "Clamshell Container",
    "Food Tray",
    "Pail with Lid",
)

FINISHED_GOOD_SIZES: tuple[str, ...] = (
    "250ml",
    "330ml",
    "500ml",
    "750ml",
    "1L",
    "1.5L",
    "2L",
    "5L",
    "10L",
    "20L",
)


def _build_finished_good_name(index: int) -> str:
    base = FINISHED_GOOD_BASES[index % len(FINISHED_GOOD_BASES)]
    size = FINISHED_GOOD_SIZES[(index // len(FINISHED_GOOD_BASES)) % len(FINISHED_GOOD_SIZES)]
    variant = index // (len(FINISHED_GOOD_BASES) * len(FINISHED_GOOD_SIZES))
    if variant == 0:
        return f"{size} {base}"
    return f"{size} {base} Variant {variant + 1}"


def generate_materials(sizes: DatasetSizes, rng: np.random.Generator) -> pd.DataFrame:
    raw_name_pool = list(RAW_MATERIAL_NAMES)
    rng.shuffle(raw_name_pool)
    selected_raw_names = raw_name_pool[: sizes.raw_materials]

    raw_rows = [
        {
            "material_id": format_id("RM", index, 4),
            "material_name": selected_raw_names[index - 1],
            "material_type": "RAW_MATERIAL",
        }
        for index in range(1, sizes.raw_materials + 1)
    ]

    finished_indices = np.arange(sizes.finished_goods)
    rng.shuffle(finished_indices)
    finished_rows = [
        {
            "material_id": format_id("FG", index, 4),
            "material_name": _build_finished_good_name(int(finished_indices[index - 1])),
            "material_type": "FINISHED_GOOD",
        }
        for index in range(1, sizes.finished_goods + 1)
    ]

    return pd.DataFrame(raw_rows + finished_rows)
