"""API clients for HAAS CNC machines.

Two communication backends:
  1. MTConnect HTTP Agent  – primary, XML-based, read-only.
  2. MDC TCP socket        – fallback, ASCII ?Q commands via port 5051.

The high-level ``HaasApiClient`` tries MTConnect first and falls back to
MDC transparently.  Coordinators call a single ``async_get_*`` method
without caring which transport was used.
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any
from xml.etree import ElementTree as ET

import aiohttp

from .const import (
    AVAIL_AVAILABLE,
    AVAIL_UNAVAILABLE,
    DEFAULT_MDC_PORT,
    DEFAULT_MTCONNECT_PORT,
    KEY_A_ACT,
    KEY_ALARM,
    KEY_ALARM_CODE,
    KEY_AVAIL,
    KEY_B_ACT,
    KEY_BLOCK,
    KEY_COOLANT_LEVEL,
    KEY_CYCLE_TIME,
    KEY_EXECUTION,
    KEY_LINE,
    KEY_MDC_STATUS,
    KEY_MODE,
    KEY_MODEL,
    KEY_MOTION_TIME,
    KEY_PART_COUNT,
    KEY_PATH_FEEDRATE,
    KEY_POWER_ON_TIME,
    KEY_PROGRAM,
    KEY_SERIAL,
    KEY_SOFTWARE_VERSION,
    KEY_SPINDLE_LOAD,
    KEY_SPINDLE_SPEED,
    KEY_TOOL_DIAMETER,
    KEY_TOOL_LENGTH,
    KEY_TOOL_NUMBER,
    KEY_WORK_OFFSET,
    KEY_X_ACT,
    KEY_Y_ACT,
    KEY_Z_ACT,
    MDC_Q100,
    MDC_Q104,
    MDC_Q200,
    MDC_Q300,
    MDC_Q500,
    MDC_Q600,
)

_LOGGER = logging.getLogger(__name__)

# Timeout for individual HTTP requests (seconds)
_HTTP_TIMEOUT = aiohttp.ClientTimeout(total=8)
# Timeout for MDC TCP socket operations (seconds)
_MDC_TIMEOUT = 5.0

# MTConnect XML namespaces (auto-detected at runtime)
_NS_PATTERN = re.compile(r"\{(.+?)\}")


# ======================================================================
# Helpers
# ======================================================================

def _safe_float(value: str | None) -> float | None:
    """Convert a string to float, returning None on failure."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _safe_int(value: str | None) -> int | None:
    """Convert a string to int, returning None on failure."""
    if value is None:
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


# ======================================================================
# MDC response parsing helpers  (NGC returns labeled fields)
# ======================================================================

# Known labels in HAAS NGC MDC responses, grouped by Q-code.
# NGC format: ">LABEL, VALUE, LABEL, VALUE, ..."
_Q100_LABELS = frozenset({
    "SERIAL NUMBER", "SERIAL", "S/N",
    "SOFTWARE VERSION", "SOFTWARE", "VERSION",
    "MODEL", "MODEL NUMBER",
})
_Q104_LABELS = frozenset({
    "MODE", "PROGRAM", "STATUS",
})
_Q200_LABELS = frozenset({
    "TOOL IN SPINDLE", "TOOL NUMBER", "TOOL",
    "NEXT TOOL", "PREVIOUS TOOL",
    "TOOL CHANGES", "T CHANGES",
})
_Q300_AXIS_LABELS = frozenset({
    "X", "Y", "Z", "A", "B", "C",
    "X MACHINE", "Y MACHINE", "Z MACHINE",
    "A MACHINE", "B MACHINE", "C MACHINE",
    "X WORK", "Y WORK", "Z WORK",
    "A WORK", "B WORK", "C WORK",
})
_Q300_OTHER_LABELS = frozenset({
    "RPM", "SPINDLE SPEED", "SPINDLE RPM",
    "TORQUE", "LOAD", "SPINDLE LOAD",
    "COOLANT LEVEL", "COOLANT",
    "FEEDRATE", "FEED",
})
_Q500_LABELS = frozenset({
    "PROGRAM", "STATUS", "PARTS", "PART COUNT",
    "TOOL", "TOOL NUMBER",
})


