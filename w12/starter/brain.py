# ============================================
# brain.py — UNO Q 大腦：讀 ESP32 → 想一想 → 叫 ESP32 做事 → 記下來
# ============================================
# 分工（雙腦合作）：
#   ESP32＋EZ 擴充板＝感官和手腳：溫溼度、光線、旋鈕、A 鍵、三顆燈、彩色燈、蜂鳴器
#   UNO Q 的 Linux＝大腦：跑 Python、做判斷、存資料、量延遲（以後還能接 AI）
#
# 三種連法（--link）：
#   wifi      ESP32 跑第 10 課 d10_wifi_web.py，用 HTTP 問答
#   ble       ESP32 跑第 11 課 d11_ble_remote.py，用藍牙寫入／通知（藍牙套件在 vendor/，不用安裝）
#   ble-sim   沒有藍牙也能練：把藍牙的文字指令送去 fake_esp32.py
#
# 例子：
#   python3 brain.py --link wifi --esp 192.168.4.1          真的 ESP32（基地台模式）
#   python3 brain.py --link wifi --esp 127.0.0.1:8090       假的 ESP32（先在同一台跑 fake_esp32.py）
#   python3 brain.py --link wifi --esp 192.168.0.23:8090    假的 ESP32 跑在別台電腦（換成那台的 IP）
#   python3 brain.py --link ble  --name maker-A1B2          真的 ESP32，藍牙
#   python3 brain.py --link ble-sim --esp 127.0.0.1:8090    模擬藍牙
#
# 每一輪印一行，也寫進 log_<連法>_<時間>.csv；Ctrl+C 停下來時印延遲統計、把 ESP32 的燈關掉。
# ============================================

import argparse
import asyncio
import csv
import statistics
import time

import rules


def make_link(a):
    if a.link == "wifi":
        from link_wifi import WifiLink
        return WifiLink(a.esp)
    if a.link == "ble":
        from link_ble import BleLink
        return BleLink(a.name)
    from link_ble import SimBleLink
    return SimBleLink(a.esp)


async def apply(link, now, shown, sent):
    """只送「有變的」動作：燈本來就亮著就不再送一次，省流量也省時間。
    shown＝ESP32 上「確定已經是這樣」的燈；每送成功一個才記一個。"""
    for led in ("red", "yellow", "green"):
        want = bool(now.get(led, False))        # 規則沒提到的燈＝關
        if want != shown.get(led):
            await link.send(led, want)
            shown[led] = want
            sent.append("{}{}".format(led, "開" if want else "關"))
    if now["rgb"] != shown.get("rgb"):
        await link.send("rgb", now["rgb"])
        shown["rgb"] = now["rgb"]
        sent.append("彩色燈{}".format(now["rgb"]))
    if now["beep"]:
        await link.send("beep")
        sent.append("嗶")
    return sent


def fmt(v, unit=""):
    return "--" if v is None else "{}{}".format(v, unit)


