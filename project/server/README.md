# Ingest MVP Server

Minimal FastAPI service that accepts a `.zip`, scans top-level directories, and stores a lightweight selection in memory. No ingestion work happens this week.

## Quickstart

```bash
uvicorn server.server:app --reload
```

Server listens on `http://127.0.0.1:8000` by default.

## API Guide

Create a sample archive for testing:

```bash
mkdir -p /tmp/demo/{stories,docs,backend}
echo "print('hi')" > /tmp/demo/stories/main.py
echo "# docs" > /tmp/demo/docs/readme.md
echo '{"env":"dev"}' > /tmp/demo/backend/config.json
(cd /tmp/demo && zip -r demo.zip .)
```

Upload the archive:

```bash
curl -F "file=@/tmp/demo/demo.zip" http://127.0.0.1:8000/ingest/upload
```

Check progress:

```bash
curl http://127.0.0.1:8000/ingest/{ingest_id}/progress
```

List candidates once ready:

```bash
curl http://127.0.0.1:8000/ingest/{ingest_id}/candidates
```

Persist a selection:

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"selected_paths":["stories","root_files"]}' \
  http://127.0.0.1:8000/ingest/{ingest_id}/select
```

All data is kept in memory using the in-process store defined in `storage.py`.
