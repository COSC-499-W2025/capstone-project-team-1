# Running the ARTIFACT-MINER TUI

Follow these steps from the repository root.

1. Create (once) and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r project/requirements.txt
   ```
3. Start the FastAPI server in a dedicated terminal and keep it running:
   ```bash
   UVLOOP_NO_EXTENSIONS=1 uvicorn server.server:app --app-dir project --loop asyncio --http h11 --reload
   ```
4. In a second terminal (same virtual environment), launch the Textual client:
   ```bash
   python project/tui/app.py
   ```

The TUI will now connect to the local API. Upload a `.zip`, wait for the candidate list, select the desired folders, and save the selection. Stop both processes with `Ctrl+C` when finished.
