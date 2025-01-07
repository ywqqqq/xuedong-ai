import os
import time
import sqlite3
from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Body
from volcenginesdkarkruntime import Ark
import base64
from dotenv import load_dotenv
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import faiss
from sentence_transformers import SentenceTransformer
import numpy as np
import json
import requests
import uuid
from uvicorn import run
import subprocess
import wave
import hmac
import hashlib
import websocket
import ssl
import _thread as thread
from wsgiref.handlers import format_date_time
from urllib.parse import urlencode
import shutil
from time import mktime

# Load environment variables
load_dotenv('.env')

# Initialize FastAPI app
app = FastAPI()

# Database connection
def get_db():
    conn = sqlite3.connect('tty.db')
    conn.row_factory = sqlite3.Row
    return conn

# Initialize Ark client
client = Ark(
    api_key=os.environ.get("ARK_API_KEY"),
    timeout=120,
    max_retries=2,
    base_url="https://ark.cn-beijing.volces.com/api/v3"
)

# Initialize FAISS index
embedding_dim = 384  
index = faiss.IndexFlatL2(embedding_dim)
model = SentenceTransformer('all-MiniLM-L6-v2')

def get_message_history(session_id: int) -> List[Dict]:
    """从数据库获取会话历史记录"""
    db = get_db()
    try:
        cursor = db.execute(
            """
            SELECT sender_type, content, timestamp 
            FROM message 
            WHERE session_id = ? 
            ORDER BY timestamp
            """, 
            (session_id,)
        )
        messages = []
        for row in cursor:
            role = "user" if row['sender_type'] == 'user' else "assistant"
            messages.append({
                "role": role,
                "content": json.loads(row['content']) if row['sender_type'] == 'user' else row['content'],
                "timestamp": row['timestamp']
            })
        return messages
    finally:
        db.close()

def get_user_sessions(user_id: str) -> List[Dict]:
    """获取用户的所有会话记录及消息数量"""
    db = get_db()
    try:
        cursor = db.execute(
            """
            SELECT s.session_id, 
                   s.start_time,
                   s.status,
                   COUNT(m.message_id) as message_count,
                   (SELECT content 
                    FROM message 
                    WHERE session_id = s.session_id 
                    AND sender_type = 'user' 
                    ORDER BY timestamp 
                    LIMIT 1) as first_message
            FROM session s
            LEFT JOIN message m ON s.session_id = m.session_id
            WHERE s.user_id = ?
            GROUP BY s.session_id
            ORDER BY s.start_time DESC
            """,
            (user_id,)
        )
        sessions = []
        for row in cursor:
            preview = ""
            # 处理第一条消息
            first_message = row['first_message']
            if first_message:
                try:
                    # 尝试解析JSON格式的用户消息
                    message_content = json.loads(first_message)
                    # 提取文本内容
                    preview = next((item['text'] for item in message_content if item['type'] == 'text'), '')
                except json.JSONDecodeError:
                    preview = first_message

            sessions.append({
                "session_id": row['session_id'],
                "start_time": row['start_time'],
                "status": row['status'],
                "message_count": row['message_count'],
                "preview": preview[:50] + '...' if len(preview) > 50 else preview  # 预览前50个字符
            })
        return sessions
    finally:
        db.close()

