# -*- coding: utf-8 -*-
"""Build WeChat group KPI dashboard data + single-file HTML.
Sources: SiverWXbot memory JSON (3 roots) + manually transcribed screenshot supplement.
"""
import json, os, collections, datetime, html, sys

ROOTS = [
    r"D:\SiverWXbot_v4.7.32\guber2zyy",
    r"D:\SiverWXbot_v4.7.32\wxid_v19el76zachv22",
    r"D:\SiverWXbot_v4.7.32\memory\guber2zyy",
]
HERE = os.path.dirname(os.path.abspath(__file__))
SUPP = os.path.join(HERE, "supplement.json")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "outputs")

TRACK = {
    "陈景斯": ["陈景斯", "陈景斯-运维-华友"],
    "郝天琪": ["郝天琪", "郝天琪-产品-华友", "Jenny"],
    "何昕怡": ["何昕怡", "吃颗团团儿"],
    "张康宁": ["张康宁", "🌱康师৩ི傅🍀"],
    "史敦兵": ["史敦兵", "顶着阳光越过雨"],
}
ALIAS2PERSON = {}
for p, als in TRACK.items():
    for a in als:
        ALIAS2PERSON[a] = p

ISSUE_KW = ["麻烦", "辛苦", "帮我", "处理", "看下", "看看", "联不上", "打不开", "进不去",
            "无法", "不了", "什么原因", "怎么办", "怎么", "安排", "加一下", "检查", "试试"]
RESOLVE_AUTHOR_KW = ["好了", "可以了", "解决了", "正常了", "收到", "谢谢", "行了", "好的",
                     "上去了", "搞定", "没问题", "知道了"]
RESOLVE_RESP_KW = ["已处理", "已开通", "已维护", "解决了", "修好了", "加完了", "推送了",
                   "调整了", "已修复", "处理好了", "可以了", "好了"]
ONTIME_MIN = 30
RESP_WINDOW_H = 8
RESOLVE_WINDOW_H = 4


def norm_ts(ts):
    if not ts:
        return ts
    return ts.replace("/", "-")


def person_of(sender):
    if sender in ALIAS2PERSON:
        return ALIAS2PERSON[sender]
    for a, p in ALIAS2PERSON.items():
        if sender and (sender.startswith(a) or a in sender):
            return p
    return None


def load():
    msgs = []
    seen = set()

    def add(group, ts, sender, content, mtype, src):
        ts = norm_ts(ts)
        if not ts or len(ts) < 10:
            return
        key = (group, ts[:10], sender, content)
        if key in seen:
            return
        seen.add(key)
        msgs.append({"ts": ts, "date": ts[:10], "group": group, "sender": sender,
                     "content": content, "type": mtype, "src": src,
                     "person": person_of(sender)})

    for root in ROOTS:
        for dp, dn, fns in os.walk(root):
            for fn in fns:
                if not fn.endswith(".json"):
                    continue
                g = os.path.basename(dp)
                with open(os.path.join(dp, fn), encoding="utf-8") as f:
                    arr = json.load(f)
                for m in arr:
                    if m.get("attr") == "system" or m.get("type") == "time":
                        continue
                    sender = m.get("sender")
                    if sender == "self":
                        sender = "self(机器人/本人)"
                    add(g, m.get("time", ""), sender, m.get("content", ""), m.get("type", ""), "json")
    with open(SUPP, encoding="utf-8") as f:
        supp = json.load(f)
    for g, ts, sender, content, mtype in supp:
        add(g, ts, sender, content, mtype, "screenshot")

    msgs.sort(key=lambda m: m["ts"])
    return msgs


ACK_WORDS = ["好的", "谢谢", "收到", "辛苦", "明白了", "知道了", "行了", "嗯", "ok", "OK", "好嘞", "收到收到"]


def is_ack(content):
    s = content or ""
    for a in ALIAS2PERSON:
        s = s.replace("@" + a, "")
    s = s.replace(" ", "").strip()
    if not s or len(s) > 10:
        return False
    return any(w in s for w in ACK_WORDS)


def mentions_in(content):
    out = []
    for a, p in ALIAS2PERSON.items():
        if ("@" + a) in content and p not in out:
            out.append(p)
    return out


def analyze(msgs):
    by_group = collections.defaultdict(list)
    for m in msgs:
        by_group[m["group"]].append(m)

    issues = []
    for g, stream in by_group.items():
        for i, m in enumerate(stream):
            content = m["content"] or ""
            targets = [p for p in mentions_in(content) if p != m["person"]]
            if is_ack(content):
                continue
            is_q = ("?" in content) or ("？" in content) or any(k in content for k in ISSUE_KW)
            if not targets and not (m["person"] is None and is_q):
                continue
            if m["type"] in ("image", "file", "video", "emotion") and not targets:
                continue
            t0 = datetime.datetime.strptime(m["ts"], "%Y-%m-%d %H:%M:%S")
            responder, resp_min, jresp = None, None, None
            for j in range(i + 1, len(stream)):
                mj = stream[j]
                tj = datetime.datetime.strptime(mj["ts"], "%Y-%m-%d %H:%M:%S")
                if (tj - t0).total_seconds() > RESP_WINDOW_H * 3600:
                    break
                if targets:
                    if mj["person"] in targets:
                        responder, jresp = mj["person"], j
                        break
                else:
                    if mj["person"]:
                        responder, jresp = mj["person"], j
                        break
            if responder:
                tj = datetime.datetime.strptime(stream[jresp]["ts"], "%Y-%m-%d %H:%M:%S")
                resp_min = round((tj - t0).total_seconds() / 60.0, 1)
            # resolution
            resolved = False
            if responder and jresp is not None:
                t_r = datetime.datetime.strptime(stream[jresp]["ts"], "%Y-%m-%d %H:%M:%S")
                for k in range(jresp, min(jresp + 9, len(stream))):
                    mk = stream[k]
                    tk = datetime.datetime.strptime(mk["ts"], "%Y-%m-%d %H:%M:%S")
                    if (tk - t_r).total_seconds() > RESOLVE_WINDOW_H * 3600:
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


def aggregate(msgs, issues):
    days = sorted({m["date"] for m in msgs})
    people = list(TRACK.keys())

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
            if it["resp_min"] <= ONTIME_MIN:
                d["ontime"] += 1

    pd_out = {}
    for (p, d), v in per_pd.items():
        pd_out[f"{p}|{d}"] = {
            "msgs": v["msgs"], "resp": v["resp"], "resolved": v["resolved"],
            "unresolved": v["unresolved"],
            "avg_rt": round(sum(v["rt"]) / len(v["rt"]), 1) if v["rt"] else None,
            "ontime": v["ontime"],
        }
    return {"days": days, "people": people, "per_pd": pd_out, "issues": issues,
            "track": TRACK}


def main():
    os.makedirs(OUT, exist_ok=True)
    msgs = load()
    issues = analyze(msgs)
    agg = aggregate(msgs, issues)
    data = {
        "generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "total_msgs": len(msgs),
        "total_issues": len(issues),
        "ontime_min": ONTIME_MIN,
        **agg,
    }
    with open(os.path.join(OUT, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("msgs", len(msgs), "issues", len(issues), "days", len(agg["days"]))
    print("day range", agg["days"][0], "->", agg["days"][-1])
    # quick sanity: per person totals
    tot = collections.Counter()
    for k, v in agg["per_pd"].items():
        p = k.split("|")[0]
        tot[p] += v["msgs"]
    print(dict(tot))


if __name__ == "__main__":
    main()
