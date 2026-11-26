# ============================================
# link_wifi.py — WiFi 這條線：UNO Q 用 HTTP 跟 ESP32 講話
# ============================================
# ESP32 跑的是創客課第 10 課 d10_wifi_web.py（不用改），它開了這幾個網址：
#   GET /api/status                    → 回一段 JSON：溫度、濕度、光線、旋鈕、三顆燈的狀態
#   GET /api/led?name=red&on=1         → 紅燈開（name 可以是 red／yellow／blue）
#   GET /api/rgb?r=255&g=0&b=0         → 彩色燈
#   GET /api/beep                      → 嗶一聲
#   GET /api/off                       → 全部關
# ⚠️ d10 裡第三顆燈的名字叫 blue，但它在板子上其實是「綠燈」（GPIO 13）。
#
# 只用 Python 內建的 urllib，UNO Q 上不用另外裝套件。
# ============================================

import json
import time
import urllib.request

LED_NAME = {"red": "red", "yellow": "yellow", "green": "blue"}   # 我們說 green，d10 叫它 blue


def current_wifi():
    """問 Linux：UNO Q 現在連的是哪個 WiFi？（不是 Linux 或問不到就回空字串）
    ESP32 輪流用的時候很重要：UNO Q 會記得上一塊板子，可能自己連回鄰座那一塊。"""
    import subprocess
    try:
        # 問 wlan0 這張網卡現在用的是哪一筆連線（名字就是 WiFi 名稱；這樣問不用重新掃描，很快）
        out = subprocess.run(["nmcli", "-t", "-f", "GENERAL.CONNECTION", "device", "show", "wlan0"],
                             capture_output=True, text=True, timeout=5).stdout
        for line in out.splitlines():
            name = line.partition(":")[2].strip()
            if name and name != "--":
                return name
    except Exception:
        pass
    return ""


class WifiLink:
    kind = "wifi"

    def __init__(self, host, timeout=3.0):
        self.base = "http://" + host
        self.timeout = timeout
        self.last_rtt_ms = None

    def _get(self, path):
        t0 = time.perf_counter()
        with urllib.request.urlopen(self.base + path, timeout=self.timeout) as r:
            body = r.read()
        self.last_rtt_ms = (time.perf_counter() - t0) * 1000
        return json.loads(body)

    async def connect(self):
        try:
            st = self._get("/api/status")      # 先問一次，確定找得到板子
        except OSError as e:
            ap = current_wifi()
            now = "UNO Q 現在連的 WiFi 是 {}".format(ap) if ap else "UNO Q 現在沒有連任何 WiFi"
            raise RuntimeError("{}（{}）。要連真的 ESP32，先連它的 WiFi（XXXX 換成 ESP32 的 OLED 上那四個字）：\n"
                               "  nmcli device wifi connect maker-XXXX password makerXXXX".format(e, now))
        ap = current_wifi()
        self.ap_at_start = ap                  # 記住一開始連的是哪一塊，之後斷線接回來要比對
        where = "；UNO Q 現在連的 WiFi 是 {}——跟你手上 ESP32 的 OLED 一樣嗎？".format(ap) if ap else ""
        return "WiFi 連上 {}（回應 {:.0f} ms）{}".format(self.base, self.last_rtt_ms, where)

    async def read(self):
        st = self._get("/api/status")
        self.last_status = st                  # 整包 JSON 留著（webui.py 的儀表板要看燈的狀態）
        sensors = {
            "temp": st.get("temp"),
            "hum": st.get("hum"),
            "light": st.get("light"),
            "knob": st.get("knob"),
            "button": None,                    # d10 的 JSON 裡沒有按鈕，WiFi 這條線讀不到
        }
        return sensors, self.last_rtt_ms

    async def send(self, action, value=None):
        """action：'red'／'yellow'／'green'（value＝True/False）、'rgb'（value＝(r,g,b)）、'beep'、'off'"""
        if action in LED_NAME:
            self._get("/api/led?name={}&on={}".format(LED_NAME[action], 1 if value else 0))
        elif action == "rgb":
            r, g, b = value
            self._get("/api/rgb?r={}&g={}&b={}".format(r, g, b))
        elif action == "beep":
            self._get("/api/beep")
        elif action == "off":
            self._get("/api/off")

    def where(self):
        """斷線又接回來之後，讓大腦再說一次現在連的是哪一塊（可能已經換了一塊）"""
        ap = current_wifi()
        return "UNO Q 現在連的 WiFi 是 {}——跟你手上 ESP32 的 OLED 一樣嗎？".format(ap) if ap else ""

    def moved(self):
        """UNO Q 是不是自己跳到「另一個」WiFi 了？是就回傳新的名字（沒有就回空字串）"""
        ap, start = current_wifi(), getattr(self, "ap_at_start", "")
        return ap if (ap and start and ap != start) else ""

    async def close(self):
        pass
