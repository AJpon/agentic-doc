from adoc import catalogue, config, state


def test_classify_five_states(five):
    cfg = config.load(five.root)
    data = catalogue.load(cfg)
    got = {p["id"]: state.classify(cfg, p).state for p in data["pages"]}
    assert got == {"g/fresh": "fresh", "g/changed": "changed", "g/unresolved": "unresolved",
                   "g/unverified": "unverified", "g/missing": "missing"}


def test_changed_lists_files(five):
    cfg = config.load(five.root)
    p = catalogue.page_index(catalogue.load(cfg))["g/changed"]
    assert state.classify(cfg, p).changed == ["src/b.py"]


def test_excluded_change_does_not_make_page_changed(repo):
    repo.write("src/a.py", "a")
    repo.write("src/gen/x.py", "x")
    base = repo.commit()
    repo.write("docs/wiki/g/p.md", "x")
    repo.config(exclude=["src/gen/**"])
    repo.catalogue([{"id": "g/p", "sources": ["src/**"], "source_commit": base}])
    repo.commit()
    repo.write("src/gen/x.py", "y")
    repo.commit()
    cfg = config.load(repo.root)
    p = catalogue.page_index(catalogue.load(cfg))["g/p"]
    assert state.classify(cfg, p).state == "fresh"


def test_non_ascii_source_change_detected(repo):
    repo.write("src/日本語 ファイル.py", "a")
    base = repo.commit()
    repo.write("docs/wiki/g/p.md", "x")
    repo.config()
    repo.catalogue([{"id": "g/p", "sources": ["src/日本語 ファイル.py"], "source_commit": base}])
    repo.write("src/日本語 ファイル.py", "b")
    repo.commit()
    cfg = config.load(repo.root)
    st = state.classify(cfg, catalogue.page_index(catalogue.load(cfg))["g/p"])
    assert st.state == "changed" and st.changed == ["src/日本語 ファイル.py"]
