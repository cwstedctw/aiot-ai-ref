# ============================================
# fake_esp32.py — 假的 ESP32（沒有板子也能練）
# ============================================
# 在電腦或 UNO Q 上跑一個「假裝是 ESP32」的小伺服器：
#   - 網址跟創客課第 10 課 d10_wifi_web.py 一模一樣（/api/status、/api/led…），
#     所以 brain.py 不用改一個字，就能把假板子當真板子用。
#   - 另外多兩個「模擬專用」的網址（真的 ESP32 沒有）：
#       /sim/ble?cmd=temp   用 d11 的文字指令格式回話，模擬藍牙那條線
#       /sim/set?temp=30    網頁上的拉桿用來改假感測值
#   - 瀏覽器打開 http://127.0.0.1:8090 就看得到一塊「虛擬 EZ 板」：
#     燈有沒有亮、彩色燈什麼顏色、有沒有嗶，還有拉桿可以調溫度、光線、旋鈕，A 鍵可以按。
#
# 用法：python3 fake_esp32.py            （預設 port 8090）
#       python3 fake_esp32.py --port 8091
# 只用 Python 內建模組。
# ============================================

import argparse
import json
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

LOCK = threading.Lock()
# 跟 d10 的 state 同樣的欄位（d10 的第三顆燈叫 blue，實際是綠燈）
state = {
    "red": False, "yellow": False, "blue": False,
    "rgb": [0, 0, 0],
    "temp": 26, "hum": 60,
    "light": 2400, "knob": 2200,
    "last": "",
    "requests": 0,
}
base = {"temp": 26, "hum": 60, "light": 2400, "knob": 2200}   # 拉桿設定的值
sim = {"beep_at": 0.0, "button": 0, "log": []}


def log(who, what):
    sim["log"].insert(0, "{} {:<4} {}".format(time.strftime("%H:%M:%S"), who, what))
    del sim["log"][20:]


def read_sensors():
    """像 d10 一樣讀感測器：DHT11 只給整數，光線和旋鈕會有一點點抖動"""
    state["temp"] = int(round(base["temp"] + random.uniform(-0.4, 0.4)))
    state["hum"] = int(round(base["hum"] + random.uniform(-1, 1)))
    state["light"] = max(0, min(4095, int(base["light"] + random.uniform(-25, 25))))
    state["knob"] = max(0, min(4095, int(base["knob"] + random.uniform(-8, 8))))


def ble_reply(text):
    """照 d11_ble_remote.py 的 run_command() 回話（文字格式一樣）"""
    words = text.strip().lower().split()
    if not words:
        return ""
    cmd = words[0]
    pins = {"red": "red", "yellow": "yellow", "green": "blue", "blue": "blue"}
    if cmd in pins and len(words) > 1:
        state[pins[cmd]] = words[1] == "on"
        return "OK " + cmd + " " + words[1]
    if cmd == "rgb" and len(words) == 4:
        state["rgb"] = [max(0, min(255, int(v))) for v in words[1:]]
        return "OK rgb"
    if cmd == "beep":
        sim["beep_at"] = time.time()
        return "OK beep"
    if cmd == "off":
        for k in ("red", "yellow", "blue"):
            state[k] = False
        state["rgb"] = [0, 0, 0]
        return "OK all off"
    if cmd == "temp":
        read_sensors()
        return "temp {} C, hum {} %".format(state["temp"], state["hum"])
    return "? try: red on / green on / rgb 255 0 0 / beep / off / temp"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):          # 不要每個請求都印一行
        pass

    def send(self, body, ctype="application/json", status=200):
        if isinstance(body, str):
            body = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        route = u.path
        args = {k: v[0] for k, v in parse_qs(u.query).items()}
        with LOCK:
            # ---- 跟 d10 一樣的網址 ----
            if route == "/api/status":
                state["requests"] += 1
                read_sensors()
                log("wifi", "GET /api/status")
                return self.send(json.dumps(state))
            if route == "/api/led" and args.get("name") in ("red", "yellow", "blue"):
                state["requests"] += 1
                state[args["name"]] = args.get("on") == "1"
                state["last"] = args["name"] + (" on" if state[args["name"]] else " off")
                log("wifi", "GET " + self.path)
                return self.send(json.dumps(state))
            if route == "/api/rgb":
                state["requests"] += 1
                state["rgb"] = [max(0, min(255, int(args.get(c, 0)))) for c in "rgb"]
                log("wifi", "GET " + self.path)
                return self.send(json.dumps(state))
            if route == "/api/beep":
                state["requests"] += 1
                sim["beep_at"] = time.time()
                log("wifi", "GET /api/beep")
                return self.send(json.dumps(state))
            if route == "/api/off":
                state["requests"] += 1
                for k in ("red", "yellow", "blue"):
                    state[k] = False
                state["rgb"] = [0, 0, 0]
                log("wifi", "GET /api/off")
                return self.send(json.dumps(state))
            # ---- 模擬專用（真的 ESP32 沒有）----
            if route == "/sim/ble":
                reply = ble_reply(args.get("cmd", ""))
                pressed = sim["button"]
                sim["button"] = 0
                if args.get("cmd"):                      # 空指令只是來問 A 鍵的，不記
                    log("ble", "寫入「{}」→ 通知「{}」".format(args.get("cmd", ""), reply))
                return self.send(json.dumps({"reply": reply, "pressed": pressed}))
            if route == "/sim/set":
                for k in base:
                    if k in args:
                        base[k] = float(args[k])
                return self.send(json.dumps(base))
            if route == "/sim/press":
                sim["button"] = 1
                log("板子", "有人按了 A 鍵")
                return self.send('{"ok":true}')
            if route == "/sim/state":
                out = dict(state, base=base, beeping=time.time() - sim["beep_at"] < 0.4, log=sim["log"])
                return self.send(json.dumps(out))
            if route == "/":
                return self.send(PAGE, "text/html; charset=utf-8")
        return self.send('{"error":"not found"}', status=404)


