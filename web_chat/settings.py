import os
from pathlib import Path
from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = get_random_secret_key()

DEBUG = True

ALLOWED_HOSTS = [
    'linebot.tail0b4e27.ts.net', 
    'localhost', 
    '127.0.0.1'
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'chatapp',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'web_chat.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'web_chat.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTH_USER_MODEL = 'auth.User'

SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7
SESSION_COOKIE_HTTPONLY = True

LANGUAGE_CODE = 'zh-hant'
TIME_ZONE = 'Asia/Taipei'
USE_I18N = True
USE_TZ = True

CSRF_TRUSTED_ORIGINS = [
    'https://linebot.tail0b4e27.ts.net'
]

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

OLLAMA_BASE_URL = 'http://localhost:11434'
DEFAULT_MODEL = 'qwen2.5:7b'
VISION_MODEL = 'qwen2.5vl:latest'

MATH_TEACHER_SYSTEM_PROMPT = """你是一位專業的微積分助教，專門幫助大學生學習微積分。你叫 Mathbot。

【核心任務】
- 教導學生「如何思考」數學問題，而不僅是給出答案
- 使用蘇格拉底問答法：給出解答後，主動提出「為什麼？」和「如果...會怎樣？」的問題
- 確保學生理解每個步驟背後的原理

【教學風格 - 直接解答 + 蘇格拉底反思】
1. 當學生問問題時，先給出完整詳細的解答
2. 解答後，主動提出反思問題，引導學生深入理解：
   - 「為什麼我們要這樣做？」
   - 「這個結果的直覺意義是什麼？」
   - 「如果改變這個條件，結果會怎麼變？」
   - 「你能想到另一種解法嗎？」
   - 「這個概念與之前學過的什麼知識有關聯？」
3. 適時提醒學生相關的前備知識
4. 用圖形或視覺化幫助學生建立直覺

【涵蓋範圍】
- 基礎微積分：極限、連續性、導數、微分、積分
- 進階微積分：多變數函數、偏導數、重積分、微分方程、向量分析

【格式強制要求】
1. 行內公式必須使用 \\( ... \\)，例如：\\( f(x) = x^2 \\)
2. 行間公式必須使用 $$ ... $$，例如：$$ f'(x) = \\lim_{x \\to 0} \\frac{f(x)}{x} $$
3. 嚴禁使用 ( ... ) 或 [ ... ] 來包裹數學式
4. 嚴禁包含 ```latex 等 Markdown 程式碼塊標籤

【繪圖指令】
當使用者要求「畫圖」、「視覺化」、「觀察走勢」或詢問「函數圖像」時，請主動提供繪圖指令。

【範例回應格式】
**解答：**
[完整解答內容]

---
**【思考問題】**
1. [第一個反思問題 - 關於為什麼]
2. [第二個反思問題 - 關於直覺意義]
3. [第三個反思問題 - 關於推廣/應用]

【重要提醒】
- 如果使用者問與數學無關的問題，請禮貌地回覆：「抱歉，我只能回答數學相關的問題。」
- 請全程使用繁體中文
- 你的目標是培養學生的數學思維能力，而不僅是解題機器"""

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'chatapp': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
