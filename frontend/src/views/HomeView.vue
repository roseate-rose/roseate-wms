<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import http from "../api/http";

const router = useRouter();
const loading = ref(false);
const errorMessage = ref("");
const stats = ref({
  total_value: 0,
  expired_count: 0,
  warning_count: 0,
  healthy_count: 0,
});

async function loadStats() {
  loading.value = true;
  errorMessage.value = "";

  try {
    const { data } = await http.get("/dashboard/stats");
    stats.value = data.data;
  } catch (error) {
    errorMessage.value = error.response?.data?.msg || "看板数据加载失败";
  } finally {
    loading.value = false;
  }
}

function openExpiry(status) {
  router.push({
    name: "stock",
    query: status ? { status } : {},
  });
}

onMounted(loadStats);
</script>

<template>
  <section class="space-y-4">
    <div class="rounded-[2rem] bg-white/90 p-5 shadow-sm backdrop-blur md:p-6">
      <p class="text-xs uppercase tracking-[0.35em] text-brand/60">Dashboard</p>
      <div class="mt-3 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h3 class="text-2xl font-semibold text-slate-900">保质期预警看板</h3>
          <p class="mt-2 text-sm text-slate-500">首页展示已过期、30 天内临期和健康批次数量，支持一键跳转明细。</p>
        </div>
        <div class="rounded-3xl bg-slate-900 px-5 py-4 text-white">
          <p class="text-xs uppercase tracking-[0.25em] text-white/60">Total Value</p>
          <p class="mt-2 text-3xl font-semibold">{{ loading ? "..." : stats.total_value }}</p>
        </div>
      </div>
    </div>

    <p v-if="errorMessage" class="text-sm text-red-600">{{ errorMessage }}</p>

    <div class="grid gap-4 md:grid-cols-3">
      <button
        type="button"
        class="rounded-3xl bg-red-50 p-5 text-left shadow-sm transition hover:-translate-y-0.5"
        @click="openExpiry('expired')"
      >
        <p class="text-sm font-medium text-red-700">已过期</p>
        <p class="mt-3 text-4xl font-semibold text-red-800">{{ stats.expired_count }}</p>
        <p class="mt-2 text-sm text-red-600">点击查看过期批次</p>
      </button>

      <button
        type="button"
        class="rounded-3xl bg-amber-50 p-5 text-left shadow-sm transition hover:-translate-y-0.5"
        @click="openExpiry('warning')"
      >
        <p class="text-sm font-medium text-amber-700">临期 30 天</p>
        <p class="mt-3 text-4xl font-semibold text-amber-800">{{ stats.warning_count }}</p>
        <p class="mt-2 text-sm text-amber-600">点击查看临期批次</p>
      </button>

      <button
        type="button"
        class="rounded-3xl bg-emerald-50 p-5 text-left shadow-sm transition hover:-translate-y-0.5"
        @click="openExpiry('healthy')"
      >
        <p class="text-sm font-medium text-emerald-700">健康库存</p>
        <p class="mt-3 text-4xl font-semibold text-emerald-800">{{ stats.healthy_count }}</p>
        <p class="mt-2 text-sm text-emerald-600">点击查看健康批次</p>
      </button>
    </div>
  </section>
</template>
