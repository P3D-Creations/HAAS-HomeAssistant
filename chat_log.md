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
- [x] Test the integration in a Home Assistant development environment
- [ ] Create Lovelace dashboard UI (cards and views)
- [ ] Implement estimated remaining time logic as a HA template sensor
- [ ] Add maintenance alert monitoring via machine parameter polling
- [x] Set up GitHub repository remote and CI (GitHub Actions validation)

---

## Session 2 – 2026-03-24

### Summary

HACS configuration, automated release pipeline, integration icons, and log review.

### Request

> 1. Automate the release process so pushing commits auto-increments version and creates a release
> 2. Fix integration icon/thumbnail
> 3. Review attached HA logs – axis positions timing out
> 4. Disable cartridge information since machine is not dispensing version

### Actions Taken

1. **Auto-release workflow** – Replaced the tag-triggered `release.yml` with a full auto-versioning pipeline:
   - Triggers on every push to `main`/`master`
   - Reads current version from `manifest.json`
   - Determines bump type from commit messages (conventional commits):
     - `BREAKING` or `!:` → **major** bump
     - `feat:` → **minor** bump
     - Everything else → **patch** bump
   - Updates `manifest.json`, commits with `[skip ci]` (prevents infinite loop)
   - Tags and pushes the new version
   - Creates a GitHub Release with the zipped component
   - HACS picks up the release automatically

2. **Integration icons** – Generated PNG brand images for the integration:
   - Created `generate_icons.py` script (Pillow-based, draws a CNC machine icon)
   - Generated 256px and 512px variants of `icon.png` and `logo.png`
   - Placed in both `custom_components/haas_cnc/` and repo root (HACS checks both locations)
   - Note: For the icon to appear in HA's Settings > Integrations page (not just HACS), a submission to the `home-assistant/brands` repository would be required.

3. **Log analysis** – Reviewed the attached HA log:
   - **No `haas_cnc` errors found** – the integration is either not installed yet or loaded cleanly
   - The axis position timeouts (`Timeout after 15.xxx s for GET .../AxisPositions`) are from `custom_components.datron_next`, a **separate** integration for a Datron CNC machine at 192.168.2.19
   - The cartridge errors (`API error 400 for /Cartridge/CurrentLevel: The value is only available in the Dispensing Edition`) are also from `datron_next`
   - These issues are in the **datron_next** integration, not haas_cnc – they would need to be addressed in that project's workspace

### Decisions & Rationale

| Decision | Rationale |
|---|---|
| Conventional-commits-based version bumping | Gives control over major/minor/patch via commit message prefixes; no extra config files needed |
| `[skip ci]` on version-bump commits | Prevents infinite loop (workflow push triggering itself) |
| PNG icons via Pillow script | Can regenerate easily; text-based SVG not fully supported by HA brands system |
| Icons in both repo root and component dir | HACS checks repo root; future HA brands support may check component dir |

### Next Steps

- [ ] Expand the MQTT adapter with extended macro variables (A/B axes, alarm code, tool offsets, cycle time)
- [ ] Create Lovelace dashboard UI (cards and views)
- [ ] Implement estimated remaining time logic as a HA template sensor
- [ ] Add maintenance alert monitoring via machine parameter polling
- [ ] Submit brand images to `home-assistant/brands` repository for official HA UI icon support
- [ ] Address datron_next axis timeout and cartridge issues (separate workspace/project)
- [ ] Install haas_cnc on HA instance and verify MQTT connectivity
