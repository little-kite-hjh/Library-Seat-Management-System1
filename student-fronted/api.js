const baseURL = "http://127.0.0.1:8000";

async function request(url, options = {}) {
  const baseURL = "http://127.0.0.1:8000";
  const headers = {
    "Content-Type": "application/json",
    ...options.headers
  };

  try {
    const response = await fetch(`${baseURL}${url}`, {
      method: options.method || 'GET',
      headers,
      // 关键：去掉 credentials: 'include'，浏览器就不会校验跨域凭证了
      body: options.body ? JSON.stringify(options.body) : undefined
    });
    return await response.json();
  } catch (error) {
    console.error('请求失败:', error);
    return { code: 500, msg: '网络错误' };
  }
}

export async function getMyReserves() {
    const userId = localStorage.getItem('userId');
    if (!userId) {
        return { code: 401, msg: '请先登录' };
    }
    return await request(`/my_reservations/${userId}`, {
        method: 'GET'
    });
}

export async function reserveSeat(seatId) {
    const userId = localStorage.getItem('userId');
    if (!userId) {
        alert('请先登录！');
        return;
    }
    return await request(`/reserve`, {
        method: 'POST',
        body: {
            seat_id: seatId,
            user_id: userId
        }
    });
}
export async function cancelReserve(reservationId) {
  return await request(`/cancel_reservation/${reservationId}`, {
    method: 'POST'
  });
}