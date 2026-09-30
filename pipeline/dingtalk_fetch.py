# -*- coding: utf-8 -*-
"""Fetch DingTalk group messages via `dws` CLI, append to JSONL store.

Usage:
  python dingtalk_fetch.py                     # fetch today (local)
  python dingtalk_fetch.py --date 2026-09-28   # fetch a specific day
  python dingtalk_fetch.py --start 2026-09-01 --end 2026-09-28  # backfill range

Storage: pipeline/dingtalk_msgs.jsonl (one JSON per line, deduped by messageId).
Config:  pipeline/dingtalk_config.json (groups + track list + windows).
"""
import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CFG_PATH = os.path.join(HERE, "dingtalk_config.json")
JSONL_PATH = os.path.join(HERE, "dingtalk_msgs.jsonl")
STATE_PATH = os.path.join(HERE, "dingtalk_fetch_state.json")


def load_cfg():
    with open(CFG_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_seen_ids():
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


def find_dws():
    """Locate the dws executable (Windows .cmd or POSIX shell script)."""
    for name in ("dws.cmd", "dws.bat", "dws.exe", "dws"):
        p = shutil.which(name)
        if p:
            return p
    # Fallback to known install location
    default = r"C:\Users\guber\.qwenworkcn\bin\dws.cmd"
    if os.path.exists(default):
        return default
    raise RuntimeError("dws CLI not found on PATH")


def fetch_group(dws_exe, cid, start_iso, end_iso, timeout=300):
    """Run `dws chat +chat-messages` and return list of message dicts."""
    cmd = [
        dws_exe, "chat", "+chat-messages",
        "--group", cid,
        "--start", start_iso,
        "--end", end_iso,
        "--page-all",
        "--no-reactions",
        "--format", "json",
    ]
    proc = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=timeout, shell=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "dws exited %d\nstderr: %s\nstdout(head): %s"
            % (proc.returncode, (proc.stderr or "")[:500], (proc.stdout or "")[:500])
        )
    out = (proc.stdout or "").strip()
    if not out:
        return []
    try:
        payload = json.loads(out)
    except json.JSONDecodeError as e:
        raise RuntimeError("dws returned non-JSON: %s (head: %s)" % (e, out[:200]))
    return payload.get("messages") or []


def normalize(msg, group_name, cid):
    """Project a raw DWS message into the compact schema we persist."""
    quoted = msg.get("quotedMessage") or None
    q = None
    if quoted:
        q = {
            "sender": quoted.get("sender"),
            "text": quoted.get("text"),
            "createTime": quoted.get("createTime"),
            "messageId": quoted.get("messageId"),
        }
    has_image = bool(msg.get("resourceRefs")) or "[图片消息]" in (msg.get("text") or "")
    return {
        "messageId": msg.get("messageId"),
        "cid": cid,
        "group": group_name,
        "ts": msg.get("createTime"),
        "sender": msg.get("sender"),
        "senderId": msg.get("senderId"),
        "text": msg.get("text") or "",
        "has_image": has_image,
        "quoted": q,
    }


def append_jsonl(records):
    if not records:
        return 0
    with open(JSONL_PATH, "a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(records)


def save_state(state):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)


def load_state():
    if not os.path.exists(STATE_PATH):
        return {}
    with open(STATE_PATH, encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="YYYY-MM-DD; fetch that single day")
    ap.add_argument("--start", help="YYYY-MM-DD; range start (inclusive)")
    ap.add_argument("--end", help="YYYY-MM-DD; range end (inclusive)")
    args = ap.parse_args()

    today = datetime.date.today()
    if args.date:
        d0 = d1 = datetime.date.fromisoformat(args.date)
    elif args.start or args.end:
        d0 = datetime.date.fromisoformat(args.start or args.end)
        d1 = datetime.date.fromisoformat(args.end or args.start)
    else:
        d0 = d1 = today

    tz = "+08:00"
    start_iso = "%sT00:00:00%s" % (d0.isoformat(), tz)
    end_iso = "%sT23:59:59%s" % (d1.isoformat(), tz)

    cfg = load_cfg()
    dws_exe = find_dws()
    seen = load_seen_ids()
    state = load_state()

    print("dingtalk_fetch: range %s -> %s, groups=%d, existing=%d msgs"
          % (d0, d1, len(cfg["groups"]), len(seen)))

    total_new = 0
    fatal_errors = []
    per_group = []
    for g in cfg["groups"]:
        name, cid = g["name"], g["cid"]
        try:
            raw = fetch_group(dws_exe, cid, start_iso, end_iso)
        except Exception as e:
            # A dws failure (e.g. headless run without a QwenWork session) is a
            # HARD failure: propagate a non-zero exit so callers do not publish
            # stale data. Zero new messages on a successful call is NOT a failure.
            print("  [%s] FETCH FAILED: %s" % (name, e))
            per_group.append({"group": name, "raw": 0, "new": 0, "error": str(e)[:200]})
            fatal_errors.append("%s: %s" % (name, str(e)[:120]))
            continue
        fresh = []
        for m in raw:
            mid = m.get("messageId")
            if not mid or mid in seen:
                continue
            seen.add(mid)
            fresh.append(normalize(m, name, cid))
        n = append_jsonl(fresh)
        total_new += n
        per_group.append({"group": name, "raw": len(raw), "new": n})
        print("  [%s] raw=%d new=%d" % (name, len(raw), n))

    state["last_run"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    state["last_range"] = [d0.isoformat(), d1.isoformat()]
    state["last_new"] = total_new
    state["total_stored"] = len(seen)
    state["history"] = (state.get("history") or [])[-30:] + [{
        "run": state["last_run"], "range": state["last_range"],
        "new": total_new, "per_group": per_group,
    }]
    save_state(state)
    print("dingtalk_fetch: appended %d new msgs, store total %d"
          % (total_new, len(seen)))
    if fatal_errors:
        print("dingtalk_fetch: FAILED %d/%d group(s): %s"
              % (len(fatal_errors), len(cfg["groups"]), " | ".join(fatal_errors)))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
