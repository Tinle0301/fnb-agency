"""Demo mode: canned outputs instead of the model API, to click through the console for free.

AGENCY_DEMO=1 makes every agent return the Harbor Hops golden fixtures whatever the brief
says, so use it to learn the workflow, never to judge output quality.
"""

from __future__ import annotations

import asyncio

from app.llm import LLMResult
from evals.fixtures import BREWERY_OUTPUTS


class DemoLLM:
    async def generate(self, *, system, prompt, output_type, model, effort=None, max_tokens=16000):
        await asyncio.sleep(0.5)  # long enough to see the "Working" lane
        return LLMResult(
            output=BREWERY_OUTPUTS[output_type], model=f"demo:{model}", input_tokens=0, output_tokens=0, stop_reason="end_turn"
        )
