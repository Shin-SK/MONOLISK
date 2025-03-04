import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true  // 🔥 これを追加（認証絡むなら特に重要）
});

export default api;
