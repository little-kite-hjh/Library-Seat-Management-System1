from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from database import Base
import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, comment="学号")
    password = Column(String(255), comment="密码")
    name = Column(String(20), comment="姓名")
    role = Column(String(10), default="student", comment="student/admin")
    is_black = Column(Boolean, default=False, comment="是否黑名单")

class Seat(Base):
    __tablename__ = "seats"
    id = Column(Integer, primary_key=True)
    room = Column(String(20), comment="教室")
    number = Column(String(10), comment="座位号")
    status = Column(String(10), default="available")  # available/used/maintain

class Record(Base):
    __tablename__ = "records"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    seat_id = Column(Integer, ForeignKey("seats.id"))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    status = Column(String(15), default="reserved")  # reserved/canceled/used
    create_time = Column(DateTime, default=datetime.datetime.now)