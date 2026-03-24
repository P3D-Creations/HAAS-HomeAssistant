"""Constants for the HAAS CNC Machine Monitor integration.

Data sources:
  - Primary:  MTConnect HTTP Agent (/current, /probe, /sample endpoints)
  - Fallback: MDC TCP socket (port 5051, ?Q commands)
"""
from __future__ import annotations

DOMAIN = "haas_cnc"
DEFAULT_NAME = "HAAS CNC"

# ---------------------------------------------------------------------------
# Configuration keys (config_flow / options)
# ---------------------------------------------------------------------------
CONF_HOST = "host"
CONF_MACHINE_NAME = "machine_name"
CONF_MTCONNECT_PORT = "mtconnect_port"
CONF_MDC_PORT = "mdc_port"
CONF_MTCONNECT_DEVICE = "mtconnect_device"  # device name in MTConnect agent

# Defaults
DEFAULT_MACHINE_NAME = "HAAS UMC-500"
DEFAULT_MTCONNECT_PORT = 5000
DEFAULT_MDC_PORT = 5051
DEFAULT_MTCONNECT_DEVICE = ""  # empty = auto-detect first device

# ---------------------------------------------------------------------------
# Coordinator keys (tiers)
# ---------------------------------------------------------------------------
COORD_FAST = "fast"          # ~2 s – status, execution, positions, spindle
COORD_MEDIUM = "medium"      # ~10 s – tool info, work offsets, part count
COORD_SLOW = "slow"          # ~600 s – machine identity, versions

# Update intervals (seconds)
UPDATE_INTERVAL_FAST = 2
UPDATE_INTERVAL_MEDIUM = 10
UPDATE_INTERVAL_SLOW = 600

# ---------------------------------------------------------------------------
# Data dictionary keys  (populated by api.py, consumed by entities)
# ---------------------------------------------------------------------------
# MTConnect data-item names (from HAAS MTConnect device model)
# Fast tier
KEY_AVAIL = "avail"
KEY_EXECUTION = "execution"
KEY_MODE = "mode"
KEY_PROGRAM = "program"
KEY_X_ACT = "x_act"
KEY_Y_ACT = "y_act"
KEY_Z_ACT = "z_act"
KEY_A_ACT = "a_act"
KEY_B_ACT = "b_act"
KEY_SPINDLE_SPEED = "spindle_speed"
KEY_SPINDLE_LOAD = "spindle_load"
KEY_PATH_FEEDRATE = "path_feedrate"
KEY_BLOCK = "block"                    # current G-code block
KEY_LINE = "line"                      # current line number

# Medium tier
KEY_TOOL_NUMBER = "tool_number"
KEY_TOOL_LENGTH = "tool_length"
KEY_TOOL_DIAMETER = "tool_diameter"
KEY_WORK_OFFSET = "work_offset"
KEY_PART_COUNT = "part_count"
KEY_COOLANT_LEVEL = "coolant_level"
KEY_ALARM = "alarm"
KEY_ALARM_CODE = "alarm_code"

# Slow tier
KEY_SERIAL = "serial_number"
KEY_MODEL = "model"
KEY_SOFTWARE_VERSION = "software_version"
KEY_POWER_ON_TIME = "power_on_time"     # accumulated hours
KEY_MOTION_TIME = "motion_time"         # accumulated hours
KEY_CYCLE_TIME = "cycle_time"

# Derived / MDC-only keys
KEY_MDC_STATUS = "mdc_status"          # IDLE / BUSY / ALARM from ?Q500
KEY_CYCLE_COUNT = "cycle_count"

# ---------------------------------------------------------------------------
# MTConnect execution & availability states
# ---------------------------------------------------------------------------
EXECUTION_IDLE = "IDLE"
EXECUTION_ACTIVE = "ACTIVE"
EXECUTION_FEED_HOLD = "FEED_HOLD"
EXECUTION_STOPPED = "STOPPED"
EXECUTION_READY = "READY"
EXECUTION_INTERRUPTED = "INTERRUPTED"
EXECUTION_WAIT = "WAIT"

AVAIL_AVAILABLE = "AVAILABLE"
AVAIL_UNAVAILABLE = "UNAVAILABLE"

# ---------------------------------------------------------------------------
# MDC ?Q command identifiers
# ---------------------------------------------------------------------------
MDC_Q100 = "?Q100"   # Serial, software version, model
MDC_Q104 = "?Q104"   # Operating mode
MDC_Q200 = "?Q200"   # Tool change info (previous, current, next)
MDC_Q300 = "?Q300"   # Coordinates + spindle RPM/load
MDC_Q500 = "?Q500"   # Machine status (IDLE / BUSY / ALARM)
MDC_Q600 = "?Q600"   # Macro variable read

# HAAS macro variable ranges (for reference & MDC queries)
MACRO_TOOL_LENGTH_GEOM_START = 2001      # #2001-#2200
MACRO_TOOL_LENGTH_WEAR_START = 2201      # #2201-#2400
MACRO_TOOL_DIAM_GEOM_START = 2401        # #2401-#2600
MACRO_TOOL_DIAM_WEAR_START = 2601        # #2601-#2800
MACRO_WORK_OFFSET_BASE = 5221            # G54 X,Y,Z,A,B,C (#5221-#5226)
MACRO_POSITION_START = 5021              # Current position #5021-#5026

# ---------------------------------------------------------------------------
# Extra entity attributes
# ---------------------------------------------------------------------------
ATTR_DATA_SOURCE = "data_source"        # "mtconnect" or "mdc"
ATTR_LAST_UPDATE = "last_update"
