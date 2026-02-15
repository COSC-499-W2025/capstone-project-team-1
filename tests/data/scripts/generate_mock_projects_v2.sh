#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SOURCE_ZIP="${DATA_DIR}/mock_projects.zip"
OUTPUT_ZIP="${DATA_DIR}/mock_projects_v2.zip"

if [[ ! -f "${SOURCE_ZIP}" ]]; then
  echo "Missing source fixture: ${SOURCE_ZIP}" >&2
  exit 1
fi

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/mock_projects_v2.XXXXXX")"
trap 'rm -rf "${TMP_DIR}"' EXIT

WORK_DIR="${TMP_DIR}/work"
mkdir -p "${WORK_DIR}"

unzip -q "${SOURCE_ZIP}" -d "${WORK_DIR}"

export GIT_AUTHOR_NAME="Artifact Miner Fixtures"
export GIT_AUTHOR_EMAIL="fixtures@artifactminer.local"
export GIT_COMMITTER_NAME="${GIT_AUTHOR_NAME}"
export GIT_COMMITTER_EMAIL="${GIT_AUTHOR_EMAIL}"

commit_repo() {
  local repo_path="$1"
  local commit_date="$2"
  local message="$3"

  (
    cd "${repo_path}"
    git add -A
    GIT_AUTHOR_DATE="${commit_date}" GIT_COMMITTER_DATE="${commit_date}" git commit -m "${message}" >/dev/null
  )
}

SENSOR_REPO="${WORK_DIR}/projects/sensor-fleet-backend"
GO_REPO="${WORK_DIR}/projects/go-task-runner"

mkdir -p "${SENSOR_REPO}/doc" "${SENSOR_REPO}/test"
cat > "${SENSOR_REPO}/app/snapshot_v2_support.py" <<'EOF'
"""Snapshot v2 helper used for incremental fixture validation."""


def get_snapshot_version() -> str:
    return "v2"
EOF
cat > "${SENSOR_REPO}/doc/snapshot_v2_notes.md" <<'EOF'
# Snapshot V2 Notes

- Added an app helper to model incremental changes.
- Added dedicated test artifacts for incremental upload checks.
EOF
commit_repo "${SENSOR_REPO}" "2025-11-24T10:00:00+00:00" "feat: add snapshot v2 app/doc updates"

cat > "${SENSOR_REPO}/test/incremental_upload_check.md" <<'EOF'
# Incremental Upload Check

This file exists only in snapshot v2 and validates later-snapshot ingestion.
EOF
if [[ -f "${SENSOR_REPO}/README.md" ]]; then
  printf '\n- Snapshot v2: added incremental upload validation artifacts.\n' >> "${SENSOR_REPO}/README.md"
fi
commit_repo "${SENSOR_REPO}" "2025-11-24T11:00:00+00:00" "test: add incremental upload validation file"

mkdir -p "${GO_REPO}/doc"
cat > "${GO_REPO}/doc/incremental_upload_notes.md" <<'EOF'
# Incremental Upload Notes

This markdown document is introduced in v2 to emulate project evolution.
EOF
commit_repo "${GO_REPO}" "2025-11-24T12:00:00+00:00" "docs: add incremental upload notes"

cat > "${GO_REPO}/tests/incremental_snapshot_test.go" <<'EOF'
package tests

import "testing"

func TestIncrementalSnapshotFixture(t *testing.T) {
	if 2 <= 1 {
		t.Fatalf("snapshot fixture version should be newer")
	}
}
EOF
if [[ -f "${GO_REPO}/README.md" ]]; then
  printf '\n## Snapshot v2\nAdditional files and commits were added for incremental upload tests.\n' >> "${GO_REPO}/README.md"
fi
commit_repo "${GO_REPO}" "2025-11-24T13:00:00+00:00" "test: extend fixture with snapshot v2 coverage"

rm -f "${OUTPUT_ZIP}"
(
  cd "${WORK_DIR}"
  zip -qr "${OUTPUT_ZIP}" projects
)

echo "Generated ${OUTPUT_ZIP}"
