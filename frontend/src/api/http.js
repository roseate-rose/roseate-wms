import axios from "axios";

import { clearStoredUser } from "../auth/session";

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

function clearAuthAndRedirect() {
  localStorage.removeItem(TOKEN_KEY);
  clearStoredUser();

  if (window.location.pathname === "/login") {
    return;
  }

  const redirect = `${window.location.pathname}${window.location.search}${window.location.hash}`;
  const target = redirect && redirect !== "/" ? `/login?redirect=${encodeURIComponent(redirect)}` : "/login";
  window.location.replace(target);
}

http.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    const message = error?.response?.data?.msg || "";
    const requestUrl = String(error?.config?.url || "");
    const isLoginRequest = requestUrl.includes("/auth/login");

    if (!isLoginRequest && status === 401) {
      const shouldResetAuth =
        message === "token has expired" ||
        message === "Missing Authorization Header" ||
        message.toLowerCase().includes("token");

      if (shouldResetAuth) {
        clearAuthAndRedirect();
      }
    }

    return Promise.reject(error);
  },
);

export { TOKEN_KEY };
export default http;
