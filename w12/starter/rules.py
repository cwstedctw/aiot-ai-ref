# ============================================
# rules.py — UNO Q 大腦的「規則」（你主要改這一支）
# ============================================
# 大腦每一輪做三件事：
#   1. 從 ESP32 讀到「現在的感測值」s（溫度、濕度、光線、旋鈕、A 鍵）
#   2. 用 decide() 想一想，決定要 ESP32 做什麼動作
#   3. 把動作送回 ESP32（紅燈、綠燈、彩色燈、嗶一聲）
#
# decide() 只管「想」，不管「怎麼傳」——
# 所以同一份規則，WiFi 跟藍牙兩條線都能用。
# 拿不到的值是 None（例如藍牙那條線讀不到光線和旋鈕），規則要自己處理。
# ============================================

# ---- 可以改的數字 ----
TEMP_HOT_FIXED = 28      # 沒有旋鈕可讀時（藍牙那條線），溫度到這個數字（含）以上就算「熱」
KNOB_MIN_C = 20          # 有旋鈕可讀時（WiFi 那條線）：旋鈕轉到底＝20 度
KNOB_MAX_C = 35          #                               轉到頂＝35 度
LIGHT_DARK = 1000        # 光線數字低於（或高於）這個就算「暗」——先遮光看數字往哪走再改
DARK_WHEN_LOW = True     # 遮住光感測器時數字變小＝True；變大＝False
NIGHT_RGB = (255, 160, 60)   # 暗的時候彩色燈亮暖黃色（夜燈）


def threshold(s):
    """熱的門檻：有旋鈕就用旋鈕（0–4095 對到 20–35 度），沒有就用固定值"""
    if s.get("knob") is None:
        return TEMP_HOT_FIXED
    return round(KNOB_MIN_C + (KNOB_MAX_C - KNOB_MIN_C) * s["knob"] / 4095, 1)


def is_dark(light):
    if light is None:
        return False
    return light < LIGHT_DARK if DARK_WHEN_LOW else light > LIGHT_DARK


def decide(s, prev):
    """s＝這一輪的感測值；prev＝上一輪的決定（第一輪是空的 dict）
    回傳這一輪的決定：要哪些燈亮、要不要嗶、以及「為什麼」"""
    why = []
    limit = threshold(s)
    if s.get("temp") is None:
        # 溫溼度感測器偶爾讀失敗（d11 會回 DHT11 read failed）：維持上一輪的判斷，不要當成「變涼了」
        hot = prev.get("red", False)
        why.append("溫度沒讀到，維持上一輪")
    else:
        hot = s["temp"] >= limit
    dark = is_dark(s.get("light"))

    if hot and s.get("temp") is not None:
        why.append("溫度 {} ≥ 門檻 {}".format(s["temp"], limit))
    if dark:
        why.append("光線 {} 算暗→夜燈".format(s["light"]))

    # 只在「剛變熱」那一輪嗶一聲，不要每秒一直叫
    beep = hot and not prev.get("red", False)  # 第一輪一開始就熱，也會嗶一聲
    # A 鍵（只有藍牙那條線讀得到）：按一下就嗶一聲，代表大腦收到了
    if s.get("button"):
        beep = True
        why.append("有人按了 ESP32 的 A 鍵")

    return {
        "red": hot,
        "yellow": False,               # 黃燈現在沒用到——留給你（例如濕度太高就亮）
        "green": not hot,              # 綠燈＝一切正常、大腦有在顧
        "rgb": NIGHT_RGB if dark else (0, 0, 0),
        "beep": beep,
        "limit": limit,
        "why": why,
    }
