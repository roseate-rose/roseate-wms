<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute } from "vue-router";

import http from "../api/http";
import { getStoredRole } from "../auth/session";
import { formatBoundQuantity } from "../utils/quantity";

const PRODUCT_IMPORT_HEADERS = [
  "hb_code",
  "name",
  "spec",
  "barcode",
  "unit",
  "base_unit",
  "purchase_unit",
  "conversion_rate",
  "extra_data(JSON)",
];

const route = useRoute();
const role = getStoredRole();
const isAdmin = role === "admin";

const loading = ref(false);
const saving = ref(false);
const errorMessage = ref("");
const jsonError = ref("");
const searchText = ref("");
const products = ref([]);
const showCreateForm = ref(false);
const showImportPanel = ref(false);
const formMode = ref("create");
const deletingHbCode = ref("");

const importMode = ref("skip");
const importFile = ref(null);
const importPreview = ref(null);
const importingPreview = ref(false);
const importingCommit = ref(false);
const importError = ref("");
const importSuccess = ref("");
const expandedExtra = ref(new Set());

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

const conversionHint = computed(() => {
  const purchase = productForm.purchase_unit.trim();
  const base = productForm.base_unit.trim();
  const rate = Number(productForm.conversion_rate);
  if (!purchase || !base || !rate || rate <= 0) {
    return "";
  }
  const perBase = 1 / rate;
  if (!Number.isFinite(perBase)) {
    return "";
  }
  return `1 ${base} = ${perBase} ${purchase}`;
});

function applyRouteDefaults() {
  if (route.query.create === "1") {
    showCreateForm.value = true;
    formMode.value = "create";
  }

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
  formMode.value = "create";
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

function openCreateForm() {
  resetForm();
  showCreateForm.value = true;
}

function openEditForm(product) {
  formMode.value = "edit";
  showCreateForm.value = true;
  jsonError.value = "";
  errorMessage.value = "";
  productForm.hb_code = product.hb_code || "";
  productForm.barcode = product.barcode || "";
  productForm.name = product.name || "";
  productForm.spec = product.spec || "";
  productForm.unit = product.unit || "";
  productForm.base_unit = product.base_unit || "";
  productForm.purchase_unit = product.purchase_unit || "";
  productForm.conversion_rate = Number(product.conversion_rate || 1);
  productForm.extra_data_text = JSON.stringify(product.extra_data || {}, null, 2);
}

function formatStock(item, key) {
  return formatBoundQuantity(item?.[key], item);
}

function toggleExtra(hbCode) {
  const next = new Set(expandedExtra.value);
  if (next.has(hbCode)) {
    next.delete(hbCode);
  } else {
    next.add(hbCode);
  }
  expandedExtra.value = next;
}

function onImportFileChange(event) {
  const [file] = event.target.files || [];
  importFile.value = file || null;
  importPreview.value = null;
  importError.value = "";
  importSuccess.value = "";
}

function buildImportFormData() {
  const formData = new FormData();
  formData.append("mode", importMode.value);
  formData.append("file", importFile.value);
  return formData;
}

async function previewImport() {
  if (!importFile.value) {
    importError.value = "请先选择 CSV / Excel 文件";
    return;
  }

  importingPreview.value = true;
  importError.value = "";
  importSuccess.value = "";

  try {
    const { data } = await http.post("/products/import/preview", buildImportFormData(), {
      headers: { "Content-Type": "multipart/form-data" },
    });
    importPreview.value = data.data;
  } catch (error) {
    importError.value = error.response?.data?.msg || "预览失败";
  } finally {
    importingPreview.value = false;
  }
}

async function commitImport() {
  if (!importFile.value) {
    importError.value = "请先选择文件";
    return;
  }
  if (!importPreview.value) {
    importError.value = "请先预览确认";
    return;
  }

  importingCommit.value = true;
  importError.value = "";
  importSuccess.value = "";

  try {
    const { data } = await http.post("/products/import", buildImportFormData(), {
      headers: { "Content-Type": "multipart/form-data" },
    });
    importSuccess.value = `导入完成：新建 ${data.data.created}，覆盖 ${data.data.updated}，跳过 ${data.data.skipped}。`;
    importPreview.value = null;
    importFile.value = null;
    await loadProducts();
  } catch (error) {
    importError.value = error.response?.data?.msg || "导入失败";
  } finally {
    importingCommit.value = false;
  }
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
    const payload = {
      hb_code: productForm.hb_code.trim(),
      barcode: productForm.barcode.trim(),
      name: productForm.name.trim(),
      spec: productForm.spec.trim(),
      unit: productForm.unit.trim(),
      base_unit: productForm.base_unit.trim(),
      purchase_unit: productForm.purchase_unit.trim(),
      conversion_rate: Number(productForm.conversion_rate),
      extra_data: extraData,
    };

    if (formMode.value === "edit") {
      await http.put(`/products/${productForm.hb_code.trim()}`, payload);
    } else {
      await http.post("/products", payload);
    }

    resetForm();
    showCreateForm.value = false;
    await loadProducts();
  } catch (error) {
    errorMessage.value =
      error.response?.data?.msg || (formMode.value === "edit" ? "商品更新失败" : "商品创建失败");
  } finally {
    saving.value = false;
  }
}