PAGE = """<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>假的 ESP32</title>
<style>
:root{--bg:#f6f5f1;--card:#fff;--ink:#1d1f23;--mute:#6b6f76;--line:#dcdad3}
@media (prefers-color-scheme:dark){:root{--bg:#15171a;--card:#1f2226;--ink:#ecebe7;--mute:#9a9ea5;--line:#33363b}}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,"Noto Sans TC",sans-serif}
main{max-width:720px;margin:0 auto;padding:16px}
h1{font-size:20px;margin:4px 0}.note{color:var(--mute);font-size:14px;margin:0 0 12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;margin-bottom:12px}
.leds{display:flex;gap:18px;align-items:center;flex-wrap:wrap}
.led{width:34px;height:34px;border-radius:50%;border:2px solid var(--line);background:#444;opacity:.35}
.led.on{opacity:1;box-shadow:0 0 14px currentColor}
.lab{font-size:13px;color:var(--mute);text-align:center}
.bz{padding:4px 10px;border-radius:6px;border:1px solid var(--line)}.bz.on{background:#f2c14e;color:#000}
label{display:block;margin:8px 0 2px}input[type=range]{width:100%}
button{font:inherit;padding:8px 14px;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--ink)}
pre{font:13px/1.45 ui-monospace,Consolas,monospace;white-space:pre-wrap;margin:0;max-height:260px;overflow:auto}
</style></head><body><main>
<h1>假的 ESP32（虛擬 EZ 板）</h1>
<p class="note">brain.py 連到這裡，就跟連到真的 ESP32 一樣。拉桿是「環境」，燈是大腦叫 ESP32 做的事。</p>
<div class="card"><div class="leds">
<div><div id="red" class="led" style="color:#e5484d;background:#e5484d"></div><div class="lab">紅燈</div></div>
<div><div id="yellow" class="led" style="color:#f2c14e;background:#f2c14e"></div><div class="lab">黃燈</div></div>
<div><div id="blue" class="led" style="color:#30a46c;background:#30a46c"></div><div class="lab">綠燈</div></div>
<div><div id="rgb" class="led"></div><div class="lab">彩色燈</div></div>
<div><div id="bz" class="bz">蜂鳴器</div></div>
</div></div>
<div class="card">
<label>溫度 <b id="tv"></b> °C</label><input id="temp" type="range" min="15" max="40" step="1">
<label>光線 <b id="lv"></b>（0–4095，假板子：數字小＝暗）</label><input id="light" type="range" min="0" max="4095" step="1">
<label>旋鈕 <b id="kv"></b>（0–4095）</label><input id="knob" type="range" min="0" max="4095" step="1">
<p><button id="btnA">按 A 鍵（藍牙那條線才讀得到）</button></p>
</div>
<div class="card"><b>最近收到的指令</b><pre id="log"></pre></div>
</main><script>
var first=true;
function $(i){return document.getElementById(i)}
['temp','light','knob'].forEach(function(k){$(k).addEventListener('input',function(){
  fetch('/sim/set?'+k+'='+this.value);show(k,this.value)})});
function show(k,v){({temp:$('tv'),light:$('lv'),knob:$('kv')})[k].textContent=v}
$('btnA').onclick=function(){fetch('/sim/press')};
function tick(){fetch('/sim/state').then(function(r){return r.json()}).then(function(s){
  ['red','yellow','blue'].forEach(function(k){$(k).classList.toggle('on',s[k])});
  var c=s.rgb,on=c[0]+c[1]+c[2]>0;$('rgb').classList.toggle('on',on);
  $('rgb').style.background=on?'rgb('+c.join(',')+')':'#444';$('rgb').style.color=$('rgb').style.background;
  $('bz').classList.toggle('on',s.beeping);
  if(first){['temp','light','knob'].forEach(function(k){$(k).value=s.base[k];show(k,s.base[k])});first=false}
  $('log').textContent=s.log.join('\\n')||'（還沒有人連進來）';
}).catch(function(){})}
setInterval(tick,300);tick();
</script></body></html>"""


def main():
    ap = argparse.ArgumentParser(description="假的 ESP32（d10 同樣的網址＋模擬藍牙）")
    ap.add_argument("--port", type=int, default=8090)
    ap.add_argument("--host", default="0.0.0.0", help="0.0.0.0＝同網路的電腦也連得到")
    a = ap.parse_args()
    try:
        srv = ThreadingHTTPServer((a.host, a.port), Handler)
    except OSError:
        print("埠 {} 已經有人在用：是不是前一個 fake_esp32.py 還沒關？關掉它（Ctrl+C），或加 --port 換一個埠。".format(a.port))
        return
    print("假的 ESP32 開好了：瀏覽器開 http://127.0.0.1:{}".format(a.port))
    print("（在 UNO Q 上跑的話，教室機瀏覽器要開 http://192.168.7.2:{}）".format(a.port))
    print("brain.py 這樣連：python3 brain.py --link wifi --esp 127.0.0.1:{}".format(a.port))
    print("停止：Ctrl+C")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
