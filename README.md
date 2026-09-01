# ISYGLT Modbus for Home Assistant

Custom Home Assistant integration for controlling ISYGLT installations directly over Modbus TCP.

> Development status: active development. Version 0.4.3 uses direct HACS repository installation and includes native ISYGLT addressing with automatic Light mapping.

## HACS installation

Add `https://github.com/Smart-Activity/isyglt_modbus` as a custom HACS repository of type **Integration**. HACS installs the integration directly from `custom_components/isyglt`; no release ZIP asset is required. Create a normal GitHub release/tag (for example `v0.4.3`) after committing the files so HACS can see the new version.

## Architecture

One ISYGLT main controller is configured per Modbus TCP endpoint. Multiple Modbus slave/unit IDs can exist below that controller. Entities are assigned to existing Home Assistant Areas.

```text
ISYGLT Hoofdcontroller
├── Light
├── Cover
├── Climate
└── Switch
```

## Native ISYGLT addressing

The integration now contains an addressing layer that translates native ISYGLT addresses to the correct zero-based Modbus protocol address.

| ISYGLT type | Modbus reference range | Protocol type |
|---|---|---|
| NE | 0xxxxx | Coil |
| NA | 1xxxxx | Discrete input |
| SM | 3xxxxx | Input register |
| M | 4xxxxx | Holding register |

NE/NA bit addresses use the formula:

```text
one_based = ((group - 1) × 8) + bit
protocol_address = one_based - 1
```

Examples:

```text
NE 1.1  -> 000001 -> protocol coil 0
NE 2.1  -> 000009 -> protocol coil 8
NE 30.3 -> 000235 -> protocol coil 234
M 1     -> 400001 -> protocol holding register 0
M 8     -> 400008 -> protocol holding register 7
```

The user configures ISYGLT addresses; raw Modbus offsets are hidden for new Light entities.

## Light

When adding a Light, select one of two types:

### Dimbaar

- Uses an **M** address automatically.
- Uses a Modbus holding register automatically.
- `0` = off.
- `1-100` = on and brightness percentage.
- Feedback is read from the same M address.
- Example input: `8` means `M 8` and maps to Modbus reference `400008` / protocol address `7`.

### Schakelbaar

- Uses an **NE** address automatically.
- Uses a Modbus coil automatically.
- `False/0` = off.
- `True/1` = on.
- Feedback is read from the same NE address.
- Example input: `30.3` means `NE 30.3` and maps to Modbus reference `000235` / protocol address `234`.

Existing v0.3 Light entries keep their old raw holding-register behavior for backward compatibility. Re-create them through the v0.4 UI when you want to move them to native ISYGLT addressing.

## Switch, Cover and Climate

These platforms are still present from v0.3 and currently use their generic register configuration. They will be migrated to the same NE/NA/SM/M addressing layer as their exact ISYGLT semantics are confirmed.

## Installation

### HACS custom repository

Add this GitHub repository to HACS as a custom repository of type **Integration**, install ISYGLT and restart Home Assistant.

### Manual

Download `isyglt.zip` from the latest GitHub Release, extract it and copy:

```text
custom_components/isyglt
```

to:

```text
/config/custom_components/isyglt
```

Restart Home Assistant and add **ISYGLT** through **Settings → Devices & services**.

## Configuration

1. Add the ISYGLT integration.
2. Enter controller name, host/IP, port and timeout.
3. Open **Configure** on the integration.
4. Choose **Light toevoegen**.
5. Select an existing Home Assistant Area and slave/unit ID.
6. Choose **Dimbaar (M)** or **Schakelbaar (NE)**.
7. Enter only the native ISYGLT address, without needing the raw Modbus offset.

## GitHub releases

Pushing a version tag automatically validates the source, creates `isyglt.zip` and publishes it as a GitHub Release asset.

```bash
git add .
git commit -m "Release v0.4.0"
git push origin main
git tag v0.4.0
git push origin v0.4.0
```

Stable latest-release URL:

```text
https://github.com/Smart-Activity/isyglt_modbus/releases/latest/download/isyglt.zip
```

## License

MIT License. See `LICENSE`.

## Installeren via HACS

Voeg `https://github.com/Smart-Activity/isyglt_modbus` toe als **Custom repository** van het type **Integration**. De repository gebruikt GitHub Releases; HACS downloadt de release-asset `isyglt.zip`.

Vanaf v0.4.1 bevat `isyglt.zip` de bestanden van `custom_components/isyglt` direct in de root van het archief. Dit voorkomt een dubbel geneste installatiemap bij HACS.

Na installatie of update via HACS moet Home Assistant opnieuw worden gestart.
