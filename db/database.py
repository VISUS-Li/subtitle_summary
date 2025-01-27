import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any
import json
from datetime import datetime
from .models import ServiceConfig

class Database:
    def __init__(self, db_path: str = "video2text.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建服务配置表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS service_configs (
            service_name TEXT,
            config_key TEXT,
            config_value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (service_name, config_key)
        )
        ''')
        
        conn.commit()
        conn.close()

    def set_service_config(self, service_name: str, config_key: str, config_value: Any):
        """设置服务配置"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 如果值是字典或列表，转换为JSON字符串
        if isinstance(config_value, (dict, list)):
            config_value = json.dumps(config_value)
            
        cursor.execute('''
        INSERT OR REPLACE INTO service_configs 
        (service_name, config_key, config_value, updated_at)
        VALUES (?, ?, ?, ?)
        ''', (service_name, config_key, config_value, datetime.now()))
        
        conn.commit()
        conn.close()

    def get_service_config(self, service_name: str, config_key: str) -> Optional[Any]:
        """获取服务配置"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT config_value FROM service_configs WHERE service_name = ? AND config_key = ?',
            (service_name, config_key)
        )
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            try:
                return json.loads(result[0])
            except json.JSONDecodeError:
                return result[0]
        return None

    def delete_service_config(self, service_name: str, config_key: str = None):
        """删除服务配置"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if config_key:
            cursor.execute(
                'DELETE FROM service_configs WHERE service_name = ? AND config_key = ?',
                (service_name, config_key)
            )
        else:
            cursor.execute(
                'DELETE FROM service_configs WHERE service_name = ?',
                (service_name,)
            )
        
        conn.commit()
        conn.close()

    def get_all_service_configs(self, service_name: str) -> Dict[str, Any]:
        """获取服务的所有配置"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT config_key, config_value FROM service_configs WHERE service_name = ?',
            (service_name,)
        )
        results = cursor.fetchall()
        
        conn.close()
        
        configs = {}
        for key, value in results:
            try:
                configs[key] = json.loads(value)
            except json.JSONDecodeError:
                configs[key] = value
                
        return configs