# -*- coding: utf-8 -*-
"""check_fetch_marker.py — gate for push_daily.bat.

Returns exit 0 ONLY if pipeline/dingtalk_fetch_state.json contains a
last_marker with ok=true whose fetch_date == today (local). Otherwise exit 1,
which tells push_daily.bat to SKIP publishing (write PUSHOK=SKIP).

This guarantees the dashboard is only published after today's DingTalk fetch
succeeded (performed by the QwenWork 17:50 cron via dws + merge_today.py).

Usage:
    python check_fetch_marker.py            # check against today
    python check_fetch_marker.py --date 2026-09-30
"""
import argparse
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(HERE, "dingtalk_fetch_state.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="YYYY-MM-DD expected fetch_date (default: today)")
    args = ap.parse_args()
    expected = args.date or datetime.date.today().isoformat()

    if not os.path.exists(STATE_PATH):
        print("check_fetch_marker: FAIL no state file (%s)" % STATE_PATH)
        return 1
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            state = json.load(f)
    except Exception as e:
        print("check_fetch_marker: FAIL unreadable state: %s" % e)
        return 1

    marker = state.get("last_marker") or {}
    if not marker:
        print("check_fetch_marker: FAIL no last_marker in state")
        return 1
    if not marker.get("ok"):
        print("check_fetch_marker: FAIL marker ok=false reason=%s date=%s"
              % (marker.get("reason", "?"), marker.get("fetch_date", "?")))
        return 1
    if marker.get("fetch_date") != expected:
        print("check_fetch_marker: FAIL marker date %s != expected %s (fetch cron did not run today?)"
              % (marker.get("fetch_date"), expected))
        return 1

    print("check_fetch_marker: OK fetch_date=%s total_new=%s total_stored=%s fetched_at=%s"
          % (marker.get("fetch_date"), marker.get("total_new"),
             marker.get("total_stored"), marker.get("fetched_at")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
