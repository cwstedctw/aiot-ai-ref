# AIoT 智慧裝置實作（115-1）：給 AI 讀的參考資料

這個 repo 是寫給**你的 AI agent**（Antigravity、`agy` 或其他 AI 助手）讀的。裡面放了每一週用到的板子、程式、指令和常見錯誤，AI 讀過之後，回答會比較貼近我們課堂上的真實狀況，不會叫你裝一堆用不到的東西。

給人看的完整步驟還是看各週的學生頁，連結在 e學苑。

## 怎麼用（三選一）

**1. 直接把網址給 AI（最快）**：把下面這句複製給筆電上的 Antigravity，空格填你要它幫的事：

```
請先讀 https://github.com/cwstedctw/aiot-ai-ref 的 AGENTS.md 和 w12/README.md，照裡面的規則幫我：＿＿＿＿
```

例如：「看懂這段錯誤訊息（貼上整段，密碼先刪掉）」「我想讓濕度高的時候亮黃燈，rules.py 要改哪裡」「為什麼藍牙掃不到我的 ESP32」「幫我一步一步檢查這塊 ESP32 是不是好的（讀 [w12/esp32/README.md](w12/esp32/README.md)）」。

**2. 下載到筆電**，用 Antigravity 開這個資料夾：

```
git clone https://github.com/cwstedctw/aiot-ai-ref.git
```

**3. 放到板子上給 `agy` 讀**（要在 UNO Q 連 ESP32 的 WiFi **之前**做；連上之後板子沒有外網，板子上的 `agy` 也會連不上，這時候改用筆電上的 AI。⚠️ 這個方法老師還沒在板子上試過，不行就用第 1 種）：

```
cd ~
curl -fL https://github.com/cwstedctw/aiot-ai-ref/archive/refs/heads/main.tar.gz | tar xz
cd aiot-ai-ref-main
agy
```

## 三個提醒

- **板子密碼、任何金鑰都不要貼給 AI。** 錯誤訊息裡如果有，先刪掉再貼。
- **AI 改的程式，你自己看懂再存回板子。** 改哪一行、為什麼，請它講清楚。
- **作業的數字要你自己在真板上量。** 60 秒的紀錄檔、三句比較，AI 可以幫你看懂數字，但不能幫你編。

## 有哪些週

| 夾 | 週次 | 主題 |
|---|---|---|
| [`w12/`](w12/README.md) | W12（11/26） | 雙腦合作：UNO Q 當大腦、ESP32 當手腳（WiFi＋藍牙） |
