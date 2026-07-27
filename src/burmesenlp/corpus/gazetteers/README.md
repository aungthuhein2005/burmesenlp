# Gazetteers

String-list entity gazetteers for rule-based lookup (`GazetteerManager`).

**Wired into** `BurmeseNLP.process()` after POS (post-BMWE words) →
`doc.entities`. Pass `gazetteer=False` to skip. Still usable standalone
via `GazetteerManager`.

## Format

Most files are a JSON **array of strings**:

```json
["ရန်ကုန်", "မန္တလေး"]
```

Entity type is inferred from the **filename** (see `EntityType` /
`FILENAME_TO_ENTITY` in `burmesenlp.gazetteer`).

`holidays.json` is special:

```json
{
  "holidays": [
    {"name": "...", "date": "...", "days": "...", "remarks": "..."}
  ]
}
```

## Files

| File | EntityType |
| --- | --- |
| `male_names.json` / `female_names.json` | PERSON |
| `towns.json` | TOWN |
| `villages.json` | VILLAGE |
| `districts.json` | DISTRICT |
| `states.json` | STATE |
| `self_administered_zones.json` | ZONE |
| `rivers.json` | RIVER |
| `mountains.json` | MOUNTAIN |
| `organizations.json` | ORGANIZATION |
| `universities.json` | UNIVERSITY |
| `religions.json` | RELIGION |
| `ethnic_groups.json` | ETHNIC_GROUP |
| `holidays.json` | HOLIDAY |
| `pagodas.json` | PAGODA |

See `metadata.json` for corpus version/license.
