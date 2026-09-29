# -*- coding: utf-8 -*-
"""Build KPI dashboard data from two sources:
  1. WeChat  — SiverWXbot memory JSON (3 roots) + supplement.json (screenshot backfill)
  2. DingTalk — pipeline/dingtalk_msgs.jsonl (fetched via `dws chat +chat-messages`)

Both sources share the same issue-detection heuristic (question/@mention + response
window + resolution window), but DingTalk uses wider windows because that group
chats far less frequently, and additionally treats `quotedMessage` as a strong
response link.

Output: pipeline/data.json with shape:
  {
    "generated": "...",
    "sources": {
       "wechat":   {"total_msgs","total_issues","ontime_min","days","people","per_pd","issues","track","groups"},
       "dingtalk": { ...same fields..., "resp_window_h","resolve_window_h" }
    }
  }
"""
import collections
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "outputs")

# ---------- WeChat config (unchanged) ----------
WX_ROOTS = [
    r"D:\SiverWXbot_v4.7.32\guber2zyy",
    r"D:\SiverWXbot_v4.7.32\wxid_v19el76zachv22",
    r"D:\SiverWXbot_v4.7.32\memory\guber2zyy",
]
WX_SUPP = os.path.join(HERE, "supplement.json")
WX_TRACK = {
    "陈景斯": ["陈景斯", "陈景斯-运维-华友"],
    "郝天琪": ["郝天琪", "郝天琪-产品-华友", "Jenny"],
    "何昕怡": ["何昕怡", "吃颗团团儿"],
    "张康宁": ["张康宁", "🌱康师৩ི傅🍀"],
    "史敦兵": ["史敦兵", "顶着阳光越过雨"],
    "胡晟瑞": ["胡晟瑞", "Mmmm."],
    "刘佳琪": ["刘佳琪"],
}
WX_ONTIME_MIN = 30
WX_RESP_WINDOW_H = 8
WX_RESOLVE_WINDOW_H = 4

# ---------- DingTalk config ----------
DT_CFG_PATH = os.path.join(HERE, "dingtalk_config.json")
DT_JSONL_PATH = os.path.join(HERE, "dingtalk_msgs.jsonl")

# ---------- shared keyword rules ----------
ISSUE_KW = ["麻烦", "辛苦", "帮我", "处理", "看下", "看看", "联不上", "打不开", "进不去",
            "无法", "不了", "什么原因", "怎么办", "怎么", "安排", "加一下", "检查", "试试",
            "修复", "报错", "问题", "异常", "失败"]
RESOLVE_AUTHOR_KW = ["好了", "可以了", "解决了", "正常了", "收到", "谢谢", "行了", "好的",
                     "上去了", "搞定", "没问题", "知道了", "成功了"]
RESOLVE_RESP_KW = ["已处理", "已开通", "已维护", "解决了", "修好了", "加完了", "推送了",
                   "调整了", "已修复", "处理好了", "可以了", "好了", "已更", "更新了",
                   "已下发", "已改"]
ACK_WORDS = ["好的", "谢谢", "收到", "辛苦", "明白了", "知道了", "行了", "嗯", "ok", "OK",
             "好嘞", "收到收到"]


def build_alias_map(track):
    m = {}
    for p, aliases in track.items():
        for a in aliases:
            m[a] = p
    return m


def norm_ts(ts):
    if not ts:
        return ts
    return ts.replace("/", "-")


def make_person_of(alias_map):
    def person_of(sender):
        if not sender:
            return None
        if sender in alias_map:
            return alias_map[sender]
        for a, p in alias_map.items():
            if sender.startswith(a) or a in sender:
                return p
        return None
    return person_of


def is_ack(content, alias_map):
    s = content or ""
    for a in alias_map:
        s = s.replace("@" + a, "")
    s = s.replace(" ", "").strip()
    if not s or len(s) > 10:
        return False
    return any(w in s for w in ACK_WORDS)


def mentions_in(content, alias_map):
    out = []
    for a, p in alias_map.items():
        if ("@" + a) in content and p not in out:
            out.append(p)
    return out


def parse_ts(ts):
    return datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")


