# ============================================
# link_ble.py — 藍牙這條線：UNO Q 當「中心」去連 ESP32
# ============================================
# ESP32 跑的是創客課第 11 課 d11_ble_remote.py（不用改），它提供兩組服務：
#   文字指令服務（Nordic UART，NUS）
#     RX 6E400002-…  UNO Q「寫入」一行字：red on／green off／rgb 255 0 0／beep／off／temp
#     TX 6E400003-…  ESP32「通知」回一行字：OK red on／temp 25 C, hum 60 %
#   LED 與按鈕服務（Nordic LBS）
#     按鈕 00001524-…  ESP32 的 A 鍵按下／放開時「通知」1／0
#
# 手機 App 做得到的事，UNO Q 的 Linux 用 Python 也做得到：
# 這裡用 bleak 這個套件（透過 Linux 的 BlueZ 用板子的藍牙）；起始檔的 vendor/ 已經帶一份，UNO Q 不用安裝。
# 藍牙這條線讀不到光線和旋鈕（d11 沒有提供），這就是「協定決定你拿得到什麼」。
# ============================================

import asyncio
import re
import time

NUS_RX = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"   # UNO Q → ESP32（寫入）
NUS_TX = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"   # ESP32 → UNO Q（通知）
LBS_BUTTON = "00001524-1212-efde-1523-785feabcd123"  # A 鍵（通知）

TEMP_RE = re.compile(r"temp\s+(-?\d+(?:\.\d+)?)\s*C,\s*hum\s+(-?\d+(?:\.\d+)?)")


