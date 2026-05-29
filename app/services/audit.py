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

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS batch_jobs (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                state TEXT NOT NULL,
                input_dir TEXT NOT NULL,
                output_dir TEXT NOT NULL,
                total INTEGER NOT NULL DEFAULT 0,
                current INTEGER NOT NULL DEFAULT 0,
                current_file TEXT DEFAULT '',
                current_stage TEXT DEFAULT '',
                current_file_percent INTEGER NOT NULL DEFAULT 0,
                overall_percent REAL NOT NULL DEFAULT 0,
                success INTEGER NOT NULL DEFAULT 0,
                failed INTEGER NOT NULL DEFAULT 0,
                skipped INTEGER NOT NULL DEFAULT 0,
                duration REAL NOT NULL DEFAULT 0,
                message TEXT DEFAULT '',
                options TEXT DEFAULT '{}'
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS batch_job_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                file_name TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT DEFAULT '',
                output_file TEXT DEFAULT '',
                duration REAL NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(job_id) REFERENCES batch_jobs(id)
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

    @classmethod
    def create_batch_job(cls, job_id: str, input_dir: str, output_dir: str, total: int, options: dict):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(cls.DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO batch_jobs (
                id, created_at, updated_at, state, input_dir, output_dir, total,
                current, current_file, current_stage, current_file_percent,
                overall_percent, success, failed, skipped, duration, message, options
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, '', '', 0, 0, 0, 0, 0, 0, ?, ?)
        ''', (
            job_id, now, now, "PENDING", input_dir, output_dir, total,
            "任务已创建", json.dumps(options, ensure_ascii=False)
        ))
        conn.commit()
        conn.close()

    @classmethod
    def update_batch_job(cls, job_id: str, **fields):
        if not fields:
            return
        fields["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        allowed = {
            "updated_at", "state", "total", "current", "current_file", "current_stage",
            "current_file_percent", "overall_percent", "success", "failed", "skipped",
            "duration", "message"
        }
        clean_fields = {key: value for key, value in fields.items() if key in allowed}
        if not clean_fields:
            return
        assignments = ", ".join([f"{key} = ?" for key in clean_fields])
        values = list(clean_fields.values()) + [job_id]
        conn = sqlite3.connect(cls.DB_PATH)
        cursor = conn.cursor()
        cursor.execute(f"UPDATE batch_jobs SET {assignments} WHERE id = ?", values)
        conn.commit()
        conn.close()

    @classmethod
    def add_batch_file_result(cls, job_id: str, file_name: str, status: str, message: str = "",
                              output_file: str = "", duration: float = 0):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(cls.DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO batch_job_files (
                job_id, file_name, status, message, output_file, duration, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (job_id, file_name, status, message, output_file, duration, now))
        conn.commit()
        conn.close()

    @classmethod
    def get_batch_job(cls, job_id: str):
        if not os.path.exists(cls.DB_PATH):
            return None
        conn = sqlite3.connect(cls.DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM batch_jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None
        job = dict(row)
        cursor.execute(
            "SELECT file_name, status, message, output_file, duration FROM batch_job_files WHERE job_id = ? ORDER BY id ASC",
            (job_id,)
        )
        job["files"] = [
            {
                "name": file_row["file_name"],
                "status": file_row["status"],
                "message": file_row["message"],
                "output": file_row["output_file"],
                "duration": file_row["duration"],
            }
            for file_row in cursor.fetchall()
        ]
        conn.close()
        return job
