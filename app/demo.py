"""Demo mode: canned outputs instead of the model API, to click through the dashboard for free.

AGENCY_DEMO=1 makes every agent return the Harbor Hops golden fixtures whatever the brief
says, so use it to learn the workflow, never to judge output quality. No web lookup is made,
and the research check says so.
"""

from __future__ import annotations

import asyncio

from app.llm import LLMResult, SearchResult
from app.schemas import ResearchOutput
from evals.fixtures import BREWERY_OUTPUTS

DEMO_NOTE = (
    "Demo mode: these are sample answers for Harbor Hops, a Maine brewery, whatever name you typed. "
    "Nothing was looked up. Turn demo mode off to analyze a real business."
)


class DemoLLM:
    async def generate(self, *, system, prompt, output_type, model, effort=None, max_tokens=16000):
        await asyncio.sleep(0.5)  # long enough to see the "Working" lane
        output = BREWERY_OUTPUTS[output_type]
        if output_type is ResearchOutput:
            data = output.model_dump()
            data["business_profile"]["basis"] = DEMO_NOTE
            output = ResearchOutput.model_validate(data)
        return LLMResult(output=output, model=f"demo:{model}", input_tokens=0, output_tokens=0, stop_reason="end_turn")

    async def search(self, *, system, prompt, model, max_searches=5):
        await asyncio.sleep(0.3)
        return SearchResult(DEMO_NOTE, [], f"demo:{model}", 0, 0, 0)
