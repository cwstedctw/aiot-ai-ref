# ============================================
# webui.py — UNO Q 開一個網頁：ESP32 的資料儀表板＋用 ESP32 當搖桿的小遊戲
# ============================================
# UNO Q 在這裡同時做三件事：
#   1. 跟 ESP32 講話（WiFi 或藍牙，用的是 link_wifi.py／link_ble.py，跟 brain.py 同一套）
#   2. 當網頁伺服器：教室機瀏覽器開 http://192.168.7.2:8088 就看得到
#   3. 把 ESP32 來的資料「推」給瀏覽器（Server-Sent Events：伺服器一有新資料就往瀏覽器送）
#
# 例子：
#   python3 webui.py --link wifi --esp 192.168.4.1          儀表板資料最完整（溫溼度、光線、旋鈕、燈）
#   python3 webui.py --link ble  --name maker-A1B2          ESP32 的 A 鍵可以當遊戲搖桿
#   python3 webui.py --link ble-sim --esp 127.0.0.1:8090    沒有板子：假的 ESP32 網頁上的 A 鍵當搖桿
#
# 跟 brain.py 二選一跑（藍牙一次只能有一條連線）。這支不跑 rules.py。
# 只用 Python 內建模組。停止：Ctrl+C（會把 ESP32 的燈關掉）。
# ============================================

import argparse
import asyncio
import json
import os
import queue
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
T0 = time.time()

# ---- 伺服器跟瀏覽器之間的「廣播站」：每個開著的網頁一個信箱 ----
clients = []                # 每個瀏覽器分頁一個 queue.Queue
clients_lock = threading.Lock()
state = {"hello": None, "sensors": None}


def now():
    return round(time.time() - T0, 2)


def publish(evt):
    """把一則事件送給所有開著的網頁（任何執行緒都可以呼叫）"""
    if evt.get("type") in ("hello", "sensors"):
        state[evt["type"]] = evt
    with clients_lock:
        for q in clients:
            q.put(evt)


