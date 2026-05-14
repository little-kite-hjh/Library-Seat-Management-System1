from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import User, Seat, Record
from schemas import UserCreate, UserLogin
from auth import get_password_hash, verify_password, create_token, get_current_user, admin_required
from datetime import datetime
from sqlalchemy import func

router = APIRouter()

# 1. 注册
@router.post("/register")
def register(data: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="学号已存在")
    user = User(
        username=data.username,
        password=get_password_hash(data.password),
        name=data.name
    )
    db.add(user)
    db.commit()
    return {"msg": "注册成功"}

# 2. 登录
@router.post("/login")
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status_code=400, detail="账号或密码错误")
    token = create_token(user.id, user.username, user.role)
    return {"token": token, "role": user.role}

# 3. 我的预约
@router.get("/my/records")
def my_records(user=Depends(get_current_user), db: Session = Depends(get_db)):
    records = db.query(Record).filter(Record.user_id == user.id).all()
    return records

# 4. 取消预约
@router.post("/record/cancel/{rid}")
def cancel_record(rid: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    record = db.query(Record).filter(Record.id == rid, Record.user_id == user.id).first()
    if not record:
        raise HTTPException(status_code=404)
    record.status = "canceled"
    seat = db.query(Seat).filter(Seat.id == record.seat_id).first()
    seat.status = "available"
    db.commit()
    return {"msg": "已取消"}

# ==================== 管理员接口（人员B核心） ====================
# 5. 管理员：查看所有预约
@router.get("/admin/records", dependencies=[Depends(admin_required)])
def admin_all_records(db: Session = Depends(get_db)):
    return db.query(Record).all()

# 6. 管理员：座位管理（设为维护）
@router.post("/admin/seat/maintain/{sid}", dependencies=[Depends(admin_required)])
def set_seat_maintain(sid: int, db: Session = Depends(get_db)):
    seat = db.query(Seat).filter(Seat.id == sid).first()
    seat.status = "maintain"
    db.commit()
    return {"msg": "已设为维护"}

# 7. 管理员：加入黑名单
@router.post("/admin/black/{uid}", dependencies=[Depends(admin_required)])
def add_black(uid: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == uid).first()
    user.is_black = True
    db.commit()
    return {"msg": "已加入黑名单"}

# 8. 统计：座位使用率
@router.get("/stats/usage", dependencies=[Depends(admin_required)])
def usage_stats(db: Session = Depends(get_db)):
    total = db.query(Seat).count()
    used = db.query(Seat).filter(Seat.status == "used").count()
    rate = round(used / total * 100, 2) if total > 0 else 0
    return {"total": total, "used": used, "rate": f"{rate}%"}

# 9. 统计：热门座位
@router.get("/stats/hot", dependencies=[Depends(admin_required)])
def hot_seats(db: Session = Depends(get_db)):
    return db.query(
        Record.seat_id, func.count(Record.id).label("count")
    ).group_by(Record.seat_id).order_by(func.count(Record.id).desc()).limit(10).all()