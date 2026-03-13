<script setup>
import { computed, ref } from "vue";

import http from "../api/http";

const selectedFile = ref(null);
const columns = ref([]);
const mapping = ref({});
const previewRows = ref([]);
const totalRows = ref(0);
const validRows = ref(0);
const errorRows = ref(0);
const errors = ref([]);

const defaultChannelName = ref("抖音");
const templateName = ref("generic");

const loadingPreview = ref(false);
const importing = ref(false);
const errorMessage = ref("");
const successMessage = ref("");

const hasPreview = computed(() => previewRows.value.length > 0 || errors.value.length > 0);

function onFileChange(event) {
  const [file] = event.target.files || [];
  selectedFile.value = file || null;
  columns.value = [];
  mapping.value = {};
  previewRows.value = [];
  totalRows.value = 0;
  validRows.value = 0;
  errorRows.value = 0;
  errors.value = [];
  errorMessage.value = "";
  successMessage.value = "";
}

function buildFormData() {
  const formData = new FormData();
  formData.append("file", selectedFile.value);
  formData.append("mapping", JSON.stringify(mapping.value || {}));
  formData.append("default_channel_name", defaultChannelName.value.trim());
  formData.append("template", templateName.value);
  return formData;
}

async function previewImport() {
  if (!selectedFile.value) {
    errorMessage.value = "请先选择 CSV / Excel 文件";
    return;
  }

  loadingPreview.value = true;
  errorMessage.value = "";
  successMessage.value = "";

  try {
    const { data } = await http.post("/orders/import/preview", buildFormData(), {
      headers: { "Content-Type": "multipart/form-data" },
    });
    const payload = data.data || {};
    columns.value = payload.columns || [];
    mapping.value = payload.mapping_effective || {};
    previewRows.value = payload.preview_rows || [];
    totalRows.value = payload.total_rows || 0;
    validRows.value = payload.valid_rows || 0;
    errorRows.value = payload.error_rows || 0;
    errors.value = payload.errors || [];
  } catch (error) {
    errorMessage.value = error.response?.data?.msg || "预览失败";
  } finally {
    loadingPreview.value = false;
  }
}

async function commitImport() {
  if (!selectedFile.value) {
    errorMessage.value = "请先选择文件";
    return;
  }
  if (!hasPreview.value) {
    errorMessage.value = "请先预览确认";
    return;
  }

  importing.value = true;
  errorMessage.value = "";
  successMessage.value = "";

  try {
    const { data } = await http.post("/orders/import", buildFormData(), {
      headers: { "Content-Type": "multipart/form-data" },
    });
    const payload = data.data || {};
    successMessage.value = `导入完成：创建订单 ${payload.created}，错误 ${payload.error_rows}。`;
    errors.value = payload.errors || [];
    previewRows.value = payload.preview_rows || [];
  } catch (error) {
    errorMessage.value = error.response?.data?.msg || "导入失败";
  } finally {
    importing.value = false;
  }
}
</script>