async function deleteProduct(item) {
  if (!window.confirm(`确认删除商品 ${item.hb_code} - ${item.name} 吗？`)) {
    return;
  }

  deletingHbCode.value = item.hb_code;
  errorMessage.value = "";

  try {
    await http.delete(`/products/${item.hb_code}`);
    if (productForm.hb_code === item.hb_code) {
      resetForm();
      showCreateForm.value = false;
    }
    await loadProducts();
  } catch (error) {
    errorMessage.value = error.response?.data?.msg || "商品删除失败";
  } finally {
    deletingHbCode.value = "";
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
            v-if="isAdmin"
            type="button"
            class="rounded-2xl bg-brand px-4 py-3 text-sm font-semibold text-white transition hover:bg-brand-dark"
            @click="showCreateForm ? (showCreateForm = false) : openCreateForm()"
          >
            {{ showCreateForm ? "收起档案表单" : "新建商品" }}
          </button>
          <button
            v-if="isAdmin"
            type="button"
            class="rounded-2xl border border-slate-200 px-4 py-3 text-sm font-medium text-slate-700 transition hover:border-brand hover:text-brand-dark"
            @click="showImportPanel = !showImportPanel"
          >
            {{ showImportPanel ? "收起导入" : "导入表格" }}
          </button>
        </div>
      </div>
    </div>

    <article
      v-if="showImportPanel"
      class="rounded-[2rem] bg-white/90 p-5 shadow-sm backdrop-blur md:p-6"
    >
      <h4 class="text-lg font-semibold text-slate-900">导入商品档案</h4>
      <p class="mt-1 text-sm text-slate-500">
        支持 CSV / Excel。必填列：hb_code、name、spec。可选列：barcode、unit、base_unit、purchase_unit、conversion_rate、extra_data(JSON)。
      </p>

      <div v-if="!isAdmin" class="mt-4 rounded-3xl bg-amber-50 p-4 text-sm text-amber-700">
        当前账号不是管理员，无法导入。
      </div>

      <div v-else class="mt-5 grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
        <div class="space-y-4">
          <label class="block">
            <span class="mb-2 block text-sm font-medium text-slate-700">文件</span>
            <input
              type="file"
              accept=".csv,.xlsx,.xls,text/csv,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              class="block w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm"
              @change="onImportFileChange"
            />
          </label>

          <label class="block">
            <span class="mb-2 block text-sm font-medium text-slate-700">冲突处理</span>
            <select
              v-model="importMode"
              class="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
            >
              <option value="skip">跳过已存在 hb_code</option>
              <option value="overwrite">覆盖已存在 hb_code</option>
            </select>
          </label>

          <div class="rounded-[1.5rem] border border-brand/10 bg-brand-soft/30 p-4">
            <p class="text-sm font-semibold text-slate-900">标准表头顺序</p>
            <p class="mt-1 text-sm text-slate-600">
              这份模板现在会严格按以下字段解析，并自动忽略后面纯空白的尾随列，避免 `unit` 后面的数据错位。
            </p>
            <div class="mt-3 flex flex-wrap gap-2">
              <span
                v-for="header in PRODUCT_IMPORT_HEADERS"
                :key="header"
                class="rounded-full border border-white/80 bg-white px-3 py-1 text-xs font-medium text-slate-700"
              >
                {{ header }}
              </span>
            </div>
            <p class="mt-3 text-xs text-slate-500">
              别名也支持：例如 `HB编码`、`商品名称`、`计量单位`、`最小单位`、`采购单位`、`换算率`、`extra_data(JSON)`。
            </p>
          </div>

          <div class="grid gap-3 sm:grid-cols-2">
            <button
              type="button"
              class="rounded-2xl border border-slate-200 px-4 py-3 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:opacity-70"
              :disabled="importingPreview"
              @click="previewImport"
            >
              {{ importingPreview ? "预览中..." : "预览前 5 条" }}
            </button>
            <button
              type="button"
              class="rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:opacity-70"
              :disabled="importingCommit || !importPreview"
              @click="commitImport"
            >
              {{ importingCommit ? "导入中..." : "确认导入" }}
            </button>
          </div>

          <p v-if="importError" class="text-sm text-red-600">{{ importError }}</p>
          <p v-if="importSuccess" class="text-sm text-emerald-700">{{ importSuccess }}</p>
        </div>

        <div class="rounded-[2rem] border border-slate-100 bg-slate-50 p-5">
          <p class="text-sm font-semibold text-slate-900">预览</p>
          <p class="mt-1 text-sm text-slate-500">
            总计 {{ importPreview?.total_rows || 0 }} 行，有效 {{ importPreview?.valid_rows || 0 }} 行，错误
            {{ importPreview?.error_rows || 0 }} 行。
          </p>

          <div v-if="!importPreview" class="mt-4 text-sm text-slate-500">
            选择文件后点击预览。
          </div>

          <div v-else class="mt-4 space-y-3">
            <div v-if="importPreview.errors?.length" class="rounded-3xl bg-amber-50 p-4 text-sm text-amber-700">
              已显示前 {{ importPreview.errors.length }} 条错误，请先修正表格再导入。
            </div>

            <div
              v-if="importPreview.column_mapping && Object.keys(importPreview.column_mapping).length"
              class="rounded-3xl border border-slate-100 bg-white/80 p-4"
            >
              <p class="text-sm font-semibold text-slate-900">本次识别结果</p>
              <div class="mt-3 grid gap-3 md:grid-cols-2">
                <div
                  v-for="header in PRODUCT_IMPORT_HEADERS"
                  :key="`mapping-${header}`"
                  class="rounded-2xl border border-slate-100 bg-slate-50 px-4 py-3"
                >
                  <div class="flex items-center justify-between gap-3">
                    <p class="text-sm font-medium text-slate-800">{{ header }}</p>
                    <span
                      class="rounded-full px-3 py-1 text-xs font-semibold"
                      :class="importPreview.column_mapping[header] ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'"
                    >
                      {{ importPreview.column_mapping[header] || "未识别" }}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <div class="overflow-x-auto">
              <table class="min-w-full text-left text-sm">
                <thead class="text-xs uppercase tracking-[0.25em] text-slate-400">
                  <tr>
                    <th class="py-2 pr-4">HB</th>
                    <th class="py-2 pr-4">名称</th>
                    <th class="py-2 pr-4">规格</th>
                    <th class="py-2 pr-4">单位</th>
                    <th class="py-2 pr-4">换算</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-200 text-slate-700">
                  <tr v-for="row in importPreview.preview_rows" :key="row.row_number">
                    <td class="py-2 pr-4">{{ row.hb_code }}</td>
                    <td class="py-2 pr-4">{{ row.name }}</td>
                    <td class="py-2 pr-4">{{ row.spec }}</td>
                    <td class="py-2 pr-4">{{ row.unit }}</td>
                    <td class="py-2 pr-4">
                      1 {{ row.purchase_unit }} = {{ row.conversion_rate }} {{ row.base_unit }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </article>

    <article v-if="showCreateForm && isAdmin" class="rounded-[2rem] bg-white/90 p-5 shadow-sm backdrop-blur md:p-6">
      <h4 class="text-lg font-semibold text-slate-900">
        {{ formMode === "edit" ? "编辑商品档案" : "新建商品档案" }}
      </h4>
      <p class="mt-1 text-sm text-slate-500">
        品牌、产地、过敏原等扩展属性可直接写入 `extra_data` JSON。导入有误时，优先在这里直接修正主档。
      </p>

      <form class="mt-5 space-y-4" @submit.prevent="createProduct">
        <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <label class="block">
            <span class="mb-2 block text-sm font-medium text-slate-700">HB 编码</span>
            <input
              v-model="productForm.hb_code"
              type="text"
              required
              :disabled="formMode === 'edit'"
              class="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
            />
            <p v-if="formMode === 'edit'" class="mt-2 text-xs text-slate-500">
              为避免主键及关联记录漂移，编辑模式下不允许修改 HB 编码。
            </p>
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
            <span class="mb-2 block text-sm font-medium text-slate-700">计量单位</span>
            <input
              v-model="productForm.unit"
              type="text"
              required
              class="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
              placeholder="例如：罐 / 盒 / 个"
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
            <p v-if="conversionHint" class="mt-2 text-xs text-slate-500">{{ conversionHint }}</p>
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
            {{ saving ? "保存中..." : formMode === "edit" ? "保存修改" : "保存档案" }}
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
                <th class="px-6 py-4">扩展字段</th>
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
                <td class="px-6 py-4">{{ formatStock(item, "sellable_stock") }}</td>
                <td class="px-6 py-4">
                  <span class="rounded-full bg-brand-soft px-3 py-1 text-xs font-semibold text-brand-dark">
                    {{ formatStock(item, "total_stock") }}
                  </span>
                </td>
                <td class="px-6 py-4">
                  <div v-if="item.extra_data && Object.keys(item.extra_data).length" class="space-y-2">
                    <button
                      type="button"
                      class="text-xs font-semibold text-slate-600 underline decoration-dotted"
                      @click="toggleExtra(item.hb_code)"
                    >
                      {{ expandedExtra.has(item.hb_code) ? "收起" : `查看(${Object.keys(item.extra_data).length})` }}
                    </button>
                    <div v-if="expandedExtra.has(item.hb_code)" class="rounded-2xl bg-white/70 p-3">
                      <pre class="whitespace-pre-wrap break-words font-mono text-xs text-slate-700">{{
                        JSON.stringify(item.extra_data, null, 2)
                      }}</pre>
                    </div>
                  </div>
                  <span v-else class="text-slate-400">-</span>
                </td>
                <td class="px-6 py-4">
                  <div class="flex items-center gap-3">
                    <RouterLink
                      :to="{ name: 'product-detail', params: { hbCode: item.hb_code } }"
                      class="text-sm font-medium text-brand-dark hover:text-brand"
                    >
                      查看详情
                    </RouterLink>
                    <button
                      v-if="isAdmin"
                      type="button"
                      class="text-sm font-medium text-slate-700 hover:text-brand-dark"
                      @click="openEditForm(item)"
                    >
                      编辑
                    </button>
                    <button
                      v-if="isAdmin"
                      type="button"
                      class="text-sm font-medium text-red-600 hover:text-red-700 disabled:opacity-60"
                      :disabled="deletingHbCode === item.hb_code"
                      @click="deleteProduct(item)"
                    >
                      {{ deletingHbCode === item.hb_code ? "删除中..." : "删除" }}
                    </button>
                  </div>
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
                可售 {{ formatStock(item, "sellable_stock") }}
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
                <p class="font-medium text-slate-800">{{ formatStock(item, "total_stock") }}</p>
              </div>
              <div class="col-span-2">
                <p class="text-slate-500">扩展字段</p>
                <button
                  v-if="item.extra_data && Object.keys(item.extra_data).length"
                  type="button"
                  class="mt-1 text-left text-sm font-medium text-brand-dark underline decoration-dotted"
                  @click="toggleExtra(item.hb_code)"
                >
                  {{ expandedExtra.has(item.hb_code) ? "收起" : `查看(${Object.keys(item.extra_data).length})` }}
                </button>
                <p v-else class="mt-1 font-medium text-slate-800">-</p>
                <div
                  v-if="expandedExtra.has(item.hb_code) && item.extra_data && Object.keys(item.extra_data).length"
                  class="mt-2 rounded-2xl bg-white/70 p-3"
                >
                  <pre class="whitespace-pre-wrap break-words font-mono text-xs text-slate-700">{{
                    JSON.stringify(item.extra_data, null, 2)
                  }}</pre>
                </div>
              </div>
            </div>
            <div class="mt-4 flex flex-wrap gap-3">
              <RouterLink
                :to="{ name: 'product-detail', params: { hbCode: item.hb_code } }"
                class="inline-flex text-sm font-medium text-brand-dark"
              >
                查看详情
              </RouterLink>
              <button
                v-if="isAdmin"
                type="button"
                class="text-sm font-medium text-slate-700"
                @click="openEditForm(item)"
              >
                编辑
              </button>
              <button
                v-if="isAdmin"
                type="button"
                class="text-sm font-medium text-red-600 disabled:opacity-60"
                :disabled="deletingHbCode === item.hb_code"
                @click="deleteProduct(item)"
              >
                {{ deletingHbCode === item.hb_code ? "删除中..." : "删除" }}
              </button>
            </div>
          </article>
        </div>
      </div>
    </article>
  </section>
</template>
