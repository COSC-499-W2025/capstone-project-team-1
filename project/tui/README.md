Textual client that uploads a `.zip` to the API, waits for scanning to finish, and lets you tick the candidate directories to keep.

## Running the TUI

```bash
python -m tui.app
```

The client expects the FastAPI server to be running at `http://127.0.0.1:8000`. To target a different host, set `API_BASE`:

```bash
API_BASE=http://localhost:9000 python -m tui.app
```

### Flow

1. Enter the path to a `.zip` file and press **Upload**.
2. Watch the progress label move through validating, scanning, and waiting for selection.
3. Once the candidate list appears, tick the directories you want.
4. Press **Save Selection** to POST the choice back to the server.

This week the selection is stored in memory only; ingestion work will plug in later.
