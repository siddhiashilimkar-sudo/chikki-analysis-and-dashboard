# Excel watcher

From the project root with the virtual environment active, run `python automation\excel_watcher.py`. The process watches only `data\raw\business_data.xlsx`. Save the workbook to trigger a two-second debounce, validation, transformation, and transactional ETL. Temporary Excel lock files and unrelated workbook-directory events are ignored. A file-signature check prevents repeated notifications for the same workbook version from importing twice; changes made during an active import are queued by the serialized ETL runner.

The watcher heartbeat and last run are recorded at `data\processed\watcher_status.json`; ETL status and structured run metadata are in `data\processed\etl_status.json`, `/api/etl/status`, `/api/etl/logs`, and the existing MySQL/SQLite `etl_logs` table. Status records the source path, run ID, start/completion times, elapsed seconds, outcome, rows, warnings, and validation/errors. A watcher heartbeat older than 45 seconds is reported as stopped. Press Ctrl+C to stop the watcher cleanly.

Invalid workbooks are rejected before writes. Database load failures roll back the whole snapshot transaction, preserving the prior successful data.
