def test_run_callable():
    import artifactminer.tui.app as app
    assert callable(app.run)
