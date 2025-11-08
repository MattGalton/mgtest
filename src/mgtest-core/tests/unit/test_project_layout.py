from mgtest.project.layout import ProjectLayout


def test_definition_document_classification(tmp_path):
    resource = tmp_path / "r_database.yaml"
    test = tmp_path / "t_health.yml"
    other = tmp_path / "config.yaml"
    for path in (resource, test, other):
        path.write_text("{}")

    assert ProjectLayout.is_mgtest_resource(resource)
    assert not ProjectLayout.is_mgtest_test(resource)
    assert ProjectLayout.definition_kind(resource) == "resources"
    assert ProjectLayout.is_mgtest_test(test)
    assert ProjectLayout.definition_kind(test) == "tests"
    assert ProjectLayout.definition_kind(other) is None


def test_discovery_skips_runtime_and_builtin_directories(tmp_path):
    layout = ProjectLayout(tmp_path)
    suite = tmp_path / "s_smoke"
    runtime = tmp_path / ".mgtest"
    builtin = tmp_path / "builtin"
    for directory in (suite, runtime, builtin):
        directory.mkdir()

    assert layout.is_discoverable_directory(suite)
    assert ProjectLayout.is_mgtest_suite(suite)
    assert not layout.is_discoverable_directory(runtime)
    assert not layout.is_discoverable_directory(builtin)


def test_find_root_accepts_files_and_ancestor_directories(tmp_path):
    root = tmp_path / "mgtest"
    nested = root / "s_smoke" / "t_health.yaml"
    (root / "builtin").mkdir(parents=True)
    nested.parent.mkdir()
    nested.write_text("{}")

    assert ProjectLayout.find_root(nested) == root
    assert ProjectLayout.find_root(tmp_path) == root
