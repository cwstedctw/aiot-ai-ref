# W12（2026-11-26）雙腦合作：UNO Q 當大腦、ESP32 當手腳

> 寫給 AI agent 讀。先讀 repo 根目錄的 `AGENTS.md`（做事的規則）。
> 這裡的指令和輸出，大多是老師 2026-11-26 上午用**一塊** UNO Q＋**一塊** ESP32 擴充板跑過的（老師經 USB 除錯線操作板子）。**還沒驗的**：學生從 SSH 跑 `nmcli` 會不會要求授權、兩塊不同的 ESP32 互換、全班同時開基地台。跟學生畫面不一樣時，以學生畫面為準。
> 給學生看的完整步驟：[學生頁](https://cwstedctw.github.io/ndhu-ted-course-hub/weekly/11501-aiot/w12/student.html)、[指令小抄](https://cwstedctw.github.io/ndhu-ted-course-hub/weekly/11501-aiot/w12/cheatsheet.html)、[互動概念頁](https://cwstedctw.github.io/ndhu-ted-course-hub/weekly/11501-aiot/w12/concept.html)。

## 一、這週在做什麼

- **ESP32＋EZ 擴充板＝感官和手腳**：溫溼度 DHT11、光線、旋鈕、A 鍵、紅黃綠三顆燈、彩色燈（RGB）、蜂鳴器、OLED。ESP32 **不寫新程式**，直接跑創客課第 10 課（WiFi）或第 11 課（藍牙）。
- **UNO Q 的 Linux＝大腦**：學生只在 UNO Q 上跑 Python。每一輪：讀感測值 → `rules.py` 的 `decide()` 決定動作 → 只把有變的動作送回 ESP32 → 印一行、寫進 `log_<連法>_<時間>.csv`、量來回時間。
- **同一個大腦換一條線**：`--link wifi` 或 `--link ble`，`rules.py` 不用改。重點是讓學生自己看見「兩條線各拿得到什麼」和「各多快」。
- 沒輪到真板的時候，用 `fake_esp32.py`（假的 ESP32）練。

## 二、兩條線的格式（ESP32 那邊，原始碼在 `esp32/`）

> ESP32 板子本身（元件與腳位、開機畫面、一個元件一個元件怎麼檢查、故障對照）寫在 **[`esp32/README.md`](esp32/README.md)**。學生問「ESP32 是不是壞了」時讀那份；學生要**改 ESP32 程式**時讀 [`esp32/rewrite.md`](esp32/rewrite.md)（工具安裝、先在電腦上試、上傳、交出去前還原）。

| | WiFi：第 10 課 `esp32/d10_wifi_web.py` | 藍牙：第 11 課 `esp32/d11_ble_remote.py` |
|---|---|---|
| 怎麼連 | ESP32 自己開基地台：名稱 `maker-XXXX`、密碼 `makerXXXX`、網址 `http://192.168.4.1`（XXXX 看 OLED） | 藍牙名稱 `maker-XXXX`（OLED 第二行） |
| 讀 | `GET /api/status` → JSON：`red`、`yellow`、`blue`、`rgb`、`temp`、`hum`、`light`、`knob`、`last`、`requests` | 寫入文字 `temp` → 通知回 `temp 25 C, hum 61 %`；讀失敗回 `DHT11 read failed` |
| 做 | `/api/led?name=red&on=1`（`name`＝`red`／`yellow`／`blue`）、`/api/rgb?r=&g=&b=`、`/api/beep`、`/api/off` | 寫入 `red on`、`green off`、`yellow on`、`rgb 255 0 0`、`beep`、`off`；燈的指令回 `OK <燈> on`／`OK <燈> off`（例如 `OK red on`、`OK green off`、`OK yellow on`），其他回 `OK rgb`、`OK beep`、`OK all off` |
| 板子主動說 | 沒有（只會回答） | A 鍵按下／放開 → 按鈕特徵值通知 `1`／`0`（按鈕在另一個服務，不在文字指令那個服務裡） |
| 拿不到 | **按鈕** | **光線、旋鈕** |

藍牙 UUID：文字指令服務（Nordic UART）`6E400001-B5A3-F393-E0A9-E50E24DCCA9E`，RX（寫入）`6E400002-…`，TX（通知）`6E400003-…`；按鈕特徵值 `00001524-1212-EFDE-1523-785FEABCD123`（另一個服務）。

容易弄錯的地方：

- 第三顆燈在第 10 課程式裡叫 `blue`，**板子上是綠燈**；`rules.py` 和第 11 課叫 `green`。
- **兩條線量溫度的方式不同**：WiFi 線（第 10 課）大約每 2 秒才更新一次溫溼度，每秒問會連續拿到同一筆，正常；藍牙線（第 11 課）是每收到一次 `temp` 才量一次，量失敗就回 `DHT11 read failed`。溫溼度都是整數。
- 第 10 課**一次只服務一個連線**：學生手機同時開著 `192.168.4.1` 的網頁，大腦會常常「沒回應」。量測時請他關掉手機網頁。
- 藍牙文字指令最多 128 位元組，回話最多 100 位元組。

**ESP32 開機選單**（`starter/esp32/main_w12.py`，老師已經刷好）：直接開機＝WiFi（第 10 課）；**按住 A 再按 EN，看到 OLED 顯示 `BLE` 才放開**＝藍牙（第 11 課）。**WiFi 和藍牙之間切換，一定要真的重開 ESP32**；只停程式不夠（實測藍牙會起不來，`OSError: [Errno 5] EIO`）。

## 三、起始檔（`starter/`）

學生在板子上用的是課程網的打包檔，**裡面多一個 `vendor/`**（藍牙套件 bleak 3.1.0＋dbus_fast 5.2.0，UNO Q 專用，所以不用安裝）。`link_ble.py` 是照**自己這個檔案的位置**去找旁邊的 `vendor/`。這個 repo 的 `starter/` 是給你讀的副本，沒有 `vendor/`，**不要叫學生從這個 repo 跑藍牙**。

抓打包檔（在板子上，要在連 ESP32 的 WiFi **之前**，連上之後板子沒有外網）：

```
cd ~
curl -fLO https://cwstedctw.github.io/ndhu-ted-course-hub/weekly/11501-aiot/w12/starter/w12-starter.tar.gz
tar xzf w12-starter.tar.gz
cd ~/w12-starter
```

板子已經沒有外網、`curl` 抓不到時：先在教室機下載同一個網址，用 USB 傳進板子（在教室機打）`scp w12-starter.tar.gz arduino@192.168.7.2:~/`，再到板子上 `tar xzf w12-starter.tar.gz`。

| 檔 | 做什麼 |
|---|---|
| `brain.py` | 主程式。`--link wifi`／`ble`／`ble-sim`（預設 `wifi`）；`--esp` ESP32 的 IP，可加 `:port`（預設 `192.168.4.1`）；`--name` 藍牙名字（**`--link ble` 一定要給**）；`--period` 幾秒一輪（預設 1）；`--seconds` 跑幾秒停（0＝跑到 Ctrl+C）。停下時會試著送 `off` 關燈（發現連到別組的板子時連關燈都不送），印「這次跑了幾輪、失敗幾次、紀錄在哪個檔」；**至少讀到兩筆**才會再印「讀一次感測值來回：中位數…、最快…、最慢…、95% 在…內」 |
| `rules.py` | **學生改這支**。可改的數字：`TEMP_HOT_FIXED = 28`（藍牙線沒有旋鈕時的熱門檻）、`KNOB_MIN_C = 20`、`KNOB_MAX_C = 35`（WiFi 線：旋鈕 0–4095 對到 20–35 °C）、`LIGHT_DARK = 1000`、`DARK_WHEN_LOW = True`（遮光數字變小，真板驗過）、`NIGHT_RGB = (255, 160, 60)`。函式：`threshold(s)`、`is_dark(light)`、`decide(s, prev)`；`decide` 回傳 `red`、`yellow`、`green`、`rgb`、`beep`、`limit`、`why`。拿不到的值是 `None`。**黃燈 `yellow` 目前固定 `False`，留給學生用**（例如濕度高就亮），只改 `rules.py` 就做得到 |
| `link_wifi.py` | WiFi 線，只用 Python 內建的 `urllib` |
| `link_ble.py` | 藍牙線，用 bleak；另有 `SimBleLink`（`--link ble-sim`）把同樣的文字指令送到假的 ESP32 |
| `fake_esp32.py` | 假的 ESP32：網址、JSON 欄位跟第 10 課一樣；預設埠 **8090**；瀏覽器開它可以拉溫度、光線、旋鈕、按 A 鍵 |
| `webui.py`＋`webui.html` | 加碼：UNO Q 開網頁（預設埠 **8088**），儀表板＋用 A 鍵玩的小遊戲；跟 `brain.py` 二選一跑，不用 `rules.py` |
| `esp32/main_w12.py` | ESP32 的開機選單（見上） |

常用指令（都在 `~/w12-starter` 裡跑）：

```
python3 fake_esp32.py                                  # 假的 ESP32（另開一個視窗跑大腦）
python3 brain.py --link wifi --esp 127.0.0.1:8090      # 大腦 × 假的 ESP32（WiFi 格式）
python3 brain.py --link ble-sim --esp 127.0.0.1:8090   # 大腦 × 假的 ESP32（藍牙格式）
python3 brain.py --link wifi --esp 192.168.4.1 --seconds 60   # 真板 WiFi，跑 60 秒
python3 brain.py --link ble --name maker-XXXX --seconds 60    # 真板藍牙，跑 60 秒
python3 webui.py --link wifi --esp 192.168.4.1         # 加碼網頁（WiFi 儀表板）
python3 webui.py --link ble --name maker-XXXX          # 加碼網頁（A 鍵當搖桿）
python3 webui.py --link ble-sim --esp 127.0.0.1:8090   # 加碼網頁，沒有真板：在假的 ESP32 網頁上按 A 鍵
```

假的 ESP32 跑在 UNO Q 上時，電腦瀏覽器開 `http://192.168.7.2:8090`；加碼網頁開 `http://192.168.7.2:8088`。假板子跑在**別台電腦**時，`--esp` 要寫那台電腦的 IP 加 `:8090`，不是 `127.0.0.1`。

## 四、UNO Q 連 ESP32 的 WiFi（不用 sudo）

```
nmcli device wifi list
nmcli device wifi connect maker-XXXX password makerXXXX
```

成功會印 `Device 'wlan0' successfully activated with '…'.`；UNO Q 拿到 `192.168.4.2`，ESP32 是 `192.168.4.1`。連上之後 UNO Q 就離開原本的網路（沒有外網），所以：**進板子一律走 USB `ssh arduino@192.168.7.2`**。

如果 `nmcli` 要求授權或密碼：**不要叫學生加 `sudo`**，請他舉手問老師（學生從 SSH 跑這一步，老師還沒驗過）。

查 UNO Q 現在連哪個網路：`nmcli -t dev status`（只看 `wifi` 那一行；`lo`、`br-…`、`docker0` 那幾行不用管）。回原本的網路：`nmcli connection show` 查名字，再 `nmcli connection up <名字>`。

藍牙不用先連網路，直接 `python3 brain.py --link ble --name maker-XXXX`。

## 五、ESP32 不夠、輪流用

一塊 UNO Q 一次只對一塊 ESP32，用完交給下一組。沒輪到的時候做假的 ESP32、改 `rules.py`、加碼網頁（`--link ble-sim`）。

- **交出去之前**：①在跑的 `brain.py`／`webui.py` 按 **Ctrl+C**（不停的話下一組藍牙掃不到，而且你的程式還會自己重新連線把板子搶回去）；②**用過 WiFi 線的話**，`nmcli connection delete maker-XXXX`（XXXX 是這塊板子的名字；不刪的話 UNO Q 之後可能自己連回這塊板子，讀到別組的數字）。
- **拿到另一塊之後（WiFi）**：照第四節連 `maker-YYYY` → 先跑 `nmcli -t dev status`，看 `wifi` 那一行的名字**跟手上 ESP32 的 OLED 一樣**，再跑 `python3 brain.py --link wifi --esp 192.168.4.1`。大腦第一行也會印「UNO Q 現在連的 WiFi 是 maker-YYYY——跟你手上 ESP32 的 OLED 一樣嗎？」再對一次。名字不一樣就是連到別組的板子：Ctrl+C → `nmcli connection delete maker-ZZZZ`（ZZZZ 是連錯的那個名字）→ 連自己這塊。
- **拿到另一塊之後（藍牙）**：ESP32 按住 A 再按 EN、看到 OLED 顯示 `BLE` 才放開 → `python3 brain.py --link ble --name maker-YYYY`。

## 六、常見錯誤

| 學生看到 | 原因 | 怎麼辦 |
|---|---|---|
| `ESP32 沒回應（第 N 次）：…` | ESP32 重開了、UNO Q 沒連在它的 WiFi，或手機網頁在搶連線 | 偶爾一兩次正常，大腦下一輪會把燈號全部重送；一直出現就 `nmcli -t dev status` 看 wifi 那行，關掉手機網頁 |
| `連不上 ESP32：<urlopen error [Errno 101] Network is unreachable>（UNO Q 現在沒有連任何 WiFi）…` | 還沒連 ESP32 的 WiFi 就跑 | 照它下一行印的 `nmcli device wifi connect …` 打，再跑一次 |
| `nmcli` 找不到 `maker-XXXX` | 名字抄錯，或清單還沒更新 | 看 OLED 對名字，再跑一次 `nmcli device wifi list` |
| `連不上 ESP32：掃不到 maker-XXXX：…` | ESP32 不在藍牙模式、名字打錯、上一組的程式還連著 | 照順序查：①OLED 顯示 `BLE` 了嗎（按住 A 再按 EN）②名字 ③**先確認上一組的程式真的停了**（Ctrl+C）。上一組的程式還開著的話，重開 ESP32 也沒用，它會自己重新連線把板子搶回去；確定那邊停了還是掃不到，再重開 ESP32（按住 A 再按 EN），還不行就舉手 |
| `上一次的藍牙連線還掛著，先斷開再找一次…` | 上一次直接關視窗、沒按 Ctrl+C | 不用處理，程式會自己斷開再連 |
| `No module named 'bleak'` | 跑的不是課程網打包檔裡的 `brain.py`（例如這個 repo 的副本），或解壓不完整、`brain.py` 旁邊沒有 `vendor/` | `ls ~/w12-starter` 看有沒有 `vendor/`；沒有就重新抓打包檔、重新解壓。**不要叫學生 pip install** |
| `溫度沒讀到，維持上一輪` | 溫溼度感測器偶爾讀失敗（藍牙回 `DHT11 read failed`） | 正常：只有「熱不熱」（紅燈）沿用上一輪，光線和 A 鍵照常判斷 |
| 溫度一直不變 | 溫溼度是整數；WiFi 線大約 2 秒才更新 | 用手握住感測器 30 秒；WiFi 線也可以轉旋鈕把門檻調低（藍牙線沒有旋鈕，門檻固定 28） |
| 夜燈一直亮 | 教室比較暗，光線數字接近門檻 1000（只有 WiFi 線讀得到光線） | 先遮一次光、看數字往哪走，再把 `LIGHT_DARK` 調小 |
| 時間顯示 5 月、紀錄檔檔名是 5 月的日期 | 板子沒有外網，時鐘停在映像檔的日期 | 正常，不影響量延遲 |
| SSH 突然斷線 | 用的是板子在 WiFi 上的 IP | 改用 USB：`ssh arduino@192.168.7.2` |

ESP32 這邊的故障（OLED 全黑、某顆燈不亮、溫度一直 `null`、模式切不過去）見 [`esp32/README.md`](esp32/README.md) 第八節。

## 七、這週的作業（學生要自己做）

交 e學苑：

- **兩份紀錄檔**：第二部分 WiFi 跑 60 秒的 `log_wifi_….csv`、第三部分藍牙跑 60 秒的 `log_ble_….csv`（量完當場抄下畫面印的檔名）。**藍牙真板做不到，就交 `ble-sim` 那份並註明**，比較表藍牙那格寫「未量到真板（附 ble-sim 紀錄）」。沒有統計行就照實寫「沒有統計」。
- **三句比較**：兩條線各讀得到什麼、來回中位數各幾毫秒、哪條線斷了怎麼表現。
- **二選一**（都做就都附）：改了 `rules.py` 哪一條、為什麼；或加碼網頁的兩張截圖（儀表板＋遊戲最高分）。

你可以幫學生看懂紀錄檔的欄位（`time,link,temp,hum,light,knob,button,limit,red,green,rgb,sent,read_ms,fail,why`）、解釋中位數是什麼、提示他規則可以怎麼改、檢查他改得對不對。**但這些要他自己完成**：紀錄檔和毫秒數字一定要是他自己跑出來的，不要幫他編，也不要把模擬藍牙的數字說成真板；三句比較、`rules.py` 的修改和修改的理由，要他自己寫。
