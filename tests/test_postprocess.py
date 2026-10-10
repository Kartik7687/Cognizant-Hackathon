from drugrag.pipeline.postprocess import iso_date, postprocess, split_text
from drugrag.schema import Chunk, validate_chunks


def test_iso_date():
    assert iso_date("20250603") == "2025-06-03"
    assert iso_date("2025-06-03") == "2025-06-03"
    assert iso_date("") == ""


def test_split_keeps_all_words_and_respects_limit():
    sents = [f"Sentence number {i} says take the tablet with water." for i in range(120)]
    text = " ".join(sents)
    parts = split_text(text, 500)
    assert len(parts) > 5 and all(len(p) <= 500 for p in parts)
    assert " ".join(parts).split() == text.split()


def test_split_handles_one_giant_unbroken_sentence():
    text = "word " * 2000
    parts = split_text(text, 300)
    assert all(len(p) <= 300 for p in parts)
    assert " ".join(parts).split() == text.split()


def test_short_text_untouched_and_tail_not_tiny():
    assert split_text("Short passage that stays whole.", 500) == ["Short passage that stays whole."]
    parts = split_text("A" * 10 + ". " + "B" * 495 + ". C.", 500)
    assert all(len(p) >= 40 for p in parts)


def _chunk(**kw):
    base = dict(chunk_id="x-1", drug_name="lantus", section="Drug Interactions", set_id="6c81d894-aaaa",
                version="2", effective_date="20260101", section_code="DRUG INTERACTIONS", aliases=["Lantus"],
                text="Some medications may alter insulin requirements and increase the risk of hypoglycemia. " * 40)
    base.update(kw)
    return Chunk(**base)


def test_postprocess_end_to_end():
    pdp = _chunk(section="Principal Display Panel", chunk_id="x-2", text="Carton label NDC 1234 " * 5)
    out = postprocess([_chunk(), pdp])
    assert all(c.section != "Principal Display Panel" for c in out)
    assert {c.drug_name for c in out} == {"insulin glargine"}          # renamed from the brand
    assert "lantus" in out[0].aliases and "Lantus" not in out[0].aliases  # lowercase, brand kept as alias
    assert all(c.effective_date == "2026-01-01" for c in out)
    ids = [c.chunk_id for c in out]
    assert len(ids) == len(set(ids)) and ids[0] == "insulin-glargine-6c81d894-drug-interactions-0"
    errors, _ = validate_chunks(out)
    assert errors == []
