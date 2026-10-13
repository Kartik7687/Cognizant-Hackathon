"""End-to-end tests of answer() with a fake Ollama, so they run offline."""
import sys
import types

import pytest

from drugrag.generation.answer import answer
from drugrag.mock_data import mock_chunks
from drugrag.retrieval import Index, Retriever, get_embedder


@pytest.fixture(scope="module")
def retriever(tmp_path_factory):
    idx = Index.build(mock_chunks(), get_embedder("hash"))
    d = tmp_path_factory.mktemp("index")
    idx.save(d)
    return Retriever.from_dir(str(d))


@pytest.fixture(autouse=True)
def fake_ollama(monkeypatch):
    calls = []
    fake = types.ModuleType("ollama")

    def chat(model, messages, options=None):
        calls.append(messages)
        return {"message": {"content": "Metformin starts at 500 mg [1] with meals [2.1]."}}

    fake.chat = chat
    fake.calls = calls
    monkeypatch.setitem(sys.modules, "ollama", fake)
    return fake


def run(retriever, q, mode="clinician"):
    return answer(q, retriever.retrieve(q, mode="hybrid", top_k=3).hits, mode)


def test_normal_question_is_generated_cited_and_has_sources(retriever, fake_ollama):
    a = run(retriever, "What is the starting dose of metformin?")
    assert not a.refused and not a.not_found
    assert "[1]" in a.text and "[2.1]" not in a.text  # label section numbers removed
    assert a.text.rstrip().split("Sources:")[-1].strip() and a.sources
    assert len(fake_ollama.calls) == 1


def test_advice_question_gets_safe_template_without_calling_llm(retriever, fake_ollama):
    a = run(retriever, "Should I double my metformin dose?")
    assert a.refused and "personal medical advice" in a.text
    assert not fake_ollama.calls


def test_emergency_gets_urgent_message(retriever, fake_ollama):
    a = answer("I took too many pills", [], "patient")
    assert a.refused and "URGENT" in a.text and "102" in a.text and "112" in a.text
    assert not fake_ollama.calls


@pytest.mark.parametrize("q", [
    "I m having a heart attack",
    "I just had an accident and have broken some bones",
    "My father is having a stroke",
])
def test_general_emergencies_tell_user_to_call_102(retriever, fake_ollama, q):
    a = run(retriever, q)
    assert a.refused and "URGENT" in a.text and "102" in a.text
    assert not a.sources and not fake_ollama.calls


def test_unknown_drug_is_not_found_and_never_reaches_llm(retriever, fake_ollama):
    a = run(retriever, "Does zolpidem cause sleepwalking?")
    assert a.not_found and not a.refused and not a.sources
    assert not fake_ollama.calls


def test_no_hits_is_not_found(fake_ollama):
    a = answer("What is the dose of metformin?", [], "patient")
    assert a.not_found and not fake_ollama.calls