def _get_mdc_parts(raw: str) -> list[str]:
    """Clean and split an MDC response into comma-separated parts.

    Handles multi-line responses by joining all lines.
    """
    combined = ""
    for line in raw.split("\n"):
        clean = line.lstrip(">").strip()
        if clean:
            if combined:
                combined += ", "
            combined += clean
    return [p.strip() for p in combined.split(",") if p.strip()]


def _find_labeled(parts: list[str], labels: frozenset[str]) -> dict[str, str]:
    """Walk comma-separated *parts* and extract label→value pairs.

    A "label" is a part whose upper-case text is in *labels*; the next
    part is treated as its value.
    """
    found: dict[str, str] = {}
    i = 0
    while i < len(parts):
        upper = parts[i].upper()
        if upper in labels and i + 1 < len(parts):
            found[upper] = parts[i + 1]
            i += 2
        else:
            i += 1
    return found


# ======================================================================
# MTConnect HTTP Client
# ======================================================================

class MTConnectClient:
    """Async client for an MTConnect HTTP agent."""

    def __init__(
        self,
        host: str,
        port: int = DEFAULT_MTCONNECT_PORT,
        device: str = "",
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._host = host
        self._port = port
        self._device = device
        self._session = session
        self._owns_session = session is None
        self._base_url = f"http://{host}:{port}"
        self._ns: str | None = None  # auto-detected XML namespace

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=_HTTP_TIMEOUT)
            self._owns_session = True
        return self._session

    async def close(self) -> None:
        """Close the HTTP session if we own it."""
        if self._owns_session and self._session and not self._session.closed:
            await self._session.close()

    # ------------------------------------------------------------------
    # Low-level HTTP + XML
    # ------------------------------------------------------------------

    async def _fetch_xml(self, path: str) -> ET.Element | None:
        """GET *path* and return parsed XML root, or None on failure."""
        session = await self._ensure_session()
        url = f"{self._base_url}{path}"
        try:
            async with session.get(url) as resp:
                if resp.status != 200:
                    _LOGGER.warning("MTConnect %s returned HTTP %s", url, resp.status)
                    return None
                text = await resp.text()
                root = ET.fromstring(text)
                # Auto-detect namespace from root tag
                m = _NS_PATTERN.match(root.tag)
                if m:
                    self._ns = m.group(1)
                return root
        except (aiohttp.ClientError, asyncio.TimeoutError, ET.ParseError) as err:
            _LOGGER.debug("MTConnect request %s failed: %s", url, err)
            return None

    def _find(self, root: ET.Element, xpath: str) -> ET.Element | None:
        """Namespace-aware find."""
        if self._ns:
            xpath = xpath.replace("{ns}", self._ns)
        else:
            xpath = re.sub(r"\{ns\}", "", xpath)
        return root.find(xpath)

    def _findall(self, root: ET.Element, xpath: str) -> list[ET.Element]:
        """Namespace-aware findall."""
        if self._ns:
            xpath = xpath.replace("{ns}", self._ns)
        else:
            xpath = re.sub(r"\{ns\}", "", xpath)
        return root.findall(xpath)

    def _findtext_by_dataid(
        self, root: ET.Element, data_item_name: str
    ) -> str | None:
        """Search all elements for one whose 'name' attribute matches."""
        ns = f"{{{self._ns}}}" if self._ns else ""
        for elem in root.iter():
            if elem.get("name") == data_item_name or elem.get("dataItemId") == data_item_name:
                return (elem.text or "").strip() or None
        return None

    def _get_stream_element(self, root: ET.Element) -> ET.Element | None:
        """Return the DeviceStream element (possibly filtered by device)."""
        ns = f"{{{self._ns}}}" if self._ns else ""
        for ds in root.iter(f"{ns}DeviceStream"):
            if self._device:
                if ds.get("name") == self._device or ds.get("uuid") == self._device:
                    return ds
            else:
                return ds  # first device
        return None

    # ------------------------------------------------------------------
    # Public API – MTConnect queries
    # ------------------------------------------------------------------

    async def async_probe(self) -> dict[str, Any] | None:
        """Fetch /probe to get device identity info."""
        device_path = f"/{self._device}" if self._device else ""
        root = await self._fetch_xml(f"{device_path}/probe")
        if root is None:
            return None

        ns = f"{{{self._ns}}}" if self._ns else ""
        info: dict[str, Any] = {}

        # Find first Device element
        for device in root.iter(f"{ns}Device"):
            info[KEY_SERIAL] = device.get("sampleInterval", device.get("uuid", ""))
            info[KEY_MODEL] = device.get("name", "")
            # Look for Description element
            desc = device.find(f"{ns}Description")
            if desc is not None:
                info[KEY_SERIAL] = desc.get("serialNumber", info.get(KEY_SERIAL, ""))
                info[KEY_MODEL] = desc.get("model", info.get(KEY_MODEL, ""))
                info[KEY_SOFTWARE_VERSION] = desc.text.strip() if desc.text else ""
            break

        return info if info else None

    async def async_current(self) -> dict[str, Any] | None:
        """Fetch /current and return a flat dict of data-item values."""
        device_path = f"/{self._device}" if self._device else ""
        root = await self._fetch_xml(f"{device_path}/current")
        if root is None:
            return None

        data: dict[str, Any] = {}
        ns = f"{{{self._ns}}}" if self._ns else ""

        # Walk all elements inside the Streams
        streams = root.find(f".//{ns}Streams")
        if streams is None:
            _LOGGER.debug("No <Streams> in MTConnect /current response")
            return data

        device_stream = self._get_stream_element(root)
        search_root = device_stream if device_stream is not None else streams

        # Build a lookup of all data item values by name and dataItemId
        items: dict[str, str] = {}
        for elem in search_root.iter():
            name = elem.get("name") or elem.get("dataItemId") or ""
            text = (elem.text or "").strip()
            if name and text:
                items[name] = text

        # Map MTConnect names → our const keys
        # Axis positions
        data[KEY_X_ACT] = _safe_float(items.get("Xabs") or items.get("Xact") or items.get("x"))
        data[KEY_Y_ACT] = _safe_float(items.get("Yabs") or items.get("Yact") or items.get("y"))
        data[KEY_Z_ACT] = _safe_float(items.get("Zabs") or items.get("Zact") or items.get("z"))
        data[KEY_A_ACT] = _safe_float(items.get("Aabs") or items.get("Aact") or items.get("a"))
        data[KEY_B_ACT] = _safe_float(items.get("Babs") or items.get("Bact") or items.get("b"))

        # Spindle
        data[KEY_SPINDLE_SPEED] = _safe_float(items.get("Srpm") or items.get("speed"))
        data[KEY_SPINDLE_LOAD] = _safe_float(items.get("Sload") or items.get("spindle_load"))
        data[KEY_PATH_FEEDRATE] = _safe_float(
            items.get("Frt") or items.get("path_feedrate") or items.get("PathFeedrate")
        )

        # Execution state
        data[KEY_EXECUTION] = items.get("execution") or items.get("exec")
        data[KEY_MODE] = items.get("mode") or items.get("cmode")
        data[KEY_PROGRAM] = items.get("program") or items.get("pgm")
        data[KEY_BLOCK] = items.get("block")
        data[KEY_LINE] = items.get("line")

        # Tool
        data[KEY_TOOL_NUMBER] = items.get("Tool_number") or items.get("tool_id") or items.get("tool_number")

        # Part count
        data[KEY_PART_COUNT] = _safe_int(
            items.get("PartCountAct") or items.get("part_count")
        )

        # Alarms / conditions
        alarm_val = items.get("alarm") or items.get("system")
        if alarm_val and alarm_val.upper() not in ("NORMAL", "UNAVAILABLE", ""):
            data[KEY_ALARM] = alarm_val
            data[KEY_ALARM_CODE] = alarm_val
        else:
            data[KEY_ALARM] = None
            data[KEY_ALARM_CODE] = None

        # Availability
        avail_raw = items.get("avail") or items.get("Avail")
        if avail_raw and avail_raw.upper() == "AVAILABLE":
            data[KEY_AVAIL] = AVAIL_AVAILABLE
        elif avail_raw:
            data[KEY_AVAIL] = AVAIL_UNAVAILABLE
        else:
            data[KEY_AVAIL] = AVAIL_AVAILABLE  # assume available if connected

        # Accumulated times (may be floating seconds or formatted)
        data[KEY_POWER_ON_TIME] = _safe_float(
            items.get("p1") or items.get("PowerOnTime") or items.get("power_on_time")
        )
        data[KEY_MOTION_TIME] = _safe_float(
            items.get("motion_time") or items.get("MotionTime")
        )
        data[KEY_CYCLE_TIME] = _safe_float(
            items.get("cycle_time") or items.get("CycleTime")
        )

        # Work offset
        data[KEY_WORK_OFFSET] = items.get("work_offset") or items.get("Gwcs")

        # Coolant
        data[KEY_COOLANT_LEVEL] = _safe_float(
            items.get("coolant_level") or items.get("CoolantLevel")
        )

        return data

    async def async_test_connection(self) -> bool:
        """Return True if the MTConnect agent responds."""
        result = await self._fetch_xml("/probe")
        return result is not None