class BleLink:
    kind = "ble"

    def __init__(self, name, timeout=3.0):
        self.name = name
        self.timeout = timeout
        self.client = None
        self.lines = asyncio.Queue()    # ESP32 通知回來的每一行字
        self.pressed = False            # 上一輪之後有沒有人按過 A 鍵
        self.on_button = None           # 有人想「一按就知道」可以放一個函式在這裡（webui.py 的遊戲用）
        self.last_rtt_ms = None

    def _on_text(self, _char, data):
        for line in bytes(data).decode(errors="replace").splitlines():
            if line.strip():
                self.lines.put_nowait(line.strip())

    def _on_disconnect(self, _client):
        self.lines.put_nowait("__DISCONNECTED__")   # 叫醒正在等回話的人

    async def _ensure(self):
        """斷線了就重新掃描、重連一次（d11 斷線後會自己重新廣播）"""
        if self.client is None or not self.client.is_connected:
            print("藍牙斷線了，重新連線…")
            print(await self.connect())
            # ESP32 可能重開過、燈都滅了：這一輪算失敗，大腦下一輪會把燈號全部重送
            raise ConnectionError("藍牙剛重新連上，下一輪重送燈號")

    def _on_button(self, _char, data):
        if bytes(data)[:1] == b"\x01":   # 1＝按下
            self.pressed = True
            if self.on_button:
                self.on_button()

    async def connect(self):
        try:
            from bleak import BleakClient, BleakScanner
        except ImportError:
            # UNO Q 的系統 Python 沒有 pip：改用起始檔自己帶的那一份（vendor/ 資料夾）
            import os
            import sys
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
            from bleak import BleakClient, BleakScanner
        dev = await BleakScanner.find_device_by_name(self.name, timeout=10.0)
        if dev is None and self._drop_stale():
            # 上一次的程式沒好好收尾（例如直接關掉視窗），板子的藍牙還連著 ESP32，ESP32 就不會再廣播
            print("上一次的藍牙連線還掛著，先斷開再找一次…")
            await asyncio.sleep(2)
            dev = await BleakScanner.find_device_by_name(self.name, timeout=10.0)
        if dev is None:
            seen = []
            try:
                found = await BleakScanner.discover(timeout=4.0)
                seen = sorted({d.name for d in found if d.name and d.name.startswith("maker-")})
            except Exception:
                pass
            hint = "附近看得到的板子：{}。".format("、".join(seen)) if seen else "附近沒有任何 maker- 開頭的板子在廣播。"
            raise RuntimeError("掃不到 {}：{}ESP32 有按住 A 開機嗎（OLED 顯示 BLE）？名字打對了嗎？"
                               "上一位同學的程式停了嗎（藍牙一次只能連一台）？".format(self.name, hint))
        self.client = BleakClient(dev, disconnected_callback=self._on_disconnect)
        await self.client.connect()
        await self.client.start_notify(NUS_TX, self._on_text)
        await self.client.start_notify(LBS_BUTTON, self._on_button)
        return "藍牙連上 {}（{}）".format(self.name, dev.address)

    def _drop_stale(self):
        """問 Linux 的藍牙（BlueZ）：是不是還連著同名的裝置？是就斷開。回傳有沒有斷開過。"""
        import subprocess
        try:
            out = subprocess.run(["bluetoothctl", "devices", "Connected"], capture_output=True,
                                 text=True, timeout=5).stdout
            dropped = False
            for line in out.splitlines():                 # 每行三段：Device、裝置位址、名字
                parts = line.split(None, 2)
                if len(parts) == 3 and parts[2].strip() == self.name:
                    subprocess.run(["bluetoothctl", "disconnect", parts[1]], capture_output=True, timeout=10)
                    dropped = True
            return dropped
        except Exception:
            return False                                  # 不是 Linux，或沒有 bluetoothctl：當作沒這回事

    async def _say(self, text, expect=None):
        """寫一行指令過去；expect 有給就等 ESP32 回一行開頭是 expect 的字"""
        while not self.lines.empty():           # 先把之前沒讀的回覆清掉
            self.lines.get_nowait()
        t0 = time.perf_counter()
        await asyncio.wait_for(self.client.write_gatt_char(NUS_RX, text.encode(), response=True),
                               timeout=self.timeout)
        if expect is None:
            self.last_rtt_ms = (time.perf_counter() - t0) * 1000
            return None
        deadline = t0 + self.timeout
        while True:
            left = deadline - time.perf_counter()
            if left <= 0:
                raise TimeoutError("ESP32 沒回「{}」".format(expect))
            line = await asyncio.wait_for(self.lines.get(), timeout=left)
            if line == "__DISCONNECTED__":
                raise ConnectionError("藍牙斷線了")
            if line.startswith(expect):
                self.last_rtt_ms = (time.perf_counter() - t0) * 1000
                return line

    async def read(self):
        await self._ensure()
        temp = hum = None
        line = await self._say("temp", expect=("temp", "DHT11"))
        m = TEMP_RE.search(line or "")
        if m:
            temp, hum = [float(x) if "." in x else int(x) for x in m.groups()]
        sensors = {
            "temp": temp, "hum": hum,
            "light": None, "knob": None,        # d11 沒有提供，藍牙這條線讀不到
            "button": self.pressed,
        }
        self.pressed = False
        return sensors, self.last_rtt_ms

    async def send(self, action, value=None):
        # 每個指令都等「它自己的」回話，免得把上一個指令遲到的 OK 當成這一個的
        if action in ("red", "yellow", "green"):
            word = "{} {}".format(action, "on" if value else "off")
            await self._say(word, expect="OK " + word)
        elif action == "rgb":
            await self._say("rgb {} {} {}".format(*value), expect="OK rgb")
        elif action == "beep":
            await self._say("beep", expect="OK beep")
        elif action == "off":
            await self._say("off", expect="OK all off")

    async def close(self):
        if self.client is not None and self.client.is_connected:
            try:
                await asyncio.wait_for(self.client.disconnect(), timeout=self.timeout)
            except Exception:
                pass


class SimBleLink(BleLink):
    """模擬藍牙：不用真的藍牙，改把同樣的文字指令送到 fake_esp32.py 的 /sim/ble。
    指令、回話格式都跟真的 d11 一樣；但延遲是電腦內部的，不能拿來當藍牙的數字。"""
    kind = "ble-sim"

    def __init__(self, host, timeout=3.0):
        super().__init__(name="sim", timeout=timeout)
        self.base = "http://" + host

    async def _ensure(self):
        pass

    async def connect(self):
        await self._say("temp", expect="temp")
        return "模擬藍牙連上 {}（假的，延遲不算數）".format(self.base)

    async def _say(self, text, expect=None):
        import json
        import urllib.parse
        import urllib.request
        t0 = time.perf_counter()
        url = self.base + "/sim/ble?cmd=" + urllib.parse.quote(text)
        with urllib.request.urlopen(url, timeout=self.timeout) as r:
            data = json.loads(r.read())
        self.last_rtt_ms = (time.perf_counter() - t0) * 1000
        if data.get("pressed"):
            self.pressed = True
            if self.on_button:
                self.on_button()
        line = data.get("reply", "")
        if expect is not None and not line.startswith(expect):
            raise TimeoutError("ESP32 沒回「{}」，回的是「{}」".format(expect, line))
        return line

    async def poll_button(self):
        """模擬專用：送一句空指令，順便問假板子 A 鍵有沒有被按"""
        await self._say("")

    async def close(self):
        pass
