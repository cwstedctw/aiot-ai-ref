# W12 起始檔：UNO Q 大腦 × ESP32 手腳

| 檔 | 在哪跑 | 做什麼 |
|---|---|---|
| `brain.py` | UNO Q（電腦也可以） | 主程式：每秒讀 ESP32 → 用 `rules.py` 想一想 → 叫 ESP32 做事 → 寫 CSV、量延遲 |
| `rules.py` | — | **你要改的那支**：溫度門檻、夜燈、A 鍵要做什麼 |
| `link_wifi.py` | — | WiFi 這條線：HTTP 問答（只用 Python 內建模組） |
| `link_ble.py` | — | 藍牙這條線：bleak 寫入／通知；另有 `SimBleLink` 給沒藍牙時模擬 |
| `vendor/` | UNO Q | 藍牙套件 bleak（已經帶好，**不用安裝**；說明在裡面的 README） |
| `fake_esp32.py` | UNO Q 或電腦 | 假的 ESP32：網址跟創客課第 10 課一模一樣，瀏覽器看得到虛擬板子 |
| `webui.py`＋`webui.html` | UNO Q（電腦也可以） | **加碼**：UNO Q 開一個網頁——ESP32 資料儀表板＋用 ESP32 A 鍵當搖桿的小遊戲 |

ESP32 那邊**不用寫程式**：跑創客課 repo 的 `d10_wifi_web.py`（WiFi）或 `d11_ble_remote.py`（藍牙）。

## 先用假的 ESP32 練（不用任何板子）

```
python3 fake_esp32.py
```
另開一個終端機：
```
python3 brain.py --link wifi --esp 127.0.0.1:8090
python3 brain.py --link ble-sim --esp 127.0.0.1:8090
```
瀏覽器開 `http://127.0.0.1:8090`（在 UNO Q 上跑的話，電腦開 `http://192.168.7.2:8090`）拉溫度、光線、旋鈕，看燈怎麼變。
假板子跑在**別台電腦**時，`--esp` 寫那台電腦的 IP 加 `:8090`，不是 `127.0.0.1`。

## 接真的 ESP32：WiFi

1. ESP32 跑 `d10_wifi_web.py`，OLED 會顯示 `maker-XXXX`、`pw makerXXXX`、`192.168.4.1`。
2. UNO Q 連上 ESP32 的基地台（UNO Q 的 WiFi 會暫時離開原本的網路）：
   ```
   nmcli device wifi list
   nmcli device wifi connect maker-XXXX password makerXXXX
   ```
3. `python3 brain.py --link wifi --esp 192.168.4.1`

## 接真的 ESP32：藍牙

1. ESP32 跑 `d11_ble_remote.py`（W12 選單：按住 A 再按 EN，看到 OLED 顯示 `BLE` 才放開），OLED 第二行是 `maker-XXXX`。
2. 不用安裝任何東西：藍牙套件已經在 `vendor/` 裡（UNO Q 的系統 Python 沒有 pip）。
3. `python3 brain.py --link ble --name maker-XXXX`

從 WiFi 換到藍牙（或換回來）一定要**真的重開 ESP32**（按 EN 或重插電），只停程式不夠。

## 加碼：網頁儀表板＋搖桿小遊戲

跟 `brain.py` 二選一跑（先把 `brain.py` 用 Ctrl+C 停掉）：

```
python3 webui.py --link wifi --esp 192.168.4.1
```
教室機瀏覽器開 `http://192.168.7.2:8088`：WiFi 這條線的儀表板最完整（溫溼度、光線、旋鈕、三顆燈、來回毫秒）。

```
python3 webui.py --link ble --name maker-XXXX
```
藍牙這條線可以用 ESP32 的 **A 鍵**玩「遊戲」分頁（開始亮綠燈、撞到亮紅燈＋嗶）。沒有板子：`python3 webui.py --link ble-sim --esp 127.0.0.1:8090`，在假板子的網頁按 A 鍵。

## 停下來

`Ctrl+C`：ESP32 的燈會全關，畫面印出「讀一次感測值來回」的中位數、最快、最慢。紀錄在 `log_<連法>_<時間>.csv`。

小提醒：ESP32 的感測值大約每 2 秒才更新一次，每秒問會連續拿到同一筆；手機同時開著 d10 網頁會跟大腦搶連線：量 60 秒的時候先把手機上的網頁關掉；平常想同時開，加 `--period 2` 可以少搶一點，但還是可能撞到。
