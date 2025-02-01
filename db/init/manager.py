from sqlalchemy import inspect, text, create_engine
from sqlalchemy.orm import sessionmaker

from db.init.base import Base
from db.init.config import DB_CONFIG


class DatabaseManager:
    def __init__(self):
        # 统一使用SQLAlchemy引擎
        self.engine = create_engine(
            f"mysql+mysqlconnector://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
            f"@{DB_CONFIG['host']}/{DB_CONFIG['database']}",
            pool_size=DB_CONFIG['pool_size'],
            max_overflow=10
        )
        self._check_and_create_database()
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self._config_cache = {}

    def _check_and_create_database(self):
        """优化后的数据库创建检查"""
        # 先尝试连接管理数据库
        admin_engine = create_engine(
            f"mysql+mysqlconnector://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
            f"@{DB_CONFIG['host']}/",
            connect_args={
                'connect_timeout': 5,
                'charset': 'utf8mb4',
                'use_unicode': True,
                'collation': 'utf8mb4_unicode_ci'
            }
        )
        
        try:
            with admin_engine.connect() as conn:
                # 检查数据库是否存在
                result = conn.execute(text(
                    f"SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA "
                    f"WHERE SCHEMA_NAME = '{DB_CONFIG['database']}'"
                ))
                database_exists = result.scalar() is not None

                if not database_exists:
                    # 数据库不存在时才创建
                    conn.execute(text(
                        f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']} "
                        f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                    ))
                    print(f"已创建新数据库: {DB_CONFIG['database']}")
            
        finally:
            admin_engine.dispose()

        self.init_database()

    def init_database(self) -> None:
        """合并初始化逻辑"""
        try:
            # 自动创建所有表
            Base.metadata.create_all(self.engine)
            
            # 自动添加新字段
            inspector = inspect(self.engine)
            with self.engine.connect() as conn:
                for table in Base.metadata.tables.values():
                    if not inspector.has_table(table.name):
                        continue
                        
                    existing_columns = {col['name'] for col in inspector.get_columns(table.name)}
                    for column in table.columns:
                        if column.name not in existing_columns:
                            conn.execute(text(
                                f"ALTER TABLE {table.name} "
                                f"ADD COLUMN {column.name} {column.type.compile(self.engine.dialect)}"
                            ))
                    conn.commit()
        except Exception as e:
            print(f"初始化失败: {str(e)}")
            raise
