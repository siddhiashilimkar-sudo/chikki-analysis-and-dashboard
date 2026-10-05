# Maganlal Chikki Business Intelligence Dashboard

A college-project-ready business analytics application built with React/Vite, FastAPI, SQLAlchemy, MySQL, transactional Excel ETL, and an optional SQLite development database. Generated workbook records are synthetic and labeled **DEMO DATA**; do not treat them as actual shop records.

## Architecture

```text
Excel today / POS, barcode billing, or REST API later
        → Python validation and ETL
        → MySQL (maganlal_chikki_bi)
        → SQL views and source-independent analytics
        → FastAPI
        → React operational dashboard
        → Power BI (refresh-based reporting)
```

The legacy database `maganlal_bi_dashboard` is unrelated and must remain untouched. The MySQL project database is `maganlal_chikki_bi`. SQLite remains available for local development and automated regression tests.

## Installation and configuration

On Windows, run `run_project.bat` from this project root. It prepares the Python and frontend dependencies, initializes the selected database, loads the workbook, starts FastAPI, and launches Vite. Open `http://localhost:5173`; API docs are at `http://localhost:8000/docs`. Start the workbook watcher separately as described below.

For manual setup, create/activate `.venv`, install `backend\requirements.txt`, then install frontend packages in `frontend`. Configure the ignored local `.env` using `.env.example` as a template:

| Variable | Purpose |
|---|---|
| `DATABASE_MODE` | `mysql` for the current production-style setup; `sqlite` for local/demo testing |
| `DB_HOST`, `DB_PORT` | MySQL server address and port |
| `DB_NAME` | `maganlal_chikki_bi` |
| `DB_USER`, `DB_PASSWORD` | Local database credentials; never commit or share `.env` |
| `DATABASE_URL` | Optional SQLAlchemy URL override; keep credentials local |
| `CORS_ORIGINS` | Allowed dashboard origins |
| `DATA_CLASSIFICATION` | `demo` for synthetic source data; set to `business` after switching to real records |
| `DATA_STALE_AFTER_MINUTES` | Age after which the last successful import is labeled `STALE` (default 60) |

`.env` is ignored by Git. `.env.example` has placeholders only.

## MySQL mode

The existing configuration targets `maganlal_chikki_bi`. On a fresh MySQL setup, run `python scripts\setup_database.py`, apply `database\views.sql` if provisioning from SQL, then run `python etl\pipeline.py`. Use a least-privilege application account in deployments and a read-only account for Power BI. `setup_database.py` and the ETL use the configured database; do not point them at the old legacy database.

MySQL connection, schema, relationships, views, workbook ETL, analytics, and API were exercised on the local MySQL 8.0.46 server. The existing tables and records are not dropped during ETL: snapshot replacement is transactional. Product IDs created by the API are serialized with a MySQL named lock because the current populated project table’s primary key is not auto-incrementing.

## SQLite development mode

Temporarily set `DATABASE_MODE=sqlite` in `.env` or in the current process. Initialize with `python scripts\setup_database.py`, load with `python etl\pipeline.py`, and start the API with `uvicorn backend.app.main:app --reload`. Start the React dev server from `frontend` with `npm run dev`. The automated suite was run with a temporary process-only SQLite override and passed 17/17 tests; the local `.env` remains configured for MySQL.

## Excel source, demo data, and migration

The current source is `data\raw\business_data.xlsx`, containing 13 sheets: Products, Categories, Suppliers, Sales, Sale_Items, Purchases, Purchase_Items, Inventory, Inventory_Movements, Expenses, Payments, Returns, and Return_Items. The demo generator is `python scripts\generate_demo_data.py`; it creates synthetic records and should only be run when you intend to replace the demo workbook. The web UI identifies the configured data classification, and forecasts are explicitly identified as estimates.

To migrate to shop records:

1. Back up the existing workbook and database.
2. Replace `data\raw\business_data.xlsx` with the real workbook.
3. Map source headers to the column contracts in `etl\cleaner.py`; keep stable unique IDs and valid foreign-key references.
4. Set `DATA_CLASSIFICATION=business` in `.env`.
5. Validate the workbook, then run `python etl\pipeline.py` or let the watcher import it.
6. Check `/api/etl/status`, `/api/etl/logs`, table counts, financial totals, inventory, and sampled source rows.
7. Refresh Power BI according to its configured refresh mode.

Invalid workbooks fail validation before loading. The loader replaces the 13-sheet snapshot within one database transaction; a failed write rolls back to the previous successful records. It does not silently discard bad rows.

## Near-real-time operations

For Excel updates, run `python automation\excel_watcher.py` from the project root. It watches the existing workbook, debounces saves for two seconds, ignores temporary Excel lock files, and skips already processed file signatures. A heartbeat lets the API distinguish an active watcher from a stale status file. Every run records an ID, relative source path, start/completion timestamps, duration, row count, status, validation errors, and outcome in `etl_logs` and the processed ETL status file.

