# ============================================
# main_w12.py — AIoT W12 用的 ESP32 開機選單（上傳成板子的 main.py）
# ============================================
# 開機（按 EN／RST 或重新插電）時：
#   沒按任何鍵      → 跑第 10 課 WiFi 網頁（d10_wifi_web）
#   按住 A 鍵開機   → 跑第 11 課藍牙遙控（d11_ble_remote）
# 兩課的程式都不用改，跟創客課用的是同一份。
#
# 老師課前（在創客課 repo maker-esp32 的資料夾）：
#   ./tools/upload.sh                                    先把 lib／demos 全部傳上去
#   uv run mpremote connect auto sleep 2 cp <本檔路徑> :main.py
#   uv run mpremote connect auto reset
# 還原成創客課的選單：再跑一次 ./tools/upload.sh
# ============================================

from lib.ezkit import btn_a, oled
import time

time.sleep_ms(300)                 # 等手指按穩
use_ble = btn_a.value() == 0       # A 鍵按下＝0（上拉電阻）

oled.fill(0)
oled.text("AIoT W12", 0, 0, 1)
oled.text("BLE  (d11)" if use_ble else "WiFi (d10)", 0, 16, 1)
oled.show()
print("W12 選單：", "藍牙 d11" if use_ble else "WiFi d10")
time.sleep_ms(800)

__import__("demos.d11_ble_remote" if use_ble else "demos.d10_wifi_web")
