<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute } from "vue-router";

import http from "../api/http";

const route = useRoute();

const loading = ref(false);
const saving = ref(false);
const errorMessage = ref("");
const jsonError = ref("");
const searchText = ref("");
const products = ref([]);
const showCreateForm = ref(false);

const productForm = reactive({
  hb_code: "",
  barcode: "",
  name: "",
  spec: "",
  unit: "",
  base_unit: "",
  purchase_unit: "",
  conversion_rate: 1,
  extra_data_text: "",
});

const hasProducts = computed(() => products.value.length > 0);

function applyRouteDefaults() {
  showCreateForm.value = route.query.create === "1";

  if (route.query.barcode && !productForm.barcode) {
    productForm.barcode = String(route.query.barcode);
  }
}

async function loadProducts() {
  loading.value = true;
  errorMessage.value = "";

  try {
    const { data } = await http.get("/products", {
      params: searchText.value.trim() ? { q: searchText.value.trim() } : {},
    });
    products.value = data.data.items || [];
  } catch (error) {
    errorMessage.value = error.response?.data?.msg || "商品列表加载失败";
  } finally {
    loading.value = false;
  }
}

function resetForm() {
  productForm.hb_code = "";
  productForm.barcode = "";
  productForm.name = "";
  productForm.spec = "";
  productForm.unit = "";
  productForm.base_unit = "";
  productForm.purchase_unit = "";
  productForm.conversion_rate = 1;
  productForm.extra_data_text = "";
  jsonError.value = "";
}

async function createProduct() {
  saving.value = true;
  errorMessage.value = "";
  jsonError.value = "";

  let extraData = {};
  if (productForm.extra_data_text.trim()) {
    try {
      extraData = JSON.parse(productForm.extra_data_text);
    } catch {
      jsonError.value = "扩展字段必须是合法 JSON";
      saving.value = false;
      return;
    }
  }

  try {
    await http.post("/products", {
      hb_code: productForm.hb_code.trim(),
      barcode: productForm.barcode.trim(),
      name: productForm.name.trim(),
      spec: productForm.spec.trim(),
      unit: productForm.unit.trim(),
      base_unit: productForm.base_unit.trim(),
      purchase_unit: productForm.purchase_unit.trim(),
      conversion_rate: Number(productForm.conversion_rate),
      extra_data: extraData,
    });

    resetForm();
    showCreateForm.value = false;
    await loadProducts();
  } catch (error) {
    errorMessage.value = error.response?.data?.msg || "商品创建失败";
  } finally {
    saving.value = false;
  }
}

onMounted(async () => {
  applyRouteDefaults();
  await loadProducts();
});

watch(
  () => route.query,
  () => {
    applyRouteDefaults();
  },
);
</script>

