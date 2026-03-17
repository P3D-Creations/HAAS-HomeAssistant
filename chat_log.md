# Chat Log – HAAS CNC Home Assistant Integration

---

## Session 1 – 2026-03-17

### Summary

Initial repository creation and integration framework scaffold.

### Request

> See prompt attached. (haas_homeassistant.prompt.md)
>
> Set up the repository for a Home Assistant custom integration to monitor a HAAS UMC-500 5-axis CNC milling machine via the Haas MQTT MTConnect Adapter. Build the integration framework according to HA best practices, covering the critical monitoring endpoints.

### Actions Taken

1. **Researched** the [Haas MQTT MTConnect Adapter](https://github.com/EfrainRodriguez/Haas-MQTT-MTConnect-Adapter) repository to identify all MQTT topics published by the adapter:
   - `avail`, `mode`, `execution`, `program`, `part_count`
   - `x_act`, `y_act`, `z_act`, `position`
   - `speed`, `coolant_level`, `load`, `tool`, `timestamp`

2. **Designed** the integration architecture:
   - `local_push` IoT class (pure MQTT subscription, no HA-side polling)
   - Central `HaasDataCoordinator` class manages all subscriptions and distributes updates to entities via callbacks, eliminating redundant MQTT listener overhead
   - Entity descriptions use a dataclass pattern with optional value transforms and attribute functions for clean extensibility

3. **Created** the full integration file structure under `custom_components/haas_cnc/`:
   - `manifest.json` – domain, MQTT dependency, config flow enabled
   - `const.py` – all constants, topic names, defaults, update group labels
   - `coordinator.py` – `HaasDataCoordinator`: subscribes to all topics, fan-outs callbacks
   - `__init__.py` – `async_setup_entry` / `async_unload_entry`, forwards to platforms
   - `config_flow.py` – UI config flow (machine name + topic prefix), options flow
   - `sensor.py` – 22 sensor entities covering all critical and extended endpoints
   - `binary_sensor.py` – 3 binary sensors: Machine Available, Running, Alarm Active
   - `strings.json` / `translations/en.json` – full UI string set

4. **Created** repo meta files: `README.md`, `.gitignore`, `hacs.json`

5. **Created** `project_notes.md` with:
   - Full HAAS NGC macro variable reference table
   - Extended variable list for future adapter expansion
   - Update frequency recommendations
   - Dashboard entity grouping guide
   - Known limitations and future work backlog

### Entities Created

**Binary Sensors (3):**
- Machine Available (`avail` → AVAILABLE/UNAVAILABLE)
- Running (`execution` → non-IDLE = running)
- Alarm Active (`alarm` → non-empty/non-zero)

**Sensors (22):**
- Execution State, Operating Mode, Active Program, Part Count
- X / Y / Z / A / B axis positions
- Spindle Speed (RPM), Spindle Load (%)
- Coolant Level, Air Pressure
- Tool in Spindle, Tool Length Offset, Tool Diameter Offset, Active Work Offset
- Alarm text, Alarm Code
- Cycle Time, Run Time
- Adapter Timestamp (disabled by default)

### Decisions & Rationale

| Decision | Rationale |
|---|---|
| `local_push` IoT class | Adapter already publishes at ≤500 ms; no need to poll from HA. More efficient, lower latency. |
| Single coordinator per entry | One set of MQTT subscriptions shared across all entities. Avoids N×topic MQTT connections. |
| Callback-based entity updates | `async_write_ha_state` only when the relevant topic fires. Zero idle CPU for static values. |
| Extended topics in const.py even if adapter doesn't publish them yet | Entities are wired up and ready; they just show unavailable until the adapter publishes. Future-proof. |
| `entity_registry_enabled_default=False` for adapter_timestamp | It's a debug/diagnostic value rather than user-facing. Keeps the default entity list clean. |

### Next Steps

- [ ] Expand the MQTT adapter with extended macro variables (A/B axes, alarm code, tool offsets, cycle time)
- [ ] Test the integration in a Home Assistant development environment
- [ ] Create Lovelace dashboard UI (cards and views)
- [ ] Implement estimated remaining time logic as a HA template sensor
- [ ] Add maintenance alert monitoring via machine parameter polling
- [ ] Set up GitHub repository remote and CI (GitHub Actions validation)
