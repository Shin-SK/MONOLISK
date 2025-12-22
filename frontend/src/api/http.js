// frontend/src/api/http.js
import axios from "axios";
import { wireInterceptors } from "./interceptors";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "",
  timeout: 30000,
});

wireInterceptors(api);

export default api;
