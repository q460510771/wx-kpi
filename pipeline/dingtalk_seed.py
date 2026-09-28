# -*- coding: utf-8 -*-
"""One-off: seed dingtalk_msgs.jsonl from the manual verification snapshot.

Reads pipeline/dingtalk_msgs_钉钉WMS接口对接_20260901_20260928.json (saved during
the 2026-09-28 verification pass) and appends each message to the JSONL store
in the same shape produced by dingtalk_fetch.py. Safe to re-run: dedupes by
messageId against existing JSONL content.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "dingtalk_msgs_钉钉WMS接口对接_20260901_20260928.json")
DST = os.path.join(HERE, "dingtalk_msgs.jsonl")


def load_seen():
    seen = set()
    if not os.path.exists(DST):
        return seen
    with open(DST, encoding="utf-8") as f:
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


def main():
    with open(SRC, encoding="utf-8") as f:
        blob = json.load(f)
    group_name = blob["group"]
    cid = blob["openConversationId"]
    seen = load_seen()
    added = 0
    with open(DST, "a", encoding="utf-8") as f:
        for m in blob["messages"]:
            mid = m.get("mid")
            if not mid or mid in seen:
                continue
            seen.add(mid)
            quoted = m.get("quoted")
            q = None
            if quoted:
                q = {
                    "sender": quoted.get("sender"),
                    "text": quoted.get("text"),
                    "createTime": None,
                    "messageId": None,
                }
            rec = {
                "messageId": mid,
                "cid": cid,
                "group": group_name,
                "ts": m.get("ts"),
                "sender": m.get("sender"),
                "senderId": None,
                "text": m.get("text") or "",
                "has_image": bool(m.get("has_image")),
                "quoted": q,
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            added += 1
    print("seed: appended %d msgs, store total %d" % (added, len(seen)))


if __name__ == "__main__":
    main()
