import os
from pathlib import Path

# 从环境变量获取配置，如果不存在则使用默认值
DB_CONFIG = {
    'host': os.getenv('DB_HOST', '10.0.160.86'),
    'user': os.getenv('DB_USER', 'visus'),
    'password': os.getenv('DB_PASSWORD', '123456'),
    'database': os.getenv('DB_NAME', 'video2text'),
    'pool_name': os.getenv('DB_POOL_NAME', 'mypool'),
    'pool_size': int(os.getenv('DB_POOL_SIZE', '5')),
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci',
    'connect_timeout': 5  # 增加连接超时设置
}

# 增加SQLAlchemy配置
DB_CONFIG.update({
    'pool_size': 5,
    'max_overflow': 10,
    'pool_recycle': 3600,
    'echo': False  # 生产环境设为False
}) 