# ---------- WeChat loader ----------
def load_wechat():
    alias_map = build_alias_map(WX_TRACK)
    person_of = make_person_of(alias_map)
    msgs, seen = [], set()

    def add(group, ts, sender, content, mtype, src):
        ts = norm_ts(ts)
        if not ts or len(ts) < 10:
            return
        key = (group, ts[:10], sender, content)
        if key in seen:
            return
        seen.add(key)
        msgs.append({
            "ts": ts, "date": ts[:10], "group": group, "sender": sender,
            "content": content, "type": mtype, "src": src,
            "person": person_of(sender),
            "quoted_sender": None,
        })

    for root in WX_ROOTS:
        if not os.path.isdir(root):
            continue
        for dp, dn, fns in os.walk(root):
            for fn in fns:
                if not fn.endswith(".json"):
                    continue
                g = os.path.basename(dp)
                try:
                    with open(os.path.join(dp, fn), encoding="utf-8") as f:
                        arr = json.load(f)
                except Exception:
                    continue
                for m in arr:
                    if m.get("attr") == "system" or m.get("type") == "time":
                        continue
                    sender = m.get("sender")
                    if sender == "self":
                        sender = "self(机器人/本人)"
                    add(g, m.get("time", ""), sender, m.get("content", ""),
                        m.get("type", ""), "json")
    if os.path.exists(WX_SUPP):
        with open(WX_SUPP, encoding="utf-8") as f:
            supp = json.load(f)
        for row in supp:
            g, ts, sender, content, mtype = row
            add(g, ts, sender, content, mtype, "screenshot")

    msgs.sort(key=lambda m: m["ts"])
    return msgs


