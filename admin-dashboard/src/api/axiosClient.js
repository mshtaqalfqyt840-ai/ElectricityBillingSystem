import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api';

const axiosClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ── متغيرات للتحكم في تجديد التوكن (منع Race Condition) ──
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

// ── دالة تسجيل الخروج الإجباري (مركزية) ──
const forceLogout = () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('user');
  // بدلاً من window.location.href الذي يسبب شاشة سوداء،
  // نستخدم إعادة تحميل كاملة بعد تنظيف localStorage
  // هذا يضمن أن React يعيد التحميل من الصفر ويقرأ localStorage فارغ
  // فيوجه المستخدم لصفحة تسجيل الدخول عبر ProtectedRoute
  if (window.location.pathname !== '/login') {
    window.location.replace('/login');
  }
};

// ── Request Interceptor: إرفاق التوكن تلقائياً بكل طلب ──
axiosClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ── Response Interceptor: تجديد التوكن تلقائياً عند انتهائه ──
// مع حماية كاملة ضد Race Condition
axiosClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // لو الرد 401 (غير مصرح) ولم نحاول التجديد مسبقاً لهذا الطلب
    if (error.response?.status === 401 && !originalRequest._retry) {
      // لو عملية التجديد جارية بالفعل من طلب آخر، ننتظر نتيجتها
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return axiosClient(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;

      const refreshToken = localStorage.getItem('refresh_token');
      if (!refreshToken) {
        // ما فيه refresh token → تسجيل خروج إجباري
        forceLogout();
        return Promise.reject(error);
      }

      isRefreshing = true;

      try {
        // نطلب access token جديد باستخدام الـ refresh token
        const response = await axios.post(`${API_BASE_URL}/token/refresh/`, {
          refresh: refreshToken,
        });

        const newAccessToken = response.data.access;
        localStorage.setItem('access_token', newAccessToken);

        // نعالج كل الطلبات المعلقة بالتوكن الجديد
        processQueue(null, newAccessToken);

        // نعيد الطلب الأصلي بالتوكن الجديد
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return axiosClient(originalRequest);
      } catch (refreshError) {
        // حتى الـ refresh token انتهت صلاحيته → تسجيل خروج إجباري
        processQueue(refreshError, null);
        forceLogout();
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default axiosClient;
