from assistant.registries import indexes, prompts, refusals, tools


def test_refusal_registry_has_phase0_codes():
    codes = set(refusals.all_refusals())
    expected = {
        "NO_RELEVANT_CONTEXT",
        "INSUFFICIENT_COVERAGE",
        "CONFLICTING_SOURCES",
        "OUT_OF_SCOPE",
        "ACCESS_DENIED",
        "TENANT_SCOPE_EMPTY",
        "PROVIDER_UNAVAILABLE",
    }
    assert expected.issubset(codes)


def test_index_registry_has_three_logical_indexes():
    assert set(indexes.all_indexes()) == {"gov_tier_a", "gov_tier_b", "tenant_doc"}


def test_prompt_registry_non_empty():
    assert prompts.all_prompts()


def test_registry_versions_are_strings():
    assert tools.registry_version().startswith("tools-")
    assert indexes.registry_version().startswith("indexes-")
    assert refusals.registry_version().startswith("refusals-")
    assert prompts.registry_version().startswith("prompts-")
