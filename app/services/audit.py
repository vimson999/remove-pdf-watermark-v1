import sqlite3
import json
import os
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class AuditManager:
    """
    审计日志管理器 (Module 5: Persistence)
    将所有 PDF 处理操作（解析、拆分、清洗）持久化到本地 SQLite 数据库中。
    """
    DB_PATH = "logs/audit.db"

    @classmethod
    def init_db(cls):
        """初始化审计数据库与表结构"""
        os.makedirs(os.path.dirname(cls.DB_PATH), exist_ok=True)
        conn = sqlite3.connect(cls.DB_PATH)
        cursor = conn.cursor()
        
        # 创建审计日志表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                operation_type TEXT NOT NULL,
                source_file TEXT,
                params TEXT,
                status TEXT,
                result_info TEXT
            )
        ''')
        
        conn.commit()
        conn.close()

    @classmethod
    def log_operation(cls, op_type: str, source: str, params: dict, status: str, result: str):
        """
        记录一次 PDF 操作痕迹
        :param op_type: 操作类型 (ANALYSIS, SPLIT, CLEAN, ENCRYPT)
        :param source: 原始文件名
        :param params: 使用的参数字典
        :param status: SUCCESS / ERROR
        :param result: 结果简述或生成的文件列表
        """
        try:
            conn = sqlite3.connect(cls.DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO audit_logs (timestamp, operation_type, source_file, params, status, result_info)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                op_type,
                source,
                json.dumps(params, ensure_ascii=False),
                status,
                result
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to log audit: {e}")

    @classmethod
    def get_recent_logs(cls, limit=50):
        """获取最近的历史记录"""
        if not os.path.exists(cls.DB_PATH):
            return []
        
        conn = sqlite3.connect(cls.DB_PATH)
        conn.row_factory = sqlite3.Row  # 返回字典格式
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?', (limit,))
        logs = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return logs