<template>
  <section class="space-y-4">
    <div class="rounded-[2rem] bg-white/90 p-5 shadow-sm backdrop-blur md:p-6">
      <p class="text-xs uppercase tracking-[0.35em] text-brand/60">Orders Import</p>
      <h3 class="mt-2 text-2xl font-semibold text-slate-900">批量订单导入</h3>
      <p class="mt-2 text-sm text-slate-500">
        支持 CSV / Excel。通过映射适配菜鸟/顺丰等发货模板，未映射列会写入订单 extra_data，便于未来对接物流商 API。
      </p>
    </div>

    <div class="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
      <article class="rounded-[2rem] bg-white/90 p-5 shadow-sm backdrop-blur md:p-6">
        <h4 class="text-lg font-semibold text-slate-900">上传与映射</h4>

        <div class="mt-5 space-y-4">
          <div class="grid gap-4 sm:grid-cols-2">
            <label class="block">
              <span class="mb-2 block text-sm font-medium text-slate-700">默认渠道</span>
              <input
                v-model="defaultChannelName"
                type="text"
                class="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
                placeholder="例如 抖音 / 有赞"
              />
            </label>
            <label class="block">
              <span class="mb-2 block text-sm font-medium text-slate-700">模板标识</span>
              <select
                v-model="templateName"
                class="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
              >
                <option value="generic">通用</option>
                <option value="cainiao">菜鸟</option>
                <option value="shunfeng">顺丰</option>
              </select>
            </label>
          </div>

          <label class="block">
            <span class="mb-2 block text-sm font-medium text-slate-700">文件</span>
            <input
              type="file"
              accept=".csv,.xlsx,.xls,text/csv,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              class="block w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm"
              @change="onFileChange"
            />
          </label>

          <div v-if="columns.length" class="rounded-[1.5rem] border border-slate-100 bg-slate-50 p-4">
            <p class="text-sm font-semibold text-slate-900">字段映射</p>
            <p class="mt-1 text-xs text-slate-500">必须映射 external_sku_id 和 quantity；channel_name 可选。</p>

            <div class="mt-4 grid gap-3 md:grid-cols-2">
              <label class="block">
                <span class="mb-2 block text-sm font-medium text-slate-700">channel_name 列(可选)</span>
                <select
                  v-model="mapping.channel_name"
                  class="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
                >
                  <option value="">不映射(使用默认渠道)</option>
                  <option v-for="col in columns" :key="`cn-${col}`" :value="col">{{ col }}</option>
                </select>
              </label>
              <label class="block">
                <span class="mb-2 block text-sm font-medium text-slate-700">external_sku_id 列(必填)</span>
                <select
                  v-model="mapping.external_sku_id"
                  class="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
                >
                  <option value="">请选择</option>
                  <option v-for="col in columns" :key="`sku-${col}`" :value="col">{{ col }}</option>
                </select>
              </label>
              <label class="block">
                <span class="mb-2 block text-sm font-medium text-slate-700">quantity 列(必填)</span>
                <select
                  v-model="mapping.quantity"
                  class="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
                >
                  <option value="">请选择</option>
                  <option v-for="col in columns" :key="`qty-${col}`" :value="col">{{ col }}</option>
                </select>
              </label>
              <label class="block">
                <span class="mb-2 block text-sm font-medium text-slate-700">external_order_no 列(可选)</span>
                <select
                  v-model="mapping.external_order_no"
                  class="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
                >
                  <option value="">不映射</option>
                  <option v-for="col in columns" :key="`on-${col}`" :value="col">{{ col }}</option>
                </select>
              </label>
            </div>
          </div>

          <div class="grid gap-3 sm:grid-cols-2">
            <button
              type="button"
              class="rounded-2xl border border-slate-200 px-4 py-3 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:opacity-70"
              :disabled="loadingPreview"
              @click="previewImport"
            >
              {{ loadingPreview ? "预览中..." : "预览前 5 条" }}
            </button>
            <button
              type="button"
              class="rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:opacity-70"
              :disabled="importing || !hasPreview"
              @click="commitImport"
            >
              {{ importing ? "导入中..." : "确认导入" }}
            </button>
          </div>

          <p v-if="errorMessage" class="text-sm text-red-600">{{ errorMessage }}</p>
          <p v-if="successMessage" class="text-sm text-emerald-700">{{ successMessage }}</p>
        </div>
      </article>

      <article class="rounded-[2rem] bg-white/90 shadow-sm backdrop-blur">
        <div class="border-b border-slate-100 px-5 py-4 md:px-6">
          <h4 class="text-lg font-semibold text-slate-900">预览窗口</h4>
          <p class="mt-1 text-sm text-slate-500">
            总计 {{ totalRows }} 行，有效 {{ validRows }} 行，错误 {{ errorRows }} 行。
          </p>
        </div>

        <div v-if="!hasPreview" class="px-5 py-8 text-sm text-slate-500 md:px-6">
          选择文件并点击预览后，将在这里显示解析结果。
        </div>
        <div v-else class="space-y-4 px-5 py-5 md:px-6">
          <div v-if="errors.length" class="rounded-3xl bg-amber-50 p-4 text-sm text-amber-700">
            已显示前 {{ errors.length }} 条错误，建议先修正表格或调整映射。
          </div>

          <div v-if="previewRows.length" class="overflow-x-auto">
            <table class="min-w-full text-left text-sm">
              <thead class="bg-slate-50 text-xs uppercase tracking-[0.25em] text-slate-400">
                <tr>
                  <th class="px-5 py-4 md:px-6">渠道</th>
                  <th class="px-5 py-4 md:px-6">外部 SKU</th>
                  <th class="px-5 py-4 md:px-6">HB</th>
                  <th class="px-5 py-4 md:px-6">数量</th>
                  <th class="px-5 py-4 md:px-6">可售</th>
                  <th class="px-5 py-4 md:px-6">预估</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-slate-700">
                <tr v-for="row in previewRows" :key="`${row.row_number}-${row.external_sku_id}`">
                  <td class="px-5 py-4 md:px-6">{{ row.channel_name }}</td>
                  <td class="px-5 py-4 md:px-6">{{ row.external_sku_id }}</td>
                  <td class="px-5 py-4 md:px-6">{{ row.hb_code }}</td>
                  <td class="px-5 py-4 md:px-6">{{ row.quantity }}</td>
                  <td class="px-5 py-4 md:px-6">{{ row.sellable_stock }}</td>
                  <td class="px-5 py-4 md:px-6">
                    <span
                      class="rounded-full px-3 py-1 text-xs font-semibold"
                      :class="
                        row.predicted_status === 'ok'
                          ? 'bg-emerald-100 text-emerald-700'
                          : 'bg-red-100 text-red-700'
                      "
                    >
                      {{ row.predicted_status === "ok" ? "可预占" : "库存不足" }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>

