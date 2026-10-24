import pytest
from adoc import gitutil
from adoc.errors import Refused


def test_git_outside_repo_refused(tmp_path):
    with pytest.raises(Refused, match="not a git repository"):
        gitutil.ensure_repo(tmp_path)


def test_changed_since_reports_non_ascii_and_space_paths(repo):
    repo.write("src/日本語 ファイル.py", "a")
    base = repo.commit()
    repo.write("src/日本語 ファイル.py", "b")
    repo.commit()
    assert gitutil.changed_since(repo.root, base, ["src/**"], []) == ["src/日本語 ファイル.py"]


def test_changed_since_unresolvable_returns_none(repo):
    repo.write("a.py", "a")
    repo.commit()
    assert gitutil.changed_since(repo.root, "0" * 40, ["**"], []) is None


def test_glob_star_does_not_cross_slash(repo):
    repo.write("src/a.py", "a")
    repo.write("src/deep/b.py", "b")
    repo.commit()
    assert gitutil.ls_files(repo.root, ["src/*.py"], []) == ["src/a.py"]
    assert sorted(gitutil.ls_files(repo.root, ["src/**/*.py"], [])) == ["src/a.py", "src/deep/b.py"]


def test_exclude_applies(repo):
    repo.write("src/a.py", "a")
    repo.write("vendor/x.py", "x")
    repo.commit()
    assert gitutil.ls_files(repo.root, [], ["vendor/**"]) == ["src/a.py"]


@pytest.mark.parametrize("exclude", ["zzz/**", "abc/**", "x", "vendor/**"])
def test_ls_files_single_nested_literal_with_exclude(repo, exclude):
    # Apple Git 2.50 は、肯定の pathspec が 1 ファイルだけのとき、除外の pathspec の長さ次第で 0 件を返す
    repo.write("a/b/c.py", "a")
    repo.write("src/pkg/main.py", "m")
    repo.write("vendor/x.py", "x")
    repo.commit()
    assert gitutil.ls_files(repo.root, ["a/b/c.py"], [exclude]) == ["a/b/c.py"]
    assert gitutil.ls_files(repo.root, ["src/pkg/main.py"], [exclude]) == ["src/pkg/main.py"]


def test_ls_files_exclude_still_removes(repo):
    repo.write("vendor/x.py", "x")
    repo.write("src/a.py", "a")
    repo.commit()
    assert gitutil.ls_files(repo.root, ["vendor/x.py"], ["vendor/**"]) == []
    assert gitutil.ls_files(repo.root, ["**/*.py"], ["vendor/**"]) == ["src/a.py"]


def test_untracked_lists_new_unignored_files(repo):
    repo.write(".gitignore", "*.log\n")
    repo.commit()
    repo.write("new.py", "n")
    repo.write("x.log", "l")
    assert gitutil.untracked(repo.root, [], []) == ["new.py"]


def test_dirty_lists_modified_paths(repo):
    repo.write("a.py", "a")
    repo.commit()
    repo.write("a.py", "b")
    assert gitutil.dirty(repo.root, ["a.py"], []) == ["a.py"]


def test_head_resolve_and_ancestor(repo):
    repo.write("a", "1")
    c1 = repo.commit()
    repo.write("a", "2")
    c2 = repo.commit()
    assert gitutil.head(repo.root) == c2
    assert gitutil.resolve_commit(repo.root, "HEAD~1") == c1
    assert gitutil.resolve_commit(repo.root, "nope") is None
    assert gitutil.is_ancestor(repo.root, c1, c2) and not gitutil.is_ancestor(repo.root, c2, c1)
