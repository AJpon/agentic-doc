import pytest
from adoc import catalogue, config
from adoc.errors import Refused


def test_dump_format():
    assert catalogue.dump({"a": "日本"}) == '{\n  "a": "日本"\n}\n'


def test_missing_catalogue_refused(repo):
    repo.config()
    with pytest.raises(Refused, match="run outline"):
        catalogue.load(config.load(repo.root))


def test_schema_mismatch_refused(repo):
    repo.config()
    repo.write("docs/wiki/catalogue.json", '{\n  "version": 1\n}\n')
    with pytest.raises(Refused, match="schema"):
        catalogue.load(config.load(repo.root))


def test_save_refuses_non_canonical(repo):
    repo.config()
    repo.write("docs/wiki/catalogue.json", '{"version":1,"chapters":[],"pages":[]}')
    cfg = config.load(repo.root)
    data = catalogue.load(cfg)
    with pytest.raises(Refused, match="canonical"):
        catalogue.save(cfg, data)


def test_save_roundtrips_canonical(five):
    cfg = config.load(five.root)
    before = cfg.catalogue.read_text(encoding="utf-8")
    catalogue.save(cfg, catalogue.load(cfg))
    assert cfg.catalogue.read_text(encoding="utf-8") == before


def test_empty_sources_rejected_by_schema(repo):
    repo.config()
    repo.catalogue([{"id": "g/p", "sources": []}])
    with pytest.raises(Refused, match="sources"):
        catalogue.load(config.load(repo.root))