# ======================================================================
# MDC TCP Client  (?Q commands via port 5051)
# ======================================================================

class MDCClient:
    """Async TCP client for HAAS MDC (Machine Data Collection) interface.

    Requires HAAS Setting 143 = ON.  All queries are ASCII, terminated
    with ``\\r\\n``.  Responses are also ``\\r\\n`` terminated.
    """

    def __init__(self, host: str, port: int = DEFAULT_MDC_PORT) -> None:
        self._host = host
        self._port = port
        self._lock = asyncio.Lock()

    async def _send_command(self, command: str) -> str | None:
        """Open a TCP connection, send *command*, read all response lines, close."""
        async with self._lock:
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(self._host, self._port),
                    timeout=_MDC_TIMEOUT,
                )
                writer.write(f"{command}\r\n".encode("ascii"))
                await writer.drain()

                # Read all available lines (NGC may return multi-line)
                lines: list[str] = []
                while True:
                    try:
                        line = await asyncio.wait_for(
                            reader.readline(),
                            timeout=(0.5 if lines else _MDC_TIMEOUT),
                        )
                        if not line:
                            break
                        text = line.decode("ascii", errors="replace").strip()
                        if text:
                            lines.append(text)
                    except asyncio.TimeoutError:
                        break

                writer.close()
                await writer.wait_closed()

                raw = "\n".join(lines)
                _LOGGER.debug("MDC %s → %r", command, raw)
                return raw if raw else None
            except (OSError, asyncio.TimeoutError) as err:
                _LOGGER.debug("MDC command %r failed: %s", command, err)
                return None

    # ------------------------------------------------------------------
    # Parsed Q-command helpers
    # ------------------------------------------------------------------

    async def async_q100(self) -> dict[str, Any]:
        """?Q100 → serial number, software version, model.

        NGC format:  ``>SERIAL NUMBER, 1182001, SOFTWARE VERSION, 100.21, ...``
        Classic:     ``>MODEL, SERIAL, SOFTWARE``
        """
        data: dict[str, Any] = {}
        raw = await self._send_command(MDC_Q100)
        if not raw:
            return data

        parts = _get_mdc_parts(raw)

        # Try NGC labeled format first
        labeled = _find_labeled(parts, _Q100_LABELS)
        if labeled:
            data[KEY_SERIAL] = (
                labeled.get("SERIAL NUMBER")
                or labeled.get("SERIAL")
                or labeled.get("S/N")
            )
            data[KEY_SOFTWARE_VERSION] = (
                labeled.get("SOFTWARE VERSION")
                or labeled.get("SOFTWARE")
                or labeled.get("VERSION")
            )
            data[KEY_MODEL] = (
                labeled.get("MODEL NUMBER") or labeled.get("MODEL")
            )
        else:
            # Positional fallback: MODEL, SERIAL, SOFTWARE_VERSION
            if len(parts) >= 3:
                data[KEY_MODEL] = parts[0]
                data[KEY_SERIAL] = parts[1]
                data[KEY_SOFTWARE_VERSION] = parts[2]
            elif len(parts) == 2:
                data[KEY_SERIAL] = parts[0]
                data[KEY_SOFTWARE_VERSION] = parts[1]
            elif len(parts) == 1:
                data[KEY_SERIAL] = parts[0]

        return {k: v for k, v in data.items() if v is not None}

    async def async_q104(self) -> dict[str, Any]:
        """?Q104 → operating mode.

        NGC format:  ``>MODE, (MDI), PROGRAM, O00001, STATUS, IDLE``
        Classic:     ``>LIST MDI, O02020, IDLE``
        """
        data: dict[str, Any] = {}
        raw = await self._send_command(MDC_Q104)
        if not raw:
            return data

        parts = _get_mdc_parts(raw)

        # Try NGC labeled format
        labeled = _find_labeled(parts, _Q104_LABELS)
        if labeled:
            if "MODE" in labeled:
                data[KEY_MODE] = labeled["MODE"]
            if "PROGRAM" in labeled:
                data[KEY_PROGRAM] = labeled["PROGRAM"]
        else:
            # Positional fallback: mode is typically the first or last field
            if parts:
                data[KEY_MODE] = parts[0]

        return data

    async def async_q200(self) -> dict[str, Any]:
        """?Q200 → tool change info (previous, current, next tool).

        NGC format:  ``>TOOL IN SPINDLE, 5, NEXT TOOL, 0, TOOL CHANGES, 71484``
        Classic:     ``>PREV_TOOL, CURRENT_TOOL, NEXT_TOOL``
        """
        data: dict[str, Any] = {}
        raw = await self._send_command(MDC_Q200)
        if not raw:
            return data

        parts = _get_mdc_parts(raw)

        # Try NGC labeled format
        labeled = _find_labeled(parts, _Q200_LABELS)
        tool = (
            labeled.get("TOOL IN SPINDLE")
            or labeled.get("TOOL NUMBER")
            or labeled.get("TOOL")
        )
        if tool is not None:
            data[KEY_TOOL_NUMBER] = tool
        elif parts:
            # Positional fallback – pick the first part that's a
            # reasonable tool number (0-999)
            for p in parts:
                val = _safe_int(p)
                if val is not None and 0 <= val <= 999:
                    data[KEY_TOOL_NUMBER] = str(val)
                    break

        return data

    async def async_q300(self) -> dict[str, Any]:
        """?Q300 → axis positions + spindle RPM + load.

        NGC labeled:
            ``>X, +0.0000, Y, +0.0000, Z, +0.0000, A, +0.0000,
              B, +0.0000, COOLANT LEVEL, 0, RPM, 0, TORQUE, 0``
        Classic positional:
            ``>X+000.0000, Y+000.0000, Z+000.0000,
              A+000.0000, B+000.0000, RPM, LOAD%``
        """
        data: dict[str, Any] = {}
        raw = await self._send_command(MDC_Q300)
        if not raw:
            return data

        parts = _get_mdc_parts(raw)
        all_labels = _Q300_AXIS_LABELS | _Q300_OTHER_LABELS
        labeled = _find_labeled(parts, all_labels)

        if labeled:
            # NGC labeled format
            for lbls, key in (
                (("X", "X MACHINE", "X WORK"), KEY_X_ACT),
                (("Y", "Y MACHINE", "Y WORK"), KEY_Y_ACT),
                (("Z", "Z MACHINE", "Z WORK"), KEY_Z_ACT),
                (("A", "A MACHINE", "A WORK"), KEY_A_ACT),
                (("B", "B MACHINE", "B WORK"), KEY_B_ACT),
            ):
                for lbl in lbls:
                    if lbl in labeled and key not in data:
                        data[key] = _safe_float(labeled[lbl])
                        break

            data[KEY_SPINDLE_SPEED] = _safe_float(
                labeled.get("RPM")
                or labeled.get("SPINDLE SPEED")
                or labeled.get("SPINDLE RPM")
            )
            data[KEY_SPINDLE_LOAD] = _safe_float(
                labeled.get("TORQUE")
                or labeled.get("LOAD")
                or labeled.get("SPINDLE LOAD")
            )
            data[KEY_PATH_FEEDRATE] = _safe_float(
                labeled.get("FEEDRATE") or labeled.get("FEED")
            )
            data[KEY_COOLANT_LEVEL] = _safe_float(
                labeled.get("COOLANT LEVEL") or labeled.get("COOLANT")
            )
        else:
            # Classic positional: "X+nnn.nnnn, Y+nnn.nnnn, ..."
            axis_keys = [KEY_X_ACT, KEY_Y_ACT, KEY_Z_ACT, KEY_A_ACT, KEY_B_ACT]
            for i, key in enumerate(axis_keys):
                if i < len(parts):
                    # Strip axis letter prefix like "X+123.456"
                    val = re.sub(r"^[A-Za-z]", "", parts[i]).strip()
                    data[key] = _safe_float(val)

            # Spindle speed and load follow the axes
            axis_count = min(5, len(parts))
            remaining = parts[axis_count:]
            if remaining:
                data[KEY_SPINDLE_SPEED] = _safe_float(remaining[0])
            if len(remaining) >= 2:
                data[KEY_SPINDLE_LOAD] = _safe_float(remaining[1])

        return data

    async def async_q500(self) -> dict[str, Any]:
        """?Q500 → machine status: IDLE, BUSY(program), or ALARM.

        NGC labeled:
            ``>PROGRAM, O00001, STATUS, BUSY, PARTS, 123``
        Classic:
            ``>IDLE``  /  ``>BUSY``  /  ``>ALARM``
        """
        data: dict[str, Any] = {}
        raw = await self._send_command(MDC_Q500)
        if not raw:
            return data

        parts = _get_mdc_parts(raw)
        data[KEY_MDC_STATUS] = raw.lstrip(">").strip()

        # Try NGC labeled format
        labeled = _find_labeled(parts, _Q500_LABELS)
        status_str = labeled.get("STATUS", "")

        if labeled:
            if labeled.get("PROGRAM"):
                data[KEY_PROGRAM] = labeled["PROGRAM"]
            if labeled.get("PARTS") or labeled.get("PART COUNT"):
                data[KEY_PART_COUNT] = _safe_int(
                    labeled.get("PARTS") or labeled.get("PART COUNT")
                )
        if not status_str and parts:
            # Positional: single word like "IDLE" / "BUSY" / "ALARM"
            status_str = parts[0]

        # Map status to execution state
        upper = status_str.upper()
        if "ALARM" in upper:
            data[KEY_EXECUTION] = "STOPPED"
            data[KEY_ALARM] = status_str
            data[KEY_ALARM_CODE] = status_str
        elif "BUSY" in upper or "RUN" in upper or "ACTIVE" in upper:
            data[KEY_EXECUTION] = "ACTIVE"
        else:
            data[KEY_EXECUTION] = "IDLE"
            data[KEY_ALARM] = None
            data[KEY_ALARM_CODE] = None

        data[KEY_AVAIL] = AVAIL_AVAILABLE
        return data

    async def async_read_macro(self, variable: int) -> float | None:
        """Read a single macro variable via ?Q600 <var>."""
        raw = await self._send_command(f"{MDC_Q600} {variable}")
        if raw:
            clean = raw.lstrip(">").strip()
            parts = [p.strip() for p in clean.split(",")]
            # Response is typically "> VARIABLE, VALUE" or just "> VALUE"
            val_str = parts[-1] if parts else clean
            if val_str.upper() in ("", "UNKNOWN", "VARIABLE"):
                return None
            return _safe_float(val_str)
        return None

    async def async_test_connection(self) -> bool:
        """Return True if the MDC interface responds to ?Q500."""
        raw = await self._send_command(MDC_Q500)
        return raw is not None and len(raw) > 0

    # ------------------------------------------------------------------
    # Aggregated MDC queries (for coordinators)
    # ------------------------------------------------------------------

    async def async_get_fast_data(self) -> dict[str, Any]:
        """Query fast-changing data via MDC (status + positions)."""
        results: dict[str, Any] = {}
        q500, q300 = await asyncio.gather(
            self.async_q500(), self.async_q300(), return_exceptions=True
        )
        if isinstance(q500, dict):
            results.update(q500)
        if isinstance(q300, dict):
            results.update(q300)
        return results

    async def async_get_medium_data(self) -> dict[str, Any]:
        """Query medium-rate data via MDC (tool info, mode, alarm)."""
        results: dict[str, Any] = {}
        q200, q104, q500 = await asyncio.gather(
            self.async_q200(),
            self.async_q104(),
            self.async_q500(),
            return_exceptions=True,
        )
        if isinstance(q200, dict):
            results.update(q200)
        if isinstance(q104, dict):
            results.update(q104)
        if isinstance(q500, dict):
            # Merge alarm/program/part_count from Q500 into medium tier
            for k in (KEY_ALARM, KEY_ALARM_CODE, KEY_PROGRAM, KEY_PART_COUNT,
                       KEY_EXECUTION, KEY_AVAIL, KEY_MDC_STATUS):
                if q500.get(k) is not None:
                    results.setdefault(k, q500[k])

        # Read active tool offsets if tool number known
        tool_num = results.get(KEY_TOOL_NUMBER)
        if tool_num:
            try:
                tool_idx = int(tool_num)
                length_var = 2000 + tool_idx   # #2001 .. #2200
                diam_var = 2400 + tool_idx     # #2401 .. #2600
                l_val, d_val = await asyncio.gather(
                    self.async_read_macro(length_var),
                    self.async_read_macro(diam_var),
                    return_exceptions=True,
                )
                if isinstance(l_val, (int, float)):
                    results[KEY_TOOL_LENGTH] = l_val
                if isinstance(d_val, (int, float)):
                    results[KEY_TOOL_DIAMETER] = d_val
            except (ValueError, TypeError):
                pass

        return results

    async def async_get_slow_data(self) -> dict[str, Any]:
        """Query slow-changing data via MDC (identity)."""
        return await self.async_q100()


