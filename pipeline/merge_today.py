# -*- coding: utf-8 -*-
"""merge_today.py — append cron-fetched DingTalk messages into the JSONL store
and write a success marker that push_daily.bat checks before publishing.

Designed to be run by the QwenWork 17:50 cron AFTER the agent has saved each
group's normalized messages to pipeline/raw_today/g1.json .. g6.json (one JSON
array per file, in the same order as dingtalk_config.json "groups").

Each record in gN.json is expected to already be normalized by the dws --jq
projection to: {messageId, ts, sender, senderId, text, has_image, quoted}.
This script injects cid/group, dedups by messageId against the store, appends
new records, and stamps pipeline/dingtalk_fetch_state.json with a marker:

    {"today": "YYYY-MM-DD", "ok": true, "fetched_at": "...",
     "fetch_date": "YYYY-MM-DD", "total_new": N, "total_stored": M,
     "per_group": [{"group","raw","new"}...]}

Exit codes:
    0 — all 6 group files present & parsed; marker ok=true written.
    1 — any group file missing/unparseable; marker ok=false written (publish gated off).

Usage:
    python merge_today.py                # fetch_date = today (local)
    python merge_today.py --date 2026-09-30
"""
import argparse
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CFG_PATH = os.path.join(HERE, "dingtalk_config.json")
JSONL_PATH = os.path.join(HERE, "dingtalk_msgs.jsonl")
STATE_PATH = os.path.join(HERE, "dingtalk_fetch_state.json")
RAW_DIR = os.path.join(HERE, "raw_today")


def load_cfg():
    with open(CFG_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_seen():
    seen = set()
    if not os.path.exists(JSONL_PATH):
        return seen
    with open(JSONL_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                mid = rec.get("messageId")
                if mid:
                    seen.add(mid)
            except json.JSONDecodeError:
                continue
    return seen


def load_state():
    if not os.path.exists(STATE_PATH):
        return {}
    with open(STATE_PATH, encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def save_state(state):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)


def write_marker(ok, fetch_date, per_group, total_new, total_stored, reason=""):
    state = load_state()
    marker = {
        "today": fetch_date,
        "fetch_date": fetch_date,
        "ok": ok,
        "fetched_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_new": total_new,
        "total_stored": total_stored,
        "per_group": per_group,
    }
    if reason:
        marker["reason"] = reason
    state["last_marker"] = marker
    # keep a short history of markers for observability
    hist = state.get("marker_history") or []
    state["marker_history"] = (hist[-30:] + [marker])
    save_state(state)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="YYYY-MM-DD the fetch covers (default: today)")
    args = ap.parse_args()
    fetch_date = args.date or datetime.date.today().isoformat()

    cfg = load_cfg()
    groups = cfg["groups"]
    seen = load_seen()

    per_group = []
    fresh_records = []
    fatal = None

    for idx, g in enumerate(groups, start=1):
        name, cid = g["name"], g["cid"]
        path = os.path.join(RAW_DIR, "g%d.json" % idx)
        if not os.path.exists(path):
            fatal = "missing raw file g%d.json (%s)" % (idx, name)
            per_group.append({"group": name, "raw": 0, "new": 0, "error": "missing_file"})
            continue
        try:
            with open(path, encoding="utf-8") as f:
                payload = json.load(f)
        except Exception as e:
            fatal = "unparseable g%d.json (%s): %s" % (idx, name, e)
            per_group.append({"group": name, "raw": 0, "new": 0, "error": "parse_error"})
            continue
        msgs = payload if isinstance(payload, list) else (payload.get("messages") or [])
        n_new = 0
        for m in msgs:
            mid = m.get("messageId")
            if not mid or mid in seen:
                continue
            seen.add(mid)
            rec = {
                "messageId": mid,
                "cid": cid,
                "group": name,
                "ts": m.get("ts") or m.get("createTime"),
                "sender": m.get("sender"),
                "senderId": m.get("senderId"),
                "text": m.get("text") or "",
                "has_image": bool(m.get("has_image")) or bool(m.get("resourceRefs"))
                              or ("[图片消息]" in (m.get("text") or "")),
                "quoted": m.get("quoted"),
            }
            fresh_records.append(rec)
            n_new += 1
        per_group.append({"group": name, "raw": len(msgs), "new": n_new})

    if fatal:
        # Do NOT touch the store; write a failure marker so publish is gated off.
        write_marker(False, fetch_date, per_group, 0, len(seen), reason=fatal)
        print("merge_today FAILED: %s" % fatal)
        return 1

    # Append fresh records atomically-ish (single open in append mode).
    if fresh_records:
        with open(JSONL_PATH, "a", encoding="utf-8") as f:
            for r in fresh_records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    write_marker(True, fetch_date, per_group, len(fresh_records), len(seen))
    print("merge_today OK: date=%s appended=%d total_stored=%d"
          % (fetch_date, len(fresh_records), len(seen)))
    for pg in per_group:
        print("  [%s] raw=%s new=%s%s"
              % (pg["group"], pg.get("raw"), pg.get("new"),
                 (" error=" + pg["error"]) if pg.get("error") else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
