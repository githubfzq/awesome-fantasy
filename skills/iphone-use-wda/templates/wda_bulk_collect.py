#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WDA 直连批量采集引擎模板 v2（青藤之恋 2026-10-31 实战验证版）
v2 修正: W3C pointer tap / base64 截图 / session 前缀 / 内容聚簇卡片识别 /
Table-cell QA 解析 / 深滚动+逐屏截图 / 动态tab / dupkey 防重(索引式重试)
复制后按目标 APP 修改: 列宽阈值 / KNOWN_QUESTIONS / SECTION_HEADERS / 星座省份表
用法: probe / collect [N] / status
"""
import json, os, re, sys, time, datetime, urllib.request, subprocess, hashlib

WDA = "http://localhost:18100"
BASE = os.path.expanduser("~/.hermes/cache/qingteng")
PROF = os.path.join(BASE, "profiles")
STATE_F = os.path.join(BASE, "state.json")
TARGET = 3000
os.makedirs(PROF, exist_ok=True)

# ---------- WDA 基础 ----------
_SID = None
def session_id():
    global _SID
    if _SID is None:
        d = wda("POST", "/session", {"capabilities": {}})
        _SID = d["value"]["sessionId"]
    return _SID

def wda(method, endpoint, payload=None, timeout=25):
    if endpoint.split("?")[0] in ("/source", "/screenshot", "/status", "/session"):
        url = WDA + endpoint
    else:
        url = f"{WDA}/session/{session_id()}{endpoint}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    return json.load(urllib.request.urlopen(req, timeout=timeout))

def get_tree():
    d = json.load(urllib.request.urlopen(WDA + "/source?format=json&excluded_attributes=isReady", timeout=25))
    return d.get("value", d)

FRAME_RE = re.compile(r"\{\{([-\d.]+),\s*([-\d.]+)\},\s*\{([-\d.]+),\s*([-\d.]+)\}\}")

def parse_frame(s):
    if not s: return None
    m = FRAME_RE.search(str(s))
    if not m: return None
    return {"x": float(m.group(1)), "y": float(m.group(2)),
            "width": float(m.group(3)), "height": float(m.group(4))}

def all_nodes(t):
    out = []
    def walk(n):
        if isinstance(n, dict):
            out.append(n)
            for c in n.get("children") or []:
                walk(c)
    walk(t)
    return out

def node_rect(n):
    r = n.get("rect")
    if isinstance(r, dict) and "width" in r: return r
    return parse_frame(n.get("frame") or n.get("nativeFrame"))

def visible(n):
    return n.get("isVisible") in (True, 1, "1", None)

def screenshot(path):
    import base64
    d = json.load(urllib.request.urlopen(WDA + "/screenshot", timeout=25))
    with open(path, "wb") as f:
        f.write(base64.b64decode(d.get("value", "")))
    return path

def do_tap(x, y):
    wda("POST", "/actions", {"actions": [{
        "type": "pointer", "id": "qt-finger",
        "parameters": {"pointerType": "touch"},
        "actions": [
            {"type": "pointerMove", "duration": 0, "origin": "viewport", "x": x, "y": y},
            {"type": "pointerDown", "button": 0},
            {"type": "pause", "duration": 50},
            {"type": "pointerUp", "button": 0},
        ]}]})

def do_drag(x1, y1, x2, y2, dur=0.35):
    wda("POST", "/wda/dragfromtoforduration",
        {"fromX": x1, "fromY": y1, "toX": x2, "toY": y2, "duration": dur})

def tree_signature(t):
    labels = []
    def walk(n):
        if isinstance(n, dict):
            lb = n.get("label") or n.get("name") or ""
            if lb: labels.append(lb)
            for c in n.get("children") or []:
                walk(c)
    walk(t)
    return hashlib.md5("|".join(labels).encode()).hexdigest()[:12]

# ---------- 状态 ----------
def load_state():
    if os.path.exists(STATE_F):
        return json.load(open(STATE_F))
    return {"seen": [], "order": [], "dupkeys": [], "target": TARGET, "bottom": False, "fails": 0}

def save_state(s):
    tmp = STATE_F + ".tmp"
    json.dump(s, open(tmp, "w"), ensure_ascii=False, indent=1)
    os.replace(tmp, STATE_F)

# ---------- 卡片识别: 内容聚簇（无业务 ID 的画廊） ----------
def find_card_clusters(t, list_viewport_top=60, list_viewport_bottom=845, col_split=190):
    texts = []
    for n in all_nodes(t):
        lb = (n.get("label") or "").strip()
        if not lb or not visible(n) or n.get("type") != "StaticText": continue
        r = node_rect(n)
        if not r or r["height"] > 24 or r["width"] > 200: continue
        if not (list_viewport_top <= r["y"] <= list_viewport_bottom): continue
        if any(k in lb for k in ("小纸条", "最后更新", "你喜欢了", "表达心意", "配对率", "back")): continue
        texts.append((r["y"], r["x"], lb))
    texts.sort(key=lambda a: (a[0], a[1]))
    clusters = []
    for y, x, lb in texts:
        col = "L" if x < col_split else "R"
        placed = False
        for c in clusters:
            if c["col"] == col and abs(c["ys"][-1] - y) < 32:
                c["ys"].append(y); c["labels"].append(lb); placed = True; break
        if not placed:
            clusters.append({"col": col, "ys": [y], "labels": [lb]})
    out = []
    for c in clusters:
        if len(c["ys"]) < 2: continue
        top_y = min(c["ys"])
        sig = hashlib.md5(("|".join(sorted(set(c["labels"])))).encode()).hexdigest()[:10]
        tap_x = 92 if c["col"] == "L" else 290
        out.append({"sig": sig, "tap_x": tap_x, "tap_y": max(list_viewport_top, top_y - 60),
                    "info_y": top_y, "labels": sorted(set(c["labels"]))})
    out.sort(key=lambda c: (c["info_y"], c["tap_x"]))
    return out

# ---------- 详情页: Table-cell 解析（QA key-value） ----------
SECTION_HEADERS = ["自我介绍", "我的标签", "更多资料", "我的认证", "性格测试", "IP所属地",
                   "向往的恋爱", "MBTI类型", "动态", "关于我"]
KNOWN_QUESTIONS = ["向往的恋爱", "我最近爱听音乐/歌手是", "下一个旅行目的地", "期待的相处模式",
                   "选择伴侣最看重", "最近在追的综艺/剧", "喜欢的运动", "喜欢的电影/书籍",
                   "周末最喜欢做什么", "家乡最推荐", "最想去的地方", "自己的三个关键词",
                   "想去哪里旅行", "近期的小目标", "最离不开的一样东西", "星座"]
ZODIAC = {"白羊座","金牛座","双子座","巨蟹座","狮子座","处女座","天秤座","天蝎座",
          "射手座","摩羯座","水瓶座","双鱼座"}
NOISE = {"back", "profile nav more", "profile note action btn", "notes operation",
         "bottom action btn note", "揭秘你们的合拍度", "水平滚动条, 1页", "亮点"}
AUTH_BADGES = {"头像", "实名", "学历", "婚况"}
MBTI_RE = re.compile(r"^[IE][NS][FT][JP]·")
PROVINCES = ["北京","天津","河北","山西","内蒙古","辽宁","吉林","黑龙江","上海","江苏",
             "浙江","安徽","福建","江西","山东","河南","湖北","湖南","广东","广西","海南",
             "重庆","四川","贵州","云南","西藏","陕西","甘肃","青海","宁夏","新疆","香港","澳门","台湾"]

def _flatten(n, out):
    if isinstance(n, dict):
        lb = (n.get("label") or "").strip()
        if lb and lb not in NOISE: out.append(lb)
        for c in n.get("children") or []: _flatten(c, out)
    return out

def find_table(t):
    for n in all_nodes(t):
        if n.get("type") == "Table" and n.get("children"): return n
    return None

def is_question(s):
    if any(k in s for k in KNOWN_QUESTIONS): return True
    return s.endswith(("？", "?", "是…"))

def parse_cells(t):
    base = {"nickname": "", "base_row": [], "highlight": "", "auth": [], "ip": ""}
    sections, qa = {}, []
    items = []  # 平铺: 头部用
    for n in all_nodes(t):
        lb = (n.get("label") or "").strip()
        if not lb or lb in NOISE or n.get("type") not in ("StaticText", "Button"): continue
        r = node_rect(n) or {}
        items.append({"y": r.get("y", 0), "x": r.get("x", 0), "w": r.get("width", 0), "t": lb, "ty": n.get("type")})
    items.sort(key=lambda a: (a["y"], a["x"]))
    for it in items:
        y, lb = it["y"], it["t"]
        if 140 < y < 260 and it["ty"] == "StaticText" and it["w"] >= 80 and not base["nickname"]:
            base["nickname"] = lb
        elif 190 < y < 260 and it["ty"] == "StaticText" and it["w"] < 80 and lb not in base["base_row"]:
            base["base_row"].append(lb)
    for i, it in enumerate(items):
        if it["t"] == "亮点" and i + 1 < len(items):
            base["highlight"] = items[i + 1]["t"]; break
    for h in (it["t"] for it in items if 294 <= it["y"] <= 315):
        if h in ZODIAC: base["zodiac"] = h
        elif MBTI_RE.match(h): base["mbti"] = h
        elif h in AUTH_BADGES and h not in base["auth"]: base["auth"].append(h)
    tab = find_table(t)
    cells = []
    if tab:
        for ch in tab.get("children") or []:
            labs = list(dict.fromkeys(_flatten(ch, [])))
            if labs: cells.append(labs)
    for i, labs in enumerate(cells):
        if "IP所属地" in labs:
            for v in (cells[i + 1] if i + 1 < len(cells) else []) + labs:
                if v in PROVINCES: base["ip"] = v; break
            for v in labs:
                if v in AUTH_BADGES and v not in base["auth"]: base["auth"].append(v)
    cur = None
    for labs in cells:
        head = next((l for l in labs if l in SECTION_HEADERS), None)
        if head:
            cur = head
            rest = [l for l in labs if l != head]
            if head == "自我介绍":
                sections["自我介绍"] = ["\n".join(rest)] if rest else []
            elif head in ("我的标签", "更多资料"):
                sections.setdefault(head, [])
                sections[head] += [l for l in rest if l not in sections[head]]
            elif head == "我的认证":
                for l in rest:
                    if l not in base["auth"]: base["auth"].append(l)
            elif is_question(head):
                qa.append({"q": head, "a": " ".join(l for l in rest if not is_question(l))})
            else:
                sections.setdefault(head, [])
                sections[head] += rest
        else:
            if len(labs) == 2 and is_question(labs[0]):
                qa.append({"q": labs[0], "a": labs[1]})
            elif len(labs) == 1 and labs[0] in PROVINCES and not base["ip"]:
                base["ip"] = labs[0]
            elif cur:
                sections.setdefault(cur, [])
                sections[cur] += [l for l in labs if l not in sections[cur]]
    # 清理: 已结构化值不再重复出现
    struct_vals = set(x for x in (base.get("zodiac"), base.get("mbti"), base.get("ip")) if x)
    struct_vals |= set(base["auth"])
    qa = [p for p in qa if p["q"] not in ("MBTI类型", "IP所属地", "星座", "性格测试")]
    for p in qa:
        p["a"] = " ".join(w for w in p["a"].split()
                          if w not in struct_vals and not MBTI_RE.match(w) and w not in ZODIAC)
    for k in ("IP所属地", "MBTI类型", "性格测试", "我的认证"):
        sections.pop(k, None)
    for k in list(sections):
        sections[k] = [x for x in sections[k] if x not in struct_vals]
    sections = {k: v for k, v in sections.items() if v}
    return base, sections, qa, len(cells)

def extract_profile(t):
    base, sections, qa, ncells = parse_cells(t)
    return {"nickname": base["nickname"], "base_row": base["base_row"],
            "highlight": base.get("highlight", ""), "auth": base["auth"],
            "ip": base["ip"], "zodiac": base.get("zodiac", ""), "mbti": base.get("mbti", ""),
            "sections": sections, "qa": qa, "n_cells": ncells,
            "captured_at": datetime.datetime.now().isoformat(timespec="seconds")}

# ---------- 页面判定 ----------
LIST_MARKER = "MyLikeView"      # 换成目标 App 列表页 NavigationBar name
PROFILE_MARKER = "ProfileContainer"

def is_list_page(t): return LIST_MARKER in json.dumps(t, ensure_ascii=False)

def is_profile_page(t):
    s = json.dumps(t, ensure_ascii=False)
    return PROFILE_MARKER in s or (PROFILE_MARKER not in s and LIST_MARKER not in s
        and any((n.get("label") or "") == "back" for n in all_nodes(t)) and len(all_nodes(t)) > 40)

def ensure_list_page(timeout=12):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            if is_list_page(get_tree()): return True
        except Exception: pass
        back_to_list(); time.sleep(1)
    try: return is_list_page(get_tree())
    except Exception: return False

def back_to_list(timeout=10):
    for _ in range(3):
        try: t = get_tree()
        except Exception: time.sleep(1); continue
        if is_list_page(t): time.sleep(0.8); return True
        btn = None
        for n in all_nodes(t):
            if (n.get("label") or "") == "back":
                r = node_rect(n)
                if r: btn = r; break
        if btn: do_tap(btn["x"] + btn["width"]/2, btn["y"] + btn["height"]/2)
        else: do_drag(4, 420, 320, 420, 0.3)
        t0 = time.time()
        while time.time() - t0 < 5:
            time.sleep(1.0)
            try:
                if is_list_page(get_tree()): time.sleep(0.8); return True
            except Exception: pass
    return False

def wait_profile(sig, timeout=10):
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(1.0)
        try:
            t = get_tree()
            if is_profile_page(t) and tree_signature(t) != sig:
                time.sleep(0.8); return get_tree()
        except Exception: continue
    return None

# ---------- 深滚动 + 动态 tab ----------
def collect_moments():
    try:
        tab_btn = None
        for n in all_nodes(get_tree()):
            if (n.get("label") or "") == "动态":
                r = node_rect(n)
                if r and r.get("width", 99) > 20: tab_btn = r; break
        if not tab_btn: return []
        do_tap(tab_btn["x"] + tab_btn["width"]/2, tab_btn["y"] + tab_btn["height"]/2)
        time.sleep(2.0)
        texts, last_sig, stable = [], None, 0
        for _ in range(6):
            t2 = get_tree()
            sig = tree_signature(t2)
            if sig == last_sig:
                stable += 1
                if stable >= 2: break
            else: stable = 0
            last_sig = sig
            do_drag(196, 660, 196, 260, 0.4); time.sleep(1.2)
        for n in all_nodes(get_tree()):
            if (n.get("label") or "") == "关于我":
                r = node_rect(n)
                if r:
                    do_tap(r["x"] + r["width"]/2, r["y"] + r["height"]/2); break
        time.sleep(1.2)
        return texts
    except Exception as e:
        print(f"[warn] moments fail: {e}", flush=True)
        return []

def harvest_profile(idx, safe_name):
    prof = {"idx": idx}
    t1 = get_tree()
    p1 = extract_profile(t1)
    img1 = os.path.join(PROF, f"{idx:04d}_{safe_name}_a.jpg")
    try: screenshot(img1)
    except Exception as e: img1 = f"fail:{e}"
    seen_set = set()
    for n in all_nodes(t1):
        lb = (n.get("label") or "").strip()
        if lb: seen_set.add(lb)
    scroll_texts, scroll_shots, last_sig, stable = [], [], None, 0
    for s in range(14):
        try: do_drag(196, 660, 196, 200, 0.45)
        except Exception: pass
        time.sleep(1.3)
        try: t2 = get_tree()
        except Exception: continue
        for n in all_nodes(t2):
            lb = (n.get("label") or "").strip()
            if lb and lb not in seen_set:
                seen_set.add(lb); scroll_texts.append(lb)
        img = os.path.join(PROF, f"{idx:04d}_{safe_name}_s{s}.jpg")
        try: screenshot(img); scroll_shots.append(img)
        except Exception: pass
        sig = tree_signature(t2)
        if sig == last_sig:
            stable += 1
            if stable >= 2: break
        else: stable = 0
        last_sig = sig
    if scroll_texts:
        p1["sections"].setdefault("滚动补充", [])
        p1["sections"]["滚动补充"] += [x for x in scroll_texts if x not in p1["sections"]["滚动补充"]]
    moments = collect_moments()
    img2 = ""
    try:
        screenshot(img := os.path.join(PROF, f"{idx:04d}_{safe_name}_b.jpg")); img2 = img
    except Exception: pass
    prof.update({
        **{k: p1[k] for k in ("nickname", "base_row", "highlight", "auth", "ip",
                               "zodiac", "mbti", "sections", "qa", "n_cells")},
        "moments": moments,
        "shots": [str(img1)] + [str(x) for x in scroll_shots] + ([str(img2)] if img2 else []),
        "captured_at": p1["captured_at"],
    })
    json.dump(prof, open(os.path.join(PROF, f"{idx:04d}_{safe_name}.json"), "w"),
              ensure_ascii=False, indent=1)
    return prof

# ---------- 主循环 ----------
def collect(limit):
    st = load_state()
    print(f"[start] 已采 {len(st['order'])}, 目标 {st['target']}, 本次上限 {limit}", flush=True)
    done = empty_rounds = 0
    while done < limit and len(st["order"]) < st["target"] and not st["bottom"]:
        try: t = get_tree()
        except Exception as e:
            print(f"[warn] tree error: {e}", flush=True); time.sleep(3); continue
        clusters = find_card_clusters(t)
        fresh = [c for c in clusters if c["sig"] not in st["seen"]]
        if not fresh:
            empty_rounds += 1
            if empty_rounds >= 6:
                st["bottom"] = True; save_state(st)
                print("[done] 连续6轮无新卡，到底了", flush=True); break
            try: do_drag(196, 640, 196, 640 - 434, 0.4)
            except Exception as e:
                print(f"[warn] scroll error: {e}", flush=True); time.sleep(3); continue
            time.sleep(1.4); continue
        empty_rounds = 0
        fi = 0
        while fi < len(fresh):
            c = fresh[fi]
            retried_this = False
            while True:  # 同卡最多试2次: 重复页重试一次
                if done >= limit or len(st["order"]) >= st["target"]: break
                if not ensure_list_page():
                    print("[fatal] 不在列表页且无法恢复", flush=True)
                    save_state(st); return
                sig_before = tree_signature(get_tree())
                try: do_tap(c["tap_x"], c["tap_y"])
                except Exception as e:
                    print(f"[warn] tap error: {e}", flush=True); time.sleep(2); break
                pt = wait_profile(sig_before)
                if pt is None:
                    st["seen"].append(c["sig"]); st["fails"] += 1
                    back_to_list(); save_state(st); break
                idx = len(st["order"]) + 1
                try:
                    prof = harvest_profile(idx, f"u{idx}")
                    nick = prof.get("nickname") or ""
                    intro = ""
                    for v in prof.get("sections", {}).values():
                        if v: intro = v[0][:50]; break
                    feat = "|".join((prof.get("base_row") or [])[:3])
                    dupkey = nick + "||" + intro + "||" + feat
                    if dupkey in st.get("dupkeys", []):
                        if not retried_this:
                            retried_this = True
                            print(f"[dup] #{idx} {nick} 疑似重复, 重试此卡", flush=True)
                            ensure_list_page(); time.sleep(1.5); save_state(st)
                            continue
                        st["fails"] += 1
                        st["seen"].append(c["sig"]); ensure_list_page(); save_state(st)
                        print(f"[dup] #{idx} {nick} 重试仍重复, 放弃", flush=True)
                        break
                    st.setdefault("dupkeys", []).append(dupkey)
                    st["seen"].append(c["sig"])
                    st["order"].append({"idx": idx, "sig": c["sig"], "nick": nick,
                                        "ip": prof.get("ip", ""), "labels": c["labels"]})
                    done += 1
                    print(f"#{idx} OK {nick} IP={prof.get('ip','?')} qa={len(prof.get('qa', []))}", flush=True)
                except Exception as e:
                    print(f"[err] harvest #{idx}: {e}", flush=True)
                    st["fails"] += 1; back_to_list(); save_state(st); break
                save_state(st)
                if not ensure_list_page():
                    print("[fatal] 返回列表失败", flush=True)
                    save_state(st); return
                time.sleep(0.6)
                break
            fi += 1
    save_state(st)
    print(f"[end] 本次 +{done}, 总计 {len(st['order'])}/{st['target']} bottom={st['bottom']} fails={st['fails']}", flush=True)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "probe":
        t = get_tree()
        cs = find_card_clusters(t)
        print(f"clusters={len(cs)}")
        for c in cs:
            print(f"  y={c['info_y']:.0f} tap=({c['tap_x']},{c['tap_y']}) sig={c['sig']} {c['labels']}")
    elif cmd == "collect":
        collect(int(sys.argv[2]) if len(sys.argv) > 2 else 999999)
    elif cmd == "status":
        st = load_state()
        print(f"collected={len(st['order'])} target={st['target']} bottom={st['bottom']} fails={st['fails']}")
        for o in st["order"][-5:]:
            print(f"  #{o['idx']} {o['nick']} {o.get('ip','')}")
