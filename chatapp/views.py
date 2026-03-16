"""
Mathbot 聊天機器人 - 視圖函數

區塊說明：
├── 工具函數 (validate_python_code, try_sympy_plot, get_user_from_request)
├── 認證視圖 (login_view, register_view, logout_view)
├── 對話管理 (list_sessions, create_session, get_session, delete_session)
├── 聊天功能 (chat_stream, chat) - 主要 API
├── 數學功能 (math_chat, recognize_formula, check_answer)
├── 對話摘要 (summarize_session)
└── 統計功能 (get_usage_stats)
"""

import json
import requests
import re          
import os           
import base64       
import subprocess    
import sys
import logging
import ast
import hashlib
import uuid
from datetime import timedelta

from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone

from .models import ChatSession, ChatMessage, ImageCache, UsageStats, UserProfile

logger = logging.getLogger(__name__)


def validate_python_code(code: str) -> tuple[bool, str]:
    """驗證 Python 程式碼是否安全，只允許繪圖相關的安全操作"""
    dangerous_patterns = [
        r'\bimport\s+os\b', r'\bimport\s+sys\b', r'\bimport\s+subprocess\b',
        r'\bimport\s+socket\b', r'\bimport\s+urllib\b', r'\bimport\s+requests\b',
        r'\bimport\s+http\b', r'\bimport\s+ftplib\b', r'\bimport\s+smtplib\b',
        r'\bimport\s+glob\b', r'\bimport\s+shutil\b', r'\bimport\s+pickle\b',
        r'\bfrom\s+os\b', r'\bfrom\s+sys\b', r'\bfrom\s+subprocess\b',
        r'\bfrom\s+socket\b', r'\bfrom\s+urllib\b', r'\bfrom\s+requests\b',
        r'\bexec\b', r'\beval\b', r'\bcompile\b', r'\bopen\s*\(',
        r'\bfile\b', r'\binput\b', r'\b__import__\b',
        r'\bos\.', r'\bsys\.', r'\bsubprocess\.', r'\bsocket\.',
        r'\bcommands\.', r'\bpopen\b', r'\bspawn\b',
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, code, re.IGNORECASE):
            return False, f"不安全：檢測到禁止的模式 '{pattern}'"
    
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name not in ('matplotlib', 'matplotlib.pyplot', 'numpy', 'math', 'random'):
                    
                        return False, f"不安全：禁止匯入 '{alias.name}'"
            elif isinstance(node, ast.ImportFrom):
                if node.module not in ('matplotlib', 'matplotlib.pyplot', 'numpy', 'math', 'random'):
                    return False, f"不安全：禁止從 '{node.module}' 匯入"
    except SyntaxError as e:
        return False, f"語法錯誤：{str(e)}"
    
    return True, "安全"


