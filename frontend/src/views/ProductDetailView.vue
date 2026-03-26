<script setup>
import { onMounted, reactive, ref } from "vue";
import { useRoute } from "vue-router";

import http from "../api/http";
import { formatBoundQuantity, formatQuantityWithUnit } from "../utils/quantity";

const route = useRoute();

const loading = ref(false);
const reserving = ref(false);
const errorMessage = ref("");
const successMessage = ref("");
const product = ref(null);
const reserveForm = reactive({
  quantity: 1,
});

async function loadProduct() {
  loading.value = true;
  errorMessage.value = "";

  try {
    const { data } = await http.get(`/products/${route.params.hbCode}`);
    product.value = data.data.product;
  } catch (error) {
    errorMessage.value = error.response?.data?.msg || "商品详情加载失败";
  } finally {
    loading.value = false;
  }
}

async function reserveInventory() {
  reserving.value = true;
  errorMessage.value = "";
  successMessage.value = "";

  try {
    const { data } = await http.post("/inventory/reserve", {
      hb_code: route.params.hbCode,
      quantity: Number(reserveForm.quantity),
    });
    successMessage.value = `预占成功，已预占 ${formatBoundQuantity(data.data.reserved_quantity, product.value)}`;
    await loadProduct();
  } catch (error) {
    errorMessage.value = error.response?.data?.msg || "预占失败";
  } finally {
    reserving.value = false;
  }
}

onMounted(loadProduct);
</script>

<template>
  <section class="space-y-4">
    <div v-if="loading" class="rounded-[2rem] bg-white/90 p-6 text-sm text-slate-500 shadow-sm backdrop-blur">
      加载中...
    </div>

    <template v-else-if="product">
      <article class="rounded-[2rem] bg-white/90 p-5 shadow-sm backdrop-blur md:p-6">
        <p class="text-xs uppercase tracking-[0.35em] text-brand/60">Product Detail</p>
        <div class="mt-3 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h3 class="text-2xl font-semibold text-slate-900">{{ product.name }}</h3>
            <p class="mt-2 text-sm text-slate-500">
              {{ product.hb_code }} · {{ product.barcode || "无条码" }} · {{ product.spec }}
            </p>
          </div>
          <div class="grid grid-cols-3 gap-3">
            <div class="rounded-3xl bg-slate-50 px-4 py-3 text-center">
              <p class="text-xs text-slate-500">总库存</p>
              <p class="mt-2 text-xl font-semibold text-slate-900">{{ formatBoundQuantity(product.total_stock, product) }}</p>
            </div>
            <div class="rounded-3xl bg-amber-50 px-4 py-3 text-center">
              <p class="text-xs text-slate-500">预占库存</p>
              <p class="mt-2 text-xl font-semibold text-amber-700">{{ formatBoundQuantity(product.reserved_stock, product) }}</p>
            </div>
            <div class="rounded-3xl bg-emerald-50 px-4 py-3 text-center">
              <p class="text-xs text-slate-500">可售库存</p>
              <p class="mt-2 text-xl font-semibold text-emerald-700">{{ formatBoundQuantity(product.sellable_stock, product) }}</p>
            </div>
          </div>
        </div>

        <div class="mt-6 grid gap-4 md:grid-cols-3">
          <div class="rounded-3xl border border-slate-100 bg-slate-50 p-4">
            <p class="text-sm text-slate-500">最小售卖单位</p>
            <p class="mt-2 text-lg font-semibold text-slate-900">{{ product.base_unit }}</p>
          </div>
          <div class="rounded-3xl border border-slate-100 bg-slate-50 p-4">
            <p class="text-sm text-slate-500">采购单位</p>
            <p class="mt-2 text-lg font-semibold text-slate-900">{{ product.purchase_unit }}</p>
          </div>
          <div class="rounded-3xl border border-slate-100 bg-slate-50 p-4">
            <p class="text-sm text-slate-500">换算比例</p>
            <p class="mt-2 text-lg font-semibold text-slate-900">
              1 {{ product.purchase_unit }} = {{ product.conversion_rate }} {{ product.base_unit }}
            </p>
          </div>
        </div>
      </article>

      <div class="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
        <article class="rounded-[2rem] bg-white/90 p-5 shadow-sm backdrop-blur md:p-6">
          <h4 class="text-lg font-semibold text-slate-900">库存预占</h4>
          <p class="mt-1 text-sm text-slate-500">按 FIFO 顺序消耗可售库存，但不会减少实物库存。</p>

          <form class="mt-5 space-y-4" @submit.prevent="reserveInventory">
            <label class="block">
              <span class="mb-2 block text-sm font-medium text-slate-700">预占数量（{{ product.base_unit }}）</span>
              <input
                v-model="reserveForm.quantity"
                type="number"
                min="1"
                class="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
              />
            </label>

            <p v-if="errorMessage" class="text-sm text-red-600">{{ errorMessage }}</p>
            <p v-if="successMessage" class="text-sm text-emerald-700">{{ successMessage }}</p>

            <button
              type="submit"
              class="w-full rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:opacity-70"
              :disabled="reserving"
            >
              {{ reserving ? "提交中..." : "执行预占" }}
            </button>
          </form>
        </article>

        <article class="rounded-[2rem] bg-white/90 p-5 shadow-sm backdrop-blur md:p-6">
          <h4 class="text-lg font-semibold text-slate-900">批次明细</h4>
          <div class="mt-4 space-y-3">
            <div
              v-for="batch in product.batches"
              :key="batch.id"
              class="rounded-3xl border border-slate-100 bg-slate-50 p-4"
            >
              <div class="flex items-start justify-between gap-3">
                <div>
                  <p class="text-sm font-semibold text-slate-900">{{ batch.batch_no }}</p>
                  <p class="mt-1 text-xs text-slate-500">
                    到期 {{ batch.expiry_date }} · 生产 {{ batch.production_date || "未填" }}
                  </p>
                </div>
                <span class="rounded-full bg-brand-soft px-3 py-1 text-xs font-semibold text-brand-dark">
                  可售 {{ formatBoundQuantity(batch.available_quantity, product) }}
                </span>
              </div>
              <div class="mt-4 grid grid-cols-3 gap-3 text-sm">
                <div>
                  <p class="text-slate-500">实物库存</p>
                  <p class="font-medium text-slate-800">{{ formatBoundQuantity(batch.current_quantity, product) }}</p>
                </div>
                <div>
                  <p class="text-slate-500">预占库存</p>
                  <p class="font-medium text-slate-800">{{ formatBoundQuantity(batch.reserved_quantity, product) }}</p>
                </div>
                <div>
                  <p class="text-slate-500">成本</p>
                  <p class="font-medium text-slate-800">{{ formatQuantityWithUnit(batch.cost, "元") }}</p>
                </div>
              </div>
            </div>
          </div>
        </article>
      </div>
    </template>

    <div v-else class="rounded-[2rem] bg-white/90 p-6 text-sm text-red-600 shadow-sm backdrop-blur">
      {{ errorMessage || "未找到商品" }}
    </div>
  </section>
</template>