The React app checks `/api/dashboard/freshness` every 15 seconds. It reloads the dashboard API data only when the latest successful ETL timestamp changes; it does not reload the browser page. The system area displays actual database/API/ETL/watcher status, data classification, and last successful data time. Data is marked `LIVE` only while a successful import is within the configured freshness window, `STALE` after that window, and `OFFLINE` when the database check fails. “Live” means current application data; the Excel workflow’s end-to-end latency includes save debounce, ETL processing, and the next 15-second poll.

The React dashboard and FastAPI serve current MySQL data. This does not make Power BI Desktop instant real-time. Power BI Desktop is refresh-based; Power BI Service refresh depends on dataset mode, licensing/capacity, and gateway/connector configuration.

## Product, supplier, and purchase workflow

Product identity uses normalized product name + equivalent weight/unit + supplier; purchase price is excluded. The API returns HTTP 409 and existing product information for duplicate identities. Supplier creation checks normalized supplier name and phone while preserving distinct suppliers with different contact identity. The `product_suppliers` table stores canonical identity keys and has unique identity/pair constraints; existing supplier provenance is backfilled from purchase history, and the Excel ETL rebuilds these links transactionally. Conflicting workbook identities reject the ETL snapshot rather than merging or deleting records.

Use the Products screen to add a product against an existing supplier, Suppliers to register suppliers, and Purchases to post stock against an existing product. A purchase writes a purchase header/item and inventory movement, increases stock, and updates current product cost using weighted average cost. A new unit cost is transaction history; it never creates another product. API-created products/purchases are database operational records, while the Excel ETL remains a full-snapshot source for the workbook-managed dataset.

## Backend and API

Run FastAPI from the project root with `uvicorn backend.app.main:app --reload`. Existing routes cover health, dashboard summary/trends/top and slow products/categories, products CRUD, sales, inventory and low stock, purchases, suppliers, expenses, payments, returns, finance summary/trends, forecast, reorder, insights, ETL status, and manual ETL. Added status routes are `GET /api/dashboard/freshness` and `GET /api/etl/logs`. `GET /health` reports the connected database mode and dialect. List routes support pagination where applicable.

## Analytics

Metrics are calculated from database records: revenue is completed sales; COGS is quantity times stored unit cost; gross profit is revenue less COGS; net profit is gross profit less operating expenses; margins divide the respective profit by revenue; inventory value uses current stock times purchase cost; and AOV divides revenue by transaction count. Zero denominators return zero or blank as appropriate. Forecasts use a rolling three-period moving average and are estimates. Reorder quantities use recent demand, lead time, reorder levels, and safety stock. Alerts are labeled **Potential anomaly** and are not fraud conclusions.

## Power BI

Power BI SQL views are in `database\views.sql`; connection steps, page guidance, data-model notes, and DAX examples are in `powerbi\README.md` and `powerbi\dax_measures.md`. Connect to `maganlal_chikki_bi` with the MySQL connector and a read-only credential. Use the provided daily/weekly/monthly sales, product/category, inventory, supplier, finance, profit, expense, payment, return, forecast, reorder, and dashboard views. Create and mark a calendar table and relate date fields to it.

Power BI Desktop uses manual refresh. Power BI Service scheduled refresh requires supported capacity/licensing and a configured on-premises data gateway when MySQL is not directly reachable from the service. DirectQuery and refresh frequency depend on connector, gateway, and service limits. No Power BI Desktop report execution is claimed as verified on this machine.

## Testing and verification

```powershell
python -m unittest discover -s tests -v
python etl\pipeline.py
python automation\excel_watcher.py
cd frontend; npm run build
```

Use the project virtual environment. SQLite tests should run with `DATABASE_MODE=sqlite` set for that process when `.env` is configured for MySQL. Current verification: MySQL schema and 15 views verified; 13-sheet, 7,020-row ETL verified; all 18 tests passed on MySQL and all 18 passed on SQLite; product, supplier, and purchase duplicate/cost workflow cases passed; frontend production build passed. FastAPI was started on a temporary local port and health, products, suppliers, purchases, inventory, and dashboard summary returned HTTP 200. An earlier end-to-end test added one temporary sale, observed exactly one watcher import, confirmed MySQL/API and React updated, then restored the original workbook and ETL baseline.

## Troubleshooting

- **Database unavailable:** inspect `.env` locally, confirm MySQL service and database name, and check `/health`; never paste credentials into logs or chat.
- **ETL rejected:** inspect `data\processed\etl_status.json` and `/api/etl/logs` for validation errors, then fix required columns, IDs, dates, numeric values, or foreign-key references.
- **Watcher stopped:** start `python automation\excel_watcher.py` from the project root and confirm its heartbeat through `/api/dashboard/freshness`.
- **Dashboard offline:** confirm FastAPI is running at the configured `VITE_API_URL` and that `CORS_ORIGINS` includes the React origin.
- **Stale data:** check the last successful import and watcher monitoring status; a failed import preserves the previous successful dataset.

## Future POS / barcode integration

The normalized MySQL model and source-independent analytics remain behind FastAPI. A future POS or barcode billing application can write validated transactions through authenticated API endpoints, while the same database-backed dashboard and Power BI views consume them. No barcode hardware is required or implemented now. Authentication, authorization, and deployment hardening are still future work; do not expose this development server publicly.

