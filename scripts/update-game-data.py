#!/usr/bin/env python3
"""Fetch public Idle Champions game definitions and build simulator data."""
import json
import os
import sys
import urllib.request
from pathlib import Path

URLS = [
    "https://master.idlechampions.com/~idledragons/post.php?call=getdefinitions",
    "http://master.idlechampions.com/~idledragons/post.php?call=getdefinitions",
]
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

def fetch():
    last = None
    for url in URLS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "IdleChampionsHelper-data-import/1.0"})
            with urllib.request.urlopen(req, timeout=90) as response:
                raw = response.read()
            parsed = json.loads(raw)
            if not isinstance(parsed, dict) or not isinstance(parsed.get("hero_defines"), list) or not isinstance(parsed.get("upgrade_defines"), list):
                raise ValueError("The server response does not look like Idle Champions game definitions.")
            return parsed, url
        except Exception as exc:
            last = exc
    raise RuntimeError(f"Could not fetch public game definitions: {last}")

def main():
    source, source_url = fetch()
    heroes = source["hero_defines"]
    upgrades = source["upgrade_defines"]
    hero_by_id = {str(h.get("id")): h for h in heroes if h.get("id") is not None}
    valid_heroes = {}
    for hero in heroes:
        name = hero.get("name", "")
        if not name or ("Y" in name and "E" in name and name[:1] == "Y"):
            continue
        valid_heroes[str(hero.get("id"))] = hero

    by_hero = {hid: [] for hid in valid_heroes}
    spec_names = {}
    for up in upgrades:
        hid = str(up.get("hero_id", ""))
        if hid not in valid_heroes:
            continue
        row = {k: v for k, v in up.items() if k not in ("graphic_id",)}
        by_hero[hid].append(row)
        spec = up.get("specialization_name")
        if isinstance(spec, str) and spec.strip():
            name = valid_heroes[hid].get("name")
            spec_names.setdefault(name, [])
            if spec.strip() not in spec_names[name]:
                spec_names[name].append(spec.strip())

    # Keep all public definition tables needed for future mechanics parsing.
    payload = {
        "schemaVersion": 1,
        "source": source_url,
        "generatedAt": source.get("current_time"),
        "heroes": [
            {
                **{k: v for k, v in hero.items() if k not in ("graphic_id",)},
                "upgrades": by_hero.get(str(hero.get("id")), []),
            }
            for hero in valid_heroes.values()
        ],
        "attack_defines": source.get("attack_defines", []),
        "ability_defines": source.get("ability_defines", []),
        "effect_defines": source.get("effect_defines", []),
        "effect_key_defines": source.get("effect_key_defines", []),
        "buff_defines": source.get("buff_defines", []),
        "text_defines": source.get("text_defines", []),
        "game_rule_defines": source.get("game_rule_defines", []),
    }
    (DATA / "game-definitions.json").write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    spec_payload = {
        "schemaVersion": 1,
        "source": source_url,
        "generatedAt": source.get("current_time"),
        "sourceNote": "Automatically generated from public Idle Champions game definitions. Only actual specialization names are listed.",
        "champions": spec_names,
    }
    (DATA / "specializations.json").write_text(
        json.dumps(spec_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Imported {len(valid_heroes)} champions, {len(upgrades)} upgrades, {sum(map(len, by_hero.values()))} champion upgrades, {sum(map(len, spec_names.values()))} specialization options.")
    if not spec_names:
        raise RuntimeError("No specialization names were found; refusing to publish an empty specialization database.")

if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
