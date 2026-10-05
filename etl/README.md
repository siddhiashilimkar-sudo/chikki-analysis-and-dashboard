# Excel ETL

Run `python etl\pipeline.py` from the project root with the project environment active. It reads the 13-sheet source workbook, validates required fields, identifiers, numeric/date values and foreign-key references, cleans/transforms the frames, then calls the existing transactional SQLAlchemy loader. A validation or database failure leaves the previous successful snapshot intact.

Each run gets a unique ID and logs its relative source path, start and completion timestamps, duration, status, row count, validation errors, and warnings to `data\processed\etl_status.json` and the existing `etl_logs` table. API readers are `GET /api/etl/status` and `GET /api/etl/logs`. The database is selected via `.env`; supported modes are SQLite and MySQL (`maganlal_chikki_bi`).

See `cleaner.py` for sheet/column contracts and validation, `transformer.py` for normalization, and `mysql_loader.py` for the snapshot transaction.
