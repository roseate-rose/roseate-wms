import { createRouter, createWebHistory } from "vue-router";

import { TOKEN_KEY } from "../api/http";
import { getStoredRole } from "../auth/session";

const routes = [
  {
    path: "/login",
    name: "login",
    component: () => import("../views/LoginView.vue"),
    meta: { public: true },
  },
  {
    path: "/",
    component: () => import("../layouts/MainLayout.vue"),
    children: [
      {
        path: "",
        name: "home",
        component: () => import("../views/HomeView.vue"),
      },
      {
        path: "products",
        name: "products",
        component: () => import("../views/ProductsView.vue"),
      },
      {
        path: "products/:hbCode",
        name: "product-detail",
        component: () => import("../views/ProductDetailView.vue"),
      },
      {
        path: "channels",
        name: "channels",
        component: () => import("../views/ChannelMappingsView.vue"),
      },
      {
        path: "orders",
        name: "orders",
        component: () => import("../views/OrdersView.vue"),
      },
      {
        path: "data",
        name: "data",
        component: () => import("../views/DataManagementView.vue"),
      },
      {
        path: "finance",
        name: "finance",
        component: () => import("../views/FinanceView.vue"),
        meta: { adminOnly: true },
      },
      {
        path: "settings",
        name: "settings",
        component: () => import("../views/SettingsView.vue"),
        meta: { adminOnly: true },
      },
      {
        path: "inbound",
        name: "inbound",
        component: () => import("../views/InboundView.vue"),
      },
      {
        path: "outbound",
        name: "outbound",
        component: () => import("../views/OutboundView.vue"),
      },
      {
        path: "stock",
        name: "stock",
        component: () => import("../views/StockView.vue"),
      },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to) => {
  if (to.meta.public) {
    return true;
  }

  const token = localStorage.getItem(TOKEN_KEY);
  const hasValidToken = typeof token === "string" && token.trim().length > 0;

  if (!hasValidToken) {
    return {
      path: "/login",
      query: to.fullPath === "/" ? {} : { redirect: to.fullPath },
    };
  }

  if (to.meta.adminOnly && getStoredRole() !== "admin") {
    return { path: "/" };
  }

  return true;
});

export default router;
