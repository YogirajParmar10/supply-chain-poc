# Run Logs

Operational audit logs for data generation, Azure sync, and similar one-off tasks. These are **not** user guides — see [`docs/`](../docs/) for documentation.

## Layout

```text
logs/
└── YYYY-MM-DD/           # date the run completed (UTC)
    ├── *.md              # human-readable summary
    └── *-console.log     # full terminal output
```

## Runs

| Date | Summary | Console log |
|------|---------|-------------|
| 2026-07-07 | [5-year data regeneration](2026-07-07/data-regeneration.md) | [console](2026-07-07/data-regeneration-console.log) |
| 2026-07-07 | [Azure WMS blob sync](2026-07-07/azure-blob-sync.md) | [console](2026-07-07/azure-blob-sync-console.log) |

## Adding new logs

After a significant run, create `logs/YYYY-MM-DD/` and add:

1. A short `*.md` summary (what ran, commands, results, recovery steps)
2. A `*-console.log` with full terminal output (`tee` or redirect)
