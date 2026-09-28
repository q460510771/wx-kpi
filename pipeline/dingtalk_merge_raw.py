# -*- coding: utf-8 -*-
"""Merge raw `dws chat +chat-messages` JSON exports into dingtalk_msgs.jsonl.

Usage:
  python dingtalk_merge_raw.py raw_huafei.json raw_wms.json raw_cheliang.json

Each input file must be a full dws response object with a `messages` array
(schema: im.message-list.v1). Records are normalized to the same shape
produced by dingtalk_fetch.py and deduped against existing JSONL content by
messageId. Safe to re-run.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
JSONL_PATH = os.path.join(HERE, "dingtalk_msgs.jsonl")
CFG_PATH = os.path.join(HERE, "dingtalk_config.json")


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


def normalize(msg, group_name, cid):
    quoted = msg.get("quotedMessage") or None
    q = None
    if quoted:
        q = {
            "sender": quoted.get("sender"),
            "text": quoted.get("text"),
            "createTime": quoted.get("createTime"),
            "messageId": quoted.get("messageId"),
        }
    text = msg.get("text") or ""
    has_image = bool(msg.get("resourceRefs")) or "[图片消息]" in text
    return {
        "messageId": msg.get("messageId"),
        "cid": cid,
        "group": group_name,
        "ts": msg.get("createTime"),
        "sender": msg.get("sender"),
        "senderId": msg.get("senderId"),
        "text": text,
        "has_image": has_image,
        "quoted": q,
    }


def main():
    if len(sys.argv) < 2:
        print("usage: dingtalk_merge_raw.py <raw1.json> [raw2.json ...]")
        return 1
    cfg = load_cfg()
    cid2name = {g["cid"]: g["name"] for g in cfg["groups"]}
    seen = load_seen()
    total_new = 0
    per_file = []
    with open(JSONL_PATH, "a", encoding="utf-8") as out:
        for path in sys.argv[1:]:
            p = path if os.path.isabs(path) else os.path.join(HERE, path)
            with open(p, encoding="utf-8") as f:
                blob = json.load(f)
            msgs = blob.get("messages") or []
            added = 0
            skipped_no_cid = 0
            for m in msgs:
                cid = m.get("conversationId")
                mid = m.get("messageId")
                if not cid or not mid:
                    skipped_no_cid += 1
                    continue
                if mid in seen:
                    continue
                group_name = cid2name.get(cid) or cid
                seen.add(mid)
                out.write(json.dumps(normalize(m, group_name, cid), ensure_ascii=False) + "\n")
                added += 1
            total_new += added
            per_file.append({"file": os.path.basename(p), "raw": len(msgs), "new": added,
                             "skipped": skipped_no_cid})
            print("  %s: raw=%d new=%d skipped=%d" %
                  (os.path.basename(p), len(msgs), added, skipped_no_cid))
    print("merge_raw: appended %d msgs, store total %d" % (total_new, len(seen)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
