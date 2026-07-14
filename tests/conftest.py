"""Test configuration — mocks Home Assistant imports before any test module loads.

Since custom_components/home_maintenance/__init__.py imports from homeassistant,
we need to stub the entire HA module tree in sys.modules so that the package
can be imported in a test environment without HA installed.

Key requirements:
- Intermediate packages must have __path__ set so Python treats them as packages.
- Every submodule accessed via "from X.Y import Z" must be registered in
  sys.modules by its full dotted name.
"""

import sys
import types
from unittest.mock import MagicMock


def _make_package(name: str) -> types.ModuleType:
    """Create a module object that Python treats as a package."""
    mod = types.ModuleType(name)
    mod.__path__ = []
    return mod


def _stub_module(name: str, **attrs):
    """Create a MagicMock module and register it in sys.modules."""
    mod = MagicMock()
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


# ---------------------------------------------------------------------------
# homeassistant top-level
# ---------------------------------------------------------------------------
sys.modules["homeassistant"] = _make_package("homeassistant")

# homeassistant.const
_stub_module("homeassistant.const", EVENT_STATE_CHANGED=MagicMock())

# ---------------------------------------------------------------------------
# homeassistant.components  (package — needed for submodule traversal)
# ---------------------------------------------------------------------------
sys.modules["homeassistant.components"] = _make_package("homeassistant.components")

_stub_module("homeassistant.components.binary_sensor", DOMAIN="binary_sensor")

# homeassistant.components.websocket_api (package)
_sa_pkg = _make_package("homeassistant.components.websocket_api")
sys.modules["homeassistant.components.websocket_api"] = _sa_pkg
_stub_module(
    "homeassistant.components.websocket_api.connection",
    ActiveConnection=MagicMock(),
)
_stub_module(
    "homeassistant.components.websocket_api.messages",
    BASE_COMMAND_MESSAGE_SCHEMA=MagicMock(),
)

_tag_pkg = _make_package("homeassistant.components.tag")
sys.modules["homeassistant.components.tag"] = _tag_pkg
_stub_module(
    "homeassistant.components.tag.const", EVENT_TAG_SCANNED=MagicMock()
)

# ---------------------------------------------------------------------------
# homeassistant.config_entries
# ---------------------------------------------------------------------------
_stub_module("homeassistant.config_entries", ConfigEntry=MagicMock())

# ---------------------------------------------------------------------------
# homeassistant.core
# ---------------------------------------------------------------------------
_stub_module(
    "homeassistant.core",
    Event=MagicMock(),
    HomeAssistant=MagicMock(),
    ServiceCall=MagicMock(),
    callback=lambda x: x,  # identity decorator
)

# ---------------------------------------------------------------------------
# homeassistant.helpers  (package)
# ---------------------------------------------------------------------------
sys.modules["homeassistant.helpers"] = _make_package("homeassistant.helpers")

_stub_module(
    "homeassistant.helpers.device_registry", async_get=MagicMock()
)
_stub_module(
    "homeassistant.helpers.entity_registry",
    RegistryEntry=MagicMock(),
    async_get=MagicMock(),
)
_stub_module(
    "homeassistant.helpers.entity_platform", AddEntitiesCallback=MagicMock()
)
_stub_module("homeassistant.helpers.typing", ConfigType=MagicMock())

# voluptuous — for schema validation in websocket handlers
_stub_module(
    "voluptuous",
    Schema=MagicMock(),
    Required=MagicMock(),
    Optional=MagicMock(),
    Coerce=MagicMock(),
    Any=MagicMock(),
    All=MagicMock(),
    Length=MagicMock(),
    Range=MagicMock(),
    In=MagicMock(),
    Lower=MagicMock(),
    Boolean=MagicMock(),
    Number=MagicMock(),
    String=MagicMock(),
)

_stub_module(
    "homeassistant.helpers.config_validation",
    config_entry_only_config_schema=MagicMock(),
)

# ---------------------------------------------------------------------------
# homeassistant.util → homeassistant.util.dt
# ---------------------------------------------------------------------------
sys.modules["homeassistant.util"] = _make_package("homeassistant.util")

_stub_module(
    "homeassistant.util.dt",
    as_utc=MagicMock(),
    now=MagicMock(),
    parse_datetime=MagicMock(),
    parse_date=MagicMock(),
)

# ---------------------------------------------------------------------------
# Submodules of the package itself (pre-registered so relative imports in
# custom_components/home_maintenance/__init__.py resolve to stubs)
# ---------------------------------------------------------------------------
_stub_module(
    "custom_components.home_maintenance.panel",
    async_register_panel=MagicMock(),
    async_unregister_panel=MagicMock(),
)
_stub_module(
    "custom_components.home_maintenance.store",
    TaskStore=MagicMock(),
)
_stub_module(
    "custom_components.home_maintenance.websocket",
    async_register_websockets=MagicMock(),
)
