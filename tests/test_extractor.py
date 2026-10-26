from __future__ import annotations

import pytest

from app.memory.extractor import triage_facts
from app.memory.facts import InMemoryBrandMemory
from app.schemas import BrandFact, ExtractedFact, FactStatus


def fact(conf, source="client_brief", statement="Harbor Hops uses Maine grain."):
    return ExtractedFact(category="product", statement=statement, source=source, evidence="e", confidence=conf)


def triage(facts, **kw):
    return triage_facts(facts, client_id="c", run_id="r", auto_save_threshold=0.85, review_threshold=0.6, **kw)


@pytest.mark.parametrize("conf,band", [(0.95, "active"), (0.85, "active"), (0.84, "pending"), (0.6, "pending"), (0.59, "dropped")])
def test_confidence_bands(conf, band):
    result = triage([fact(conf)])
    assert {"active": result.active, "pending": result.pending, "dropped": result.dropped}[band]


def test_out_of_range_confidence_is_clamped():
    assert triage([fact(1.7)]).active[0].confidence == 1.0


def test_approved_output_cap_routes_agent_wording_through_review():
    result = triage([fact(0.95, source="approved_output")], approved_output_cap=0.8)
    assert result.pending and not result.active


@pytest.mark.asyncio
async def test_reextraction_never_downgrades_or_resurrects():
    memory = InMemoryBrandMemory()

    def bf(status, conf, statement="Harbor Hops uses Maine grain."):
        return BrandFact(client_id="c", category="product", statement=statement, source="s", evidence="e", confidence=conf, status=status)

    await memory.save_facts([bf(FactStatus.active, 0.9)])
    await memory.save_facts([bf(FactStatus.pending, 0.7, "harbor hops uses maine grain")])  # same fact, new wording
    facts = await memory.get_facts("c")
    assert len(facts) == 1 and facts[0].status is FactStatus.active and facts[0].confidence == 0.9

    await memory.save_facts([bf(FactStatus.pending, 0.7, "Harbor Hops sells cider.")])
    rejected = (await memory.get_facts("c", FactStatus.pending))[0]
    await memory.set_fact_status(rejected.id, FactStatus.rejected)
    await memory.save_facts([bf(FactStatus.active, 0.99, "Harbor Hops sells cider.")])
    assert (await memory.get_facts("c", FactStatus.rejected))[0].statement == "Harbor Hops sells cider."
