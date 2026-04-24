# Add CSV, .doc, and .xls File Type Support

## Task
Extend the document ingestion system to support three new file types: `.csv`, `.doc` (legacy Word), and `.xls` (legacy Excel).

## Changes Made

### New Files
- **`backend/ingestion/csv_ingester.py`** — `CsvIngester` class using Python's built-in `csv` module. Reads CSV files with UTF-8/BOM/Latin-1 encoding fallback, converts rows to tab-separated text (matching the Excel ingester output format). page_count is always 1.

### Modified Files
- **`backend/ingestion/excel_ingester.py`** — Added `XlsIngester` class using `xlrd` to read legacy `.xls` files. Outputs structured tab-separated text per sheet, same as `ExcelIngester`. Integers rendered without trailing `.0`.
- **`backend/ingestion/word_ingester.py`** — Added `LegacyDocIngester` class. Strategy: (1) try python-docx first (handles renamed .docx files), (2) fall back to extracting readable ASCII/Latin-1 text segments from raw binary. Raises `ValueError` if no text can be extracted.
- **`backend/ingestion/common.py`** — Added `import backend.ingestion.csv_ingester` to `_load_ingesters()`. Updated docstrings.
- **`backend/ingestion/service.py`** — Added `".csv": "csv"`, `".doc": "doc"`, `".xls": "xls"` to `_EXTENSION_MAP`.
- **`backend/api/routes.py`** — Added `.doc`, `.xls`, `.csv` to `_SUPPORTED_EXTENSIONS` set.
- **`pyproject.toml`** — Added `xlrd` as a runtime dependency, `xlwt` as a dev/test dependency.
- **`tests/test_ingestion.py`** — Added test classes: `TestCsvIngester` (5 tests), `TestXlsIngester` (5 tests), `TestLegacyDocIngester` (3 tests). Updated registry tests and unsupported-type tests (csv is no longer unsupported). Fixed `test_api.py` unsupported extension test to use `.pptx` instead of `.csv`.
- **`agents/architecture.md`** — Updated ingestion layer docs to reflect new file types.

### Dependencies Added
- `xlrd` (runtime) — reads legacy `.xls` files
- `xlwt` (dev only) — creates `.xls` test fixtures

## Test Results
All 148 tests pass.