@app.get("/user/{user_id}/sessions")
async def get_user_sessions_endpoint(user_id: str):
    """获取用户的所有会话列表"""
    try:
        sessions = get_user_sessions(user_id)
        print(sessions)
        return {
            "user_id": user_id,
            "sessions": sessions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat/{session_id}/messages")
async def get_chat_history_endpoint(session_id: str):
    """获取指定会话的历史消息"""
    try:
        messages = get_message_history(session_id)
        
        # 格式化返回的消息
        formatted_messages = []
        for msg in messages:
            message_data = {
                "role": msg["role"],
                "timestamp": None  # 数据库中的timestamp字段
            }
            
            # 处理用户消息
            if msg["role"] == "user":
                message_data["content"] = msg["content"]  # 已经是JSON格式
            else:
                # AI消息直接使用文本内容
                message_data["content"] = msg["content"]
                
            formatted_messages.append(message_data)
            
        return {
            "session_id": session_id,
            "messages": formatted_messages
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def create_new_session(user_id: str) -> str:
    """创建新的会话记录并返回session_id"""
    # 生成唯一的session_id
    session_id = f"sess_{uuid.uuid4().hex}"
    
    db = get_db()
    try:
        db.execute(
            """
            INSERT INTO session (session_id, user_id, start_time, status)
            VALUES (?, ?, datetime('now', 'localtime'), 'active')
            """,
            (session_id, user_id)
        )
        db.commit()
        return session_id
    finally:
        db.close()

def clean_message_content(content: str) -> str:
    """清理消息内容，去除多余空白和特殊字符"""
    if isinstance(content, str):
        # 替换连续的空白字符为单个空格
        content = ' '.join(content.split())
        # 去除开头和结尾的空白
        content = content.strip()
    return content

def store_message(session_id: str, sender_type: str, content: str):
    """存储消息到数据库"""
    db = get_db()
    try:
        # 如果是用户消息，需要处理JSON格式
        if sender_type == 'user':
            # 确保content是有效的JSON字符串
            if isinstance(content, str):
                try:
                    content_obj = json.loads(content)
                    # 清理文本内容
                    if isinstance(content_obj, list):
                        for item in content_obj:
                            if item.get('type') == 'text':
                                item['text'] = clean_message_content(item['text'])
                    content = json.dumps(content_obj, ensure_ascii=False)
                except json.JSONDecodeError:
                    content = json.dumps([{"type": "text", "text": clean_message_content(content)}])
        else:
            # AI回复直接清理内容
            content = clean_message_content(content)

        db.execute(
            """
            INSERT INTO message (session_id, sender_type, content)
            VALUES (?, ?, ?)
            """,
            (session_id, sender_type, content)
        )
        db.commit()
    finally:
        db.close()

def url_to_base64(image_url: str) -> Optional[str]:
    """从 URL 下载图片并转换为 Base64 字符串"""
    try:
        response = requests.get(image_url)
        response.raise_for_status()  # 检查请求是否成功
        image_content = response.content
        base64_encoded = base64.b64encode(image_content).decode('utf-8')
        return base64_encoded
    except requests.exceptions.RequestException as e:
        print(f"Error fetching image from {image_url}: {e}")
        return None

def generate_follow_up_questions(context: str) -> List[str]:
    """根据当前对话内容生成后续问题建议
    
    Args:
        context (str): 当前对话的回答内容
        
    Returns:
        List[str]: 建议的后续问题列表
    """
    # 调用 AI 生成后续问题
    follow_up_prompt = {
        "role": "system",
        "content": """基于上文回答，生成3个相关的后续问题。要求：
1. 问题要简短具体
2. 与上下文高度相关
3. 有助于加深理解
4. 每个问题不超过20字
5. 请站在用户的角度向你发问，不要站在AI的角度向用户发问
请直接返回问题列表，每行一个问题。
回复示例：
   xxx
   xxx
   xxx  
"""
    }
    
    messages = [
        follow_up_prompt,
        {"role": "user", "content": f"基于以下回答生成后续问题：\n{context}"}
    ]
    
    response = client.chat.completions.create(
        model="ep-20250105222308-5f4lk",
        messages=messages
    )
    
    # 处理返回的问题列表
    questions = response.choices[0].message.content.strip().split('\n')
    return [q.strip() for q in questions if q.strip()]

# 添加语音识别相关的类
class Ws_Param_ASR(object):
    def __init__(self, APPID, APIKey, APISecret, AudioFile):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.AudioFile = AudioFile

        # 公共参数(common)
        self.CommonArgs = {"app_id": self.APPID}
        # 业务参数(business)
        self.BusinessArgs = {"domain": "iat", "language": "zh_cn", "accent": "mandarin", "vinfo":1,"vad_eos":10000}

    def create_url(self):
        url = 'wss://ws-api.xfyun.cn/v2/iat'
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        signature_origin = "host: " + "ws-api.xfyun.cn" + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + "/v2/iat " + "HTTP/1.1"

        signature_sha = hmac.new(self.APISecret.encode('utf-8'), signature_origin.encode('utf-8'),
                               digestmod=hashlib.sha256).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')

        authorization_origin = f'api_key="{self.APIKey}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha}"'
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
        
        v = {
            "authorization": authorization,
            "date": date,
            "host": "ws-api.xfyun.cn"
        }
        return url + '?' + urlencode(v)

# 添加语音识别函数
async def speech_to_text(audio_file: UploadFile) -> str:
    """将语音文件转换为文本"""
    try:
        # 创建临时目录
        UPLOAD_FOLDER = "uploads"
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        # 保存上传的文件
        original_file = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}_{audio_file.filename}")
        pcm_file = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}.pcm")
        
        try:
            # 保存上传的文件
            with open(original_file, "wb") as buffer:
                shutil.copyfileobj(audio_file.file, buffer)

            # 使用ffmpeg转换为PCM格式
            cmd = [
                'ffmpeg', '-i', original_file,
                '-ar', '16000',
                '-ac', '1',
                '-f', 's16le',
                pcm_file
            ]
            subprocess.run(cmd, check=True)
            
            # 初始化讯飞参数
            wsParam = Ws_Param_ASR(
                APPID='a9468b3d',
                APISecret='MzM3M2JlMmZmNTEwODA2OGVmMjFlMTk5',
                APIKey='3d5e9910b46311ea048dabd3748ae2e2',
                AudioFile=pcm_file
            )
            
            # 用于存储识别结果
            final_result = ""

            def on_message(ws, message):
                nonlocal final_result
                try:
                    code = json.loads(message)["code"]
                    if code != 0:
                        print(f"Error: {json.loads(message)['message']}")
                        return
                    
                    data = json.loads(message)["data"]["result"]["ws"]
                    result = ""
                    for i in data:
                        for w in i["cw"]:
                            result += w["w"]
                    final_result += result
                except Exception as e:
                    print(f"Error processing message: {str(e)}")

            def on_error(ws, error):
                print(f"### error:{error}")

            def on_close(ws, a, b):
                print("### closed ###")

            def on_open(ws):
                def run(*args):
                    frameSize = 8000
                    intervel = 0.04
                    status = 0  # 0:第一帧, 1:中间帧, 2:最后一帧

                    with open(pcm_file, "rb") as fp:
                        while True:
                            buf = fp.read(frameSize)
                            if not buf:
                                status = 2
                            if status == 0:
                                d = {
                                    "common": wsParam.CommonArgs,
                                    "business": wsParam.BusinessArgs,
                                    "data": {
                                        "status": 0,
                                        "format": "audio/L16;rate=16000",
                                        "audio": str(base64.b64encode(buf), 'utf-8'),
                                        "encoding": "raw"
                                    }
                                }
                                d = json.dumps(d)
                                ws.send(d)
                                status = 1
                            elif status == 1:
                                d = {
                                    "data": {
                                        "status": 1,
                                        "format": "audio/L16;rate=16000",
                                        "audio": str(base64.b64encode(buf), 'utf-8'),
                                        "encoding": "raw"
                                    }
                                }
                                ws.send(json.dumps(d))
                            elif status == 2:
                                d = {
                                    "data": {
                                        "status": 2,
                                        "format": "audio/L16;rate=16000",
                                        "audio": str(base64.b64encode(buf), 'utf-8'),
                                        "encoding": "raw"
                                    }
                                }
                                ws.send(json.dumps(d))
                                time.sleep(1)
                                break
                            time.sleep(intervel)
                    ws.close()
                thread.start_new_thread(run, ())

            websocket.enableTrace(False)
            wsUrl = wsParam.create_url()
            ws = websocket.WebSocketApp(
                wsUrl,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            ws.on_open = on_open
            ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

            return final_result

        finally:
            # 清理临时文件
            if os.path.exists(original_file):
                os.remove(original_file)
            if os.path.exists(pcm_file):
                os.remove(pcm_file)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 修改chat_endpoint，添加audio_file参数
@app.post("/chat")
async def chat_endpoint(
    text: Optional[str] = Form(None),
    image_url: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None),
    audio_file: Optional[UploadFile] = File(None),
    session_id: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None)
):
    """
    聊天接口，支持文本、图片和语音输入
    """
    # 验证参数
    if session_id is None and not user_id:
        raise HTTPException(status_code=400, detail="Must provide user_id for new session")
    
    # 如果没有session_id，创建新会话
    if session_id is None:
        session_id = create_new_session(user_id)
    
    # 处理语音输入
    if audio_file:
        try:
            text = await speech_to_text(audio_file)
            if not text:
                raise HTTPException(status_code=400, detail="Failed to convert speech to text")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing audio: {str(e)}")
    print("text:  ",text)
    
    # 验证是否有输入内容
    if not text and not image_url and not image_file:
        raise HTTPException(status_code=400, detail="Must provide either text, image, or audio input")
    
    # 准备当前消息
    current_message = []
    if text:
        current_message.append({"type": "text", "text": text})

    # 处理图片URL
    if image_url:
        base64_image = url_to_base64(image_url)
        if base64_image:
            file_extension = image_url.split('.')[-1].lower()
            mime_type = f"image/{file_extension}" if file_extension in ["png", "jpg", "jpeg", "gif", "webp"] else "image"
            current_message.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{base64_image}"
                }
            })

    # 处理上传的图片文件
    elif image_file:
        image_content = await image_file.read()
        base64_image = base64.b64encode(image_content).decode('utf-8')
        current_message.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/{image_file.filename.split('.')[-1]};base64,{base64_image}"
            }
        })

    # 准备消息历史
    messages = [{"role": "system", "content": """
# 角色
你是一位耐心细致的数学老师，擅长逐步引导学生解答各类数学题目，以生动易懂的方式讲解解题方法，帮助学生真正掌握数学知识。

## 技能
### 技能 1：引导解题
1. 当学生提出数学题目时，先询问学生对题目的理解程度。
2. 逐步分析题目，提出关键问题引导学生思考。
3. 每一步引导都要详细解释原理。回复示例：
=====
   - 🔍 当前思考点：<具体指出当前思考的问题点>
   - 💡 引导思路：<解释为什么要思考这个问题以及如何思考>
=====

### 技能 2：讲解方法与巩固
1. 题目解答完成后，总结解题方法。回复示例：
=====
   - 🎯 解题方法总结：<总结解题方法的关键步骤和思路>
=====
2. 列出本题涉及的知识点。回复示例：
=====
   - 📖 知识点：<列出本题涉及的主要知识点，每个知识点后跟上数字编号>
=====
3. 询问学生对哪个知识点进行巩固练习，根据学生选择的知识点编号，给出一道包含该知识点的类似题目供学生练习。回复示例：
=====
   - 📝 巩固题目：<给出一道符合学生选择知识点的类似题目>
=====

## 限制：
- 只讨论与数学题目和解题方法相关的内容，拒绝回答与数学无关的话题。
- 所输出的内容必须按照给定的格式进行组织，不能偏离框架要求。
- 巩固题目和解答不能超过 150 字。
- 限制输出为MarkDown格式
"""}]

    # 从数据库加载历史消息
    messages.extend(get_message_history(session_id))
    
    # 添加当前用户消息
    messages.append({"role": "user", "content": current_message})
    print('\n当前输入模型的消息 :',messages)
    # 调用API获取回复
    response = client.chat.completions.create(
        model="ep-20250105222308-5f4lk",
        messages=messages
    )

    assistant_response = response.choices[0].message.content
    
    # 存储消息前先清理内容
    print("\n用户: ", json.dumps(current_message, ensure_ascii=False, indent=2))
    print("\n助手: ", clean_message_content(assistant_response))
    print("-" * 50)
    
    # 生成后续问题建议
    follow_up_questions = generate_follow_up_questions(assistant_response)
    print(follow_up_questions)
    # 存储消息
    store_message(session_id, 'user', json.dumps(current_message, ensure_ascii=False))
    store_message(session_id, 'ai', assistant_response)

    return {
        "session_id": session_id,
        "response": assistant_response,
        "follow_up_suggestions": follow_up_questions
    }

