import axios from "axios";

const TOKEN_KEY = "roseate_wms_token";

const http = axios.create({
  baseURL: "/api/v1",
  timeout: 10000,
});

http.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

export { TOKEN_KEY };
export default http;
