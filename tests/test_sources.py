from evals import fixtures as fx

from app import checks
from app.exports import report_markdown, research_tables_md
from app.schemas import ResearchOutput


def _research() -> ResearchOutput:
    return ResearchOutput.model_validate(fx.BREWERY_RESEARCH.model_dump())


def test_links_the_lookup_did_not_return_are_cleared():
    research = _research()
    lookup = {"summary": "Allagash site [https://www.allagash.com]", "sources": []}
    cleared = checks.strip_unknown_sources(research, lookup)
    assert cleared == 1  # visitportland was never in the lookup
    assert research.competitor_landscape[0].source_url == "https://www.allagash.com/"
    assert research.market_facts[0].source_url == ""


def test_no_lookup_means_no_links():
    research = _research()
    assert checks.strip_unknown_sources(research, None) == 2
    assert all(not r.source_url for r in research.market_facts + research.competitor_landscape)


def test_lookup_sources_list_counts_as_known():
    research = _research()
    lookup = {"summary": "", "sources": [{"url": "https://www.visitportland.com", "title": "Visit"}]}
    checks.strip_unknown_sources(research, lookup)
    assert research.market_facts[0].source_url == "https://www.visitportland.com/"


def test_tables_have_source_links():
    md = "\n".join(research_tables_md(_research()))
    assert "## Market data and sources" in md
    assert "| What | Finding | Source |" in md
    assert "[allagash.com](https://www.allagash.com/)" in md
    assert "no source" in md
    assert "### Online presence" in md and "not found" in md.lower()
    assert "### Competitors" in md


def test_report_markdown_includes_tables():
    md = report_markdown(fx.BREWERY_REPORT, _research())
    assert md.index("## Market data and sources") < md.index("Next steps")
