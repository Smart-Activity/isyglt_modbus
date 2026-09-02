# ISYGLT Modbus for Home Assistant

> **v0.8.1:** verwijderen van een geconfigureerd ISYGLT-apparaat ruimt nu ook het Home Assistant apparatenregister op. Bestaande verweesde apparaten uit oudere versies worden bij het laden automatisch verwijderd.

Custom Home Assistant integration for controlling ISYGLT installations directly over Modbus TCP.

> Development status: active development. Version 0.8.1 adds reliable Home Assistant device-registry cleanup on top of the native Climate support from v0.8.0.

## HACS installation

Add `https://github.com/Smart-Activity/isyglt_modbus` as a custom HACS repository of type **Integration**. HACS installs the integration directly from `custom_components/isyglt`; no release ZIP asset is required. Create a normal GitHub release/tag (for example `v0.8.1`) after committing the files so HACS can see the new version.

## Architecture

One ISYGLT main controller is configured per Modbus TCP endpoint. Multiple Modbus slave/unit IDs can exist below that controller. Entities are assigned to existing Home Assistant Areas.

```text
ISYGLT Hoofdcontroller
├── Light
├── Switch
├── Cover
├── Scene
│   └── Opslaan button
└── Climate
    └── Airco (optional): Fan High / Medium / Low / On-Off buttons
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

The user configures ISYGLT addresses; raw Modbus offsets are hidden for native Light, Switch, Cover and Scene entities.

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

## Switch

New Switch entities use a native **NE** address and read/write the corresponding Modbus coil. Legacy raw-register Switch entries remain supported for upgrades.

## Cover

New Cover entities use two native **NE** addresses: one for up and one for down. Open/close use a 3-second long press. Stop gives a 200 ms short press to the direction last started by Home Assistant. Two additional short-press Button entities are created automatically. No position is exposed because there is no real position feedback.

## Scene

A native ISYGLT Scene uses one **NE** address for the preset button and one **NA** address for feedback.

- Activate Scene: 200 ms pulse on NE.
- Feedback: read the configured NA discrete input.
- Store current preset: the automatically created `Opslaan` Button holds the same NE address for 5 seconds.
- Home Assistant Scene entities are stateless by design; the NA feedback is used to record the scene activation timestamp and is also exposed as a diagnostic state attribute.

Example:

```text
Scene: Woonkamer sfeer 1
NE: 1.1
NA feedback: 1.1

Activate -> NE 1.1 ON for 200 ms -> OFF
Store    -> NE 1.1 ON for 5 s    -> OFF
Feedback -> NA 1.1
```

## Climate

Climate is still the earlier generic register implementation. It will be migrated to native ISYGLT temperature/setpoint semantics after the exact scaling and addresses have been confirmed.

## Polling interval (v0.8.2)

Each ISYGLT main controller now has its own polling interval. The default is **5.0 seconds** and the value can be changed later through **Settings → Devices & services → ISYGLT → Configure → Hoofdcontroller instellingen**.

The field is freely editable between **0.1 and 3600 seconds** (0.1-second steps). The interval controls how often readable status values are requested from the controller for Lights, Switches, Scenes, Climate and legacy feedback-based Covers. Native Covers and command Buttons are not polled because they do not expose a readable feedback state.

A very short interval creates more Modbus TCP traffic. Requests are serialized by the integration, so one controller is never sent overlapping Modbus requests.

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

HACS installs directly from the repository. Publish a normal version tag/release after committing the new version.

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

## Switch (v0.6.0)

Nieuwe Switch entities gebruiken native **ISYGLT NE-adressering**. In Home Assistant vul je alleen naam, ruimte, Slave/Unit ID en een adres zoals `30.3` in. De integratie vertaalt dit automatisch naar `NE 30.3`, Modbus coil-referentie `000235` en protocoladres `234`. Aan/uit en feedback gebruiken dezelfde coil.

Bestaande Switch entities uit oudere versies die met een raw holding register zijn opgeslagen blijven werken voor backward compatibility. Nieuwe Switches vragen geen raw Modbus-register of 0/100-waarden meer.

## Cover (v0.6.0)
Native Covers use two ISYGLT NE addresses: one for **Omhoog** and one for **Omlaag**. Home Assistant Open/Close sends a 3-second long press. Stop sends a 200 ms short press to the same direction that Home Assistant last started. Each Cover also creates two Button entities for explicit 200 ms short presses. Native Covers intentionally expose no position percentage because the installation has no real position feedback.

Example: Omhoog `NE 20.1`, Omlaag `NE 20.2`.

## Native Climate (v0.8.0)

A new Climate is configured using native ISYGLT addressing:

- Desired temperature: **M** (read/write holding register)
- Measured temperature: **SM** (read-only input register)
- Initial temperature interpretation: **raw value equals °C** (for example M=21 means 21 °C)
- Setpoint range: **10–40 °C**, step **1 °C**

When **Airco** is enabled, configure four command/feedback pairs:

- Fan High: NE command + NA feedback
- Fan Medium: NE command + NA feedback
- Fan Low: NE command + NA feedback
- Airco On/Off: NE command + NA feedback

NE commands are short 200 ms pulses. NA inputs are authoritative feedback. Home Assistant exposes COOL/OFF and Low/Medium/High fan modes on the Climate entity, plus four matching command Button entities on the same device.
