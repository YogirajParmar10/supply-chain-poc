# Supply Chain POC

Synthetic data generators for **FlexiPack Industries Ltd.**, a fictional plastic packaging manufacturer. The project produces deterministic CSV files that simulate master and transactional data across ERP, WMS, MES, supplier, POS, and external systems.

## Pipeline overview

```text
Python Generators
       │
       ▼
   output/              (generated CSV files)
   ├── erp/
   ├── wms/
   ├── mes/
   ├── supplier/
   ├── pos/
   └── external/
       │
       ▼
Databricks Auto Loader
       │
       ▼
  Bronze → Silver → Gold tables
```

Schema definitions for all datasets live in [`schema/`](schema/).

## Current status

**Phase A — Master data (ERP)** is implemented. Running the generator produces five ERP master data CSV files under `output/erp/`.

| File | Description | Rows |
|------|-------------|------|
| `materials.csv` | Raw materials and finished goods | 125 |
| `suppliers.csv` | Supplier master records | 10 |
| `customers.csv` | Customer master records | 20 |
| `plants.csv` | Manufacturing plant locations | 2 |
| `warehouses.csv` | Warehouses linked to plants | 3 |

Future phases will add transactional data (purchase orders, sales orders, inventory, production, etc.).

## Requirements

- Python 3.12+
- pandas
- numpy

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

Generate all master data CSV files:

```bash
python -m generator.main
```

Output is written to `output/erp/`. Directories are created automatically if they do not exist.

### Programmatic usage

```python
from generator.config.settings import GeneratorConfig, DatasetSizes
from generator.main import generate_master_data

config = GeneratorConfig(seed=42, sizes=DatasetSizes(raw_materials=25))
written = generate_master_data(config)
```

## Configuration

Settings are defined in [`generator/config/settings.py`](generator/config/settings.py):

| Setting | Default | Description |
|---------|---------|-------------|
| `seed` | `42` | Random seed for deterministic output |
| `company_name` | `FlexiPack Industries Ltd.` | Company name used in generated data |
| `output_dir` | `output` | Root directory for generated CSV files |
| `sizes.raw_materials` | `25` | Number of raw materials |
| `sizes.finished_goods` | `100` | Number of finished goods |
| `sizes.suppliers` | `10` | Number of suppliers |
| `sizes.customers` | `20` | Number of customers |
| `sizes.plants` | `2` | Number of plants |
| `sizes.warehouses` | `3` | Number of warehouses |

Running the generator multiple times with the same seed produces identical CSV files.

## Project structure

```text
generator/
├── config/          # Seed, dataset sizes, output paths
├── master/          # Master data generators (materials, suppliers, etc.)
├── utils/           # ID formatting, CSV export, RNG helpers
└── main.py          # Entry point and orchestration

schema/              # CSV schema documentation per system
output/              # Generated CSV files (gitignored)
```

## Identifier conventions

| Entity | Format | Example |
|--------|--------|---------|
| Raw material | `RM` + 4 digits | `RM0001` |
| Finished good | `FG` + 4 digits | `FG0001` |
| Supplier | `SUP` + 3 digits | `SUP001` |
| Customer | `CUS` + 3 digits | `CUS001` |
| Plant | `PL` + 3 digits | `PL001` |
| Warehouse | `WH` + 3 digits | `WH001` |
