# Test ZIP Fixtures

This directory stores ZIP fixtures used by integration tests.

## Fixtures

- `mock_projects.zip`: baseline snapshot containing 8 git repositories under `projects/`.
- `mock_projects_v2.zip`: later snapshot of the same project set with additional commits and files.

## Regenerate v2 Fixture

Run:

```bash
bash tests/data/scripts/generate_mock_projects_v2.sh
```

The generator:

- starts from `mock_projects.zip`
- updates `projects/sensor-fleet-backend` and `projects/go-task-runner`
- creates new commits and files to simulate incremental project evolution
- writes `mock_projects_v2.zip`

## Expected v2 Additions

- `projects/sensor-fleet-backend/app/snapshot_v2_support.py`
- `projects/sensor-fleet-backend/doc/snapshot_v2_notes.md`
- `projects/sensor-fleet-backend/test/incremental_upload_check.md`
- `projects/go-task-runner/doc/incremental_upload_notes.md`
- `projects/go-task-runner/tests/incremental_snapshot_test.go`
