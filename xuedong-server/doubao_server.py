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
import chromadb
from chromadb.config import Settings
import re
from rank_bm25 import BM25Okapi

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
        "content": """
基于提供的模型回答，生成 3 个以用户视角的后续问题。要求：
1. 问题要简短具体
2. 与上下文高度相关
3. 有助于加深理解
4. 每个问题不超过 20 字
请直接返回问题列表，每行一个问题。
回复示例：
   <第一个后续问题>
   <第二个后续问题>
   <第三个后续问题>
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

def get_session_db(session_id: str):
    """Get or create a ChromaDB client for the session"""
    db_path = f"./chroma_dbs/{session_id}.db"
    # Ensure directory exists
    os.makedirs("./chroma_dbs", exist_ok=True)
    
    client = chromadb.PersistentClient(path=db_path)
    
    # Get or create collection for this session
    collection = client.get_or_create_collection(
        name="chat_history",
        metadata={"session_id": session_id}
    )
    
    return collection

def get_conversation_count(collection) -> int:
    """Get the current conversation count for the session"""
    try:
        results = collection.get()
        return len(results['ids'])
    except:
        return 0

def contains_temporal_reference(text: str) -> bool:
    """检查文本是否包含时间引用词"""
    temporal_words = [
        "之前", "刚刚", "上一步", "第一步", "前面", "上次",
        "刚才", "先前", "以前", "上面"
    ]
    return any(word in text for word in temporal_words)

def search_previous_context(collection, query: str, k: int = 3):
    """搜索相关的历史对话"""
    try:
        # 使用模型将查询文本向量化
        query_vector = model.encode([query]).tolist()  # 将查询文本转换为向量
        
        # 获取所有文档和元数据
        results = collection.get()
        documents = results['documents']
        metadatas = results['metadatas']
        
        # 使用 BM25 进行检索
        tokenized_docs = [doc.split(" ") for doc in documents]  # 将文档分词
        bm25 = BM25Okapi(tokenized_docs)  # 初始化 BM25
        tokenized_query = query.split(" ")  # 将查询分词
        bm25_scores = bm25.get_scores(tokenized_query)  # 计算 BM25 分数
        
        # 将 BM25 分数与向量检索结果结合
        combined_scores = [(i, bm25_scores[i]) for i in range(len(documents))]
        combined_scores.sort(key=lambda x: x[1], reverse=True)  # 按 BM25 分数排序
        
        # 选择前 k 个文档
        top_k_indices = [combined_scores[i][0] for i in range(min(k, len(combined_scores)))]
        
        # 返回 BM25 和向量检索的结果
        return {
            'documents': [documents[i] for i in top_k_indices],
            'metadatas': [metadatas[i] for i in top_k_indices]
        }
    except Exception as e:
        print(f"Vector search error: {e}")
        return None

@app.post("/chat")
async def chat_endpoint(
    text: str = Form(...),
    image_url: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None),
    session_id: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None)
):
    # 验证参数
    if session_id is None and not user_id:
        raise HTTPException(status_code=400, detail="Must provide user_id for new session")
        
    # 如果没有session_id，创建新会话
    if session_id is None:
        session_id = create_new_session(user_id)
    
    # 准备当前消息
    current_message = [{"type": "text", "text": text}]

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

    # Check for temporal references and search context
    context_message = ""
    if session_id and contains_temporal_reference(text):
        collection = get_session_db(session_id)
        search_results = search_previous_context(collection, text)
        
        if search_results and search_results['documents']:
            print("\n=== Vector Search Results ===")
            for doc, meta in zip(search_results['documents'], search_results['metadatas']):
                print("Matched Document:", doc)
                print("Metadata:", meta)  # 确保 meta 是字典
                context_message += f"第{meta['turn']}轮对话：\n{doc}\n"
            print("=========================\n")  # 输出分隔线

    # Prepare messages with context
    messages = [{"role": "system", "content": """
# 角色
你是一位耐心细致的数学老师，擅长逐步引导学生解答各类数学题目，以生动易懂的方式讲解解题方法，帮助学生真正掌握数学知识。

## 技能
### 技能 1：引导解题
1. 当学生提出数学题目时，先询问学生对题目的理解程度。
2. 逐步分析题目，提出关键问题引导学生思考。
3. 每一步引导都要详细解释原理，以 markdown 格式输出。回复示例：
=====
   - 🔍 当前思考点：<具体指出当前思考的问题点>
   - 💡 引导思路：<解释为什么要思考这个问题以及如何思考>
=====

### 技能 2：讲解方法与巩固
1. 题目解答完成后，总结解题方法，使用 markdown 格式输出，包含换行和公式。回复示例：
=====
   - 🎯 解题方法总结：
     - 关键步骤 1：<步骤描述>
     - 关键步骤 2：<步骤描述>
     - ……
   - 📖 知识点：<列出本题涉及的主要知识点，每个知识点后跟上数字编号>
=====
2. 询问学生对哪个知识点进行巩固练习，根据学生选择的知识点编号，给出一道包含该知识点的类似题目供学生练习，输出格式也使用 markdown 格式，答案不超过 150 字。回复示例：
=====
   - 📝 巩固题目：<题目描述>
     - 答案：<题目答案>
=====

## 限制：
- 只讨论与数学题目和解题方法相关的内容，拒绝回答与数学无关的话题。
- 所输出的内容必须严格按照 markdown 格式进行组织，不能偏离框架要求。
- 巩固题目和解答不能超过 150 字。
"""}]

    if context_message:
        messages.append({
            "role": "system",
            "content": f"以下是与当前问题相关的历史对话内容，请参考这些内容来回答问题：\n{context_message}"
        })

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

    # Store in vector database
    collection = get_session_db(session_id)
    conv_count = get_conversation_count(collection)
    
    # Combine Q&A into single document
    qa_text = f"Question: {text}\nAnswer: {assistant_response}"
    
    # Store in ChromaDB
    collection.add(
        documents=[qa_text],
        ids=[f"conv_{conv_count + 1}"],
        metadatas=[{
            "turn": conv_count + 1,
            "timestamp": datetime.now().isoformat(),
            "question": text,
            "answer": assistant_response
        }]
    )

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