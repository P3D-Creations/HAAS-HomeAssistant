# HAAS CNC Machine Monitor – Home Assistant Integration

A custom [Home Assistant](https://www.home-assistant.io/) integration for monitoring a **HAAS UMC-500 5-axis CNC milling machine** (HAAS NGC controller) via MQTT.

Data is sourced from the [Haas MQTT MTConnect Adapter](https://github.com/EfrainRodriguez/Haas-MQTT-MTConnect-Adapter), which reads machine state over RS-232 and publishes it to an MQTT broker. This integration subscribes to those topics and exposes the data as Home Assistant entities.

---

## Features

- **Real-time** machine status, execution state, axis positions, spindle speed/load
- **Binary sensors** for machine availability, running state, and active alarms
- **Tool monitoring** – current tool in spindle, tool length/diameter offsets
- **Job info** – active program name, part count, cycle time
- **Coolant & environment** – coolant level, air pressure
- **5-axis support** – X, Y, Z, A, B axis positions
- Efficient **push-based updates** via MQTT (no polling)
- Configurable **topic prefix** to support multiple machines

---

## Architecture

```
HAAS NGC Controller (RS-232)
        │
        ▼
Haas MQTT MTConnect Adapter  (Node.js)
        │  MQTT publish  haas/minimill/*
        ▼
MQTT Broker  (e.g. Mosquitto / Aedes)
        │  MQTT subscribe
        ▼
Home Assistant  –  haas_cnc custom integration
        │
        ├── binary_sensor:  Machine Available, Running, Alarm Active
        └── sensor:         Execution, Mode, Program, Part Count,
                            X/Y/Z/A/B position, Spindle Speed/Load,
                            Coolant Level, Tool, Tool Length/Diameter,
                            Work Offset, Alarm, Cycle Time, Run Time
```

---

## Prerequisites

1. **Home Assistant** with the **MQTT integration** configured and connected to your broker.
2. **Haas MQTT MTConnect Adapter** running and publishing to your MQTT broker.
   - See [setup instructions](https://github.com/EfrainRodriguez/Haas-MQTT-MTConnect-Adapter#how-to-use).
   - The adapter should be configured to publish to a topic like `haas/minimill/` (default).
3. **MQTT Broker** accessible to both the adapter and Home Assistant (e.g. Mosquitto).

---

## Installation

### HACS (recommended – manual repo)

1. In HACS → **Integrations** → ⋮ → **Custom repositories**
2. Add `https://github.com/yourusername/HAAS-HomeAssistant` as an **Integration**
3. Install **HAAS CNC Machine Monitor**
4. Restart Home Assistant

### Manual

1. Copy the `custom_components/haas_cnc` folder into your HA `config/custom_components/` directory.
2. Restart Home Assistant.

---

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **HAAS CNC Machine Monitor**
3. Enter:
   - **Machine Name** – display name (e.g. `HAAS UMC500`)
   - **MQTT Topic Prefix** – must match the adapter's `config.json` topic (default: `haas/minimill/`)

---

## MQTT Topics

The integration listens to the following sub-topics under the configured prefix:

| Sub-topic       | Description                        | Update group |
|-----------------|------------------------------------|--------------|
| `avail`         | Machine availability               | Real-time    |
| `execution`     | Execution state (IDLE/ACTIVE/…)    | Real-time    |
| `mode`          | Operating mode (AUTO/MANUAL/…)     | Real-time    |
| `program`       | Active program name                | Real-time    |
| `part_count`    | Parts produced count               | Real-time    |
| `x_act`         | X axis position (mm)               | Real-time    |
| `y_act`         | Y axis position (mm)               | Real-time    |
| `z_act`         | Z axis position (mm)               | Real-time    |
| `a_act`         | A axis position (°)                | Real-time    |
| `b_act`         | B axis position (°)                | Real-time    |
| `speed`         | Spindle speed (RPM)                | Real-time    |
| `load`          | Spindle load (%)                   | Real-time    |
| `coolant_level` | Coolant level                      | Real-time    |
| `air_pressure`  | Air pressure                       | Real-time    |
| `alarm`         | Alarm text                         | Real-time    |
| `alarm_code`    | Alarm code                         | Real-time    |
| `cycle_time`    | Current cycle time (s)             | Real-time    |
| `run_time`      | Total run time (s)                 | Real-time    |
| `tool`          | Tool number in spindle             | Standard     |
| `tool_length`   | Active tool length offset (mm)     | Standard     |
| `tool_diameter` | Active tool diameter offset (mm)   | Standard     |
| `work_offset`   | Active work coordinate offset      | Standard     |
| `timestamp`     | Adapter heartbeat timestamp        | Real-time    |

> **Note:** Topics marked with `a_act`, `b_act`, `alarm`, `alarm_code`, `tool_length`, `tool_diameter`, `work_offset`, `air_pressure`, `cycle_time`, `run_time` require an extended version of the MQTT adapter. See `project_notes.md` for the required macro variable additions.

---

## Extending the Adapter

The base adapter only publishes a subset of available HAAS macro variables. To enable additional sensors you will need to extend `mqtt-publisher.js` with the macro Q600 commands listed in `project_notes.md`.

---

## License

MIT
