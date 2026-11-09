from __future__ import annotations

import json
import re

from app.exports import (
    META_LIMIT,
    TITLE_LIMIT,
    business_json_ld,
    local_keywords,
    page_plan,
    schema_type,
    seo_brief_md,
)
from evals import fixtures as fx


def test_schema_type_follows_the_business():
    assert schema_type("craft brewery and taproom") == "Brewery"
    assert schema_type("plant-based bakery") == "Bakery"
    assert schema_type("coffee kiosk") == "CafeOrCoffeeShop"
    assert schema_type("wine bar") == "BarOrPub"
    assert schema_type("neighbourhood bistro") == "Restaurant"
    assert schema_type("food truck") == "FoodEstablishment"
    assert schema_type("barbecue smokehouse") == "Restaurant"  # not BarOrPub: "bar" matches whole words only
    assert schema_type("cocktail bars") == "BarOrPub"


def test_keywords_use_the_searchable_phrase_and_products():
    words = local_keywords(fx.BREWERY_BRIEF)
    assert "craft brewery Portland" in words and "craft brewery near me" in words
    assert "Sea Salt Gose Portland" in words
    assert len(words) == len({w.lower() for w in words})


def test_titles_and_descriptions_fit_search_snippets():
    for _, _, title, meta in page_plan(fx.BREWERY_BRIEF, fx.BREWERY_STRATEGY, fx.BREWERY_MESSAGING):
        assert 0 < len(title) <= TITLE_LIMIT
        assert 0 < len(meta) <= META_LIMIT


def test_json_ld_is_valid_json_and_never_self_rates():
    md = seo_brief_md(fx.BREWERY_BRIEF, fx.BREWERY_STRATEGY, fx.BREWERY_MESSAGING, fx.BREWERY_IDENTITY)
    blocks = re.findall(r"```json\n(.*?)\n```", md, re.S)
    assert len(blocks) == 2
    business, menu = (json.loads(b) for b in blocks)
    assert business["@type"] == "Brewery" and business["address"]["addressRegion"] == "Maine"
    assert "aggregateRating" not in business and "review" not in business
    names = [i["name"] for i in menu["hasMenuSection"][0]["hasMenuItem"]]
    assert names == fx.BREWERY_BRIEF.products
    assert business_json_ld(fx.BREWERY_BRIEF, fx.BREWERY_MESSAGING)["name"] == "Harbor Hops Brewing"


def test_alcohol_note_only_for_alcohol_businesses():
    brewery = seo_brief_md(fx.BREWERY_BRIEF, fx.BREWERY_STRATEGY, fx.BREWERY_MESSAGING, fx.BREWERY_IDENTITY)
    bakery_brief = fx.BAKERY_BRIEF
    bakery = seo_brief_md(bakery_brief, fx.BREWERY_STRATEGY, fx.BREWERY_MESSAGING, fx.BREWERY_IDENTITY)
    assert "legal drinking age" in brewery
    assert "legal drinking age" not in bakery
