# Changelog

## 0.8.0
- Native ISYGLT Climate configuration added.
- Desired temperature uses an M address (holding register); measured temperature uses an SM address (input register / FC04).
- Native temperature range is 10–40 °C, 1 °C steps, with initial scale 1 (raw 21 = 21 °C).
- Optional Airco mode adds Fan High, Fan Medium, Fan Low and Airco On/Off, each with NE command and NA feedback.
- Airco NA feedback is authoritative for HVAC power and fan mode state.
- Airco Climate exposes Home Assistant fan modes Low/Medium/High and COOL/OFF.
- Four Airco command Button entities are created automatically on the same Climate device.
- Existing legacy raw-register Climate configurations remain supported.


## 0.7.0
- Added native ISYGLT Scene support.
- Scene activation sends a 200 ms short press to the configured NE address.
- Added NA discrete-input feedback for scene activation/status.
- Home Assistant records the Scene activation timestamp when the configured NA feedback becomes active.
- Added one linked `Opslaan` Button entity per Scene.
- The Store button holds the same NE address active for 5 seconds so ISYGLT stores the current scene/preset.
- Added Modbus FC02 discrete-input reads for NA feedback.
- Added native Scene NE/NA address validation and address mapping tests.


## 0.6.0
- Cover rebuilt around native ISYGLT NE addresses: one for up and one for down.
- Open/close use a 3-second long press.
- Stop sends a 200 ms short press to the same direction that Home Assistant last started.
- Added two Button entities per native Cover for explicit 200 ms up/down short presses.
- Removed position support from newly configured native Covers because no real position feedback is available.
- Legacy raw-register Covers remain supported for backwards compatibility.

## 0.5.0

- Switch omgebouwd naar native ISYGLT-adressering.
- Nieuwe Switches gebruiken automatisch NE (`groep.bit`) en Modbus coils.
- Voorbeeld: `NE 30.3` wordt Modbus `000235` en protocoladres `234`.
- Feedback wordt uit dezelfde coil gelezen.
- Raw Modbus-register en configureerbare 0/100-waarden zijn verwijderd uit de nieuwe Switch-configuratie.
- Bestaande legacy Switch-configuraties blijven werken.
- Adresseringstest toegevoegd voor Switch.


## 0.4.4

- Fix Home Assistant 2026.x compatibility for the Cover platform.
- Import `ATTR_POSITION` from `homeassistant.components.cover` instead of the removed `homeassistant.const` location.
- Prevents the full ISYGLT config entry from failing during platform import.

## v0.4.3

- Simplified HACS installation to use the repository contents directly.
- Removed `zip_release`, `filename`, and `hide_default_branch` from `hacs.json`.
- Removed the GitHub Actions release workflow dependency; no `isyglt.zip` release asset is required.
- HACS now installs directly from `custom_components/isyglt`.
- Bumped integration version to `0.4.3`.

## v0.4.1

- Fixed HACS release installation metadata.
- Added `zip_release: true` and `filename: isyglt.zip` to `hacs.json`.
- Hid the default branch in HACS so normal installations use published releases.
- Added required `documentation`, `issue_tracker`, and `codeowners` fields to `manifest.json`.
- Added an integration brand icon.
- Fixed the GitHub release archive layout: `isyglt.zip` now contains the integration files directly at the archive root, exactly where HACS expects them when extracting into `custom_components/isyglt`.
- Added release archive structure validation to the GitHub Actions workflow.

## v0.4.0

- Added native ISYGLT address translation in `addressing.py`.
- Added NE -> Modbus coil translation.
- Added NA -> Modbus discrete-input translation.
- Added SM -> Modbus input-register translation.
- Added M -> Modbus holding-register translation.
- Added correct conversion from one-based ISYGLT/Modbus reference addresses to zero-based PyModbus protocol addresses.
- Light setup now lets the user choose **Dimbaar (M)** or **Schakelbaar (NE)**.
- Dimmable Light automatically uses an M holding register with value 0-100.
- Switched Light automatically uses an NE coil with boolean on/off feedback.
- Added Modbus FC01 coil reads and FC05 coil writes.
- Raw Modbus register selection is removed from the normal setup flow for new Lights.
- Added validation and normalization of native ISYGLT addresses.
- Kept existing v0.3 Light configurations working with legacy raw holding-register semantics.

### Address examples

- `M 8` -> `400008` -> PyModbus holding-register address `7`.
- `NE 1.1` -> `000001` -> PyModbus coil address `0`.
- `NE 30.3` -> `000235` -> PyModbus coil address `234`.

## v0.3.0

- Added Modbus Holding Register `SwitchEntity` support.
- Added configurable switch on/off values.
- Added `CoverEntity` support with separate command and position registers.
- Added configurable open, close and stop command values.
- Added cover position read/write support using a 0-100 holding register.
- Added `ClimateEntity` support for current temperature and target setpoint.
- Added configurable climate scale, minimum, maximum and temperature step.
- Added Home Assistant Area selection for Switch, Cover and Climate.
- Added add/remove menu entries for all four entity types.
- Main controller forwards Light, Switch, Cover and Climate platforms.

## v0.2.0

- First GitHub/HACS-ready repository structure.
- Added GitHub Actions release workflow.
- Added automatic `isyglt.zip` Release asset generation.
- Added HACS metadata, changelog and MIT license.
- Added first dimmable Light entity using a single 0-100 holding register.
- Added Modbus TCP main controller and multi-slave support.
