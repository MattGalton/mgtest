import argparse
import json
from types import SimpleNamespace

from mgtest.cli import mgtest_home
from mgtest.runtime.cache import CacheStore
from mgtest.runtime.runs import RunWorkspace


def test_home_reports_and_clears_project_runtime_state(tmp_path, capsys):
    parser = argparse.ArgumentParser()
    mgtest_home.populate_parser(parser)
    args = parser.parse_args([str(tmp_path)])
    assert args.func(args) == 0
    assert "Runtime:" in capsys.readouterr().out
    cache_file = tmp_path / ".mgtest" / "cache" / "git" / "entry" / "content"
    run_file = tmp_path / ".mgtest" / "runs" / "run" / "manifest.json"
    cache_file.parent.mkdir(parents=True)
    run_file.parent.mkdir(parents=True)
    cache_file.write_text("cached")
    run_file.write_text("{}")

    args = parser.parse_args([str(tmp_path), "--clear"])
    assert args.func(args) == 0
    assert not cache_file.exists()
    assert not run_file.exists()
    assert (tmp_path / ".mgtest" / "config.yaml").is_file()


def test_home_lists_cache_and_runs_as_json_and_prunes_retained_runs(tmp_path, capsys):
    parser = argparse.ArgumentParser()
    mgtest_home.populate_parser(parser)
    workspace = RunWorkspace.create(tmp_path, SimpleNamespace(definitions={}, test_order=()))
    workspace.finalize()
    cache = CacheStore(tmp_path / ".mgtest" / "cache", 1)
    cache.directory("git", "https://example.test/repository")

    args = parser.parse_args([str(tmp_path), "--runs", "--json"])
    assert args.func(args) == 0
    runs = json.loads(capsys.readouterr().out)
    assert runs[0]["id"] == workspace.run_id

    args = parser.parse_args([str(tmp_path), "--cache", "--json"])
    assert args.func(args) == 0
    entries = json.loads(capsys.readouterr().out)
    assert entries[0]["identity"] == "https://example.test/repository"

    args = parser.parse_args([str(tmp_path), "--prune", "--json"])
    assert args.func(args) == 0
    assert json.loads(capsys.readouterr().out) == {"runs_removed": 0}
