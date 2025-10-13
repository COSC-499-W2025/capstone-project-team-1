def test_module_imports():
    import artifactminer.tui.app as app
    assert hasattr(app, "run")


def test_app_class_exists():
    import artifactminer.tui.app as app
    assert hasattr(app, "ArtifactMinerTUI")
