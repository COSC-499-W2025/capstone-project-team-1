from pathlib import Path
from zipfile import ZipFile
import tempfile
from starlette.testclient import TestClient
from artifactminer.api.app import create_app

# Create test app and client
app = create_app()
client = TestClient(app)

# Create test ZIP
tmp_path = Path(tempfile.mkdtemp())
zip_path = tmp_path / 'test.zip'

with ZipFile(zip_path, 'w') as zf:
    zf.writestr('test-repo/.git/config', '[core]')
    zf.writestr('test-repo/.git/HEAD', 'ref: refs/heads/main')
    zf.writestr('test-repo/README.md', '# Test')

# Create intake
intake_response = client.post('/local-llm/context', json={'zip_path': str(zip_path)})
print('Intake response:', intake_response.status_code)
intake_data = intake_response.json()
print('Intake data:', intake_data)

repo_id = intake_data['repos'][0]['id']
print('Repo ID:', repo_id)

# Try contributors endpoint
contrib_response = client.post('/local-llm/context/contributors', json={'repo_ids': [repo_id]})
print('Contrib response:', contrib_response.status_code)
print('Contrib data:', contrib_response.json())
