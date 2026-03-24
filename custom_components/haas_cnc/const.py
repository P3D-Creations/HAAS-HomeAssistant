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
KEY_POWER_ON_TIME = "power_on_time"     # accumulated seconds
KEY_CYCLE_TIME = "cycle_time"           # accumulated seconds

# Part timers (fast tier, macro-read)
KEY_PRESENT_PART_TIME = "present_part_time"   # current part timer
KEY_LAST_PART_TIME = "last_part_time"         # last completed part timer
KEY_PREV_PART_TIME = "prev_part_time"         # previous part timer

# Derived / MDC-only keys
KEY_MDC_STATUS = "mdc_status"          # IDLE / BUSY / ALARM from ?Q500
KEY_OPT_STOP = "opt_stop"              # Optional stop status (0/1)

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
# Macro variable → sensor mapping  (?Q600 reads)
# ---------------------------------------------------------------------------
# Edit these to match your HAAS controller.  Set a value to None (or 0)
# to skip reading that variable.  All variables are read with ?Q600 <var>.
#
# Reference for HAAS NGC controllers:
#   #1094  = Coolant level (%)
#   #1098  = Spindle load (%)
#   #3001  = Power-on timer (milliseconds)
#   #3002  = Cycle-start timer (ms) — time the cycle has been running
#   #3003  = Last complete program number (Onnnnn)
#   #3012  = Last alarm number
#   #3026  = Part count (M30 count)
#   #3027  = Spindle RPM (actual)
#   #3030  = Single-block mode (1 = on)
#   #3033  = Coolant position (0 = off, 1 = on)
#   #4001  = Active G-code group 1 (motion mode: 0/1/2/3)
#   #4014  = Active work offset group (54–59 = G54–G59)
#   #4119  = Programmed feedrate
#   #4120  = Active tool number
#   #5001  = Relative X position (work coords)  (#5001-#5005)
#   #5021  = Machine X position (work coords)   (#5021-#5025)
#   #5041  = Machine X position (machine coords) (#5041-#5045)
#   #5221–#5226  = G54 work offset X,Y,Z,A,B,C
#   #8550  = Tool in spindle (T number)
#
# NOTE: Different HAAS generations may use different variable numbers.
#       Check your operator's manual or use MDI: #nnnnn to verify.
# ---------------------------------------------------------------------------

# -- Fast tier macros (read every ~2 s) --
MACRO_X_WORK = 5041               # Current X position (work coordinates)
MACRO_Y_WORK = 5042               # Current Y position
MACRO_Z_WORK = 5043               # Current Z position
MACRO_A_WORK = 5044               # Current A position
MACRO_B_WORK = 5045               # Current B position
MACRO_C_WORK = 5046               # Current C position
MACRO_SPINDLE_SPEED = 3027        # Actual spindle RPM
MACRO_SPINDLE_LOAD = 1098         # Spindle load %
MACRO_FEEDRATE = 4119             # Programmed feedrate (mm/min or in/min)
MACRO_COOLANT_LEVEL = 13013        # Coolant level %
MACRO_PRESENT_PART_TIME = 3023    # Present part timer (seconds, read only)
MACRO_LAST_PART_TIME = 3024       # Last complete part timer (seconds, read only)
MACRO_PREV_PART_TIME = 3025       # Previous part timer (seconds, read only)
MACRO_OPT_STOP = 3033             # Optional stop status (0 = off, 1 = on)

# -- Medium tier macros (read every ~10 s) --
MACRO_TOOL_IN_SPINDLE = 3026      # Current tool number (T)
MACRO_PART_COUNT = 3901           # M30 count (parts)
MACRO_WORK_OFFSET_GROUP = 4014    # Active work offset group (54=G54, etc.)
MACRO_LAST_ALARM = None           # Last alarm number

# -- Slow tier macros (read every ~600 s) --
MACRO_POWER_ON_TIME = 3020        # Power-on timer (milliseconds)
MACRO_CYCLE_TIME = 3021           # Cycle-start timer (milliseconds)


# ---------------------------------------------------------------------------
# Extra entity attributes
# ---------------------------------------------------------------------------
ATTR_DATA_SOURCE = "data_source"        # "mtconnect" or "mdc"
ATTR_LAST_UPDATE = "last_update"
