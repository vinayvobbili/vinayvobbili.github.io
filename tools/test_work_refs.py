"""Tests for tools/work_refs.py. Run: python -m pytest tools/test_work_refs.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import work_refs  # noqa: E402


def labels(text):
    return [label for _, label, _ in work_refs.scan(text)]


def test_flags_each_kind_of_work_reference():
    assert labels("It runs in production today.") == ["production"]
    assert labels("Our SOC handles the queue.") == ["our ..."]
    assert labels("Notifications go to Webex.") == ["work systems"]
    assert labels("Backtested on 32K tickets.") == ["ticket data"]
    assert labels("answers from an internal policy corpus") == ["internal"]
    assert labels("I extracted that wrapper into a package.") == ["origin"]
    assert labels("So I pulled them out of the SOC.") == ["origin"]
    assert labels("Why did it flag case 41872?") == ["internal names"]


def test_plain_feature_text_is_clean():
    assert labels("attestq keeps a generous rerank window so a lone chunk survives.") == []


def test_reports_line_numbers_and_trims_long_lines():
    text = "first line\n" + ("x" * 200) + " in production " + ("y" * 200)
    [(line, label, snippet)] = work_refs.scan(text)
    assert (line, label) == (2, "production")
    assert snippet.startswith("…") and snippet.endswith("…") and "production" in snippet


def test_exit_status_gates_on_hits(tmp_path):
    clean, dirty = tmp_path / "clean.md", tmp_path / "dirty.md"
    clean.write_text("A tool that reranks.\n")
    dirty.write_text("Used by my team at work.\n")
    assert work_refs.main([str(clean)]) == 0
    assert work_refs.main([str(dirty), "--summary"]) == 1


def test_repo_mode_reads_committed_text_files_only(tmp_path, capsys):
    import subprocess

    def git(*args):
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)

    git("init", "-q")
    (tmp_path / "README.md").write_text("Runs in production at work.\n")
    (tmp_path / "logo.png").write_bytes(b"\x89PNG production")
    git("add", ".")
    git("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-qm", "init")
    (tmp_path / "README.md").write_text("clean now, but not committed\n")

    assert [p for p, _ in work_refs.repo_files(tmp_path)] == ["README.md"]
    assert work_refs.main(["--repo", str(tmp_path), "--summary"]) == 1
    assert "README.md" in capsys.readouterr().out


def test_default_files_cover_posts_tabs_and_pages():
    names = {p.relative_to(work_refs.ROOT).as_posix() for p in work_refs.default_files()}
    assert any(n.startswith("_posts/") for n in names)
    assert "attestq/index.html" in names
    assert not any(n.startswith((".preview", "_site")) for n in names)
