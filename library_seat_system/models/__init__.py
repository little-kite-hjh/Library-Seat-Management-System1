from flask_sqlalchemy import SQLAlchemy

# 创建数据库对象
db = SQLAlchemy()

# 导入模型类，让它们被ORM识别
from .tables import User, Seat, Reservation