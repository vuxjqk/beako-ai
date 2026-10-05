from src.services import agent, retrieval


class _Db:
    def connection(self):
        return None


def test_search_accepts_a_list_of_phrasings(monkeypatch):
    seen = []
    monkeypatch.setattr(retrieval, "retrieve", lambda conn, embedder, query, *a, **kw: seen.append(query) or [])
    s = agent._Session(_Db(), None, retrieval.default_config(), None)
    assert s.search(["Ram horn lost", "Rem interlude"]) == "No passages found."
    assert seen == ["Ram horn lost Rem interlude"]
