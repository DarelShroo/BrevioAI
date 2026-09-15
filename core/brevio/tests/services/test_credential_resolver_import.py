"""Import/init tests for CredentialResolver — no circular / self-import regressions."""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path


def test_credential_resolver_public_import():
    """Public API must import cleanly without circular imports."""
    mod = importlib.import_module("core.brevio.services.credential_resolver")
    assert hasattr(mod, "CredentialResolver")
    assert hasattr(mod, "ResolvedCredential")
    from core.brevio.services.credential_resolver import (
        CredentialResolver,
        ResolvedCredential,
    )

    assert CredentialResolver is mod.CredentialResolver
    assert ResolvedCredential is mod.ResolvedCredential


def test_resolved_credential_lives_in_own_module():
    """DTO module must not import CredentialResolver (keeps cycle surface small)."""
    from core.brevio.services import resolved_credential as rc_mod
    from core.brevio.services.resolved_credential import ResolvedCredential

    assert hasattr(rc_mod, "ResolvedCredential")
    assert not hasattr(rc_mod, "CredentialResolver")
    assert ResolvedCredential.__module__ == "core.brevio.services.resolved_credential"


def test_credential_resolver_module_has_no_self_import():
    """
    Historical bug: credential_resolver.py line 7 was
    ``from core.brevio.services.credential_resolver import CredentialResolver, ...``
    which made the module import itself while partially initialized.
    """
    mod = importlib.import_module("core.brevio.services.credential_resolver")
    target = Path(mod.__file__)
    tree = ast.parse(target.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom) or not node.module:
            continue
        if node.module in {
            "core.brevio.services.credential_resolver",
            ".credential_resolver",
            "credential_resolver",
        }:
            names = {alias.name for alias in node.names}
            assert (
                "CredentialResolver" not in names
            ), f"self-import of CredentialResolver forbidden in {target}"


def test_dependency_and_router_import_order():
    """App startup order: dependency → resolver → router must not cycle."""
    # Drop related modules so we re-enter the historical failing order.
    for key in list(sys.modules):
        if key in {
            "core.brevio.services.credential_resolver",
            "core.brevio.services.resolved_credential",
            "core.brevio_api.dependencies.credential_resolver_dependency",
            "core.brevio_api.routers.brevio_router",
            "core.brevio.services.processing_preflight",
        } or key.endswith("credential_resolver"):
            del sys.modules[key]

    dep = importlib.import_module(
        "core.brevio_api.dependencies.credential_resolver_dependency"
    )
    assert hasattr(dep, "get_credential_resolver")

    from core.brevio.services.credential_resolver import CredentialResolver

    assert CredentialResolver is not None

    preflight = importlib.import_module("core.brevio.services.processing_preflight")
    assert hasattr(preflight, "ProcessingPreflight")
