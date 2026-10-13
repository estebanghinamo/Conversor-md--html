from collections.abc import Callable

import pytest
from hypothesis import HealthCheck, settings

from markforge import convert as convert_markdown

settings.register_profile(
    "markforge",
    max_examples=150,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.register_profile(
    "deep", max_examples=5000, deadline=None, suppress_health_check=[HealthCheck.too_slow]
)
settings.load_profile("markforge")


@pytest.fixture
def convert() -> Callable[[str], str]:
    """Expone la API pública `markforge.convert` a los tests."""
    return convert_markdown
