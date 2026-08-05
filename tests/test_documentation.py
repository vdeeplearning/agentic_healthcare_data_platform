from scripts.validate_docs import validate_docs


def test_documentation_links_and_diagrams_are_valid():
    assert validate_docs() == []