# ======================================================================
# Unified API Client
# ======================================================================

class HaasApiClient:
    """Unified API client that tries MTConnect then falls back to MDC.

    Each coordinator tier calls the corresponding ``async_get_*`` method.
    The client automatically falls back to MDC if MTConnect is unreachable.
    """

    def __init__(
        self,
        host: str,
        mtconnect_port: int = DEFAULT_MTCONNECT_PORT,
        mdc_port: int = DEFAULT_MDC_PORT,
        mtconnect_device: str = "",
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self.host = host
        self.mtconnect = MTConnectClient(host, mtconnect_port, mtconnect_device, session)
        self.mdc = MDCClient(host, mdc_port)
        self._mtconnect_available: bool | None = None  # None = untested

    async def close(self) -> None:
        """Shut down sessions."""
        await self.mtconnect.close()

    @property
    def data_source(self) -> str:
        """Return which data source is currently in use."""
        if self._mtconnect_available is True:
            return "mtconnect"
        if self._mtconnect_available is False:
            return "mdc"
        return "unknown"

    # ------------------------------------------------------------------
    # Connection test
    # ------------------------------------------------------------------

    async def async_test_connection(self) -> tuple[bool, str]:
        """Test connectivity.  Returns (success, source_name)."""
        if await self.mtconnect.async_test_connection():
            self._mtconnect_available = True
            return True, "mtconnect"

        if await self.mdc.async_test_connection():
            self._mtconnect_available = False
            return True, "mdc"

        return False, "none"

    # ------------------------------------------------------------------
    # Coordinator data-fetch methods
    # ------------------------------------------------------------------

    async def async_get_fast_data(self) -> dict[str, Any]:
        """Fast-tier data (positions, spindle, execution)."""
        if self._mtconnect_available is not False:
            mtc_data = await self.mtconnect.async_current()
            if mtc_data is not None:
                self._mtconnect_available = True
                mtc_data["_source"] = "mtconnect"
                return mtc_data
            # MTConnect failed – try MDC fallback
            self._mtconnect_available = False
            _LOGGER.info("MTConnect unavailable, falling back to MDC")

        data = await self.mdc.async_get_fast_data()
        data["_source"] = "mdc"
        return data

    async def async_get_medium_data(self) -> dict[str, Any]:
        """Medium-tier data (tool info, work offset, part count)."""
        if self._mtconnect_available is True:
            # MTConnect /current already returns all data items;
            # for medium tier we reuse the same endpoint.
            mtc_data = await self.mtconnect.async_current()
            if mtc_data is not None:
                mtc_data["_source"] = "mtconnect"
                return mtc_data

        data = await self.mdc.async_get_medium_data()
        data["_source"] = "mdc"
        return data

    async def async_get_slow_data(self) -> dict[str, Any]:
        """Slow-tier data (machine identity, accumulated times)."""
        if self._mtconnect_available is True:
            probe = await self.mtconnect.async_probe()
            current = await self.mtconnect.async_current()
            combined: dict[str, Any] = {}
            if probe:
                combined.update(probe)
            if current:
                # Extract only slow-changing items
                for k in (KEY_POWER_ON_TIME, KEY_MOTION_TIME, KEY_CYCLE_TIME):
                    if current.get(k) is not None:
                        combined[k] = current[k]
            combined["_source"] = "mtconnect"
            return combined

        data = await self.mdc.async_get_slow_data()
        data["_source"] = "mdc"
        return data

    async def async_retry_mtconnect(self) -> bool:
        """Periodically re-check if MTConnect came back online."""
        if self._mtconnect_available is False:
            if await self.mtconnect.async_test_connection():
                self._mtconnect_available = True
                _LOGGER.info("MTConnect agent is back online")
                return True
        return False
