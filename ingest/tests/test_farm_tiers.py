from scraper.farm_tiers import (
    corpus_tier,
    index_key_for_tier,
    is_corpus_eligible,
    is_tier_a,
    is_tier_b_promote,
    tier_b_promote_bucket,
)


def test_tier_a_prefixes() -> None:
    assert is_tier_a("drought-and-farm-support/assistance")
    assert is_tier_a("animal-health/terrestrial")
    assert not is_tier_a("biosecurity-trade/export")


def test_tier_b_promote_export_paths() -> None:
    path = "biosecurity-trade/export/controlled-goods/meat/beef"
    assert tier_b_promote_bucket(path) == "export_livestock_meat"
    assert is_tier_b_promote(path)
    assert corpus_tier(path) == "B"
    assert index_key_for_tier("B") == "gov_tier_b"


def test_tier_b_skips_pets_and_forestry() -> None:
    assert not is_tier_b_promote("biosecurity-trade/cats-dogs/how-to-import")
    assert not is_tier_b_promote("forestry/industries")
    assert not is_tier_b_promote("fisheries/domestic")


def test_corpus_eligible_includes_a_and_promote_b() -> None:
    assert is_corpus_eligible("crops/wheat")
    assert is_corpus_eligible("food-policy/nrs")
    assert not is_corpus_eligible("levies/about")
