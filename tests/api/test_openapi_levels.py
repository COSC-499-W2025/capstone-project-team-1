from fastapi.testclient import TestClient
from artifactminer.api.app import create_app


def test_openapi_includes_level_fields():
    client = TestClient(create_app())
    spec = client.get("/openapi.json").json()

    def props_from_ref(ref: str):
        name = ref.split("/")[-1]
        return spec["components"]["schemas"][name]["properties"]

    skills_schema = (
        spec["paths"]["/skills"]["get"]["responses"]["200"]["content"]["application/json"][
            "schema"
        ]
    )
    skills_props = props_from_ref(skills_schema["items"]["$ref"])
    assert "level" in skills_props

    chrono_schema = (
        spec["paths"]["/skills/chronology"]["get"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]
    )
    chrono_props = props_from_ref(chrono_schema["items"]["$ref"])
    assert "level" in chrono_props
