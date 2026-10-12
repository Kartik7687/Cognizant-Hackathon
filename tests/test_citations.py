from drugrag.generation.answer import clean_citations


def test_valid_citations_kept():
    assert clean_citations("A [1]. B [2][3].", 3) == "A [1]. B [2][3]."


def test_label_section_numbers_removed():
    assert clean_citations("Dose is 5 mg [2.1] daily [1].", 3) == "Dose is 5 mg  daily [1]."
    assert clean_citations("See [5.1] and [17].", 3) == "See  and ."


def test_mixed_group_keeps_valid_only():
    assert clean_citations("Fact [1, 4.7, 2].", 3) == "Fact [1][2]."


def test_see_references_untouched():
    t = "contraindicated [see Warnings and Precautions (5.1)] [1]"
    assert clean_citations(t, 2) == t