# ---- 網頁伺服器（跑在另一條執行緒）----
class Handler(BaseHTTPRequestHandler):
    loop = None             # 主程式的 asyncio 迴圈
    fx_queue = None         # 網頁要 ESP32 做的回饋（start／score／over）

    def log_message(self, *a):
        pass

    def send_json(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/":
            with open(os.path.join(HERE, "webui.html"), "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        elif u.path == "/events":
            self.serve_events()
        elif u.path == "/fx":
            name = parse_qs(u.query).get("name", [""])[0]
            if name in ("start", "score", "over"):
                self.loop.call_soon_threadsafe(self.fx_queue.put_nowait, name)
                self.send_json({"ok": True})
            else:
                self.send_json({"ok": False, "error": "name 要是 start、score 或 over"}, 400)
        elif u.path == "/api/state":
            out = dict(state["sensors"] or {})
            if state["hello"]:
                out["link"], out["has"] = state["hello"]["link"], state["hello"]["has"]
            self.send_json(out)
        else:
            self.send_json({"error": "not found"}, 404)

    def serve_events(self):
        """Server-Sent Events：這條連線不關，有新事件就寫一行 data: {...}"""
        q = queue.Queue()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        for first in (state["hello"], state["sensors"]):     # 新來的網頁先補上目前的狀況
            if first:
                q.put(first)
        with clients_lock:
            clients.append(q)
        try:
            while True:
                try:
                    evt = q.get(timeout=10)
                    self.wfile.write(("data: " + json.dumps(evt, ensure_ascii=False) + "\n\n").encode())
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")           # 沒事也喊一聲，瀏覽器才知道還連著
                self.wfile.flush()
        except OSError:
            pass                                              # 網頁關掉了
        finally:
            with clients_lock:
                if q in clients:
                    clients.remove(q)


# ---- 跟 ESP32 講話（跑在主執行緒的 asyncio）----
def make_link(a):
    if a.link == "wifi":
        from link_wifi import WifiLink
        return WifiLink(a.esp), a.esp
    if a.link == "ble":
        from link_ble import BleLink
        return BleLink(a.name), a.name
    from link_ble import SimBleLink
    return SimBleLink(a.esp), a.esp


async def run(a):
    link, target = make_link(a)
    wifi = link.kind == "wifi"
    has = {"temp": True, "hum": True, "light": wifi, "knob": wifi, "leds": wifi, "button": not wifi}
    publish({"type": "hello", "link": link.kind, "target": target, "has": has})

    lock = asyncio.Lock()                 # 一次只跟 ESP32 講一件事，免得兩句話的回答搞混
    fx_queue = asyncio.Queue()
    game = {"playing": False, "quiet_until": 0.0}
    # 藍牙線量一次溫溼度，ESP32 要忙大約 0.3 秒（那段時間它看不到按鍵），所以不要量太勤
    period = a.period if wifi else max(a.period, 2.0)
    Handler.loop, Handler.fx_queue = asyncio.get_running_loop(), fx_queue

    # A 鍵按下：ESP32 一通知就立刻轉給網頁（不等下一輪）
    link.on_button = lambda: publish({"type": "button", "down": True, "t": now()})

    try:
        srv = ThreadingHTTPServer(("0.0.0.0", a.port), Handler)
    except OSError:
        print("埠 {} 已經有人在用：是不是前一個 webui.py 還沒關？關掉它，或加 --port 換一個埠。".format(a.port))
        return
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print("網頁開好了：教室機瀏覽器開 http://192.168.7.2:{}（在板子自己上面是 http://127.0.0.1:{}）".format(a.port, a.port))

    async def read_loop():
        connected = False
        while True:
            t0 = time.time()
            try:
                if not connected:
                    async with lock:
                        print(await link.connect())
                    connected = True
                # 遊戲進行中（還有剛撞到的那幾秒），藍牙線先不量溫溼度：ESP32 忙著量的時候會漏掉按鍵
                busy_playing = game["playing"] or time.time() < game["quiet_until"]
                if not (busy_playing and not wifi):
                    async with lock:
                        s, rtt = await link.read()
                    evt = {"type": "sensors", "t": now(), "ok": True, "rtt_ms": round(rtt, 1),
                           "temp": s["temp"], "hum": s["hum"], "light": s["light"], "knob": s["knob"],
                           "red": None, "yellow": None, "green": None, "rgb": None, "requests": None}
                    st = getattr(link, "last_status", None)
                    if st:                                    # WiFi 線：d10 的 JSON 裡還有燈的狀態
                        evt.update(red=st.get("red"), yellow=st.get("yellow"), green=st.get("blue"),
                                   rgb=st.get("rgb"), requests=st.get("requests"))
                    publish(evt)
            except Exception as e:
                publish({"type": "sensors", "t": now(), "ok": False, "error": str(e) or type(e).__name__})
                print("{} ESP32 沒回應：{}".format(time.strftime("%H:%M:%S"), e or type(e).__name__))
                if not connected:
                    await asyncio.sleep(2)
            await asyncio.sleep(max(0.05, period - (time.time() - t0)))

    async def fx_loop():
        """網頁說「開始／得分／撞到」→ 叫 ESP32 用燈和蜂鳴器回應（搖桿的「震動回饋」）"""
        while True:
            name = await fx_queue.get()
            sent = True
            try:
                async with lock:
                    if name == "start":
                        game["playing"] = True
                        await link.send("red", False)
                        await link.send("green", True)
                    elif name == "score":
                        await link.send("rgb", (0, 80, 255))
                        await asyncio.sleep(0.12)
                        await link.send("rgb", (0, 0, 0))
                    elif name == "over":
                        game["playing"] = False
                        game["quiet_until"] = time.time() + 6      # 讓「再按一下重來」那一下不會被量溫度擋到
                        await link.send("green", False)
                        await link.send("red", True)
                        await link.send("beep")
            except Exception as e:
                sent = False
                if name == "over":
                    game["playing"] = False
                print("{} 回饋 {} 沒送到：{}".format(time.strftime("%H:%M:%S"), name, e or type(e).__name__))
            publish({"type": "fx", "name": name, "sent": sent})

    async def sim_button_loop():
        """模擬藍牙沒有真的「通知」，只好很快地一直去問假板子：A 鍵有沒有被按"""
        while True:
            try:
                if not lock.locked():
                    await link.poll_button()
            except Exception:
                pass
            await asyncio.sleep(0.05)

    tasks = [asyncio.create_task(read_loop()), asyncio.create_task(fx_loop())]
    if link.kind == "ble-sim":
        tasks.append(asyncio.create_task(sim_button_loop()))
    try:
        await asyncio.gather(*tasks)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        for t in tasks:
            t.cancel()
        try:
            await asyncio.wait_for(link.send("off"), timeout=5)
        except Exception:
            print("⚠️ 關燈指令沒送到（ESP32 可能還亮著燈）")
        try:
            await link.close()
        except Exception:
            pass
        print("\n網頁關了。", flush=True)
        os._exit(0)          # 還開著的瀏覽器分頁會讓伺服器收不乾淨，這裡直接結束程式


def main():
    ap = argparse.ArgumentParser(description="UNO Q 網頁：ESP32 儀表板＋搖桿小遊戲")
    ap.add_argument("--link", choices=["wifi", "ble", "ble-sim"], default="wifi")
    ap.add_argument("--esp", default="192.168.4.1", help="wifi／ble-sim：ESP32 的 IP（可加 :port）")
    ap.add_argument("--name", default="", help="ble：ESP32 的藍牙名字，OLED 第二行那個 maker-XXXX")
    ap.add_argument("--port", type=int, default=8088, help="網頁開在哪個埠（預設 8088）")
    ap.add_argument("--period", type=float, default=1.0, help="幾秒讀一次 ESP32（預設 1）")
    a = ap.parse_args()
    if a.link == "ble" and not a.name:
        ap.error("--link ble 要加 --name maker-XXXX（看 ESP32 的 OLED）")
    try:
        asyncio.run(run(a))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
