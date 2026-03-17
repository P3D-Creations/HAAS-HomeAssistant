"""Constants for the HAAS CNC Machine Monitor integration."""

DOMAIN = "haas_cnc"
DEFAULT_NAME = "HAAS CNC"

# Configuration keys
CONF_TOPIC_PREFIX = "topic_prefix"
CONF_MACHINE_NAME = "machine_name"

# Defaults
DEFAULT_TOPIC_PREFIX = "haas/minimill/"
DEFAULT_MACHINE_NAME = "HAAS UMC500"

# Update interval groups (seconds)
# Real-time: machine status, execution, axis positions, sensor data
UPDATE_INTERVAL_REALTIME = 1
# Standard: tool info, work offsets
UPDATE_INTERVAL_STANDARD = 10
# Slow: administrative info (software version, etc.)
UPDATE_INTERVAL_SLOW = 3600

# MQTT sub-topics published by the Haas MQTT MTConnect Adapter
TOPIC_AVAIL = "avail"
TOPIC_MODE = "mode"
TOPIC_EXECUTION = "execution"
TOPIC_PROGRAM = "program"
TOPIC_PART_COUNT = "part_count"
TOPIC_X_ACT = "x_act"
TOPIC_Y_ACT = "y_act"
TOPIC_Z_ACT = "z_act"
TOPIC_POSITION = "position"
TOPIC_SPEED = "speed"
TOPIC_COOLANT_LEVEL = "coolant_level"
TOPIC_LOAD = "load"
TOPIC_TOOL = "tool"
TOPIC_TIMESTAMP = "timestamp"

# --- Extended subtopics (requires expanded MQTT publisher) ---
# Alarm / error
TOPIC_ALARM = "alarm"
TOPIC_ALARM_CODE = "alarm_code"
# A and B axes (5 axis machine)
TOPIC_A_ACT = "a_act"
TOPIC_B_ACT = "b_act"
# Tool geometry (tool length/diameter offsets; Q600 macro variables)
TOPIC_TOOL_LENGTH = "tool_length"
TOPIC_TOOL_DIAMETER = "tool_diameter"
# Work coordinate offset (active WCS)
TOPIC_WORK_OFFSET = "work_offset"
# Air pressure / pallet changer
TOPIC_AIR_PRESSURE = "air_pressure"
# Cycle time / run time (calculated by adapter or HA side)
TOPIC_CYCLE_TIME = "cycle_time"
TOPIC_RUN_TIME = "run_time"

# Signal groups - used to determine what data an entity depends on
SIGNAL_UPDATE_ENTITY = f"{DOMAIN}_update"

# Entity update groups
UPDATE_GROUP_REALTIME = "realtime"     # ~1 s: status, positions, speeds, load
UPDATE_GROUP_STANDARD = "standard"    # ~10 s: tool info, offsets
UPDATE_GROUP_SLOW = "slow"            # ~1 h: static info

# State values returned by the adapter
EXECUTION_IDLE = "IDLE"
EXECUTION_ACTIVE = "ACTIVE"
EXECUTION_PROGRAM = "PROGRAM"
EXECUTION_FEED_HOLD = "FEED_HOLD"
EXECUTION_STOPPED = "STOPPED"
EXECUTION_READY = "READY"
EXECUTION_INTERRUPTED = "INTERRUPTED"
EXECUTION_WAIT = "WAIT"

AVAIL_AVAILABLE = "AVAILABLE"
AVAIL_UNAVAILABLE = "UNAVAILABLE"

# Attributes
ATTR_PROGRAM = "program"
ATTR_EXECUTION = "execution"
ATTR_PART_COUNT = "part_count"
ATTR_POSITION_X = "x"
ATTR_POSITION_Y = "y"
ATTR_POSITION_Z = "z"
ATTR_POSITION_A = "a"
ATTR_POSITION_B = "b"
ATTR_TOOL_NUMBER = "tool_number"
ATTR_SPINDLE_SPEED = "spindle_speed"
ATTR_SPINDLE_LOAD = "spindle_load"
ATTR_COOLANT_LEVEL = "coolant_level"
ATTR_LAST_UPDATE = "last_update"
ATTR_TOPIC_PREFIX = "topic_prefix"