def try_sympy_plot(ai_ans, plot_path):
    """嘗試用 SymPy 解析簡單表達式並繪圖，失敗則回傳 None"""
    try:
        import sympy
        import numpy
        from sympy import symbols, ln, log, sin, cos, tan, exp, sqrt, Abs
        
        code_match = re.search(r'```python\s*(.*?)\s*```', ai_ans, re.DOTALL)
        if not code_match:
            return None
        
        python_code = code_match.group(1).strip()
        
        if any(k in python_code for k in ['np.', 'array', 'linspace', 'arange', 'def ', 'for ', 'while ']):
            return None
        
        x = symbols('x')
        expressions = []
        
        patterns = [
            r'y\s*=\s*(.+)',
            r'plt\.plot\([^,]+,\s*(.+)',
            r'^(.+)$',
        ]
        
        for line in python_code.split('\n'):
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('import'):
                continue
            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    expr_str = match.group(1).strip()
                    try:
                        expr = sympy.sympify(expr_str)
                        if expr.free_symbols <= {x}:
                            expressions.append((expr_str, expr))
                            break
                    except:
                        continue
        
        if not expressions:
            return None
        
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        
        plt.rcParams['font.family'] = ['Microsoft JhengHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        
        colors = ['#0a84ff', '#ff453a', '#30d158', '#bf5af2', '#ff9f0a']
        fig, ax = plt.subplots(figsize=(8, 6))
        
        for i, (expr_str, expr) in enumerate(expressions):
            try:
                f = sympy.lambdify(x, expr, modules=['numpy', 'math'])
                x_plot = numpy.linspace(-10, 10, 500)
                with numpy.errstate(invalid='ignore', divide='ignore'):
                    y_plot = f(x_plot)
                mask = numpy.isfinite(y_plot)
                ax.plot(x_plot[mask], y_plot[mask], color=colors[i % len(colors)], linewidth=2, label=expr_str)
            except Exception as e:
                continue
        
        if not ax.lines:
            return None
        
        ax.spines['left'].set_position('zero')
        ax.spines['bottom'].set_position('zero')
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.spines['left'].set_linewidth(1.5)
        ax.spines['bottom'].set_linewidth(1.5)
        ax.plot(1, 0, '>k', transform=ax.get_yaxis_transform(), clip_on=False, markersize=6)
        ax.plot(0, 1, '^k', transform=ax.get_xaxis_transform(), clip_on=False, markersize=6)
        ax.grid(True, alpha=0.3)
        ax.legend()
        ax.set_xlim(-10, 10)
        
        plt.savefig(plot_path, bbox_inches='tight')
        plt.close()
        
        return plot_path
    except Exception as e:
        logger.info(f"SymPy error: {e}")
        return None


# ============================================================================
# 工具函數區塊
# ============================================================================

def get_user_from_request(request):
    """從請求中獲取用戶，如果未登入返回 None"""
    if request.user.is_authenticated:
        return request.user
    return None


# ============================================================================
# 認證視圖區塊 (login, register, logout)
# ============================================================================

@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return JsonResponse({'error': '請輸入用戶名和密碼'}, status=400)
        
        user = authenticate(username=username, password=password)
        if user:
            login(request, user)
            return JsonResponse({'status': 'ok', 'username': user.username})
        else:
            return JsonResponse({'error': '用戶名或密碼錯誤'}, status=401)
    return JsonResponse({'error': 'Invalid method'}, status=405)


@csrf_exempt
def register_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        username = data.get('username', '').strip()
        password = data.get('password', '')
        password2 = data.get('password2', '')
        
        if not username or not password:
            return JsonResponse({'error': '請輸入用戶名和密碼'}, status=400)
        
        if password != password2:
            return JsonResponse({'error': '兩次密碼不一致'}, status=400)
        
        if User.objects.filter(username=username).exists():
            return JsonResponse({'error': '用戶名已存在'}, status=400)
        
        user = User.objects.create_user(username=username, password=password)
        UserProfile.objects.create(user=user)
        login(request, user)
        return JsonResponse({'status': 'ok', 'username': user.username})
    return JsonResponse({'error': 'Invalid method'}, status=405)


def logout_view(request):
    logout(request)
    return JsonResponse({'status': 'ok'})


@csrf_exempt
@require_http_methods(["GET"])
def get_user_status(request):
    """取得目前用戶狀態"""
    user = get_user_from_request(request)
    if user:
        return JsonResponse({'username': user.username})
    return JsonResponse({})


@require_http_methods(["GET"])
def api_index(request):
    return JsonResponse({'status': 'ok', 'message': 'Mathbot API 運行中'})


# ============================================================================
# 對話管理區塊 (list, create, get, delete, summarize sessions)
# ============================================================================

@csrf_exempt
@require_http_methods(["GET"])
def list_sessions(request):
    user = get_user_from_request(request)
    if user:
        sessions = ChatSession.objects.filter(user=user).order_by('-updated_at')[:50]
    else:
        sessions = ChatSession.objects.filter(user__isnull=True).order_by('-updated_at')[:50]
    data = [{'id': s.id, 'title': s.title} for s in sessions]
    return JsonResponse({'sessions': data})


@csrf_exempt
@require_http_methods(["POST"])
def create_session(request):
    try:
        logger.info(f"Create session request body: {request.body}")
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            data = {}
        logger.info(f"Parsed data: {data}")
        user = get_user_from_request(request)
        logger.info(f"User: {user}")
        session = ChatSession.objects.create(
            user=user,
            title=data.get('title', '新對話')
        )
        logger.info(f"Session created: {session.id}")
        response = JsonResponse({'id': session.id, 'title': session.title})
        logger.info(f"Response: {response.content}")
        return response
    except Exception as e:
        logger.error(f"Create session error: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_session(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id)
    messages = session.messages.all().order_by('created_at')
    return JsonResponse({
        'id': session.id,
        'title': session.title,
        'summary': session.summary,
        'messages': [{'role': m.role, 'content': m.content} for m in messages]
    })


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_session(request, session_id):
    ChatSession.objects.filter(id=session_id).delete()
    return JsonResponse({'status': 'ok'})


@csrf_exempt
@require_http_methods(["POST"])
def summarize_session(request):
    """對話摘要功能"""
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        
        session = get_object_or_404(ChatSession, id=session_id)
        messages = session.messages.all().order_by('-created_at')[:10]
        
        if messages.count() < 3:
            return JsonResponse({'summary': '對話太短，無法產生摘要'})
        
        conversation = "\n".join([
            f"{m.role}: {m.content[:200]}" 
            for m in reversed(list(messages))
        ])
        
        summary_prompt = f"""請用 50 字以內簡潔地總結以下對話的主要內容：
{conversation}

摘要："""
        
        payload = {
            'model': settings.DEFAULT_MODEL,
            'messages': [
                {'role': 'system', 'content': '你是一個對話摘要助手，請用簡潔的繁體中文摘要對話。'},
                {'role': 'user', 'content': summary_prompt}
            ],
            'stream': False
        }
        
        res = requests.post(
            f"{settings.OLLAMA_BASE_URL}/api/chat",
            json=payload,
            timeout=60
        )
        res.raise_for_status()
        summary = res.json().get('message', {}).get('content', '').strip()
        
        session.summary = summary
        session.save()
        
        return JsonResponse({'summary': summary})
    except Exception as e:
        logger.error(f"Summarize error: {e}")
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================================
# 聊天功能區塊 (chat_stream - 主要 API, chat - 向後相容)
# ============================================================================

@csrf_exempt
@require_http_methods(["POST"])
def chat_stream(request):
    """串流回應功能"""
    try:
        data = json.loads(request.body)
        user_msg = data.get('message', '').strip()
        session_id = data.get('session_id')

        if not user_msg:
            return JsonResponse({'error': '訊息不能為空'}, status=400)

        user = get_user_from_request(request)
        session = get_object_or_404(ChatSession, id=session_id)
        
        if session.user and session.user != user:
            return JsonResponse({'error': '無權訪問'}, status=403)
        
        ChatMessage.objects.create(session=session, role='user', content=user_msg, model=settings.DEFAULT_MODEL)

        history_queryset = session.messages.all().order_by('-created_at')[:10]
        history = reversed(list(history_queryset))
        
        system_prompt = """你是一位專業的微積分助教，專門幫助大學生學習微積分。你叫 Mathbot。

【核心任務】
- 教導學生「如何思考」數學問題，而不僅是給出答案
- 使用蘇格拉底問答法：給出解答後，主動提出「為什麼？」和「如果...會怎樣？」的問題
- 確保學生理解每個步驟背後的原理

【教學風格】
1. 當學生問問題時，先給出完整詳細的解答
2. 解答後，主動提出反思問題，例如：
   - 「為什麼我們要這樣做？」
   - 「這個結果的直覺意義是什麼？」
   - 「如果改變這個條件，結果會怎麼變？」
   - 「你能想到另一種解法嗎？」
3. 適時提醒學生相關的前備知識

【範例回應格式】
解答內容...
---
【思考問題】
1. [第一個反思問題]
2. [第二個反思問題]

【涵蓋範圍】
- 基礎微積分：極限、連續性、導數、微分、積分
- 進階微積分：多變數函數、偏導數、重積分、微分方程、向量分析

【格式強制要求】
1. 行內公式必須使用 \( ... \)，例如：\( f(x) = x^2 \)
2. 行間公式必須使用 $$ ... $$，例如：$$ f'(x) = \lim_{x \to 0} \frac{f(x)}{x} $$
3. 嚴禁使用 [ 作為公式開始，嚴禁使用 ] 作為公式結束
4. 嚴禁使用 ( 作為公式開始，嚴禁使用 ) 作為公式結束（請用 \( 和 \) 代替）
5. 嚴禁包含 ```latex 等 Markdown 程式碼塊標籤

【LaTeX 語法提醒】
- 使用 \left( 必須搭配 \right)
- 使用 \left[ 必須搭配 \right]
- 使用 \left. 必須搭配 \right
- 嚴禁混用不同的括號類型
- 嚴格確保每個 \left 都有對應的 \right

【繪圖指令】
當使用者要求「畫圖」、「畫出...圖形」、「畫示意圖」、「視覺化」、「顯示圖形」時，請提供 Python 程式碼來繪圖。

【繪圖格式 - 簡單表達式優先】
1. 簡單函數（如 y = ln(x), y = x^2, y = sin(x)）使用以下格式：
```python
y = ln(x)
```

2. 複雜圖形使用完整 matplotlib 程式碼：
```python
import matplotlib
matplotlib.use('Agg')
import numpy as np
import matplotlib.pyplot as plt

x = np.linspace(-10, 10, 500)
y = np.sin(x)
plt.plot(x, y)
plt.grid(True, alpha=0.3)
plt.savefig('temp_plot.png', bbox_inches='tight')
```

3. 禁止使用 plt.show()

【重要提醒】
- 如果使用者問與數學無關的問題，請禮貌地回覆：「抱歉，我只能回答數學相關的問題。」
- 嚴禁使用 [ 作為公式開始，嚴禁使用 ] 作為公式結束
- 嚴禁使用 ( 作為公式開始，嚴禁使用 ) 作為公式結束
- 請全程使用繁體中文
- 盡可能用圖形或視覺化幫助學生建立直覺"""

        ollama_msgs = [{"role": "system", "content": system_prompt}]
        for m in history:
            ollama_msgs.append({"role": m.role, "content": m.content})

        res = requests.post(
            f"{settings.OLLAMA_BASE_URL}/api/chat",
            json={'model': settings.DEFAULT_MODEL, 'messages': ollama_msgs, 'stream': True},
            stream=True,
            timeout=120
        )
        res.raise_for_status()
        
        full_response = ""
        for line in res.iter_lines():
            if line:
                try:
                    chunk = json.loads(line)
                    content = chunk.get('message', {}).get('content', '')
                    full_response += content
                except:
                    continue
        
        logger.debug(f"LLL response = {full_response[:800]}")

        code_match = re.search(r'```python\s*(.*?)\s*```', full_response, re.DOTALL)

        if code_match:
            python_code = code_match.group(1)
            
            if "matplotlib.use" not in python_code:
                font_header = (
                    "import matplotlib\n"
                    "matplotlib.use('Agg')\n"
                    "import matplotlib.pyplot as plt\n"
                    "plt.rcParams['font.family'] = ['Microsoft JhengHei', 'DejaVu Sans']\n"
                    "plt.rcParams['axes.unicode_minus'] = False\n"
                )
                python_code = font_header + python_code
            else:
                if "rcParams" not in python_code:
                    inject = (
                        "plt.rcParams['font.family'] = ['Microsoft JhengHei', 'DejaVu Sans']\n"
                        "plt.rcParams['axes.unicode_minus'] = False\n"
                    )
                    python_code = re.sub(
                        r'(import matplotlib\.pyplot.*?\n)',
                        r'\1' + inject,
                        python_code,
                        count=1
                    )

            python_code = python_code.replace("plt.show()", "")

            base_dir = os.path.dirname(os.path.abspath(__file__))
            temp_dir = os.path.join(base_dir, "temp_files")
            os.makedirs(temp_dir, exist_ok=True)

            script_path = os.path.join(temp_dir, f"temp_script_{uuid.uuid4().hex}.py")
            plot_path = os.path.join(temp_dir, f"temp_plot_{uuid.uuid4().hex}.png")
            safe_plot_path = plot_path.replace('\\', '/')

            prompt_hash = hashlib.sha256(full_response.encode()).hexdigest()
            cache_key = f"{session_id}:{prompt_hash}"
            
            cached = ImageCache.objects.filter(
                session=session,
                prompt_hash=cache_key
            ).first()
            
            if cached:
                img_html = (
                    f"<br><img src='data:image/png;base64,{cached.image_data}' "
                    f"alt='Mathbot Generated Plot' "
                    f"style='max-width: 100%; border-radius: 8px; margin-top: 10px;'>"
                )
                full_response += img_html
            else:
                sympy_result = try_sympy_plot(full_response, plot_path)
                logger.debug(f"sympy_result = {sympy_result}")
                
                import glob
                plot_files = glob.glob(os.path.join(temp_dir, "temp_plot_*.png"))
                logger.debug(f"plot_files = {plot_files}")
                
                if sympy_result or plot_files:
                    actual_plot_path = plot_files[0] if plot_files else plot_path
                    with open(actual_plot_path, 'rb') as img_file:
                        b64_string = base64.b64encode(img_file.read()).decode('utf-8')
                    
                    try:
                        ImageCache.objects.create(
                            session=session,
                            prompt_hash=cache_key,
                            image_data=b64_string
                        )
                    except:
                        pass
                    
                    img_html = (
                        f"<br><img src='data:image/png;base64,{b64_string}' "
                        f"alt='Mathbot Generated Plot' "
                        f"style='max-width: 100%; border-radius: 8px; margin-top: 10px;'>"
                    )
                    full_response += img_html
                    if os.path.exists(actual_plot_path):
                        os.remove(actual_plot_path)
                else:
                    cross_axis_code = """
ax = plt.gca()
ax.spines['left'].set_position('zero')
ax.spines['bottom'].set_position('zero')
ax.spines['right'].set_visible(False)
ax.spines['top'].set_visible(False)
ax.spines['left'].set_linewidth(1.5)
ax.spines['bottom'].set_linewidth(1.5)
ax.plot(1, 0, '>k', transform=ax.get_yaxis_transform(), clip_on=False, markersize=6)
ax.plot(0, 1, '^k', transform=ax.get_xaxis_transform(), clip_on=False, markersize=6)
"""
                    python_code = re.sub(
                        r"plt\.savefig\(['\"](\w+\.png)['\"]",
                        f"plt.savefig('{safe_plot_path}'",
                        python_code
                    )
                    
                    if "plt.savefig" not in python_code:
                        python_code += cross_axis_code
                        python_code += f"\nplt.savefig('{safe_plot_path}', bbox_inches='tight')"

                    is_safe, safety_msg = validate_python_code(python_code)
                    if not is_safe:
                        logger.warning(f"Blocked unsafe code execution: {safety_msg}")
                        full_response += f"\n\n<br><i>[安全警告：{safety_msg}]</i>"
                    else:
                        try:
                            with open(script_path, "w", encoding="utf-8") as f:
                                f.write(python_code)
                            
                            result = subprocess.run(
                                [sys.executable, script_path],
                                timeout=15,
                                check=True,
                                capture_output=True,
                                text=True
                            )

                            plot_files = glob.glob(os.path.join(temp_dir, "temp_plot_*.png"))
                            
                            if plot_files:
                                actual_path = plot_files[0]
                                with open(actual_path, 'rb') as img_file:
                                    b64_string = base64.b64encode(img_file.read()).decode('utf-8')
                                
                                try:
                                    ImageCache.objects.create(
                                        session=session,
                                        prompt_hash=cache_key,
                                        image_data=b64_string
                                    )
                                except:
                                    pass
                                
                                img_html = (
                                    f"<br><img src='data:image/png;base64,{b64_string}' "
                                    f"alt='Mathbot Generated Plot' "
                                    f"style='max-width: 100%; border-radius: 8px; margin-top: 10px;'>"
                                )
                                full_response += img_html
                                os.remove(actual_path)
                            else:
                                full_response += "\n\n<br><i>[系統提示：程式碼執行成功但未產生圖片]</i>"
                            
                        except subprocess.CalledProcessError as e:
                            full_response += f"\n\n<br><i>[繪圖錯誤：{e.stderr}]</i>"
                        except Exception as e:
                            full_response += f"\n\n<br><i>[系統提示：嘗試繪製圖表時發生錯誤：{str(e)}]</i>"
                        finally:
                            if os.path.exists(script_path):
                                os.remove(script_path)

        full_response = re.sub(r'```python.*?```', '', full_response, flags=re.DOTALL).strip()
        
        # 過濾錯誤的數學式分隔符
        full_response = re.sub(r'\[([^\]]+)\]', r'$$\1$$', full_response)
        full_response = re.sub(r'\(([^)]+)\)', r'\(\1\)', full_response)
        
        # 修復 LaTeX 括號不匹配問題
        full_response = re.sub(r'\\left\.\s*\\right([\[\]])', r'\\right\1', full_response)
        full_response = re.sub(r'\\left\)\s*\\right([\[\]])', r'\\right\1', full_response)
        full_response = re.sub(r'\\left\]\s*\\right([\(\[])', r'\\right\1', full_response)
        
        ChatMessage.objects.create(session=session, role='assistant', content=full_response, model=settings.DEFAULT_MODEL)
        
        if session.title == '新對話':
            session.title = user_msg[:20]
        session.save()

        input_tokens = len(user_msg) // 4
        output_tokens = len(full_response) // 4
        UsageStats.objects.create(
            user=user,
            session=session,
            model_name=settings.DEFAULT_MODEL,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )

        return JsonResponse({'response': full_response, 'session_id': session.id})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def chat(request):
    """非串流回應（向後相容）"""
    return chat_stream(request)


# ============================================================================
# 數學功能區塊 (recognize_formula - OCR, math_chat - 解題, check_answer - 檢查解答)
# ============================================================================

@csrf_exempt
@require_http_methods(["POST"])
def recognize_formula(request):
    try:
        data = json.loads(request.body)
        img_b64 = data.get('image', '')
        
        payload = {
            'model': settings.VISION_MODEL,
            'messages': [
                {
                    "role": "system", 
                    "content": """你是一個專業的數學公式 OCR 專家。
                    請精準辨識圖片中的 LaTeX 公式。
                    規則：1. 只輸出 LaTeX 字串本身。
                    2. 嚴禁包含 ```latex 或任何反引號標籤。
                    3. 務必保留 \\lim 等關鍵符號。

                    特別注意：
                    1. 如果是極限務必辨識極限符號下方的趨近值（如 \\\\lim_{x \\to 1}）。
                    2. 如果公式包含運算過程，請完整保留。
                    3. 請直接輸出 LaTeX 程式碼即可。"""
                },
                {"role": "user", "content": "請精準辨識此公式並轉為 LaTeX", "images": [img_b64]}
            ],
            'stream': False,
            'options': {
                'temperature': 0.1,
                'num_gpu': 99
            }
        }
        res = requests.post(f"{settings.OLLAMA_BASE_URL}/api/chat", json=payload, timeout=120)
        res.raise_for_status()
        formula = res.json().get('message', {}).get('content', '')
        
        return JsonResponse({'formula': formula})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def math_chat(request):
    try:
        data = json.loads(request.body)
        user_msg = data.get('message', '').strip()
        session_id = data.get('session_id')
        mode = data.get('mode', 'step_by_step')
        formula = data.get('formula', '')
        
        user = get_user_from_request(request)
        session = get_object_or_404(ChatSession, id=session_id)
        
        if session.user and session.user != user:
            return JsonResponse({'error': '無權訪問'}, status=403)
        
        full_msg = f"【當前題目：{formula}】\n{user_msg}" if formula else user_msg
        ChatMessage.objects.create(session=session, role='user', content=full_msg, model=settings.DEFAULT_MODEL)
        
        history_queryset = session.messages.all().order_by('-created_at')[:6]
        history = reversed(list(history_queryset))
        
        if mode == 'step_by_step':
            mode_instruction = """你現在處於「逐步提示模式」。不要直接給出完整答案！
            - 只給出下一步的關鍵提示
            - 询问用户接下来怎么做
            - 鼓励他们自己思考和计算"""
        else:
            mode_instruction = """你現在處於「直接解答模式」。請提供完整詳細的解題步驟！"""
        
        system_prompt = f"""{settings.MATH_TEACHER_SYSTEM_PROMPT}

{mode_instruction}

如果使用者提供了公式（LaTeX 或文字），請先確認公式是否正確，然後開始解題。"""
        
        ollama_msgs = [{"role": "system", "content": system_prompt}]
        
        if formula:
            ollama_msgs.append({"role": "user", "content": f"我想要解的公式：{formula}"})
        
        for m in history:
            ollama_msgs.append({"role": m.role, "content": m.content})
        
        res = requests.post(
            f"{settings.OLLAMA_BASE_URL}/api/chat",
            json={'model': settings.DEFAULT_MODEL, 'messages': ollama_msgs, 'stream': False},
            timeout=120
        )
        res.raise_for_status()
        ai_ans = res.json().get('message', {}).get('content', '')
        
        ChatMessage.objects.create(session=session, role='assistant', content=ai_ans, model=settings.DEFAULT_MODEL)
        
        if session.title == '新對話':
            session.title = user_msg[:20]
        session.save()
        
        UsageStats.objects.create(
            user=user,
            session=session,
            model_name=settings.DEFAULT_MODEL,
            input_tokens=len(full_msg) // 4,
            output_tokens=len(ai_ans) // 4
        )
        
        return JsonResponse({'response': ai_ans, 'session_id': session.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def check_answer(request):
    try:
        data = json.loads(request.body)
        question_img = data.get('question_image', '')
        answer_img = data.get('answer_image', '')
        question_text = data.get('question_text', '')
        session_id = data.get('session_id')
        
        user = get_user_from_request(request)
        session = get_object_or_404(ChatSession, id=session_id) if session_id else None
        
        if session and session.user and session.user != user:
            return JsonResponse({'error': '無權訪問'}, status=403)
        
        messages = [{
            "role": "system", 
            "content": "你是一位嚴格的數學助教。請檢查圖片中的解答，指出計算錯誤並提供修正建議。請使用繁體中文。"
        }]
        
        user_content = "請幫我檢查這道數學題的解答是否正確。\n"
        if question_text:
            user_content += f"題目文字：{question_text}\n"
        
        images_to_send = []
        if question_img: images_to_send.append(question_img)
        if answer_img: images_to_send.append(answer_img)

        user_message = {"role": "user", "content": user_content}
        if images_to_send:
            user_message["images"] = images_to_send
        
        messages.append(user_message)

        payload = {
            'model': settings.VISION_MODEL if images_to_send else settings.DEFAULT_MODEL,
            'messages': messages,
            'stream': False
        }
        
        logger.info(f"檢查解答發送中，圖片數量: {len(images_to_send)}")

        res = requests.post(f"{settings.OLLAMA_BASE_URL}/api/chat", json=payload, timeout=120)
        res.raise_for_status()
        feedback = res.json().get('message', {}).get('content', '')
        
        if session:
            ChatMessage.objects.create(session=session, role='user', content='[檢查解答]', model=settings.DEFAULT_MODEL)
            ChatMessage.objects.create(session=session, role='assistant', content=feedback, model=settings.DEFAULT_MODEL)
            
            UsageStats.objects.create(
                user=user,
                session=session,
                model_name=settings.VISION_MODEL if images_to_send else settings.DEFAULT_MODEL,
                input_tokens=1,
                output_tokens=len(feedback) // 4
            )
        
        return JsonResponse({'response': feedback})
    except Exception as e:
        logger.error(f"Check Answer ERROR: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================================
# 統計功能區塊 (get_usage_stats - 使用量統計)
# ============================================================================

@csrf_exempt
@require_http_methods(["GET"])
def get_usage_stats(request):
    """取得使用量統計"""
    user = get_user_from_request(request)
    if not user:
        return JsonResponse({'error': '請先登入'}, status=401)
    
    stats = UsageStats.objects.filter(user=user)
    
    total_messages = stats.count()
    total_input_tokens = sum(s.input_tokens for s in stats)
    total_output_tokens = sum(s.output_tokens for s in stats)
    
    daily_stats = []
    for i in range(7):
        day = timezone.now().date() - timedelta(days=i)
        day_stats = stats.filter(created_at__date=day)
        daily_stats.append({
            'date': str(day),
            'messages': day_stats.count(),
            'input_tokens': sum(s.input_tokens for s in day_stats),
            'output_tokens': sum(s.output_tokens for s in day_stats)
        })
    
    return JsonResponse({
        'total_messages': total_messages,
        'total_input_tokens': total_input_tokens,
        'total_output_tokens': total_output_tokens,
        'daily_stats': daily_stats
    })
