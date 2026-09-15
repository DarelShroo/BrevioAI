import os
from unittest.mock import patch

import pytest

from core.brevio.services.platform_access_policy import PlatformAccessPolicy


def test_override_explicit():
    policy = PlatformAccessPolicy(override_allow_platform=True)
    assert policy.can_use_platform_credential() is True

    policy = PlatformAccessPolicy(override_allow_platform=False)
    assert policy.can_use_platform_credential() is False


@patch.dict(
    os.environ, {"ENVIRONMENT": "production", "DEV_ALLOW_PLATFORM_OVERRIDE": "true"}
)
def test_production_always_false():
    policy = PlatformAccessPolicy()
    assert policy.can_use_platform_credential() is False


@patch.dict(
    os.environ, {"ENVIRONMENT": "development", "DEV_ALLOW_PLATFORM_OVERRIDE": "true"}
)
def test_development_allow_true():
    policy = PlatformAccessPolicy()
    assert policy.can_use_platform_credential() is True


@patch.dict(
    os.environ, {"ENVIRONMENT": "development", "DEV_ALLOW_PLATFORM_OVERRIDE": "false"}
)
def test_development_allow_false():
    policy = PlatformAccessPolicy()
    assert policy.can_use_platform_credential() is False
