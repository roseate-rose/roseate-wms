<script setup>
import { computed, reactive, ref } from "vue";
import { useRouter } from "vue-router";

import http from "../api/http";
import { getStoredRole } from "../auth/session";

const router = useRouter();
const role = getStoredRole();
const isAdmin = role === "admin";

const lookupCode = ref("");
const lookupLoading = ref(false);
const lookupMessage = ref("");
const lookupError = ref("");
const selectedProduct = ref(null);
const inboundLoading = ref(false);
const inboundSuccess = ref("");
const showQuickMapping = ref(false);
const quickMapping = reactive({
  channel_name: "抖音",
  hb_code: "",
});

const batchForm = reactive({
  batch_no: "",
  production_date: "",
  expiry_date: "",
  quantity: 1,
  cost: "",
  unit_type: "base",
});

const currentStep = computed(() => {
  if (selectedProduct.value) {
    return 3;
  }

  return lookupCode.value.trim() ? 2 : 1;
});

const quantityUnitLabel = computed(() => {
  if (!selectedProduct.value) {
    return batchForm.unit_type === "purchase" ? "采购单位" : "最小单位";
  }

  return batchForm.unit_type === "purchase"
    ? selectedProduct.value.purchase_unit
    : selectedProduct.value.base_unit;
});

async function resolveProduct() {
  const code = lookupCode.value.trim();
  lookupError.value = "";
  lookupMessage.value = "";
  inboundSuccess.value = "";
  selectedProduct.value = null;
  showQuickMapping.value = false;

  if (!code) {
    lookupError.value = "请先输入条码或内部编码";
    return;
  }

  lookupLoading.value = true;

  try {
    const { data } = await http.get("/products", { params: { q: code } });
    const items = data.data.items || [];
    const exactMatch =
      items.find((item) => item.barcode === code) ||
      items.find((item) => item.hb_code === code) ||
      items[0];

    if (!exactMatch) {
      lookupMessage.value = "未找到对应商品，请先建档后再执行入库。";
      return;
    }

    selectedProduct.value = exactMatch;
    lookupMessage.value = "已识别商品，请继续填写批次信息。";
  } catch (error) {
    lookupError.value = error.response?.data?.msg || "商品查询失败";
  } finally {
    lookupLoading.value = false;
  }
}

async function submitInbound() {
  if (!selectedProduct.value) {
    lookupError.value = "请先识别商品";
    return;
  }

  inboundLoading.value = true;
  inboundSuccess.value = "";
  lookupError.value = "";

  try {
    const payload = {
      barcode: selectedProduct.value.barcode || lookupCode.value.trim(),
      hb_code: selectedProduct.value.hb_code,
      batch_no: batchForm.batch_no,
      production_date: batchForm.production_date || null,
      expiry_date: batchForm.expiry_date,
      quantity: Number(batchForm.quantity),
      cost: Number(batchForm.cost),
      unit_type: batchForm.unit_type,
    };
    const { data } = await http.post("/inventory/inbound", payload);

    inboundSuccess.value = `入库成功：${data.data.action === "merged" ? "已合并现有批次" : "已创建新批次"}，按${selectedProduct.value.base_unit}计共入 ${data.data.normalized_quantity}，当前总库存 ${data.data.product.total_stock}`;
    selectedProduct.value = data.data.product;
    batchForm.batch_no = "";
    batchForm.production_date = "";
    batchForm.expiry_date = "";
    batchForm.quantity = 1;
    batchForm.cost = "";
    batchForm.unit_type = "base";
  } catch (error) {
    lookupError.value = error.response?.data?.msg || "入库失败";
  } finally {
    inboundLoading.value = false;
  }
}

function goToCreateProduct() {
  router.push({
    name: "products",
    query: { create: "1", barcode: lookupCode.value.trim() },
  });
}

async function createQuickMapping() {
  lookupError.value = "";
  lookupMessage.value = "";

  try {
    await http.post("/channel-mappings", {
      channel_name: quickMapping.channel_name.trim(),
      external_sku_id: lookupCode.value.trim(),
      hb_code: quickMapping.hb_code.trim(),
    });
    lookupMessage.value = "映射创建成功，可继续在渠道订单中使用该外部编码。";
    showQuickMapping.value = false;
    quickMapping.hb_code = "";
  } catch (error) {
    lookupError.value = error.response?.data?.msg || "映射创建失败";
  }
}
</script>

