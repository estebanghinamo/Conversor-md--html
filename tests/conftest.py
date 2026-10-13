from collections.abc import Callable

import pytest

from markforge import convert as convert_markdown


@pytest.fixture
def convert() -> Callable[[str], str]:
    """Expone la API pública `markforge.convert` a los tests."""
    return convert_markdown
