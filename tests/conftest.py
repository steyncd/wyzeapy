import pytest
from unittest.mock import MagicMock

from wyzeapy.wyze_auth_lib import WyzeAuthLib


@pytest.fixture
def mock_auth_lib():
    """Return a MagicMock-ed instance of WyzeAuthLib for use in service tests."""
    return MagicMock(spec=WyzeAuthLib)