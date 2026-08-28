# -*- coding: utf-8 -*-
"""Static scan of zg2uni_rules.json: which rules structurally collapse
N distinct literal alternatives into a single fixed replacement (no
backreference)? Those are non-invertible by construction -- useful,
corpus-independent evidence for which spans a repair log should mark
lossy=True, rather than guessing."""
import json
import re

with open("src/burmesenlp/zawgyi/zg2uni_rules.json", encoding="utf-8") as f:
    rules = json.load(f)

ALT_GROUP = re.compile(r"^\((?:[^()|\\]\|)*[^()|\\]\)$")

many_to_one = []
for i, r in enumerate(rules):
    frm, to = r["from"], r["to"]
    has_backref = bool(re.search(r"\\[0-9]", to))
    if ALT_GROUP.match(frm) and not has_backref:
        n_alts = frm.count("|") + 1
        if n_alts > 1:
            many_to_one.append((i, frm, to, n_alts))

print(f"{len(many_to_one)} of {len(rules)} rules are STATICALLY many-to-one:")
for i, frm, to, n in many_to_one:
    print(f"  rule {i}: {n} alternatives -> {to!r}   pattern={frm!r}")
