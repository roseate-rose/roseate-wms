import { createRouter, createWebHistory } from "vue-router";

import { TOKEN_KEY } from "../api/http";
import { getStoredRole } from "../auth/session";

const routes = [
  {
    path: "/login",
    name: "login",
    component: () => import("../views/LoginView.vue"),
    meta: { public: true, title: "登录" },
  },
  {
    path: "/",
    component: () => import("../layouts/MainLayout.vue"),
    children: [
      {
        path: "",
        name: "home",
        component: () => import("../views/HomeView.vue"),
        meta: { title: "首页" },
      },
      {
        path: "products",
        name: "products",
        component: () => import("../views/ProductsView.vue"),
        meta: { title: "商品" },
      },
      {
        path: "products/:hbCode",
        name: "product-detail",
        component: () => import("../views/ProductDetailView.vue"),
        meta: { title: "商品详情" },
      },
      {
        path: "orders",
        name: "orders",
        component: () => import("../views/OrdersView.vue"),
        meta: { title: "订单" },
      },
      {
        path: "stock",
        name: "stock",
        component: () => import("../views/StockView.vue"),
        meta: { title: "库存" },
      },
      {
        path: "other",
        name: "other",
        component: () => import("../views/OtherView.vue"),
        meta: { title: "其他" },
      },
      {
        path: "settings",
        name: "settings",
        component: () => import("../views/SettingsView.vue"),
        meta: { adminOnly: true, title: "设置" },
      },
      {
        path: "channels",
        name: "channels",
        component: () => import("../views/ChannelMappingsView.vue"),
        meta: { title: "渠道映射" },
      },
      {
        path: "data",
        name: "data",
        component: () => import("../views/DataManagementView.vue"),
        meta: { title: "数据管理" },
      },
      {
        path: "finance",
        name: "finance",
        component: () => import("../views/FinanceView.vue"),
        meta: { adminOnly: true, title: "财务统计" },
      },
      {
        path: "inbound",
        name: "inbound",
        component: () => import("../views/InboundView.vue"),
        meta: { title: "入库" },
      },
      {
        path: "outbound",
        name: "outbound",
        component: () => import("../views/OutboundView.vue"),
        meta: { title: "出库" },
      },
      {
        path: "changelog",
        name: "changelog",
        component: () => import("../views/ChangelogView.vue"),
        meta: { title: "更新日志" },
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
