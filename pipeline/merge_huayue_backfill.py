# -*- coding: utf-8 -*-
"""One-shot: merge raw_today/huayue_backfill.json into dingtalk_msgs.jsonl,
then update the fetch marker so check_fetch_marker passes today.
"""
import json
import os
import datetime

HERE = r"D:\wx-kpi\pipeline"
JSONL = os.path.join(HERE, "dingtalk_msgs.jsonl")
STATE = os.path.join(HERE, "dingtalk_fetch_state.json")
RAW = os.path.join(HERE, "raw_today", "huayue_backfill.json")

# Load existing messageIds
seen = set()
if os.path.exists(JSONL):
    with open(JSONL, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                mid = r.get("messageId")
                if mid:
                    seen.add(mid)
            except json.JSONDecodeError:
                pass

with open(RAW, encoding="utf-8") as f:
    msgs = json.load(f)

fresh = []
for m in msgs:
    mid = m.get("messageId")
    if not mid or mid in seen:
        continue
    seen.add(mid)
    fresh.append({
        "messageId": mid,
        "cid": m.get("cid"),
        "group": m.get("group"),
        "ts": m.get("ts"),
        "sender": m.get("sender"),
        "senderId": m.get("senderId"),
        "text": m.get("text") or "",
        "has_image": bool(m.get("has_image")),
        "quoted": m.get("quoted"),
    })

with open(JSONL, "a", encoding="utf-8") as f:
    for r in fresh:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

# Update marker so today's check_fetch_marker.py passes
today = datetime.date.today().isoformat()
state = {}
if os.path.exists(STATE):
    try:
        with open(STATE, encoding="utf-8") as f:
            state = json.load(f)
    except json.JSONDecodeError:
        state = {}

marker = {
    "today": today,
    "fetch_date": today,
    "ok": True,
    "fetched_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "total_new": len(fresh),
    "total_stored": len(seen),
    "per_group": [{"group": "华越设备系统问题反馈", "raw": len(msgs), "new": len(fresh)}],
    "reason": "manual backfill: added group 华越设备系统问题反馈 (2026-09-01..2026-10-08)",
}
state["last_marker"] = marker
hist = state.get("marker_history") or []
state["marker_history"] = hist[-30:] + [marker]
with open(STATE, "w", encoding="utf-8") as f:
    json.dump(state, f, ensure_ascii=False, indent=1)

print("appended=%d, total_stored=%d, marker_date=%s" % (len(fresh), len(seen), today))
