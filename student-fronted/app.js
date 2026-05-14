// 登录
function login() {
    let username = document.getElementById('username').value;
    let password = document.getElementById('password').value;

    if (!username || !password) {
        alert('请输入账号密码');
        return;
    }

    // 假登录（不用后端）
    localStorage.setItem('token', 'test_token');
    localStorage.setItem('user', username);
    alert('登录成功');
    location.href = 'index.html';
}

// 注册
function register() {
    alert('注册成功，请登录');
}
// 退出登录
function logout() {
    localStorage.clear();
    location.href = 'login.html';
}

// 假座位数据
const seats = [
    { id: 'A1', status: 0 },
    { id: 'A2', status: 0 },
    { id: 'A3', status: 1 },
    { id: 'A4', status: 2 },
    { id: 'B1', status: 0 },
    { id: 'B2', status: 1 },
    { id: 'B3', status: 0 },
];

// 渲染座位
window.onload = function () {
    if (!localStorage.getItem('token')) {
        location.href = 'login.html';
        return;
    }
    renderSeats();
};

function renderSeats() {
    let area = document.getElementById('seatArea');
    area.innerHTML = '';

    seats.forEach(seat => {
        let div = document.createElement('div');
        div.className = 'seat';
        div.innerText = seat.id;

        if (seat.status === 0) {
            div.classList.add('available');
            div.onclick = () => reserve(seat.id);
        } else if (seat.status === 1) {
            div.classList.add('reserved');
        } else {
            div.classList.add('maintenance');
        }
        area.appendChild(div);
    });
}

// 预约
function reserve(seatId) {
    if (confirm('确认预约 ' + seatId + '?')) {
        // 调用 api.js 里的真实预约接口
        reserveSeat(seatId).then(result => {
            if (result.code === 200) {
                alert('预约成功！');
                // 刷新页面，从后端同步最新的座位状态和预约记录
                location.reload();
            } else {
                alert('预约失败：' + result.msg);
            }
        });
    }
}

function renderMyList() {
    let list = document.getElementById('list');
    list.innerHTML = '';

    myReserves.forEach(item => {
        let div = document.createElement('div');
        div.className = 'item';
        div.innerHTML = `
            座位：${item.seat} <br>
            时间：${item.time} <br>
            <button onclick="cancel(${item.id})">取消预约</button>
        `;
        list.appendChild(div);
    });
}

// 取消预约
function cancel(id) {
    if (confirm('确定取消？')) {
        alert('取消成功');
        // 模拟删除
        let index = myReserves.findIndex(i => i.id === id);
        if (index !== -1) myReserves.splice(index, 1);
        renderMyList();
    }
}
// 假座位数据
const seats = [
    { id: 'A1', status: 0 }, // 0=可预约
    { id: 'A2', status: 0 },
    { id: 'A3', status: 1 }, // 1=已预约
    { id: 'A4', status: 2 }, // 2=维护中
    { id: 'B1', status: 0 },
    { id: 'B2', status: 1 },
    { id: 'B3', status: 0 },
    { id: 'B4', status: 0 },
];

// 假我的预约数据
let myReserves = [
    { id: 1, seat: 'A1', time: '2026-05-06 10:00-12:00' },
    { id: 2, seat: 'B3', time: '2026-05-06 14:00-16:00' }
];

// 退出登录
function logout() {
    localStorage.clear();
    location.href = 'login.html';
}

// 座位页加载时渲染
if (location.pathname.includes('index.html')) {
    window.onload = function () {
        if (!localStorage.getItem('token')) {
            location.href = 'login.html';
            return;
        }
        renderSeats();
    };
}

// 渲染座位
function renderSeats() {
    let area = document.getElementById('seatArea');
    if (!area) return;
    area.innerHTML = '';

    seats.forEach(seat => {
        let div = document.createElement('div');
        div.className = 'seat';
        div.innerText = seat.id;

        if (seat.status === 0) {
            div.classList.add('available');
            div.onclick = () => reserve(seat.id);
        } else if (seat.status === 1) {
            div.classList.add('reserved');
        } else {
            div.classList.add('maintenance');
        }
        area.appendChild(div);
    });
}

// 预约座位
function reserve(seatId) {
    if (confirm('确认预约座位 ' + seatId + ' 吗？')) {
        alert('预约成功！');
        // 更新状态为已预约
        let item = seats.find(s => s.id === seatId);
        if (item) item.status = 1;
        renderSeats();

        // 同时添加到我的预约里
        myReserves.push({
            id: Date.now(),
            seat: seatId,
            time: new Date().toLocaleString() + ' - 2小时后'
        });
    }
}

// 我的预约页加载时渲染
if (location.pathname.includes('my.html')) {
    window.onload = function () {
        if (!localStorage.getItem('token')) {
            location.href = 'login.html';
            return;
        }
        renderMyList();
    };
}

// 渲染我的预约列表
function renderMyList() {
    let list = document.getElementById('list');
    if (!list) return;
    list.innerHTML = '';

    myReserves.forEach(item => {
        let div = document.createElement('div');
        div.className = 'item';
        div.innerHTML = `
            <h4>座位号：${item.seat}</h4>
            <p>预约时间：${item.time}</p>
            <button onclick="cancel(${item.id})">取消预约</button>
        `;
        list.appendChild(div);
    });
}

// 取消预约
function cancel(id) {
    if (confirm('确定取消预约吗？')) {
        alert('取消成功！');
        // 从列表里删除
        myReserves = myReserves.filter(r => r.id !== id);
        renderMyList();

        // 同时更新座位状态为可预约
        let seatId = myReserves.find(r => r.id === id)?.seat;
        if (seatId) {
            let seat = seats.find(s => s.id === seatId);
            if (seat) seat.status = 0;
        }
    }
}