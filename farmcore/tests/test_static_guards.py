from assistant.scope import RetrievalScope, build_gov_scope, build_tenant_scope


def test_retrieval_scope_contract_is_importable():
    assert RetrievalScope is not None
    assert callable(build_gov_scope)
    assert callable(build_tenant_scope)