async def run(a):
    link = make_link(a)
    print("連線中…")
    try:
        print(await link.connect())
    except Exception as e:
        await link.close()
        print("連不上 ESP32：{}".format(e))
        return
    stamp = time.strftime("%Y%m%d-%H%M%S")
    path = "log_{}_{}.csv".format(link.kind, stamp)
    f = open(path, "w", newline="", encoding="utf-8")
    w = csv.writer(f)
    w.writerow(["time", "link", "temp", "hum", "light", "knob", "button",
                "limit", "red", "green", "rgb", "sent", "read_ms", "fail", "why"])
    rtts, fails, rounds, prev, shown = [], 0, 0, {}, {}
    failing = False
    wrong_board = False
    t_end = time.time() + a.seconds if a.seconds else None
    try:
        while t_end is None or time.time() < t_end:
            t0 = time.time()
            rounds += 1
            sent = []
            try:
                s, rtt = await link.read()
                rtts.append(rtt)
                if failing:                                   # 剛從「沒回應」恢復：說清楚現在連的是哪一塊
                    failing = False
                    other = getattr(link, "moved", lambda: "")()
                    if other:                                 # UNO Q 自己跳到另一塊板子的 WiFi：停手，別去動別人的燈
                        print("⚠️ UNO Q 的 WiFi 換成 {} 了，不是一開始那一塊。大腦先停下來，不送任何指令。".format(other))
                        print("   連回你手上那塊再重跑：nmcli device wifi connect maker-XXXX password makerXXXX")
                        wrong_board = True
                        break
                    again = getattr(link, "where", lambda: "")()
                    if again:
                        print("接回來了。" + again)
                now = rules.decide(s, prev)
                prev = now
                await apply(link, now, shown, sent)
                print("{} {:>4}  溫度 {:>4} 濕度 {:>4} 光線 {:>5} 旋鈕 {:>5} 門檻 {:>4} | 讀 {:5.0f} ms | {}{}".format(
                    time.strftime("%H:%M:%S"), link.kind, fmt(s["temp"]), fmt(s["hum"]),
                    fmt(s["light"]), fmt(s["knob"]), now["limit"], rtt,
                    "送：" + "、".join(sent) if sent else "沒變",
                    "（" + "；".join(now["why"]) + "）" if now["why"] else ""))
                w.writerow([time.strftime("%H:%M:%S"), link.kind, s["temp"], s["hum"], s["light"],
                            s["knob"], s["button"], now["limit"], now["red"], now["green"],
                            " ".join(map(str, now["rgb"])), " ".join(sent), round(rtt, 1), 0,
                            "；".join(now["why"])])
            except Exception as e:                    # 逾時、斷線、藍牙錯誤都算這一輪失敗，下一輪再試
                fails += 1
                failing = True
                shown.clear()                         # 不確定 ESP32 現在是什麼樣子了：下一輪成功時全部重送一次
                print("{} ESP32 沒回應（第 {} 次）：{}".format(time.strftime("%H:%M:%S"), fails, e or type(e).__name__))
                w.writerow([time.strftime("%H:%M:%S"), link.kind] + [""] * 11 + [1, type(e).__name__])
            f.flush()
            await asyncio.sleep(max(0, a.period - (time.time() - t0)))
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        try:
            if not wrong_board:                               # 連到別人的板子時，連「關燈」都不送
                await asyncio.wait_for(link.send("off"), timeout=5)
        except Exception:
            print("⚠️ 關燈指令沒送到（ESP32 可能還亮著燈）：重開 ESP32 或再跑一次再 Ctrl+C")
        f.close()
        try:
            await link.close()
        except Exception:
            pass
        print("\n==== 這次跑了 {} 輪，失敗 {} 次；紀錄在 {} ====".format(rounds, fails, path))
        if len(rtts) >= 2:
            q = sorted(rtts)
            p95 = q[min(len(q) - 1, int(len(q) * 0.95))]
            print("讀一次感測值來回：中位數 {:.0f} ms、最快 {:.0f} ms、最慢 {:.0f} ms、95% 在 {:.0f} ms 內".format(
                statistics.median(q), q[0], q[-1], p95))
        if link.kind == "ble-sim":
            print("⚠️ 這是模擬藍牙：延遲是電腦裡面的 HTTP，不代表真的藍牙有多快。")


def main():
    ap = argparse.ArgumentParser(description="UNO Q 大腦：跟 ESP32 合作")
    ap.add_argument("--link", choices=["wifi", "ble", "ble-sim"], default="wifi")
    ap.add_argument("--esp", default="192.168.4.1", help="wifi／ble-sim：ESP32 的 IP（可加 :port）")
    ap.add_argument("--name", default="", help="ble：ESP32 的藍牙名字，OLED 第二行那個 maker-XXXX")
    ap.add_argument("--period", type=float, default=1.0, help="幾秒問一次（預設 1）")
    ap.add_argument("--seconds", type=float, default=0, help="跑幾秒就停（0＝一直跑到 Ctrl+C）")
    a = ap.parse_args()
    if a.link == "ble" and not a.name:
        ap.error("--link ble 要加 --name maker-XXXX（看 ESP32 的 OLED）")
    try:
        asyncio.run(run(a))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
