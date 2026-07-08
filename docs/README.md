# Documentation

Project documentation is organized by purpose. Operational run logs live in [`../logs/`](../logs/).

## Guides

How-to instructions for tools and workflows.

| Document | Description |
|----------|-------------|
| [Azure Blob sync](guides/azure-blob-sync.md) | Upload local CSVs to Azure Blob Storage |

## Pipeline

Databricks Lakeflow Declarative Pipeline architecture and table catalog.

| Document | Description |
|----------|-------------|
| [Operations transformation pipeline](pipeline/ldp-operations-transformation-pipeline.md) | Bronze → silver → gold flow, schemas, and dashboard mapping |

## Reference

Data model notes and quality documentation.

| Document | Description |
|----------|-------------|
| [Data quality and noise](reference/data-quality-and-noise.md) | Schema noise, bronze quirks, and downstream effects |

## Run logs

Audit trails for data generation and sync runs are stored under [`../logs/`](../logs/), grouped by date.