<template>
  <section class="space-y-4">
    <div class="rounded-[2rem] bg-white/90 p-5 shadow-sm backdrop-blur md:p-6">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p class="text-xs uppercase tracking-[0.35em] text-brand/60">Products</p>
          <h3 class="mt-2 text-2xl font-semibold text-slate-900">商品中心</h3>
          <p class="mt-2 text-sm text-slate-500">
            商品是全局档案，总库存由该商品下所有 `current_quantity > 0` 的批次动态汇总。
          </p>
        </div>

        <div class="flex flex-col gap-3 sm:flex-row">
          <input
            v-model="searchText"
            type="text"
            placeholder="搜索名称、条码或 HB 编码"
            class="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand sm:w-80"
            @keyup.enter="loadProducts"
          />
          <button
            type="button"
            class="rounded-2xl border border-slate-200 px-4 py-3 text-sm font-medium text-slate-700 transition hover:border-brand hover:text-brand-dark"
            @click="loadProducts"
          >
            查询
          </button>
          <button
            type="button"
            class="rounded-2xl bg-brand px-4 py-3 text-sm font-semibold text-white transition hover:bg-brand-dark"
            @click="showCreateForm = !showCreateForm"
          >
            {{ showCreateForm ? "收起建档" : "新建商品" }}
          </button>
        </div>
      </div>
    </div>

    <article v-if="showCreateForm" class="rounded-[2rem] bg-white/90 p-5 shadow-sm backdrop-blur md:p-6">
      <h4 class="text-lg font-semibold text-slate-900">新建商品档案</h4>
      <p class="mt-1 text-sm text-slate-500">品牌、产地、过敏原等扩展属性可直接写入 `extra_data` JSON。</p>

      <form class="mt-5 space-y-4" @submit.prevent="createProduct">
        <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <label class="block">
            <span class="mb-2 block text-sm font-medium text-slate-700">HB 编码</span>
            <input
              v-model="productForm.hb_code"
              type="text"
              required
              class="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
            />
          </label>
          <label class="block">
            <span class="mb-2 block text-sm font-medium text-slate-700">条码</span>
            <input
              v-model="productForm.barcode"
              type="text"
              class="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
            />
          </label>
          <label class="block">
            <span class="mb-2 block text-sm font-medium text-slate-700">商品名称</span>
            <input
              v-model="productForm.name"
              type="text"
              required
              class="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
            />
          </label>
          <label class="block">
            <span class="mb-2 block text-sm font-medium text-slate-700">规格</span>
            <input
              v-model="productForm.spec"
              type="text"
              required
              class="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
            />
          </label>
          <label class="block">
            <span class="mb-2 block text-sm font-medium text-slate-700">单位</span>
            <input
              v-model="productForm.unit"
              type="text"
              required
              class="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
            />
          </label>
          <label class="block">
            <span class="mb-2 block text-sm font-medium text-slate-700">最小售卖单位</span>
            <input
              v-model="productForm.base_unit"
              type="text"
              required
              class="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
            />
          </label>
          <label class="block">
            <span class="mb-2 block text-sm font-medium text-slate-700">采购单位</span>
            <input
              v-model="productForm.purchase_unit"
              type="text"
              required
              class="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
            />
          </label>
          <label class="block">
            <span class="mb-2 block text-sm font-medium text-slate-700">换算率</span>
            <input
              v-model="productForm.conversion_rate"
              type="number"
              min="1"
              required
              class="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
            />
          </label>
        </div>

        <label class="block">
          <span class="mb-2 block text-sm font-medium text-slate-700">扩展字段 JSON</span>
          <textarea
            v-model="productForm.extra_data_text"
            rows="4"
            class="w-full rounded-2xl border border-slate-200 px-4 py-3 font-mono text-sm outline-none transition focus:border-brand"
            placeholder='{"brand":"Roseate Lab","origin":"CN"}'
          />
        </label>

        <p v-if="jsonError" class="text-sm text-red-600">{{ jsonError }}</p>
        <p v-if="errorMessage" class="text-sm text-red-600">{{ errorMessage }}</p>

        <div class="flex gap-3">
          <button
            type="submit"
            class="rounded-2xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:opacity-70"
            :disabled="saving"
          >
            {{ saving ? "保存中..." : "保存档案" }}
          </button>
          <button
            type="button"
            class="rounded-2xl border border-slate-200 px-5 py-3 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
            @click="resetForm"
          >
            重置
          </button>
        </div>
      </form>
    </article>

    <article class="rounded-[2rem] bg-white/90 shadow-sm backdrop-blur">
      <div class="border-b border-slate-100 px-5 py-4 md:px-6">
        <h4 class="text-lg font-semibold text-slate-900">商品列表</h4>
        <p class="mt-1 text-sm text-slate-500">桌面端展示表格，移动端自动折叠为卡片。</p>
      </div>

      <div v-if="loading" class="px-5 py-8 text-sm text-slate-500 md:px-6">加载中...</div>
      <div v-else-if="!hasProducts" class="px-5 py-8 text-sm text-slate-500 md:px-6">
        暂无商品，请先创建档案。
      </div>
      <div v-else>
        <div class="hidden overflow-x-auto md:block">
          <table class="min-w-full text-left">
            <thead class="bg-slate-50 text-xs uppercase tracking-[0.25em] text-slate-400">
              <tr>
                <th class="px-6 py-4">HB 编码</th>
                <th class="px-6 py-4">条码</th>
                <th class="px-6 py-4">商品</th>
                <th class="px-6 py-4">规格</th>
                <th class="px-6 py-4">单位</th>
                <th class="px-6 py-4">可售库存</th>
                <th class="px-6 py-4">总库存</th>
                <th class="px-6 py-4">操作</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-sm text-slate-700">
              <tr v-for="item in products" :key="item.hb_code">
                <td class="px-6 py-4 font-semibold text-slate-900">{{ item.hb_code }}</td>
                <td class="px-6 py-4">{{ item.barcode || "-" }}</td>
                <td class="px-6 py-4">{{ item.name }}</td>
                <td class="px-6 py-4">{{ item.spec }}</td>
                <td class="px-6 py-4">{{ item.base_unit }} / {{ item.purchase_unit }}</td>
                <td class="px-6 py-4">{{ item.sellable_stock }}</td>
                <td class="px-6 py-4">
                  <span class="rounded-full bg-brand-soft px-3 py-1 text-xs font-semibold text-brand-dark">
                    {{ item.total_stock }}
                  </span>
                </td>
                <td class="px-6 py-4">
                  <RouterLink
                    :to="{ name: 'product-detail', params: { hbCode: item.hb_code } }"
                    class="text-sm font-medium text-brand-dark hover:text-brand"
                  >
                    查看详情
                  </RouterLink>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="grid gap-3 p-4 md:hidden">
          <article
            v-for="item in products"
            :key="item.hb_code"
            class="rounded-3xl border border-slate-100 bg-slate-50 p-4"
          >
            <div class="flex items-start justify-between gap-3">
              <div>
                <p class="text-sm font-semibold text-slate-900">{{ item.name }}</p>
                <p class="mt-1 text-xs text-slate-500">{{ item.hb_code }} · {{ item.barcode || "无条码" }}</p>
              </div>
              <span class="rounded-full bg-brand-soft px-3 py-1 text-xs font-semibold text-brand-dark">
                可售 {{ item.sellable_stock }}
              </span>
            </div>
            <div class="mt-4 grid grid-cols-2 gap-3 text-sm">
              <div>
                <p class="text-slate-500">规格</p>
                <p class="font-medium text-slate-800">{{ item.spec }}</p>
              </div>
              <div>
                <p class="text-slate-500">单位</p>
                <p class="font-medium text-slate-800">{{ item.base_unit }} / {{ item.purchase_unit }}</p>
              </div>
              <div>
                <p class="text-slate-500">总库存</p>
                <p class="font-medium text-slate-800">{{ item.total_stock }}</p>
              </div>
            </div>
            <RouterLink
              :to="{ name: 'product-detail', params: { hbCode: item.hb_code } }"
              class="mt-4 inline-flex text-sm font-medium text-brand-dark"
            >
              查看详情
            </RouterLink>
          </article>
        </div>
      </div>
    </article>
  </section>
</template>