@app.delete("/chat/{session_id}")
async def clear_chat_history(session_id: str):
    """将会话标记为已完成"""
    db = get_db()
    try:
        db.execute(
            """
            UPDATE session 
            SET status = 'completed', end_time = datetime('now', 'localtime')
            WHERE session_id = ?
            """,
            (session_id,)
        )
        db.commit()
        return {"message": "Chat session marked as completed"}
    finally:
        db.close()

@app.post("/generate_by_knowledge")
async def generate_by_knowledge(
    knowledge_points: List[str] = Body(...),
    history_questions: Optional[List[str]] = Body(None)
):
    """根据知识点生成题目
    
    Args:
        knowledge_points (List[str]): 知识点列表
        history_questions (Optional[List[str]]): 历史题目列表（可选）
    
    Returns:
        Dict: 包含生成题目的响应
    """
    # 构建提示信息
    prompt = {
        "role": "system",
        "content": """你将扮演一位经验丰富的数学老师。你的任务是根据学生薄弱的知识点出题，并提供详细的解答步骤。

学生薄弱的知识点如下：
<weak_knowledge_point>
{knowledge_points}
</weak_knowledge_point>

出题要求如下：
1. 题目必须针对学生的薄弱知识点
2. 题目类型可以是计算题、应用题等多种数学题型，但要符合教学大纲
3. 题目难度适中，既要有一定的挑战性，又不能过于复杂让学生无从下手
4. 需要提供详细的解答步骤和最终答案

请按以下格式输出：
<timu>
[题目内容]
</timu>
<jiexi>
[详细解答步骤]
</jiexi>
<daan>
[最终答案]
</daan>"""
    }
    
    # 构建用户消息
    knowledge_points_str = ', '.join(knowledge_points)
    user_message = prompt["content"].format(knowledge_points=knowledge_points_str)
    
    if history_questions:
        user_message += f"\n\n历史题目参考：\n" + "\n".join(f"{i+1}. {q}" for i, q in enumerate(history_questions))
    
    messages = [
        prompt,
        {"role": "user", "content": user_message}
    ]
    
    try:
        # 调用AI生成题目
        response = client.chat.completions.create(
            model="ep-20250105222308-5f4lk",
            messages=messages
        )
        
        generated_content = response.choices[0].message.content
        
        # 使用更简单的字符串处理方法提取内容
        def extract_content(text, tag):
            start_tag = f"<{tag}>"
            end_tag = f"</{tag}>"
            start_pos = text.find(start_tag) + len(start_tag)
            end_pos = text.find(end_tag)
            return text[start_pos:end_pos].strip() if start_pos > -1 and end_pos > -1 else ""

        result = {
            "question": extract_content(generated_content, "timu"),
            "analysis": extract_content(generated_content, "jiexi"),
            "answer": extract_content(generated_content, "daan"),
            "knowledge_points": knowledge_points
        }
        
        # 生成后续练习建议
        follow_up = generate_follow_up_questions(generated_content)
        result["follow_up_suggestions"] = follow_up
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == '__main__':
    run(app, host='0.0.0.0', port=8001)