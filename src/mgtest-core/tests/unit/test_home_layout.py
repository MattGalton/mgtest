from mgtest.home.layout import HomeLayout


def test_home_layout_resolves_environment_and_creates_its_directories(tmp_path, monkeypatch):
    base = tmp_path / "custom-home"
    monkeypatch.setenv("MGT_HOME", str(base))

    layout = HomeLayout.from_environment().ensure_exists()

    assert layout.base == base
    assert layout.directories == (base / "schemas", base / "resources", base / "tests")
    assert all(path.is_dir() for path in layout.directories)
