import pytest

from utils.groq_client import LazyChatGroq


def test_lazy_groq_does_not_require_key_on_import():
    llm = LazyChatGroq(model="openai/gpt-oss-120b", temperature=0)
    assert llm._llm is None


def test_lazy_groq_raises_only_when_used(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    llm = LazyChatGroq(model="openai/gpt-oss-120b", temperature=0)
    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        llm.invoke("hello")
