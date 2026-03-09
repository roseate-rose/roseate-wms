import { createRouter, createWebHistory } from "vue-router";

import { TOKEN_KEY } from "../api/http";

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

  return true;
});

export default router;
