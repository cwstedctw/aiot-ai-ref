# 改 ESP32 程式：工具安裝、先在電腦上試、上傳、還原（W12）

> 寫給 AI agent 讀。學生說「我想讓 ESP32 多做一件事」「幫我改 ESP32 的程式」時照這份做。先讀 repo 根目錄的 `AGENTS.md` 和本夾的 [`README.md`](README.md)（板子、腳位、怎麼檢查）。
> ESP32 程式的正本在創客課 repo [`cwstedctw/maker-esp32`](https://github.com/cwstedctw/maker-esp32)，它的 `AGENTS.md`（腳位、常見的坑、不能做的事）**也要照著做**。
> 出處標記：**〔真板〕**老師在真的板子上跑過；**〔mbp 實跑〕**2026-11-26 在老師的 Mac 上跑過，但沒有接板子；**〔模擬〕**在電腦上用假硬體跑過；**〔程式〕**只照原始碼寫；**⚠️ 沒驗**＝還沒有人試過。

## 〇、真的需要改 ESP32 嗎？

這週的大腦都在 UNO Q 上，**大部分想法只改 UNO Q 的 `rules.py` 就做得到**（換門檻、換燈色、加條件）。能只改 UNO Q 就不要動 ESP32。

要改 ESP32 的情況：想讓 ESP32 **多給一個資料**（例如按鈕 B、紅外線遙控器）、**多做一個動作**（例如繼電器、在 OLED 顯示大腦的判斷），或是期末專題要用。

## 一、AI 改 ESP32 時的規則（加在 `AGENTS.md` 的八條之上）

1. **先給計畫，學生回「可以」再動手。** 計畫要列出：要改哪個檔、加什麼功能、要跑的每一條指令（安裝、檢查、上傳、還原）。計畫裡列過的指令可以照順序跑；沒列到的先問。
2. **另存新檔再改。** 從第 10 課改就複製成 `esp32/demos/my_d10.py`，從第 11 課改就複製成 `my_d11.py`。**不要改**原本的 `d1`–`d15`、`lib/`、`tools/`、`.vscode/`。
3. **讓 UNO Q 的大腦還能用。** 原本的網址（`/api/status`、`/api/led`、`/api/rgb`、`/api/beep`、`/api/off`）、JSON 欄位名、藍牙文字指令和回話、UUID **都不要改、不要刪**。要加功能就**加新的**：新網址（例如 `/api/relay?on=1`）、JSON 新欄位、新的文字指令；再改 UNO Q 這邊的 `link_wifi.py`／`link_ble.py`／`rules.py` 去用它。
4. **照創客課的硬體規矩**（maker-esp32 的 `AGENTS.md`）：腳位不改；不要對 `ezkit.py` 已經用到的腳位再建一次 `Pin(...)` 或 `PWM(...)`（會搶腳，燈不聽話）；迴圈裡不要用很長的 `time.sleep()`；OLED 中文只認得字型檔裡有的字；WiFi 密碼、金鑰不要寫進要分享的檔。
5. **上傳前先在電腦上檢查**（第四節）。沒在真板上跑過，就說「還沒在板子上測過」，不要說「完成了」。
6. **不准做的**：燒韌體（`esptool erase-flash`、`write-flash`）、裝 USB 驅動、用 `sudo`、刪板子上的檔（`mpremote rm`）、刪板子上的 `ir_keys.json`。遇到需要這些的情況，請學生找老師。
7. **ESP32 是好幾組輪流用的。** 學生改完、測完，**交出去之前一定要還原成 W12 選單**（第六節），並請他親眼看 OLED 確認。
8. **序列埠一次只能一個程式用**：VS Code 的「ESP32: Serial monitor」、上傳、其他工具只能開一個。上傳失敗，先把其他的關掉。

## 二、在哪台電腦做

ESP32 要用 **USB 資料線**插在做上傳的那台電腦上（只能充電的線不行）。

| 電腦 | 狀況 |
|---|---|
| **自己的 Mac**（最順） | macOS 內建 ESP32 的 USB 驅動，插上就有 `/dev/cu.usbserial-…`；工具用 `uv sync` 裝。〔mbp 實跑：安裝與指令〕〔真板：創客課 11/04 在 Intel Mac 上傳過〕 |
| **自己的 Windows 筆電** | 要先裝 USB 晶片 CP2102 的驅動（**要系統管理員**，自己的筆電才裝得了）；maker-esp32 有一鍵安裝 `setup-vscode-codex.cmd`（裝 VS Code、Python、uv、擴充功能、上傳工具，**不裝驅動**）。〔真板：創客課 11/04 在 Windows 上傳過〕 |
| **E307 Ubuntu 教室機** | ⚠️ 沒驗。教室機不能用 `sudo`；ESP32 的序列埠 `/dev/ttyUSB0` 通常只開給 `dialout` 群組，學生帳號可能打不開；`uv` 要自己裝到家目錄。先跑第三節第 5、6 步的檢查，不行就換自己的筆電，或找老師 |

## 三、安裝（每台電腦第一次做，大約 5 分鐘）

**1. 兩個 repo 下載到同一層**（之後還原要用到 `aiot-ai-ref` 裡的 W12 選單）：

```
git clone https://github.com/cwstedctw/maker-esp32.git
git clone https://github.com/cwstedctw/aiot-ai-ref.git
cd maker-esp32
```

**2. 裝 uv**（Python 的套件與環境工具），已經有就跳過（`uv --version` 印得出版本＝有了）：

- Mac：有 Homebrew 就 `brew install uv`；沒有就用 uv 官方的安裝指令 `curl -LsSf https://astral.sh/uv/install.sh | sh`。
- Windows：雙擊 maker-esp32 裡的 `setup-vscode-codex.cmd`（連 uv 一起裝），或 `winget install --id astral-sh.uv -e`。
- Ubuntu 教室機：`curl -LsSf https://astral.sh/uv/install.sh | sh`（官方指令，裝到自己的家目錄、不用 `sudo`；裝完開一個新的終端機）。⚠️ 沒驗

**3. 裝上傳工具**（照 `uv.lock` 裝，版本跟老師一樣）：

```
uv sync
uv run mpremote --version
```

應該看到 `mpremote 1.29.0`。〔mbp 實跑：另外裝了 esptool 5.6.0；uv 會自己準備 Python 3.13〕

**4. 插上 ESP32，找到它的連接埠**：

- Mac：`ls /dev/cu.usbserial*` → 應該有一個 `/dev/cu.usbserial-…`；印 `no matches found` 或 `No such file`＝沒抓到板子（換線、換孔）。〔mbp 實跑：沒插板子時印 `no matches found`〕
- Windows：裝置管理員 →「連接埠 (COM 和 LPT)」→ 應該有 `Silicon Labs CP210x USB to UART Bridge (COMx)`。沒有、或旁邊有黃色驚嘆號＝驅動沒裝。
- Ubuntu：`ls -l /dev/ttyUSB*` → 應該有 `/dev/ttyUSB0`；再打 `groups`，看有沒有 `dialout`。
- 三種都可以用：`uv run mpremote connect list`，列出看得到的連接埠。

**5. 確認連得上、看韌體版本**（這一步會讓 ESP32 上的程式停下來；做完按一下 EN 讓它重開）：

```
uv run mpremote connect auto sleep 2 exec "import sys; print(sys.version)"
```

應該看到 `MicroPython v1.29.0` 那一行。〔真板：創客課〕版本不是 v1.29.0，**不要自己燒韌體**，找老師。

**6. 這一步失敗的話**：

| 看到 | 原因 | 怎麼辦 |
|---|---|---|
| `mpremote: no device found` | 沒插好、線只能充電、驅動沒裝（Windows） | 換線、換孔；Windows 看裝置管理員〔mbp 實跑：沒插板子時就是這一行〕 |
| `could not enter raw repl` | 板子剛重開、還在印開機訊息，或別的程式佔著序列埠 | 關掉序列埠監看；按一下 EN 再試 |
| 有 `Permission denied`（Ubuntu） | 學生帳號沒有序列埠的權限 | 不能用 `sudo` 修，換自己的筆電或找老師 |

## 四、改程式，先在電腦上試

**1. 另存新檔**（在 maker-esp32 資料夾）：

- Mac／Ubuntu：`cp esp32/demos/d10_wifi_web.py esp32/demos/my_d10.py`
- Windows PowerShell：`Copy-Item esp32\demos\d10_wifi_web.py esp32\demos\my_d10.py`

**2. 改 `my_d10.py`**，照第一節的規則。範例：加一個新網址 `/api/party`（彩色燈變紫色、嗶兩聲），放在 `handle()` 裡 `/api/beep` 那一段的後面：

```python
    elif route == "/api/party":          # 新加的：彩色燈變紫色、嗶兩聲
        set_rgb(255, 0, 255)
        beep(1046, 80)
        beep(1318, 80)
        state["last"] = "彩色燈"
```

（`state["last"]` 用「彩色燈」是因為 OLED 字型檔裡一定有這三個字；換成別的中文字，要先確認字型檔有，不然 OLED 上會變方塊。）

**3. 檢查有沒有打錯字、縮排錯**（三種電腦都一樣）：

```
uv run python -m py_compile esp32/demos/my_d10.py
```

什麼都沒印＝通過。這一步只抓得到語法錯，抓不到 MicroPython 專用的東西（`machine`、`network`）有沒有用錯。〔mbp 實跑〕

**4. 從第 10 課改出來的（WiFi），可以先在電腦上跑**：

```
uv run python ../aiot-ai-ref/w12/esp32/tools/run_d10.py esp32/demos/my_d10.py
```

這是創客課的模擬器：把板子的硬體換成假的，每個動作印成一行 `[HW] …`，網頁伺服器開在 `127.0.0.1:8090`。另開一個終端機測：

```
curl -sS --max-time 5 http://127.0.0.1:8090/api/party
curl -sS --max-time 5 "http://127.0.0.1:8090/api/led?name=red&on=1"
```

Windows PowerShell 要把 `curl` 打成 **`curl.exe`**（PowerShell 5.1 裡的 `curl` 是另一個指令，上面的參數它看不懂）。

新網址、原本的網址都要回 JSON（第二條確認你沒弄壞大腦要用的網址）。測完在跑模擬器的視窗按 Ctrl+C。〔模擬：上面的 `/api/party` 範例在 mbp 上這樣跑過，模擬器印出 `[HW] rgb [(255, 0, 255), …]`、`[HW] buzzer 1046 Hz`、`[HW] buzzer 1318 Hz`〕

模擬器的限制：

- 它只有第 10 課用到的零件（三顆燈、彩色燈、蜂鳴器、光線、旋鈕、溫溼度、OLED 文字、WiFi）。程式用到 `btn_a`、`btn_b`、`relay`、紅外線，會出現 `NameError: name 'btn_a' is not defined`：**那是模擬器沒有這個零件，不是程式寫錯**，這種就直接上真板試。〔模擬〕
- 假的溫溼度永遠是 24 °C、61 %，光線 1234、旋鈕 2048。
- 第 11 課（藍牙）沒有模擬器，只能上真板試。
- 模擬器用的 8090 跟假的 ESP32（`fake_esp32.py`）一樣，同一台電腦一次只能開一個。

## 五、上傳到 ESP32

**VS Code 的「ESP32: Upload lesson (pick one)」只能選原本的 15 課，選不到 `my_d10`**，所以用終端機上傳（在 maker-esp32 資料夾）：

- Mac／Ubuntu：`./tools/upload.sh my_d10`
- Windows：`powershell -ExecutionPolicy Bypass -File tools\upload.ps1 -Lesson my_d10`

它會把 `lib/` 和你的檔傳上去，**你的檔會變成板子上的 `main.py`**，然後重開：開機直接跑你的程式，W12 選單暫時沒了（第六節還原）。〔程式：`upload.sh`／`upload.ps1` 都是找 `esp32/demos/<名字>.py`；mbp 實跑時 `my_d10` 出現在可用的課程清單裡〕〔真板：創客課在 Windows 與 Mac 用同一支工具上傳過第 1 課〕

上傳完的檢查：

- 從第 10 課改的：OLED 應該是 `WiFi 遙控` 那四行；UNO Q 照本夾 [`README.md`](README.md) 第五節連上，用 `curl` 測新功能，再跑一次 `brain.py` 確認大腦還能用。
- 從第 11 課改的：照 `README.md` 第六節，用 `brain.py --link ble` 跑 10 秒。
- 沒反應、OLED 停在奇怪的畫面：程式在板子上出錯了。看錯誤訊息要用序列埠（VS Code 任務「ESP32: Serial monitor」，離開按 `Ctrl+]`）；或先還原（第六節），回電腦上改。

## 六、交出去之前：還原成 W12 選單（一定要做）

在 maker-esp32 資料夾，三行照順序跑（`aiot-ai-ref` 要在旁邊，第三節第 1 步）：

Mac／Ubuntu：

```
./tools/upload.sh
uv run mpremote connect auto sleep 2 cp ../aiot-ai-ref/w12/starter/esp32/main_w12.py :main.py
uv run mpremote connect auto sleep 2 reset
```

Windows：

```
powershell -ExecutionPolicy Bypass -File tools\upload.ps1
uv run mpremote connect auto sleep 2 cp ..\aiot-ai-ref\w12\starter\esp32\main_w12.py :main.py
uv run mpremote connect auto sleep 2 reset
```

第一行把創客課的全部檔案傳回去（包括原本的第 10、11 課），第二行把 `main.py` 換回 W12 選單，第三行重開。〔程式：跟老師課前刷板的步驟同一套〕

還原後**親眼確認**：OLED 先出現 `AIoT W12`、`WiFi (d10)`，再變成 `WiFi 遙控` 那四行；有時間的話，再按住 A 開機一次，確認看得到 `BLE  (d11)`。確認了才交給下一組。

你改的 `my_d10.py` 還留在你的電腦上（板子上也會留一份在 `demos/`，不影響別人）；想留著就自己備份。

## 七、改程式常見的錯

| 看到 | 原因 | 怎麼辦 |
|---|---|---|
| 板子上燈不聽話、亮暗怪怪的 | 對 `ezkit.py` 已經用的腳位又建了一次 `Pin(...)` 或 `PWM(...)` | 改用 `ezkit.py` 的名字（`led_red.on()`、`led_red_pwm.duty(...)`），不要自己建 |
| 網頁或藍牙反應很慢、按鍵漏掉 | 迴圈裡有很長的 `time.sleep()` | 改用 `time.ticks_ms()` 判斷時間到了沒，`sleep` 最多幾十毫秒 |
| OLED 中文變方塊 | 字型檔沒有那個字 | 換成英數字，或用字型檔裡有的字；要加字照 maker-esp32 `AGENTS.md` 的做法 |
| 大腦 `brain.py` 改完就讀不到東西 | 改到或刪了原本的網址、JSON 欄位、藍牙指令 | 把原本的放回去，新功能用新名字 |
| `ImportError`、`NameError` 出現在板子上 | 打錯名字、少了 `from lib.ezkit import *` | 看序列埠的錯誤訊息那一行，回電腦改；先用第四節的語法檢查 |
| 上傳到一半失敗 | 序列埠被別的程式佔著、線鬆了 | 關掉序列埠監看，按 EN，再上傳一次 |
