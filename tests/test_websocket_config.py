"""Tests for the getConfig websocket handler.

Verifies that the backend returns a version string matching const.VERSION.
"""

import sys
from unittest.mock import MagicMock

from custom_components.home_maintenance.const import VERSION


def test_get_config_returns_version():
    # Remove the pre-stubbed websocket module so the real one gets loaded
    sys.modules.pop("custom_components.home_maintenance.websocket", None)
    from custom_components.home_maintenance.websocket import websocket_get_config
    """The getConfig handler must include 'version' in its response dict,
    matching const.VERSION (the single source of truth)."""
    # Arrange
    hass = MagicMock()
    connection = MagicMock()
    msg = {"id": 1}

    # Mock a config entry
    entry = MagicMock(
        data={"admin_only": False, "sidebar_title": "Home Maintenance"},
        options={},
    )
    hass.config_entries.async_entries.return_value = [entry]

    # Act
    websocket_get_config(hass, connection, msg)

    # Assert
    connection.send_result.assert_called_once()
    call_args = connection.send_result.call_args
    response_id, response_data = call_args[0]

    assert response_id == 1
    assert "version" in response_data, (
        f"Response missing 'version' key. Got keys: {list(response_data.keys())}"
    )
    assert response_data["version"] == VERSION, (
        f"Response version '{response_data['version']}' does not match "
        f"const.VERSION '{VERSION}'"
    )
    # Also verify data and options are still present
    assert "data" in response_data
    assert "options" in response_data
