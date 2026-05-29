#!/usr/bin/env python3
"""One-time backfill for legacy game records (logged before normal/hakem kot
tracking and before per-hand logging).

For every live record in data/*.json that lacks a kot breakdown:
  * Split its kots into normal (+2) and hakem (+3). ~30% of each team's kots are
    assumed to have been hakem-kots. To avoid rounding every single-kot record
    down to zero, the hakem share is computed at the per-team TOTAL level and then
    distributed across records greedily.
  * Backfill hands_count, reconstructed from the final score and kots:
    hands = (red + blue) - total_kots - hakem_kots   (<= 13 for one game to 7).

Idempotent: records that already carry kots_hakem/kots_normal are left untouched.

Usage:
  python3 scripts/migrate_legacy_kots.py            # dry-run, prints a diff
  python3 scripts/migrate_legacy_kots.py --apply    # writes changes (backs up first)
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

HAKEM_RATIO = 0.3
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def round_half_up(x: float) -> int:
    return int(x + 0.5)


def is_legacy(rec: dict) -> bool:
    return (
        not rec.get("imported")
        and rec.get("kots_normal") is None
        and rec.get("kots_hakem") is None
    )


def migrate_state(state: dict) -> list[str]:
    """Mutate state in place. Return human-readable change lines."""
    legacy = [r for r in state.get("history", []) if is_legacy(r)]
    if not legacy:
        return []

    # Per-team hakem target across all legacy records (keeps the 30% honest).
    target = {"red": 0, "blue": 0}
    for team in ("red", "blue"):
        total = sum(int(r.get("kots", {}).get(team, 0)) for r in legacy)
        target[team] = round_half_up(total * HAKEM_RATIO)

    remaining = dict(target)
    changes: list[str] = []
    for r in legacy:
        kots = {t: int(r.get("kots", {}).get(t, 0)) for t in ("red", "blue")}
        hakem = {}
        for team in ("red", "blue"):
            take = min(remaining[team], kots[team])
            hakem[team] = take
            remaining[team] -= take
        normal = {t: kots[t] - hakem[t] for t in ("red", "blue")}

        fs = r.get("final_score", {})
        points = int(fs.get("red", 0)) + int(fs.get("blue", 0))
        total_kots = kots["red"] + kots["blue"]
        hands = max(0, points - total_kots - (hakem["red"] + hakem["blue"]))

        r["kots_normal"] = normal
        r["kots_hakem"] = hakem
        r["hands_count"] = hands
        changes.append(
            f"  {r.get('game_day')} score={fs.get('red')}-{fs.get('blue')} "
            f"kots={kots['red']}/{kots['blue']} -> normal={normal['red']}/{normal['blue']} "
            f"hakem={hakem['red']}/{hakem['blue']} hands={hands}"
        )
    return changes


def main() -> None:
    apply = "--apply" in sys.argv
    files = sorted(DATA_DIR.glob("*.json"))
    if not files:
        print(f"no data files in {DATA_DIR}")
        return
    for f in files:
        state = json.loads(f.read_text(encoding="utf-8"))
        changes = migrate_state(state)
        print(f"=== {f.name} === legacy records migrated: {len(changes)}")
        for line in changes:
            print(line)
        if changes and apply:
            backup = f.with_suffix(f".json.premigrate.{int(time.time())}")
            shutil.copy2(f, backup)
            f.write_text(
                json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"  -> written (backup: {backup.name})")
    if not apply:
        print("\n(dry-run) re-run with --apply to write changes")


if __name__ == "__main__":
    main()
