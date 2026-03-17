# Project Notes – HAAS CNC Home Assistant Integration

## Overview

This project provides a custom Home Assistant integration for monitoring a **HAAS UMC-500 5-axis CNC milling machine** running the **HAAS NGC controller** via MQTT. The data pathway is:

```
HAAS NGC (RS-232 / Telnet)
  └─► Haas MQTT MTConnect Adapter  (Node.js, github.com/EfrainRodriguez/Haas-MQTT-MTConnect-Adapter)
        └─► MQTT Broker  (Mosquitto / Aedes)
              └─► haas_cnc  HA Custom Integration
                    └─► Home Assistant entities
```

---

## HAAS NGC MACRO Variables Reference

The adapter queries the controller via RS-232 using HAAS Q-commands. The following macro variables are used; each maps to an MQTT sub-topic.

### Commands implemented in base adapter

| Q-Command  | Macro Variable | Description                      | MQTT sub-topic   |
|------------|---------------|----------------------------------|------------------|
| Q100       | –             | Machine availability             | `avail`          |
| Q104       | –             | Operating mode                   | `mode`           |
| Q500       | –             | Program name, execution, parts   | `program`, `execution`, `part_count` |
| Q600 5021  | 5021          | X axis work position (mm)        | `x_act`          |
| Q600 5022  | 5022          | Y axis work position (mm)        | `y_act`          |
| Q600 5023  | 5023          | Z axis work position (mm)        | `z_act`          |
| Q600 3027  | 3027          | Spindle speed (RPM)              | `speed`          |
| Q600 1094  | 1094          | Coolant level                    | `coolant_level`  |
| Q600 1098  | 1098          | Spindle load (raw → ÷81.92 = %) | `load`           |
| Q600 3026  | 3026          | Tool number in spindle           | `tool`           |

### Additional MACRO variables to implement in extended adapter

These require adding Q600 functions to `mqtt-publisher.js`. The priority column reflects how urgently they are needed.

| Macro Variable | Description                            | MQTT sub-topic    | Priority |
|---------------|----------------------------------------|-------------------|----------|
| 5041          | X axis machine (absolute) position     | `x_mach`          | High     |
| 5042          | Y axis machine (absolute) position     | `y_mach`          | High     |
| 5043          | Z axis machine (absolute) position     | `z_mach`          | High     |
| 5061          | A axis position (5-axis, degrees)      | `a_act`           | High     |
| 5062          | B axis position (5-axis, degrees)      | `b_act`           | High     |
| 3028          | Spindle override percentage            | `spindle_override` | Medium  |
| 3003          | Feed rate override percentage          | `feed_override`   | Medium   |
| 3901          | Current tool number (from T register)  | `tool_current`    | Medium   |
| 2001–2099     | Tool length offsets  (tool 1–99)       | `tool_len_{n}`    | Medium   |
| 2201–2299     | Tool diameter offsets (tool 1–99)      | `tool_dia_{n}`    | Medium   |
| 5201–5206     | Work offset G54 (X,Y,Z,A,B,C)         | `wcs_g54_{axis}`  | Medium   |
| 5221–5226     | Work offset G55                        | `wcs_g55_{axis}`  | Low      |
| 5241–5246     | Work offset G56                        | `wcs_g56_{axis}`  | Low      |
| 5261–5266     | Work offset G57                        | `wcs_g57_{axis}`  | Low      |
| 1090          | Air pressure (PSI, if sensor present)  | `air_pressure`    | Low      |
| 3030          | Cycle time in seconds                  | `cycle_time`      | High     |
| 3032          | Total run time in seconds              | `run_time`        | Medium   |
| 1092          | Chip conveyor status                   | `chip_conveyor`   | Low      |
| 9999          | Current alarm number (0 = no alarm)    | `alarm_code`      | High     |

> **Note:** Q600 variables for A/B axes and alarm state may vary by machine model and software version. Verify against the HAAS NGC Parameter Manual for your specific machine.

### Alarm / Error Monitoring

The HAAS NGC alarm state is not directly exposed by Q100/Q500. To get the current alarm number use:
- **Q600 9999** – returns the current alarm code (0 = no alarm).
- **Q600 9998** – alarm text string (some versions).

