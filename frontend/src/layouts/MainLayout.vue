<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";

const route = useRoute();

// Sidebar order requirement:
// Home (dashboard) -> Inbound -> Products -> Orders -> Stock -> Other -> Settings
const navItems = [
  { name: "home", label: "首页", path: "/" },
  { name: "inbound", label: "入库", path: "/inbound" },
  { name: "products", label: "商品", path: "/products" },
  { name: "orders", label: "订单", path: "/orders" },
  { name: "stock", label: "库存", path: "/stock" },
  { name: "other", label: "其他", path: "/other" },
  { name: "settings", label: "设置", path: "/settings" },
];

const visibleSidebarItems = computed(() => navItems);
const visibleMobileItems = computed(() =>
  visibleSidebarItems.value.filter((item) =>
    ["/", "/inbound", "/products", "/orders", "/stock", "/other"].includes(item.path),
  ),
);
const activePath = computed(() => route.path);

const mobileGridColsClass = computed(() => {
  const count = visibleMobileItems.value.length
  if (count >= 6) {
    return "grid-cols-6"
  }
  return "grid-cols-5"
})

function isActive(path) {
  if (path === "/") {
    return activePath.value === "/";
  }

  return activePath.value === path || activePath.value.startsWith(`${path}/`);
}

const currentLabel = computed(() => {
  if (route.meta?.title) {
    return route.meta.title;
  }

  const matchedItem = visibleSidebarItems.value.find((item) => isActive(item.path));
  return matchedItem?.label || "工作台";
});
</script>

<template>
  <div class="min-h-screen bg-transparent text-slate-800">
    <aside
      class="fixed inset-y-0 left-0 hidden w-64 flex-col border-r border-brand/10 bg-white/80 px-6 py-8 backdrop-blur md:flex"
    >
      <div>
        <p class="text-xs uppercase tracking-[0.4em] text-brand/60">Roseate</p>
        <h1 class="mt-3 text-2xl font-semibold text-brand-dark">蕴香和本 WMS</h1>
        <p class="mt-2 text-sm text-slate-500">批次优先 · FIFO 出库 · H5 扫码优先</p>
      </div>

      <nav class="mt-10 space-y-3 overflow-y-auto">
        <RouterLink
          v-for="item in visibleSidebarItems"
          :key="item.name"
          :to="item.path"
          class="flex items-center rounded-2xl px-4 py-3 text-sm font-medium transition"
          :class="
            isActive(item.path)
              ? 'bg-brand text-white shadow-lg shadow-brand/20'
              : 'text-slate-600 hover:bg-brand-soft hover:text-brand-dark'
          "
        >
          {{ item.label }}
        </RouterLink>
      </nav>
    </aside>

    <div class="pb-24 md:ml-64 md:pb-8">
      <header class="px-5 pt-6 md:px-10 md:pt-8">
        <div class="rounded-3xl bg-white/75 px-5 py-4 shadow-sm backdrop-blur">
          <p class="text-sm text-slate-500">当前模块</p>
          <h2 class="mt-1 text-xl font-semibold text-slate-900">
            {{ currentLabel }}
          </h2>
        </div>
      </header>

      <main class="px-5 py-6 md:px-10">
        <RouterView />
      </main>
    </div>

    <nav
      class="fixed inset-x-0 bottom-0 z-20 border-t border-brand/10 bg-white/95 px-2 py-2 backdrop-blur md:hidden"
    >
      <div class="grid gap-2" :class="mobileGridColsClass">
        <RouterLink
          v-for="item in visibleMobileItems"
          :key="item.name"
          :to="item.path"
          class="rounded-2xl px-2 py-3 text-center text-xs font-medium transition"
          :class="
            isActive(item.path)
              ? 'bg-brand text-white shadow-md shadow-brand/20'
              : 'text-slate-500 hover:bg-brand-soft hover:text-brand-dark'
          "
        >
          {{ item.label }}
        </RouterLink>
      </div>
    </nav>
  </div>
</template>
