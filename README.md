# opux-to-csv

將 1Password 的 1PUX 格式轉換為 Apple CSV 格式的工具

## 簡介

`opux-to-csv` 是一個 Python 工具，用於將 1Password 匯出的 1PUX（1Password Unencrypted Export）格式檔案轉換為 Apple CSV 格式，方便匯入到其他密碼管理工具或進行資料備份。

本工具基於 [1Password 1PUX 格式文件](https://support.1password.com/1pux-format/) 實作，支援解析 1PUX ZIP 檔案中的 `export.data` JSON 結構。

## 功能特色

- 自動解析 1PUX ZIP 檔案格式
- 完整提取所有重要欄位：Title、URL、Username、Password、Notes、OTPAuth
- 支援 OTP（一次性密碼）欄位轉換
- 智能合併多餘資訊到 Notes 欄位
- 保留標籤、額外欄位、密碼歷史等資訊
- 支援多個 Vault 和 Account
- 可選包含已歸檔的項目

## 需求

- Python 3.13 或更高版本
- [uv](https://github.com/astral-sh/uv)（推薦）或標準 Python 環境

## 安裝

### 使用 uv（推薦）

```bash
# 克隆專案
git clone <repository-url>
cd opux-to-csv

# 使用 uv 執行（無需安裝）
uv run python main.py --help
```

### 使用標準 Python

```bash
# 克隆專案
git clone <repository-url>
cd opux-to-csv

# 直接執行
python main.py --help
```

## 使用方法

### 基本用法

```bash
uv run python main.py <1pux檔案路徑>
```

這會自動產生一個與輸入檔案同名的 CSV 檔案（副檔名改為 `.csv`）。

### 指定輸出檔案

```bash
uv run python main.py <1pux檔案路徑> -o output.csv
```

### 包含已歸檔的項目

```bash
uv run python main.py <1pux檔案路徑> --include-archived
```

### 完整範例

```bash
# 轉換 1PUX 檔案
uv run python main.py my-export.1pux -o passwords.csv

# 包含已歸檔項目
uv run python main.py my-export.1pux -o all-passwords.csv --include-archived
```

## 輸出格式

轉換後的 CSV 檔案包含以下欄位：

| 欄位 | 說明 | 來源 |
|------|------|------|
| **Title** | 項目標題 | `overview.title` |
| **URL** | 主要網址 | `overview.url` 或 `overview.urls[0]` |
| **Username** | 使用者名稱 | `details.loginFields` 中 `designation="username"` 的欄位 |
| **Password** | 密碼 | `details.loginFields` 中 `designation="password"` 的欄位 |
| **Notes** | 備註 | 合併 `notesPlain`、標籤、其他欄位、額外資訊等 |
| **OTPAuth** | OTP 認證 URI | `details.sections` 中 TOTP 欄位的 `otpauth://` URI |

### Notes 欄位內容

Notes 欄位會自動合併以下資訊，不同區段之間使用 `---` 分隔：

1. **原始備註**：來自 `notesPlain` 欄位的內容
2. **標籤**：所有標籤以逗號分隔顯示
3. **其他登入欄位**：非 username/password 的登入欄位
4. **Sections 額外資訊**：Sections 中的欄位會根據類型智能格式化：
   - `ssoLogin` 類型：只顯示 provider 名稱（如 "facebook"、"google"）
   - `address` 類型：格式化為完整地址字串
   - `menu` 類型：顯示選單選項值
   - `concealed` 類型：顯示隱藏值
   - `string` 類型：顯示字串值
   - 其他複雜類型會嘗試提取可讀值，避免輸出 JSON 結構
5. **其他網址**：如果有多個 URL，額外的 URL 會列在此處
6. **密碼歷史記錄**：顯示密碼歷史記錄的數量

## 專案結構

```text
opux-to-csv/
├── main.py              # 主要轉換邏輯
├── pyproject.toml       # 專案設定檔
└── README.md           # 本檔案
```

## 開發

### 執行測試

```bash
# 執行轉換測試（使用你自己的 1PUX 檔案）
uv run python main.py <your-export.1pux> -o test_output.csv
```

## 注意事項

- 1PUX 格式是**未加密**的匯出格式，請妥善保管檔案
- 轉換後的 CSV 檔案包含敏感資訊，請注意檔案安全
- 預設情況下，已歸檔（archived）的項目不會被轉換
- CSV 檔案使用 UTF-8 with BOM 編碼，確保在 Excel 中正確顯示中文

## 貢獻

歡迎提交 Issue 或 Pull Request！

## 授權

本專案採用 MIT 授權條款。

## 相關連結

- [1Password 1PUX 格式文件](https://support.1password.com/1pux-format/)
- [uv 專案](https://github.com/astral-sh/uv)