Alternatively, use **Q500 STATUS** response – if it returns something other than IDLE/ACTIVE it may contain an alarm state string.

---

## Integration Architecture Notes

### Update Philosophy

The integration uses **pure MQTT push** (IoT class: `local_push`) – no polling occurs within HA. The adapter itself polls the machine at its configured heartbeat interval (default 500 ms / 1 s). This means:

- HA entities update immediately on each MQTT message.
- The adapter controls the underlying polling frequency.
- To change update rates, adjust the adapter's `setInterval` timing in `mqtt-publisher.js`.

### Recommended Adapter Heartbeat Settings

| Data type                         | Suggested adapter interval |
|-----------------------------------|---------------------------|
| Machine status, execution, alarms | 500 ms                    |
| Axis positions, spindle speed/load| 500 ms – 1 s              |
| Tool info, work offsets           | 5 – 10 s                  |
| Part count, cycle time            | 1 s                       |
| Static info (versions, labels)    | On connect only            |

### Job Progress Estimation

The adapter does not directly expose current program line or total lines. Options for estimated time remaining:

1. **Cycle time + history** – track cycle time for recurring programs, compute ETA from start time.
2. **Part count approach** – if a batch is running, `part_count` / expected parts × cycle time gives remaining time.
3. **Expanded adapter** – add Q600 3030 (elapsed cycle time) and a HA helper `input_number` for expected cycle duration, then compute `remaining = expected - elapsed`.

A HA `template` sensor can compute estimated time remaining once the cycle time macro is implemented.

### Entity Grouping for Dashboard

Suggested logical groupings for Lovelace dashboard:

| Card             | Entities                                                  |
|------------------|-----------------------------------------------------------|
| Status overview  | Machine Available, Running, Execution State, Active Program, Part Count |
| Alarm            | Alarm Active, Alarm, Alarm Code                           |
| Axes             | X Position, Y Position, Z Position, A Axis, B Axis        |
| Spindle          | Spindle Speed, Spindle Load, Tool in Spindle              |
| Job timing       | Cycle Time, Run Time                                      |
| Tool / WCS       | Tool Length Offset, Tool Diameter Offset, Active Work Offset |
| Environment      | Coolant Level, Air Pressure                               |

---

## File Structure

```
HAAS-HomeAssistant/
├── custom_components/
│   └── haas_cnc/
│       ├── __init__.py          # Integration entry point, setup/unload
│       ├── manifest.json        # HA manifest
│       ├── const.py             # All constants, topic names, defaults
│       ├── coordinator.py       # MQTT subscription hub, data store
│       ├── config_flow.py       # UI config + options flows
│       ├── sensor.py            # All sensor entities
│       ├── binary_sensor.py     # Availability, running, alarm binary sensors
│       ├── strings.json         # UI strings
│       └── translations/
│           └── en.json          # English translations
├── .github/
│   └── prompts/
│       └── haas_homeassistant.prompt.md
├── .gitignore
├── hacs.json
├── README.md
├── project_notes.md             # This file
└── chat_log.md                  # LLM interaction log
```

---

## Dependencies

- Home Assistant ≥ 2024.1
- `mqtt` HA integration configured and connected to a broker
- [Haas MQTT MTConnect Adapter](https://github.com/EfrainRodriguez/Haas-MQTT-MTConnect-Adapter) running
- MQTT Broker (Mosquitto recommended for production; Aedes used in the adapter for dev)

---

## Known Limitations / Future Work

- [ ] A and B axis positions require extended adapter (Q600 5061/5062)
- [ ] Alarm code monitoring requires Q600 9999 in adapter
- [ ] Tool geometry offsets (length/diameter per tool number) require significant adapter expansion
- [ ] Work coordinate offsets require adapter expansion (Q600 5201–5266)
- [ ] Job progress estimation / ETA needs adapter cycle time support (Q600 3030)
- [ ] Maintenance alerts (service intervals) – check HAAS parameter 278 (machine hours) via Q600
- [ ] Multi-machine support works via multiple config entries with different topic prefixes
- [ ] Dashboard / Lovelace card templates to be created
- [ ] Custom icons specific to HAAS/CNC to be added (currently using MDI icons)
