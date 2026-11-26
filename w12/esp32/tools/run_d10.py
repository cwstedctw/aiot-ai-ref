"""在電腦上模擬 ESP32 跑 d10_wifi_web.py：硬體換成假的、記錄每個動作，port 80 改 8090。
用法：python run_d10.py <d10 路徑>
"""
import socket as _socket
import sys
import time as _time
import types

LOG = []


def log(*a):
    msg = " ".join(str(x) for x in a)
    LOG.append(msg)
    print("[HW]", msg, flush=True)


class Pin:
    def __init__(self, name):
        self.name, self.v = name, 0

    def value(self, v=None):
        if v is None:
            return self.v
        self.v = v
        log(self.name, "=", v)


class NP(list):
    def write(self):
        log("rgb", list(self))


class Buzzer:
    def freq(self, f):
        self.f = f

    def duty(self, d):
        if d:
            log("buzzer", self.f, "Hz")


class ADC:
    def __init__(self, v):
        self.v = v

    def read(self):
        return self.v


class DHT:
    def measure(self):
        pass

    def temperature(self):
        return 24

    def humidity(self):
        return 61


class OLED:
    def fill(self, c):
        self.lines = []

    def text(self, s, x, y, c=1):
        self.lines.append(s)

    def pixel(self, *a):
        pass

    def fill_rect(self, *a):
        pass

    def show(self):
        pass


t = types.SimpleNamespace(
    sleep=_time.sleep,
    sleep_ms=lambda ms: _time.sleep(ms / 1000),
    ticks_ms=lambda: int(_time.monotonic() * 1000),
    ticks_diff=lambda a, b: a - b,
)
ez = types.ModuleType("lib.ezkit")
ez.led_red, ez.led_yellow, ez.led_blue = Pin("red"), Pin("yellow"), Pin("blue")
ez.NUM_PIXELS = 3
ez.np = NP([(0, 0, 0)] * 3)
ez.buzzer = Buzzer()
ez.light_sensor, ez.potentiometer = ADC(1234), ADC(2048)
ez.dht_sensor = DHT()
ez.oled = OLED()
ez.draw_text = lambda oled, x, y, s: oled.text(s, x, y)
ez.time = t
ez.__all__ = [k for k in vars(ez) if not k.startswith("_")]
lib = types.ModuleType("lib")
lib.ezkit = ez
sys.modules["lib"], sys.modules["lib.ezkit"] = lib, ez

net = types.ModuleType("network")
net.STA_IF, net.AP_IF, net.AUTH_WPA2_PSK = 0, 1, 3


class WLAN:
    def __init__(self, i):
        self.i, self.on = i, False

    def active(self, v=None):
        if v is None:
            return self.on
        self.on = v

    def config(self, **kw):
        log("wlan.config", kw)

    def ifconfig(self):
        return ("127.0.0.1", "255.255.255.0", "127.0.0.1", "8.8.8.8")

    def isconnected(self):
        return False


net.WLAN = WLAN
sys.modules["network"] = net
mach = types.ModuleType("machine")
mach.unique_id = lambda: b"\x24\x0a\xc4\x12\xa1\xb2"
sys.modules["machine"] = mach


# MicroPython 的 socket 有 readline；CPython 沒有 → 包一層
class Conn:
    def __init__(self, c):
        self.c, self.f = c, c.makefile("rb")

    def readline(self):
        return self.f.readline()

    def __getattr__(self, k):
        return getattr(self.c, k)

    def close(self):
        self.f.close()
        self.c.close()


class Sock(_socket.socket):
    def accept(self):
        c, a = super().accept()
        c.settimeout(None)
        return Conn(c), a


sockmod = types.ModuleType("socket")
sockmod.socket = Sock
sockmod.SOL_SOCKET, sockmod.SO_REUSEADDR = _socket.SOL_SOCKET, _socket.SO_REUSEADDR
sockmod.getaddrinfo = lambda h, p: _socket.getaddrinfo("127.0.0.1", 8090 if p == 80 else p)
sys.modules["socket"] = sockmod

src = open(sys.argv[1], encoding="utf-8").read()
exec(compile(src, sys.argv[1], "exec"), {"__name__": "__main__"})
