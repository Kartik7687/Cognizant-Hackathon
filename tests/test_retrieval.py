import numpy as np
import pytest

from drugrag.mock_data import mock_chunks
from drugrag.retrieval import MODES, Index, Retriever, format_context, get_embedder
from drugrag.retrieval.drug_detect import DrugDetector
from drugrag.retrieval.rerank import OverlapReranker
from drugrag.schema import format_citation, load_chunks, save_chunks


@pytest.fixture(scope="module")
def retriever(tmp_path_factory):
    emb = get_embedder("hash")
    idx = Index.build(mock_chunks(), emb)
    d = tmp_path_factory.mktemp("index")
    idx.save(d)
    return Retriever.from_dir(str(d), reranker="overlap")


# ---------------------------------------------------------------- drug detection
def test_detects_generic_brand_typo_and_multiple():
    det = DrugDetector(mock_chunks())
    assert det.detect("What is the dose of metformin?") == ["metformin"]
    assert det.detect("Is Lipitor safe?") == ["atorvastatin"]
    assert det.detect("side effects of metfromin") == ["metformin"]  # typo
    assert set(det.detect("Can I take ibuprofen with Coumadin?")) == {"ibuprofen", "warfarin"}
    assert det.detect("What medicine helps with a headache?") == []


# -------------------------------------------------------------------- filtering
def test_filter_restricts_to_detected_drug(retriever):
    res = retriever.retrieve("contraindications of metformin", mode="hybrid", top_k=5)
    assert res.detected_drugs == ["metformin"]
    assert {h.chunk.drug_name for h in res.hits} == {"metformin"}


def test_explicit_drugs_override_and_empty_list_disables_filter(retriever):
    res = retriever.retrieve("bleeding risk", mode="hybrid", top_k=10, drugs=["warfarin"])
    assert {h.chunk.drug_name for h in res.hits} == {"warfarin"}
    res = retriever.retrieve("bleeding risk", mode="hybrid", top_k=10, drugs=[])
    assert len({h.chunk.drug_name for h in res.hits}) > 1


def test_unknown_drug_falls_back_with_note(retriever):
    res = retriever.retrieve("bleeding risk", mode="hybrid", drugs=["notadrug"])
    assert res.hits and res.notes


# ------------------------------------------------------------------ section hits
@pytest.mark.parametrize(
    "query,drug,section",
    [
        ("What are the contraindications of metformin?", "metformin", "Contraindications"),
        ("How is amoxicillin dosed in adults?", "amoxicillin", "Dosage and Administration"),
        ("What are the side effects of atorvastatin?", "atorvastatin", "Adverse Reactions"),
        ("What is warfarin used for?", "warfarin", "Indications and Usage"),
        ("Boxed warning for ibuprofen", "ibuprofen", "Warnings and Precautions"),
    ],
)
def test_top_hit_is_right_section(retriever, query, drug, section):
    top = retriever.retrieve(query, mode="hybrid", top_k=3).hits[0].chunk
    assert (top.drug_name, top.section) == (drug, section)


def test_section_boost_does_not_confuse_contraindications_with_indications(retriever):
    res = retriever.retrieve("What is warfarin used for?", mode="hybrid", top_k=1, section_boost=True)
    assert res.hits[0].chunk.section == "Indications and Usage"
    # With the boost the intended section must rank at least as high as without it.
    def rank_of(boost):
        hits = retriever.retrieve("What is warfarin used for?", mode="hybrid", top_k=6, section_boost=boost).hits
        return next(h.rank for h in hits if h.chunk.section == "Indications and Usage")
    assert rank_of(True) <= rank_of(False)


def test_rerank_mode_keeps_drug_filter_and_uses_reranker_scores(retriever):
    # The offline OverlapReranker is lexical, so only wiring is asserted here (real quality: bge-reranker).
    res = retriever.retrieve("side effects of atorvastatin", mode="hybrid_rerank", top_k=3)
    assert {h.chunk.drug_name for h in res.hits} == {"atorvastatin"}
    assert not res.notes


def test_two_drug_question_surfaces_interactions(retriever):
    res = retriever.retrieve("Can I take ibuprofen with warfarin?", mode="hybrid_rerank", top_k=3)
    assert {h.chunk.drug_name for h in res.hits} <= {"ibuprofen", "warfarin"}
    assert any(h.chunk.section == "Drug Interactions" for h in res.hits[:2])


# ---------------------------------------------------------------------- modes
@pytest.mark.parametrize("mode", MODES)
def test_every_mode_returns_ranked_hits(retriever, mode):
    res = retriever.retrieve("lactic acidosis risk", mode=mode, top_k=4)
    assert 0 < len(res.hits) <= 4
    assert [h.rank for h in res.hits] == list(range(1, len(res.hits) + 1))
    scores = [h.score for h in res.hits]
    assert scores == sorted(scores, reverse=True)


def test_invalid_mode_raises(retriever):
    with pytest.raises(ValueError):
        retriever.retrieve("x", mode="magic")


def test_rerank_without_reranker_falls_back(tmp_path):
    idx = Index.build(mock_chunks(), get_embedder("hash"))
    r = Retriever(idx, get_embedder("hash"), reranker=None)
    res = r.retrieve("metformin dosage", mode="hybrid_rerank")
    assert res.hits and any("no reranker" in n for n in res.notes)


def test_overlap_reranker_prefers_matching_text():
    s = OverlapReranker().score("liver failure", ["acute liver failure contraindicated", "nausea and rash"])
    assert s[0] > s[1]


# ------------------------------------------------------------ persistence, format
def test_index_roundtrip(tmp_path):
    idx = Index.build(mock_chunks(), get_embedder("hash"))
    idx.save(tmp_path)
    loaded = Index.load(tmp_path)
    assert len(loaded) == len(idx) == 30
    assert np.allclose(loaded.embeddings, idx.embeddings)
    assert loaded.embedder_name == "hash"


def test_embedder_mismatch_is_rejected():
    idx = Index.build(mock_chunks(), get_embedder("hash"))
    other = get_embedder("hash")
    other.name = "bge-small"
    with pytest.raises(ValueError):
        Retriever(idx, other)


def test_chunk_jsonl_roundtrip(tmp_path):
    chunks = mock_chunks()
    save_chunks(chunks, tmp_path / "c.jsonl")
    assert load_chunks(tmp_path / "c.jsonl") == chunks


def test_citation_and_context_format(retriever):
    res = retriever.retrieve("metformin contraindications", mode="hybrid", top_k=2)
    cite = format_citation(res.hits[0].chunk)
    assert cite == "Metformin, label version 1, Contraindications, page N/A, effective 2024-01-01"
    ctx = format_context(res.hits)
    assert ctx.startswith("[1] Metformin") and "\n\n[2] " in ctx
    assert res.to_dict()["hits"][0]["citation"] == cite
