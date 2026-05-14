from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
from models import db, User, Seat, Reservation

# 1. 初始化Flask应用
app = Flask(__name__)

# 2. 配置数据库
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library_seat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_AS_ASCII'] = False

# 3. 初始化数据库
db.init_app(app)

# 4. 配置跨域
CORS(app, supports_credentials=True)

# -------------------- 预约接口 --------------------
@app.route('/reserve', methods=['POST'])
def reserve_seat():
    try:
        data = request.get_json()
        seat_id = data.get('seat_id')
        user_id = data.get('user_id')

        print(f"收到预约请求 seat_id={seat_id}, user_id={user_id}")

        if not seat_id or not user_id:
            return jsonify({"code": 400, "msg": "参数错误"})

        # 关键：把 seat 的查询也放进 with 里，让它和数据库会话绑定
        with app.app_context():
            seat = Seat.query.get(seat_id)
            if not seat or seat.status != 'available':
                return jsonify({"code": 400, "msg": "座位不可预约"})

            new_reservation = Reservation(
                seat_id=seat_id,
                user_id=user_id,
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(hours=2),
                status='reserved'
            )
            seat.status = 'reserved'
            db.session.add(new_reservation)
            db.session.commit()

        print(f"预约成功！记录ID: {new_reservation.id}")
        return jsonify({"code": 200, "msg": "预约成功"})

    except Exception as e:
        print("预约接口错误:", str(e))
        return jsonify({"code": 500, "msg": "预约失败: " + str(e)})
# -------------------- 我的预约接口 --------------------
@app.route('/my_reservations/<int:user_id>', methods=['GET'])
def my_reservations(user_id):
    try:
        with app.app_context():
            reservations = db.session.query(Reservation, Seat).join(
                Seat, Reservation.seat_id == Seat.id
            ).filter(Reservation.user_id == user_id).all()

        data = []
        for r, seat in reservations:
            data.append({
                "reservation_id": r.id,
                "seat_id": seat.id,
                "room_name": seat.room_name,
                "seat_number": seat.seat_number,
                "start_time": r.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                "end_time": r.end_time.strftime('%Y-%m-%d %H:%M:%S'),
                "status": r.status
            })

        print(f"查询到用户{user_id}的预约: {len(data)}条")
        return jsonify({"code": 200, "msg": "查询成功", "data": data})

    except Exception as e:
        print("接口错误:", str(e))
        return jsonify({"code": 500, "msg": "查询失败: " + str(e)})

@app.route('/seats', methods=['GET'])
def get_seats():
    try:
        seats = Seat.query.all()
        data = []
        for seat in seats:
            data.append({
                "id": seat.id,
                "seat_number": seat.seat_number,
                "status": seat.status
            })
        return jsonify({"code": 200, "data": data})
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e)})

@app.route('/cancel_reservation/<int:reservation_id>', methods=['POST'])
def cancel_reservation(reservation_id):
    # 1. 找到预约记录
    reservation = Reservation.query.get(reservation_id)
    if not reservation:
        return jsonify({"code": 400, "msg": "预约记录不存在"})
    
    # 2. 找到对应的座位
    seat = Seat.query.get(reservation.seat_id)
    if seat:
        # 3. 把座位状态改回可预约
        seat.status = 'available'
    
    # 4. 删除预约记录
    db.session.delete(reservation)
    db.session.commit()

    return jsonify({"code": 200, "msg": "取消预约成功"})
# -------------------- 启动代码 --------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if Seat.query.count() == 0:
            seat = Seat(room_name="1楼自习室", seat_number="A01", status="available")
            db.session.add(seat)
            db.session.commit()
            print("✅ 已创建测试座位 seat_id=1")
    app.run(debug=True)