from pydantic import BaseModel
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    password: str
    name: str

class UserLogin(BaseModel):
    username: str
    password: str

class RecordOut(BaseModel):
    id: int
    seat_id: int
    start_time: datetime
    end_time: datetime
    status: str