import os
import math
import random
import re
from collections import deque
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

GAME_HISTORIES = {
    "betvip_tx": deque(maxlen=300),
    "betvip_md5": deque(maxlen=300),
    "lc79_tx": deque(maxlen=300),
    "lc79_md5": deque(maxlen=300),
    "lc79_xd": deque(maxlen=300),
    "sunwin_sicbo": deque(maxlen=300)
}

SYSTEM_KEYS = {
    "hungcaliadmin": {"role": "admin", "name": "Hưng Đẹp Trai", "status": "Active"},
    "nhatchimbe": {"role": "guest", "name": "Khách VIP", "status": "Active"}
}

def get_id(item):
    if isinstance(item, dict):
        for k in ['id', 'phien', 'sessionId', 'sid', 'referenceId', 'matchId', 'turnNum']:
            if k in item and str(item[k]).replace('-', '').isdigit():
                return int(item[k])
    matches = re.findall(r"'?(?:id|phien|referenceId|sessionId|matchId|turnNum)'?\s*:\s*'?'?(\d+)'?'?", str(item), re.IGNORECASE)
    return int(matches[0]) if matches else 0

def simple_predict(history, md5_str=None):
    if len(history) < 8:
        return "TÀI", 55.0, "Đang thu thập dữ liệu..."
    
    t_count = history.count("T")
    x_count = history.count("X")
    ty_le_t = t_count / len(history)
    
    if md5_str and re.match(r"^[0-9a-f]{32}$", md5_str.lower()):
        tong = sum(int(c, 16) for c in md5_str)
        return ("TÀI" if tong % 2 == 0 else "XỈU"), round(65 + (tong % 15), 1), "PHÂN TÍCH MD5"
    
    if ty_le_t > 0.65:
        res, conf = "XỈU", round(55 + ty_le_t * 20, 1)
    elif ty_le_t < 0.35:
        res, conf = "TÀI", round(55 + (1 - ty_le_t) * 20, 1)
    else:
        res, conf = ("TÀI" if random.random() > 0.5 else "XỈU"), round(52 + random.uniform(0, 10), 1)
    
    return res, max(52.0, min(90.0, conf)), "PHÂN TÍCH LỊCH SỬ"

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json or {}
    key = data.get("key", "").strip()
    if key in SYSTEM_KEYS:
        return jsonify({"status": "success", "info": SYSTEM_KEYS[key]})
    return jsonify({"status": "error", "msg": "Mã khóa không hợp lệ!"})

@app.route("/api/scan", methods=["POST"])
def scan():
    data = request.json or {}
    tool = data.get("tool", "")
    is_chanle = "chanle" in tool.lower() or "xd" in tool.lower()
    
    urls = {
        "betvip_tx": "https://wtx.macminim6.online/v1/tx/sessions",
        "betvip_md5": "https://wtxmd52.macminim6.online/v1/txmd5/sessions",
        "lc79_tx": "https://wtx.tele68.com/v1/tx/sessions",
        "lc79_md5": "https://wtxmd52.tele68.com/v1/txmd5/sessions",
        "lc79_xd": "https://wcl.tele68.com/v1/chanlefull/sessions",
        "sunwin_sicbo": "https://api.wsktnus8.net/v2/history/getLastResult?gameId=ktrng_3979&size=100&tableId=39791215743193&curPage=1"
    }
    
    if tool not in urls:
        return jsonify({"status": "error", "msg": "Không tìm thấy máy chủ"})
    
    try:
        res = requests.get(urls[tool], timeout=10, headers={"User-Agent": "AI-SIMPLE"}).json()
        lst = res.get("data", res.get("list", res)) if isinstance(res, dict) else res
        if not isinstance(lst, list):
            raise ValueError("Sai dữ liệu")
        
        lst = sorted(lst, key=get_id)
        arr = []
        for item in lst:
            text = str(item).upper()
            t_key = ["CHẴN", "CHAN", "C", "0"] if is_chanle else ["TAI", "TÀI", "BIG"]
            arr.append("T" if any(k in text for k in t_key) else "X")
        
        GAME_HISTORIES[tool].extend(arr)
        next_id = get_id(lst[-1]) + 1
        md5_found = re.search(r"[0-9a-f]{32}", str(lst[-1]).lower())
        md5_str = md5_found.group(0) if md5_found and "md5" in tool else None
        
        pred, conf, method = simple_predict(list(GAME_HISTORIES[tool]), md5_str)
        if is_chanle:
            pred = "CHẴN" if pred == "TÀI" else "LẺ"
        
        return jsonify({
            "status": "success",
            "data": {
                "phien": f"#{next_id}",
                "du_doan": pred,
                "tin_cay": conf,
                "phuong_phap": method
            }
        })
        
    except Exception:
        return jsonify({
            "status": "success",
            "data": {
                "phien": "#" + str(random.randint(100000, 999999)),
                "du_doan": "TÀI" if random.random() > 0.5 else "XỈU",
                "tin_cay": round(random.uniform(60, 80), 1),
                "phuong_phap": "HỆ THỐNG DỰ PHÒNG"
            }
        })

@app.route("/")
def index():
    return send_file("index.html")

application = app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
    
