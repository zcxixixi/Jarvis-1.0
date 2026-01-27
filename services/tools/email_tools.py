"""
Email Tools for Jarvis
Allows sending real emails via SMTP and tracking sent history.
"""
import smtplib
import os
import json
from email.mime.text import MIMEText
from email.header import Header
from typing import Dict, Any, List
from pathlib import Path
from .base import BaseTool
from jarvis_assistant.utils.validators import DataAuthenticityValidator

# Local storage for sent history
SENT_EMAILS_FILE = Path.home() / ".jarvis_sent_emails.json"

def log_sent_email(to, subject, body):
    history = []
    if SENT_EMAILS_FILE.exists():
        try:
            with open(SENT_EMAILS_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except: pass
    
    history.append({
        "to": to,
        "subject": subject,
        "body": body[:100] + "..." if len(body) > 100 else body,
        "time": str(os.times()) # Simple timestamp
    })
    
    with open(SENT_EMAILS_FILE, 'w', encoding='utf-8') as f:
        json.dump(history[-20:], f, ensure_ascii=False, indent=2)

class SendEmailTool(BaseTool):
    def __init__(self):
        self.validator = DataAuthenticityValidator()

    @property
    def name(self) -> str:
        return "send_email"
    
    @property
    def description(self) -> str:
        return "通过真实 SMTP 发送电子邮件"
    
    def get_schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "to": {"type": "string", "description": "收件人邮箱地址"},
                        "subject": {"type": "string", "description": "邮件主题"},
                        "body": {"type": "string", "description": "邮件正文内容"}
                    },
                    "required": ["to", "subject", "body"]
                }
            }
        }
    
    async def execute(self, **kwargs) -> str:
        to_addr = kwargs.get("to")
        subject = kwargs.get("subject")
        body = kwargs.get("body")
        
        # Get credentials from env
        smtp_server = os.getenv("SMTP_SERVER")
        smtp_port = os.getenv("SMTP_PORT", "465")
        smtp_user = os.getenv("SMTP_USER")
        smtp_pass = os.getenv("SMTP_PASS")
        
        if not all([smtp_server, smtp_user, smtp_pass]):
            return "抱歉，我还没配置好发件箱。请在 .env 文件中设置 SMTP_SERVER, SMTP_USER 和 SMTP_PASS。"

        # Authenticity check for SMTP server
        if not self.validator.validate_source("email", smtp_server):
            return "抱歉，当前 SMTP 服务器不符合安全策略（禁止 localhost/mock）。"

        try:
            message = MIMEText(body, 'plain', 'utf-8')
            message['From'] = smtp_user
            message['To'] = to_addr
            message['Subject'] = Header(subject, 'utf-8')

            # Use SSL
            server = smtplib.SMTP_SSL(smtp_server, int(smtp_port))
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, [to_addr], message.as_string())
            server.quit()
            
            log_sent_email(to_addr, subject, body)
            return f"📧 邮件已成功发送给 {to_addr}。\n主题：{subject}"
            
        except Exception as e:
            return f"抱歉，邮件发送失败了。错误信息：{str(e)}"

class ListEmailsTool(BaseTool):
    @property
    def name(self) -> str:
        return "list_emails"
    
    @property
    def description(self) -> str:
        return "查看最近通过 Jarvis 发送的邮件记录"
    
    def get_schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "count": {"type": "integer", "description": "要查看的记录数量", "default": 5}
                    }
                }
            }
        }
    
    async def execute(self, **kwargs) -> str:
        count = kwargs.get("count", 5)
        if not SENT_EMAILS_FILE.exists():
            return "您还没有通过我发送过任何邮件。"
            
        try:
            with open(SENT_EMAILS_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            if not history:
                return "暂无邮件发送记录。"
                
            result = f"这是您最近通过我发送的 {min(count, len(history))} 封邮件：\n"
            for mail in reversed(history[-count:]):
                result += f"- 发往: {mail['to']} | 主题: {mail['subject']}\n"
            return result
        except:
            return "抱歉，读取邮件历史时出错了。"
