import requests
import os
from typing import Optional, Dict, List
from datetime import datetime
import json

class ChatClient:
    def __init__(self, user_id: str, base_url: str = "http://localhost:8000"):
        if not user_id:
            raise ValueError("user_id is required")
        self.user_id = user_id
        self.base_url = base_url
        self.session_id = None
        self.local_history: List[Dict] = []

    def save_to_history(self, user_message: str, assistant_response: dict):
        """保存对话历史到本地"""
        self.local_history.append({
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message,
            "assistant_response": assistant_response,
            "interaction_id": len(self.local_history) + 1
        })

    def display_context(self, context: dict):
        """显示检索到的上下文"""
        print("\n=== 相关历史对话 ===")
        print(f"时间: {context['timestamp']}")
        print(f"你: {context['user_message']}")
        print(f"助手: {context['assistant_message']}")
        print("=" * 50)

    def send_message(self, text: str, image_path: Optional[str] = None, image_url: Optional[str] = None) -> dict:
        """发送消息到服务器，支持本地图片路径和 URL"""
        url = f"{self.base_url}/chat"

        # 准备基本数据
        data = {
            "text": text,
        }
        
        # 如果没有session_id，说明是第一次对话，需要传入user_id
        if not self.session_id:
            data["user_id"] = self.user_id
        else:
            data["session_id"] = self.session_id

        # 处理图片
        if image_url:
            data["image_url"] = image_url
            files = {}
        elif image_path and os.path.exists(image_path):
            files = {"image_file": open(image_path, "rb")}
        else:
            files = {}

        try:
            response = requests.post(url, data=data, files=files)
            response.raise_for_status()
            result = response.json()

            # 保存服务器返回的session_id
            if not self.session_id:
                self.session_id = result["session_id"]
                print(f"新会话已创建，session_id: {self.session_id}")

            # Save to local history
            self.save_to_history(text, result)

            return result
        finally:
            if image_path and "image_file" in files:
                files["image_file"].close()

    def clear_history(self):
        """清除对话历史"""
        if self.session_id:
            url = f"{self.base_url}/chat/{self.session_id}"
            requests.delete(url)
            self.session_id = None
            self.local_history = []
            print("对话历史已清除")

    def generate_by_knowledge(self, knowledge_points: List[str], history_questions: Optional[List[str]] = None) -> dict:
        """根据知识点生成题目
        
        Args:
            knowledge_points (List[str]): 知识点列表
            history_questions (Optional[List[str]]): 历史题目列表（可选）
            
        Returns:
            dict: 服务器返回的题目数据
        """
        url = f"{self.base_url}/generate_by_knowledge"
        
        data = {
            "knowledge_points": knowledge_points,
            "history_questions": history_questions
        }
        
        try:
            response = requests.post(url, json=data)
            response.raise_for_status()
            result = response.json()
            return result
        except requests.exceptions.RequestException as e:
            print(f"网络错误: {e}")
            return None

    def grade_assignment(self, question_text: str, answer_text: Optional[str] = None, answer_image_path: Optional[str] = None) -> dict:
        """发送作业批改请求
        
        Args:
            question_text (str): 原题目文本
            answer_text (Optional[str]): 学生的答案文本（可选）
            answer_image_path (Optional[str]): 学生的答案图片路径（可选）
        
        Returns:
            dict: 服务器返回的批改反馈
        """
        url = f"{self.base_url}/grade_assignment"
        
        # 准备基本数据
        data = {
            "question_text": question_text,
            "answer_text": answer_text,
        }
        
        files = {}
        if answer_image_path and os.path.exists(answer_image_path):
            files = {"answer_image": open(answer_image_path, "rb")}
        
        try:
            response = requests.post(url, data=data, files=files)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"网络错误: {e}")
            return None
        finally:
            if answer_image_path and "answer_image" in files:
                files["answer_image"].close()


def main():
    print("欢迎使用聊天程序！")
    
    # 获取用户ID
    while True:
        user_id = input("请输入你的用户ID: ").strip()
        if user_id:
            break
        print("用户ID不能为空，请重新输入")
    
    try:
        client = ChatClient(user_id)
    except ValueError as e:
        print(f"错误: {e}")
        return

    print("\n=== 使用说明 ===")
    print("- 直接输入文字进行对话")
    print("- 输入 'image: 图片路径' 可以发送本地图片")
    print("- 输入 'url: 图片URL' 可以发送网络图片 URL")
    print("- 输入 'clear' 清除对话历史")
    print("- 输入 'quit' 或 'exit' 退出程序")
    print("- 输入 'generate: 知识点1,知识点2,...' 根据知识点生成题目")
    print("- 输入 'grade' 发送作业批改请求")
    print("-" * 50)

    while True:
        try:
            user_input = input("\n你: ").strip()

            if user_input.lower() in ['quit', 'exit']:
                print("再见！")
                break

            if user_input.lower() == 'clear':
                client.clear_history()
                continue

            if user_input.lower() == 'grade':
                question_text = input("请输入原题目: ").strip()
                answer_text = input("请输入学生答案文本（可选，直接回车跳过）: ").strip() or None
                answer_image_path = input("请输入学生答案图片路径（可选，直接回车跳过）: ").strip() or None
                
                result = client.grade_assignment(question_text, answer_text, answer_image_path)
                if result:
                    print("\n批改反馈: ", result["grading_feedback"])
                continue

            image_path = None
            image_url = None
            if user_input.startswith('image:'):
                parts = user_input.split(':', 1)
                if len(parts) == 2:
                    image_path = parts[1].strip()
                    user_input = input("请输入相关文字描述: ").strip()
                    if not os.path.exists(image_path):
                        print(f"错误: 找不到图片文件 '{image_path}'")
                        continue
            elif user_input.startswith('url:'):
                parts = user_input.split(':', 1)
                if len(parts) == 2:
                    image_url = parts[1].strip()
                    user_input = input("请输入相关文字描述: ").strip()
                    if not image_url.startswith(('http://', 'https://')):
                        print(f"错误: 无效的图片 URL '{image_url}'")
                        continue

            response = client.send_message(user_input, image_path, image_url)
            print("\n助手: ", response["response"])
            
            # 显示后续问题建议
            if "follow_up_suggestions" in response and response["follow_up_suggestions"]:
                print("\n💡 你可以继续问：")
                for i, question in enumerate(response["follow_up_suggestions"], 1):
                    print(f"{i}. {question}")
            
            print("-" * 50)

            # 处理生成题目的命令
            if user_input.startswith('generate:'):
                knowledge_points = [kp.strip() for kp in user_input[9:].split(',') if kp.strip()]
                if not knowledge_points:
                    print("请输入至少一个知识点")
                    continue
                    
                print("\n正在根据知识点生成题目...")
                print(f"输入是{knowledge_points}")
                result = client.generate_by_knowledge(knowledge_points)
                
                if result:
                    print("\n=== 生成的题目 ===")
                    print(result["question"])
                    print("\n=== 解析 ===")
                    print(result["analysis"])
                    print("\n=== 答案 ===")
                    print(result["answer"])
                    
                    # 显示后续练习建议
                    if "follow_up_suggestions" in result and result["follow_up_suggestions"]:
                        print("\n💡 你可以继续问：")
                        for i, question in enumerate(result["follow_up_suggestions"], 1):
                            print(f"{i}. {question}")
                    
                    print("-" * 50)
                continue

        except requests.exceptions.RequestException as e:
            print(f"网络错误: {e}")
        except Exception as e:
            print(f"发生错误: {e}")

if __name__ == "__main__":
    main()