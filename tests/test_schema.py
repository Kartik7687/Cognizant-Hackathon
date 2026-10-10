from dataclasses import replace

from drugrag.mock_data import mock_chunks
from drugrag.schema import Chunk, validate_chunks


def test_mock_chunks_are_valid():
    errors, warns = validate_chunks(mock_chunks())
    assert errors == [] and warns == []


def test_validator_flags_each_problem():
    good = mock_chunks()[0]
    bad = [
        replace(good, chunk_id="dup"),
        replace(good, chunk_id="dup"),                                # duplicate id
        replace(good, chunk_id="a", drug_name="Metformin HCl"),       # not lowercase
        replace(good, chunk_id="b", effective_date="05/01/2024"),     # bad date
        replace(good, chunk_id="c", page="iv"),                       # bad page
        replace(good, chunk_id="d", text=""),                         # empty text
        replace(good, chunk_id="e", text="x" * 2500),                 # too long -> warning
        replace(good, chunk_id="f", version=""),                      # missing citation field -> warning
    ]
    errors, warns = validate_chunks(bad)
    joined = "\n".join(errors)
    for needle in ("duplicate chunk_id", "drug_name", "YYYY-MM-DD", "page must be", "empty text"):
        assert needle in joined
    assert any("long text" in w for w in warns) and any("version is empty" in w for w in warns)


def test_from_dict_ignores_unknown_keys():
    c = Chunk.from_dict({"chunk_id": "x", "drug_name": "a", "section": "s", "text": "t", "extra": 1})
    assert c.chunk_id == "x" and c.page == "N/A"
