# BFF corpus audit

Audited real archives on 2026-09-27.

| Archive | Size | Entries | Type 0 | Type 1 | Type 2 | Type 3 |
|---|---:|---:|---:|---:|---:|---:|
| BMW_M3_E36.bff | 18,934,688 | 1,122 | 1 | 0 | 1,121 | 0 |
| BMW_M3_E36_Cockpit.bff | 9,956,064 | 1,043 | 1 | 0 | 1,042 | 0 |
| RENDER.bff | 2,985,696 | 694 | 0 | 0 | 694 | 0 |

All 2,859 resources in this sample use Type 2 as the main compressed path. X12d==2 is not observed.

## BMW_M3_E36.bff

- 831 FXO
- 162 MEB
- 72 DDS
- 32 BMT
- vehicle XML/BAB/BAS/VHF/CDF samples

## BMW_M3_E36_Cockpit.bff

- 876 FXO
- 75 DDS
- 43 BMT
- 44 MEB
- cockpit BAS/VHF/BML samples

## RENDER.bff

- 592 FXO
- 81 FX
- 21 FXH

## Tool

```bash
python bff_audit.py BMW_M3_E36.bff audit.json
python bff_audit.py RENDER.bff audit.json --decode --decode-extension .fx --decode-extension .fxh
```

Unknown extensions and decode failures remain visible in reports.