# ---------- DingTalk loader ----------
def load_dingtalk():
    if not os.path.exists(DT_CFG_PATH):
        return [], None
    with open(DT_CFG_PATH, encoding="utf-8") as f:
        cfg = json.load(f)
    alias_map = build_alias_map(cfg["track"])
    person_of = make_person_of(alias_map)
    msgs = []
    if os.path.exists(DT_JSONL_PATH):
        with open(DT_JSONL_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = norm_ts(r.get("ts") or "")
                if not ts or len(ts) < 19:
                    continue
                sender = r.get("sender")
                quoted = r.get("quoted") or {}
                msgs.append({
                    "ts": ts, "date": ts[:10], "group": r.get("group"),
                    "sender": sender, "content": r.get("text") or "",
                    "type": "image" if r.get("has_image") and not (r.get("text") or "").strip("[图片消息] ") else "text",
                    "src": "dingtalk",
                    "person": person_of(sender),
                    "quoted_sender": quoted.get("sender"),
                    "messageId": r.get("messageId"),
                })
    msgs.sort(key=lambda m: m["ts"])
    return msgs, cfg


# ---------- shared analyzer ----------
def analyze(msgs, alias_map, resp_window_h, resolve_window_h, use_quoted=False):
    """Detect issues (requests/questions) and pair them with the tracked-person
    response + resolution status.

    If use_quoted=True (DingTalk), a message that quotes a tracked person's
    earlier message is treated as a directed response even without @mention.
    """
    by_group = collections.defaultdict(list)
    for m in msgs:
        by_group[m["group"]].append(m)

    issues = []
    for g, stream in by_group.items():
        for i, m in enumerate(stream):
            content = m["content"] or ""
            targets = [p for p in mentions_in(content, alias_map) if p != m["person"]]
            if is_ack(content, alias_map):
                continue
            is_q = ("?" in content) or ("？" in content) or any(k in content for k in ISSUE_KW)
            if not targets and not (m["person"] is None and is_q):
                continue
            if m["type"] in ("image", "file", "video", "emotion") and not targets:
                continue
            try:
                t0 = parse_ts(m["ts"])
            except ValueError:
                continue
            responder, resp_min, jresp = None, None, None
            for j in range(i + 1, len(stream)):
                mj = stream[j]
                try:
                    tj = parse_ts(mj["ts"])
                except ValueError:
                    continue
                if (tj - t0).total_seconds() > resp_window_h * 3600:
                    break
                if targets:
                    if mj["person"] in targets:
                        responder, jresp = mj["person"], j
                        break
                    # DingTalk bonus: quoted reply pointing at author counts
                    if use_quoted and mj.get("quoted_sender") == m["sender"] and mj["person"]:
                        responder, jresp = mj["person"], j
                        break
                else:
                    if mj["person"]:
                        responder, jresp = mj["person"], j
                        break
            if responder and jresp is not None:
                try:
                    tj = parse_ts(stream[jresp]["ts"])
                    resp_min = round((tj - t0).total_seconds() / 60.0, 1)
                except ValueError:
                    resp_min = None
            # resolution scan
            resolved = False
            if responder and jresp is not None:
                try:
                    t_r = parse_ts(stream[jresp]["ts"])
                except ValueError:
                    t_r = None
                if t_r:
                    for k in range(jresp, min(jresp + 12, len(stream))):
                        mk = stream[k]
                        try:
                            tk = parse_ts(mk["ts"])
                        except ValueError:
                            continue
                        if (tk - t_r).total_seconds() > resolve_window_h * 3600:
                            break
                        txt = mk["content"] or ""
                        if mk["person"] == responder and any(kk in txt for kk in RESOLVE_RESP_KW):
                            resolved = True
                            break
                        if mk["sender"] == m["sender"] and any(kk in txt for kk in RESOLVE_AUTHOR_KW):
                            resolved = True
                            break
            issues.append({
                "date": m["date"], "group": g, "author": m["sender"],
                "author_person": m["person"], "targets": targets,
                "text": content, "ts": m["ts"],
                "responder": responder, "resp_min": resp_min, "resolved": resolved,
            })
    return issues


def aggregate(msgs, issues, track, ontime_min):
    days = sorted({m["date"] for m in msgs})
    people = list(track.keys())
    per_pd = collections.defaultdict(lambda: {"msgs": 0, "resp": 0, "resolved": 0,
                                              "unresolved": 0, "rt": [], "ontime": 0})
    for m in msgs:
        if m["person"]:
            per_pd[(m["person"], m["date"])]["msgs"] += 1
    for it in issues:
        r = it["responder"]
        if not r:
            continue
        d = per_pd[(r, it["date"])]
        d["resp"] += 1
        if it["resolved"]:
            d["resolved"] += 1
        else:
            d["unresolved"] += 1
        if it["resp_min"] is not None:
            d["rt"].append(it["resp_min"])
            if it["resp_min"] <= ontime_min:
                d["ontime"] += 1
    pd_out = {}
    for (p, d), v in per_pd.items():
        pd_out["%s|%s" % (p, d)] = {
            "msgs": v["msgs"], "resp": v["resp"], "resolved": v["resolved"],
            "unresolved": v["unresolved"],
            "avg_rt": round(sum(v["rt"]) / len(v["rt"]), 1) if v["rt"] else None,
            "ontime": v["ontime"],
        }
    groups = sorted({m["group"] for m in msgs if m.get("group")})
    group_msgs = collections.Counter(m["group"] for m in msgs if m.get("group"))
    group_issues = collections.Counter(i["group"] for i in issues if i.get("group"))
    group_stats = [
        {"name": g, "msgs": group_msgs.get(g, 0), "issues": group_issues.get(g, 0)}
        for g in groups
    ]
    group_stats.sort(key=lambda x: -x["msgs"])
    return {"days": days, "people": people, "per_pd": pd_out, "issues": issues,
            "track": track, "groups": groups, "group_stats": group_stats}


def summarize(tag, msgs, issues, agg):
    tot = collections.Counter()
    for k, v in agg["per_pd"].items():
        p = k.split("|")[0]
        tot[p] += v["msgs"]
    print("[%s] msgs %d issues %d days %d groups %d" %
          (tag, len(msgs), len(issues), len(agg["days"]), len(agg["groups"])))
    if agg["days"]:
        print("[%s] day range %s -> %s" % (tag, agg["days"][0], agg["days"][-1]))
    print("[%s] per-person msgs %s" % (tag, dict(tot)))


def main():
    os.makedirs(OUT, exist_ok=True)

    # --- WeChat ---
    wx_alias = build_alias_map(WX_TRACK)
    wx_msgs = load_wechat()
    wx_issues = analyze(wx_msgs, wx_alias, WX_RESP_WINDOW_H, WX_RESOLVE_WINDOW_H,
                        use_quoted=False)
    wx_agg = aggregate(wx_msgs, wx_issues, WX_TRACK, WX_ONTIME_MIN)
    summarize("wechat", wx_msgs, wx_issues, wx_agg)

    # --- DingTalk ---
    dt_msgs, dt_cfg = load_dingtalk()
    if dt_cfg is None:
        dt_cfg = {"track": WX_TRACK, "ontime_min": WX_ONTIME_MIN,
                  "resp_window_h": 24, "resolve_window_h": 12}
    dt_alias = build_alias_map(dt_cfg["track"])
    dt_issues = analyze(dt_msgs, dt_alias,
                        dt_cfg.get("resp_window_h", 24),
                        dt_cfg.get("resolve_window_h", 12),
                        use_quoted=True)
    dt_agg = aggregate(dt_msgs, dt_issues, dt_cfg["track"],
                       dt_cfg.get("ontime_min", WX_ONTIME_MIN))
    summarize("dingtalk", dt_msgs, dt_issues, dt_agg)

    data = {
        "generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "sources": {
            "wechat": {
                "label": "微信群",
                "total_msgs": len(wx_msgs),
                "total_issues": len(wx_issues),
                "ontime_min": WX_ONTIME_MIN,
                "resp_window_h": WX_RESP_WINDOW_H,
                "resolve_window_h": WX_RESOLVE_WINDOW_H,
                **wx_agg,
            },
            "dingtalk": {
                "label": "钉钉群",
                "total_msgs": len(dt_msgs),
                "total_issues": len(dt_issues),
                "ontime_min": dt_cfg.get("ontime_min", WX_ONTIME_MIN),
                "resp_window_h": dt_cfg.get("resp_window_h", 24),
                "resolve_window_h": dt_cfg.get("resolve_window_h", 12),
                **dt_agg,
            },
        },
    }
    with open(os.path.join(OUT, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("wrote", os.path.join(OUT, "data.json"))


if __name__ == "__main__":
    main()
