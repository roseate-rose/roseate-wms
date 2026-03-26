<script setup>
import { onMounted, reactive, ref } from "vue";

import http from "../api/http";
import { getDefaultOrderChannel, SUPPORTED_ORDER_CHANNELS } from "../constants/orderChannels";
import { formatBoundQuantity } from "../utils/quantity";

const loading = ref(false);
const syncing = ref(false);
const errorMessage = ref("");
const successMessage = ref("");
const orders = ref([]);

const orderForm = reactive({
  channel_name: getDefaultOrderChannel(),
  external_sku_id: "",
  quantity: 1,
});

async function loadOrders() {
  loading.value = true;
  errorMessage.value = "";

  try {
    const { data } = await http.get("/orders");
    orders.value = data.data.items || [];
  } catch (error) {
    errorMessage.value = error.response?.data?.msg || "订单列表加载失败";
  } finally {
    loading.value = false;
  }
}

async function syncOrder() {
  syncing.value = true;
  errorMessage.value = "";
  successMessage.value = "";

  try {
    const { data } = await http.post("/orders/sync", {
      channel_name: orderForm.channel_name,
      external_sku_id: orderForm.external_sku_id.trim(),
      quantity: Number(orderForm.quantity),
    });
    successMessage.value = `订单已同步并锁定库存，订单号 ${data.data.order.id}`;
    orderForm.external_sku_id = "";
    orderForm.quantity = 1;
    await loadOrders();
  } catch (error) {
    errorMessage.value = error.response?.data?.msg || "订单同步失败";
  } finally {
    syncing.value = false;
  }
}

async function fulfillOrder(orderId) {
  errorMessage.value = "";
  successMessage.value = "";

  try {
    const { data } = await http.post("/orders/fulfill", { order_id: orderId });
    successMessage.value = `订单 ${data.data.order.id} 已发货`;
    await loadOrders();
  } catch (error) {
    errorMessage.value = error.response?.data?.msg || "发货失败";
  }
}

onMounted(loadOrders);
</script>

<template>
  <section class="space-y-4">
    <div class="rounded-[2rem] bg-white/90 p-5 shadow-sm backdrop-blur md:p-6">
      <p class="text-xs uppercase tracking-[0.35em] text-brand/60">Orders</p>
      <h3 class="mt-2 text-2xl font-semibold text-slate-900">渠道订单列表</h3>
      <p class="mt-2 text-sm text-slate-500">从外部 SKU 映射到内部商品后执行库存预占，并在发货时转为实际 OUT 流水。当前订单渠道入口按已支持渠道显示。</p>
    </div>

    <div class="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
      <article class="rounded-[2rem] bg-white/90 p-5 shadow-sm backdrop-blur md:p-6">
        <h4 class="text-lg font-semibold text-slate-900">模拟订单同步</h4>
        <p class="mt-1 text-sm text-slate-500">渠道改为固定选项，避免手输名称与渠道映射不一致。</p>

        <form class="mt-5 space-y-4" @submit.prevent="syncOrder">
          <label class="block">
            <span class="mb-2 block text-sm font-medium text-slate-700">渠道</span>
            <select
              v-model="orderForm.channel_name"
              class="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
            >
              <option
                v-for="channel in SUPPORTED_ORDER_CHANNELS"
                :key="channel.value"
                :value="channel.value"
              >
                {{ channel.label }}
              </option>
            </select>
            <p class="mt-2 text-xs text-slate-500">
              {{ SUPPORTED_ORDER_CHANNELS.find((channel) => channel.value === orderForm.channel_name)?.importHint }}
            </p>
          </label>

          <label class="block">
            <span class="mb-2 block text-sm font-medium text-slate-700">外部 SKU ID</span>
            <input
              v-model="orderForm.external_sku_id"
              type="text"
              class="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
              placeholder="DY-SKU-11001"
            />
          </label>

          <label class="block">
            <span class="mb-2 block text-sm font-medium text-slate-700">数量</span>
            <input
              v-model="orderForm.quantity"
              type="number"
              min="1"
              class="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
            />
          </label>

          <button
            type="submit"
            class="w-full rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:opacity-70"
            :disabled="syncing"
          >
            {{ syncing ? "同步中..." : "同步订单" }}
          </button>
        </form>
      </article>

      <article class="rounded-[2rem] bg-white/90 shadow-sm backdrop-blur">
        <div class="border-b border-slate-100 px-5 py-4 md:px-6">
          <h4 class="text-lg font-semibold text-slate-900">订单状态</h4>
        </div>

        <p v-if="errorMessage" class="px-5 py-4 text-sm text-red-600 md:px-6">{{ errorMessage }}</p>
        <p v-if="successMessage" class="px-5 py-4 text-sm text-emerald-700 md:px-6">{{ successMessage }}</p>
        <div v-if="loading" class="px-5 py-8 text-sm text-slate-500 md:px-6">加载中...</div>
        <div v-else-if="!orders.length" class="px-5 py-8 text-sm text-slate-500 md:px-6">
          暂无订单。
        </div>
        <div v-else class="divide-y divide-slate-100">
          <div
            v-for="order in orders"
            :key="order.id"
            class="px-5 py-4 md:px-6"
          >
            <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <p class="text-sm font-semibold text-slate-900">
                  #{{ order.id }} · {{ order.channel_name }} · {{ order.external_sku_id }}
                </p>
                <p class="mt-1 text-xs text-slate-500">
                  {{ order.hb_code }} · 数量 {{ formatBoundQuantity(order.quantity, order) }} · {{ order.created_at }}
                </p>
              </div>
              <div class="flex items-center gap-3">
                <span
                  class="rounded-full px-3 py-1 text-xs font-semibold"
                  :class="
                    order.status === 'fulfilled'
                      ? 'bg-emerald-100 text-emerald-700'
                      : 'bg-amber-100 text-amber-700'
                  "
                >
                  {{ order.status === "fulfilled" ? "已发货" : "待发货" }}
                </span>
                <button
                  v-if="order.status === 'reserved'"
                  type="button"
                  class="rounded-2xl bg-brand px-4 py-2 text-xs font-semibold text-white"
                  @click="fulfillOrder(order.id)"
                >
                  发货核销
                </button>
              </div>
            </div>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>
