<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import http from "../api/http";
import { formatBoundQuantity, formatQuantityWithUnit } from "../utils/quantity";

const route = useRoute();
const router = useRouter();
const loading = ref(false);
const errorMessage = ref("");
const items = ref([]);

const activeFilter = computed(() => String(route.query.status || "all"));

const filterOptions = [
  { label: "全部", value: "all" },
  { label: "已过期", value: "expired" },
  { label: "临期 30 天", value: "warning" },
  { label: "健康", value: "healthy" },
];

function rowClass(status) {
  if (status === "expired") {
    return "bg-red-50";
  }
  if (status === "warning") {
    return "bg-amber-50";
  }
  return "bg-emerald-50";
}

async function loadReport() {
  loading.value = true;
  errorMessage.value = "";

  try {
    const params = activeFilter.value === "all" ? {} : { status: activeFilter.value };
    const { data } = await http.get("/inventory/expiry-report", { params });
    items.value = data.data.items || [];
  } catch (error) {
    errorMessage.value = error.response?.data?.msg || "到期报表加载失败";
  } finally {
    loading.value = false;
  }
}

function setFilter(status) {
  router.replace({
    name: "stock",
    query: status === "all" ? {} : { status },
  });
}

onMounted(loadReport);
watch(() => route.query.status, loadReport);
</script>

<template>
  <section class="space-y-4">
    <div class="rounded-[2rem] bg-white/90 p-5 shadow-sm backdrop-blur md:p-6">
      <p class="text-xs uppercase tracking-[0.35em] text-brand/60">Expiry Report</p>
      <div class="mt-3 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h3 class="text-2xl font-semibold text-slate-900">保质期批次列表</h3>
          <p class="mt-2 text-sm text-slate-500">按到期日升序排列，可按已过期、临期、健康筛选。</p>
        </div>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="filter in filterOptions"
            :key="filter.value"
            type="button"
            class="rounded-full px-4 py-2 text-sm font-medium transition"
            :class="
              activeFilter === filter.value
                ? 'bg-slate-900 text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            "
            @click="setFilter(filter.value)"
          >
            {{ filter.label }}
          </button>
        </div>
      </div>
    </div>

    <p v-if="errorMessage" class="text-sm text-red-600">{{ errorMessage }}</p>

    <div v-if="loading" class="rounded-3xl bg-white/85 p-6 text-sm text-slate-500 shadow-sm backdrop-blur">
      加载中...
    </div>
    <div v-else-if="!items.length" class="rounded-3xl bg-white/85 p-6 text-sm text-slate-500 shadow-sm backdrop-blur">
      当前筛选下暂无批次。
    </div>
    <div v-else class="space-y-3">
      <article
        v-for="item in items"
        :key="item.id"
        class="rounded-3xl border border-white/70 p-5 shadow-sm"
        :class="rowClass(item.status)"
      >
        <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p class="text-lg font-semibold text-slate-900">{{ item.product_name }}</p>
            <p class="mt-1 text-sm text-slate-600">{{ item.hb_code }} · 批号 {{ item.batch_no }}</p>
          </div>
          <span
            class="rounded-full px-3 py-1 text-xs font-semibold"
            :class="
              item.status === 'expired'
                ? 'bg-red-100 text-red-700'
                : item.status === 'warning'
                  ? 'bg-amber-100 text-amber-700'
                  : 'bg-emerald-100 text-emerald-700'
            "
          >
            {{ item.status === "expired" ? "已过期" : item.status === "warning" ? "临期" : "健康" }}
          </span>
        </div>

        <div class="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5 text-sm">
          <div>
            <p class="text-slate-500">到期日期</p>
            <p class="font-medium text-slate-800">{{ item.expiry_date }}</p>
          </div>
          <div>
            <p class="text-slate-500">实物库存</p>
            <p class="font-medium text-slate-800">{{ formatBoundQuantity(item.current_quantity, item) }}</p>
          </div>
          <div>
            <p class="text-slate-500">预占库存</p>
            <p class="font-medium text-slate-800">{{ formatBoundQuantity(item.reserved_quantity, item) }}</p>
          </div>
          <div>
            <p class="text-slate-500">可售库存</p>
            <p class="font-medium text-slate-800">{{ formatBoundQuantity(item.available_quantity, item) }}</p>
          </div>
          <div>
            <p class="text-slate-500">成本</p>
            <p class="font-medium text-slate-800">{{ formatQuantityWithUnit(item.cost, "元") }}</p>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>