<template>
  <section class="space-y-4">
    <div class="rounded-[2rem] bg-white/90 p-5 shadow-sm backdrop-blur md:p-6">
      <div class="flex items-center justify-between">
        <div>
          <p class="text-xs uppercase tracking-[0.35em] text-brand/60">Inbound</p>
          <h3 class="mt-2 text-xl font-semibold text-slate-900">H5 入库流程</h3>
        </div>
        <span class="rounded-full bg-brand-soft px-3 py-1 text-xs font-medium text-brand-dark">
          Step {{ currentStep }}/3
        </span>
      </div>

      <div class="mt-6 grid gap-3 md:grid-cols-3">
        <div
          class="rounded-2xl border px-4 py-3"
          :class="currentStep >= 1 ? 'border-brand bg-brand-soft/50' : 'border-slate-200 bg-slate-50'"
        >
          <p class="text-sm font-semibold text-slate-900">1. 扫码/录码</p>
          <p class="mt-1 text-xs text-slate-500">输入条码或内部编码进行识别。</p>
        </div>
        <div
          class="rounded-2xl border px-4 py-3"
          :class="currentStep >= 2 ? 'border-brand bg-brand-soft/50' : 'border-slate-200 bg-slate-50'"
        >
          <p class="text-sm font-semibold text-slate-900">2. 识别商品</p>
          <p class="mt-1 text-xs text-slate-500">不存在则可建档，管理员可直接建立映射。</p>
        </div>
        <div
          class="rounded-2xl border px-4 py-3"
          :class="currentStep >= 3 ? 'border-brand bg-brand-soft/50' : 'border-slate-200 bg-slate-50'"
        >
          <p class="text-sm font-semibold text-slate-900">3. 批次入库</p>
          <p class="mt-1 text-xs text-slate-500">支持采购单位与最小单位换算入库。</p>
        </div>
      </div>
    </div>

    <div class="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
      <article class="rounded-[2rem] bg-white/90 p-5 shadow-sm backdrop-blur md:p-6">
        <div class="flex items-center justify-between">
          <div>
            <h4 class="text-lg font-semibold text-slate-900">步骤 1: 识别商品</h4>
            <p class="mt-1 text-sm text-slate-500">支持模拟扫码输入条码，也支持直接输入 HB 编码。</p>
          </div>
        </div>

        <div class="mt-5 flex flex-col gap-3 sm:flex-row">
          <input
            v-model="lookupCode"
            type="text"
            placeholder="例如 6900000000001 / HB2001"
            class="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
          />
          <button
            type="button"
            class="rounded-2xl bg-brand px-5 py-3 text-sm font-semibold text-white transition hover:bg-brand-dark disabled:opacity-70"
            :disabled="lookupLoading"
            @click="resolveProduct"
          >
            {{ lookupLoading ? "识别中..." : "识别商品" }}
          </button>
        </div>

        <p v-if="lookupError" class="mt-4 text-sm text-red-600">{{ lookupError }}</p>
        <div
          v-else-if="lookupMessage"
          class="mt-4 rounded-2xl border border-brand/20 bg-brand-soft/60 px-4 py-3 text-sm text-brand-dark"
        >
          {{ lookupMessage }}
        </div>

        <div v-if="selectedProduct" class="mt-5 rounded-3xl border border-slate-200 bg-slate-50 p-4">
          <p class="text-xs uppercase tracking-[0.3em] text-slate-400">Matched Product</p>
          <div class="mt-3 grid gap-3 sm:grid-cols-2">
            <div>
              <p class="text-sm text-slate-500">商品名称</p>
              <p class="text-base font-semibold text-slate-900">{{ selectedProduct.name }}</p>
            </div>
            <div>
              <p class="text-sm text-slate-500">内部编码</p>
              <p class="text-base font-semibold text-slate-900">{{ selectedProduct.hb_code }}</p>
            </div>
            <div>
              <p class="text-sm text-slate-500">单位体系</p>
              <p class="text-base font-semibold text-slate-900">
                {{ selectedProduct.purchase_unit }} = {{ selectedProduct.conversion_rate }} {{ selectedProduct.base_unit }}
              </p>
            </div>
            <div>
              <p class="text-sm text-slate-500">当前可售库存</p>
              <p class="text-base font-semibold text-slate-900">{{ selectedProduct.sellable_stock }}</p>
            </div>
          </div>
        </div>

        <div v-else-if="lookupCode.trim() && !lookupLoading && lookupMessage" class="mt-4 space-y-3">
          <div class="flex flex-wrap gap-2">
            <button
              type="button"
              class="rounded-2xl border border-brand/20 px-4 py-3 text-sm font-medium text-brand-dark transition hover:bg-brand-soft"
              @click="goToCreateProduct"
            >
              前往商品中心建档
            </button>
            <button
              v-if="isAdmin"
              type="button"
              class="rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white"
              @click="showQuickMapping = !showQuickMapping"
            >
              {{ showQuickMapping ? "收起映射" : "映射" }}
            </button>
          </div>

          <div v-if="showQuickMapping" class="rounded-3xl border border-slate-200 bg-slate-50 p-4">
            <p class="text-sm font-semibold text-slate-900">未知扫码快速映射</p>
            <div class="mt-4 grid gap-3 sm:grid-cols-2">
              <input
                v-model="quickMapping.channel_name"
                type="text"
                class="rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
                placeholder="渠道名称"
              />
              <input
                v-model="quickMapping.hb_code"
                type="text"
                class="rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
                placeholder="绑定到 HB 编码"
              />
            </div>
            <button
              type="button"
              class="mt-3 rounded-2xl bg-brand px-4 py-3 text-sm font-semibold text-white"
              @click="createQuickMapping"
            >
              保存映射
            </button>
          </div>
        </div>
      </article>

      <article class="rounded-[2rem] bg-white/90 p-5 shadow-sm backdrop-blur md:p-6">
        <h4 class="text-lg font-semibold text-slate-900">步骤 2: 填写批次信息</h4>
        <p class="mt-1 text-sm text-slate-500">批次合并规则：同一商品、相同到期日将累计到同一批次。</p>

        <form class="mt-5 space-y-4" @submit.prevent="submitInbound">
          <label class="block">
            <span class="mb-2 block text-sm font-medium text-slate-700">生产批号</span>
            <input
              v-model="batchForm.batch_no"
              type="text"
              class="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
              placeholder="LOT-20260309"
            />
          </label>

          <label class="block">
            <span class="mb-2 block text-sm font-medium text-slate-700">数量单位</span>
            <select
              v-model="batchForm.unit_type"
              class="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
            >
              <option value="base">最小单位</option>
              <option value="purchase">采购单位</option>
            </select>
          </label>

          <div class="grid gap-4 sm:grid-cols-2">
            <label class="block">
              <span class="mb-2 block text-sm font-medium text-slate-700">生产日期</span>
              <input
                v-model="batchForm.production_date"
                type="date"
                class="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
              />
            </label>
            <label class="block">
              <span class="mb-2 block text-sm font-medium text-slate-700">到期日期</span>
              <input
                v-model="batchForm.expiry_date"
                type="date"
                required
                class="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
              />
            </label>
          </div>

          <div class="grid gap-4 sm:grid-cols-2">
            <label class="block">
              <span class="mb-2 block text-sm font-medium text-slate-700">入库数量（{{ quantityUnitLabel }}）</span>
              <input
                v-model="batchForm.quantity"
                type="number"
                min="1"
                required
                class="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
              />
            </label>
            <label class="block">
              <span class="mb-2 block text-sm font-medium text-slate-700">成本单价</span>
              <input
                v-model="batchForm.cost"
                type="number"
                min="0"
                step="0.01"
                required
                class="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
              />
            </label>
          </div>

          <p v-if="inboundSuccess" class="rounded-2xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
            {{ inboundSuccess }}
          </p>

          <button
            type="submit"
            class="w-full rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
            :disabled="!selectedProduct || inboundLoading"
          >
            {{ inboundLoading ? "提交中..." : "确认入库" }}
          </button>
        </form>
      </article>
    </div>
  </section>
</template>
