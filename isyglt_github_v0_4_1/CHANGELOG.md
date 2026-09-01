# Changelog

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
