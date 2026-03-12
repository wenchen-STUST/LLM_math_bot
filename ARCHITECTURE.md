# Mathbot 專案架構說明

## 專案概述
這是一個基於 Django + Ollama 的數學助教聊天機器人，專為微積分學生設計。

---

## 目錄結構

```
X:\llm_chatbot\
├── requirements.txt          # Python 依賴
└── web_chat/               # Django 專案
    ├── manage.py           # Django 管理腳本
    ├── db.sqlite3          # SQLite 資料庫
    ├── chatapp/            # 主應用程式
    │   ├── models.py       # 資料庫模型
    │   ├── views.py        # 視圖函數 (API 端點)
    │   ├── urls.py         # URL 路由對照表
    │   ├── admin.py        # Django 管理後台
    │   ├── apps.py         # App 配置
    │   ├── migrations/     # 資料庫遷移
    │   └── __pycache__/    # 編譯快取
    ├── web_chat/           # Django 專案配置
    │   ├── settings.py     # 專案設定 (含 Prompt)
    │   ├── urls.py        # 根 URL 配置
    │   └── wsgi.py        # WSGI 入口
    └── templates/
        └── chat.html       # 前端頁面
```

---

## URL 路由對照表

| 前端路徑 | 對應函數 | 功能說明 |
|----------|----------|----------|
| `/` | `TemplateView` | 渲染 chat.html 首頁 |
| `/api/sessions/` | `list_sessions` | 取得對話列表 |
| `/api/sessions/create/` | `create_session` | 建立新對話 |
| `/api/sessions/<id>/` | `get_session` | 取得特定對話 |
| `/api/sessions/<id>/delete/` | `delete_session` | 刪除對話 |
| `/api/sessions/<id>/summarize/` | `summarize_session` | 摘要對話 |
| `/api/chat/stream/` | `chat_stream` | 串流聊天 API (主要) |
| `/api/chat/` | `chat` | 非串流聊天 (向後相容) |
| `/api/math/recognize/` | `recognize_formula` | 圖片公式辨識 (OCR) |
| `/api/math/chat/` | `math_chat` | 數學解題 API |
| `/api/math/check/` | `check_answer` | 檢查解答 |
| `/api/auth/login/` | `login_view` | 用戶登入 |
| `/api/auth/register/` | `register_view` | 用戶註冊 |
| `/api/auth/logout/` | `logout_view` | 用戶登出 |
| `/api/stats/usage/` | `get_usage_stats` | 使用量統計 |

---

## 資料庫模型 (models.py)

| 模型名稱 | 用途 |
|----------|------|
| `UserProfile` | 用戶擴展資料 (一對一綁定 User) |
| `ChatSession` | 對話會話 (包含標題、摘要、建立時間) |
| `ChatMessage` | 訊息記錄 (role: user/assistant, content) |
| `ImageCache` | 圖片快取 (以 prompt hash 索引) |
| `UsageStats` | 使用量統計 (tokens, 訊息數) |

---

## 關鍵設定 (settings.py)

| 變數 | 說明 | 預設值 |
|------|------|--------|
| `OLLAMA_BASE_URL` | Ollama API 伺服器 | `http://localhost:11434` |
| `DEFAULT_MODEL` | 預設語言模型 | `qwen2.5:7b` |
| `VISION_MODEL` | 視覺辨識模型 | `qwen2.5vl:latest` |
| `MATH_TEACHER_SYSTEM_PROMPT` | 數學助教 Prompt | (見 settings.py:87-141) |

---

## 前端頁面 (chat.html)

| 區塊 | 功能 |
|------|------|
| `#sidebar` | 對話列表側邊欄 |
| `#chat-container` | 訊息顯示區域 |
| `.input-bar` | 輸入框 (文字/圖片) |
| `#formula-modal` | 公式辨識結果彈窗 |
| `#check-modal` | 解答檢查彈窗 |
| `#stats-modal` | 使用量統計彈窗 |

### 前端 JavaScript 函數

| 函數 | 位置 | 功能 |
|------|------|------|
| `createNewChat()` | :689 | 建立新對話 |
| `loadSession(id)` | :716 | 載入對話歷史 |
| `sendMessage()` | :750 | 發送訊息 |
| `addMessage(role, content)` | :631 | 渲染訊息 |
| `loadSessions()` | :820 | 取得對話列表 |
| `deleteSession(id)` | :814 | 刪除對話 |
| `openCheckModal()` | :494 | 開啟解答檢查 |
| `openStatsModal()` | :511 | 開啟統計面板 |
| `recognizeFormula()` | :607 | 辨識圖片公式 |

---

## Prompt 說明

### chat_stream 的 system prompt (views.py:355-423)
- 核心任務：教導學生「如何思考」數學問題
- 風格：蘇格拉底問答法 + 直接解答
- 涵蓋：基礎微積分 + 進階微積分

### MATH_TEACHER_SYSTEM_PROMPT (settings.py:87-141)
- 用於 `math_chat` API
- 與 chat_stream 類似，但更強調教學互動
