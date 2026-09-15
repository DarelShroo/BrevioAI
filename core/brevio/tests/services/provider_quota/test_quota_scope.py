"""Quota scope documentation/behavior."""

from core.brevio.services.provider_quota.keys import build_quota_scope_id


def test_platform_scope():
    assert build_quota_scope_id(is_platform=True, credential_id="x") == "platform"


def test_cred_scope():
    assert build_quota_scope_id(is_platform=False, credential_id="abc") == "cred:abc"


def test_gcp_project_override():
    assert (
        build_quota_scope_id(
            is_platform=False, credential_id="abc", policy_scope="gcp-project:X"
        )
        == "gcp-project:X"
    )


def test_resolved_credential_property():
    from datetime import datetime, timezone

    from core.brevio.services.credential_resolver import ResolvedCredential

    c = ResolvedCredential(
        api_key="SECRET",
        base_url="https://example.com",
        is_platform=False,
        credential_id="cid1",
        updated_at=datetime.now(timezone.utc),
    )
    assert c.quota_scope_id == "cred:cid1"
    assert "SECRET" not in c.quota_scope_id
