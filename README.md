# movie-srt-zh-tw

將英文電影、紀錄片或影集 `.srt` 字幕全自動轉換為道地「台灣繁體中文」字幕（`*_zh-TW.srt`）的 Antigravity Skill。

透過「**Python 結構化切分與驗證 ＋《翻譯聖經》全片校準 ＋ 跨行預讀語意翻譯**」四階段全自動流程，確保長片（3,000 行以上）絕不截斷、時間軸 100% 零誤差、譯名與口吻全片一致，並產出完整 `QA_Report.md`。

---

## 目錄結構

```text
movie-srt-zh-tw/
├── README.md
├── SKILL.md                         # Antigravity Skill 主工作流指令
├── scripts/
│   └── srt_helper.py                # split / boundaries / merge / qa CLI 工具
└── references/
    └── localization_rules.md        # 台灣繁體中文電影字幕翻譯、標點與 CPS 規範
```

---

## 安裝方式（Antigravity）

### 方式 A：全域安裝（所有專案皆可使用）
將整個儲存庫內容放進自己電腦的全域 Skills 目錄：

- **Windows (PowerShell)：**
  ```powershell
  git clone https://github.com/laishou53-PaPa/movie-srt-zh-tw.git "$env:USERPROFILE\.gemini\config\skills\movie-srt-zh-tw"
  ```
- **macOS / Linux：**
  ```bash
  git clone https://github.com/laishou53-PaPa/movie-srt-zh-tw.git ~/.gemini/config/skills/movie-srt-zh-tw
  ```
> 若沒有安裝 Git，也可直接下載 ZIP 並解壓縮至上述目錄（注意資料夾名稱為 `movie-srt-zh-tw`）。

### 方式 B：專案內共用
複製本資料夾到任意專案的 `.agents/skills/movie-srt-zh-tw/`，團隊成員 `git pull` 後即可自動探索載入。

---

## 前置需求與使用方式

1. 電腦需安裝 **Python 3**（建議 3.10+）。
2. 在 Antigravity 對話中上傳或指定要翻譯的英文 `.srt` 字幕檔，並輸入：
   > 請使用 `movie-srt-zh-tw` skill 把這份英文字幕翻譯成台灣繁體中文字幕。
3. 執行完成後會產出：
   - `<電影名稱>_zh-TW.srt`（標準 UTF-8 編碼、100% 鎖定原始時間軸）
   - `Translation_Bible.md`（全片人物稱謂、譯名與雙關對照表）
   - `QA_Report.md`（時間軸健康度、行寬、CPS 與在地化檢查報告）

---

## 核心品管標準（全自動套用）

- **時間軸零誤差：** 總條數、起始／結束 ID 與每一條 `timecode` 逐條鎖定比對。
- **跨行預讀重組：** 預讀 3～5 條英文句子重組為自然中文語序，再依各條秒數比例分配。
- **台灣在地化：** 嚴格禁用簡體字與中國大陸用語（支援 Windows `LCMapStringEx zh-TW` 與跨平台 2,118 字純簡體字備援檢查）。
- **語意標點與間隔規範：**
  - 依文意自動補入適當全形中文標點（`，`、`、`、`：`、`。`、`？`、`！`），**禁用全形空格（`　`）斷句**。
  - **保留中英文／數字之間的半形空格**（如 `歡迎收聽 ABC 音訊的`、`120 奈米`）。
  - 行末／換行處維持乾淨不強加 `。`；中文標點旁不得殘留多餘空格；嚴禁半形 `,`、非小數點 `.`、`..`、`--`。
- **排版與閱讀速度：** 單條最多 2 行、單行理想 ≤ 16 全形字、閱讀速度目標 **CPS ≤ 13 字/秒**；雙人對話強制分兩行加 `- `。
