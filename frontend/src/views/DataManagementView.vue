<script setup>
import { ref } from "vue";

import http from "../api/http";
import { TOKEN_KEY } from "../api/http";
import { getStoredRole } from "../auth/session";

const mergeMode = ref("accumulate");
const selectedFile = ref(null);
const previewRows = ref([]);
const totalRows = ref(0);
const loadingPreview = ref(false);
const importing = ref(false);
const errorMessage = ref("");
const successMessage = ref("");
const exporting = ref("");
const role = getStoredRole();
const isAdmin = role === "admin";

function onFileChange(event) {
  const [file] = event.target.files || [];
  selectedFile.value = file || null;
  previewRows.value = [];
  totalRows.value = 0;
  errorMessage.value = "";
  successMessage.value = "";
}

function buildFormData() {
  const formData = new FormData();
  formData.append("merge_mode", mergeMode.value);
  formData.append("file", selectedFile.value);
  return formData;
}

async function previewImport() {
  if (!selectedFile.value) {
    errorMessage.value = "请先选择 CSV 文件";
    return;
  }

  loadingPreview.value = true;
  errorMessage.value = "";
  successMessage.value = "";

  try {
    const { data } = await http.post("/inventory/import/preview", buildFormData(), {
      headers: { "Content-Type": "multipart/form-data" },
    });
    previewRows.value = data.data.preview_rows || [];
    totalRows.value = data.data.total_rows || 0;
  } catch (error) {
    errorMessage.value = error.response?.data?.msg || "预览失败";
  } finally {
    loadingPreview.value = false;
  }
}

async function executeImport() {
  if (!selectedFile.value) {
    errorMessage.value = "请先选择 CSV 文件";
    return;
  }

  importing.value = true;
  errorMessage.value = "";
  successMessage.value = "";

  try {
    const { data } = await http.post("/inventory/import", buildFormData(), {
      headers: { "Content-Type": "multipart/form-data" },
    });
    previewRows.value = data.data.preview_rows || [];
    totalRows.value = data.data.total_rows || 0;
    successMessage.value = `导入完成，共处理 ${data.data.total_rows} 条记录`;
  } catch (error) {
    errorMessage.value = error.response?.data?.msg || "导入失败";
  } finally {
    importing.value = false;
  }
}

async function downloadReport(format) {
  exporting.value = format;
  errorMessage.value = "";

  try {
    const token = localStorage.getItem(TOKEN_KEY);
    const response = await fetch(`/api/v1/reports/export?format=${format}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      const payload = await response.json();
      throw new Error(payload.msg || "导出失败");
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = format === "xlsx" ? "roseate_report.xlsx" : "roseate_report.csv";
    link.click();
    window.URL.revokeObjectURL(url);
  } catch (error) {
    errorMessage.value = error.message || "导出失败";
  } finally {
    exporting.value = "";
  }
}
</script>

<template>
  <section class="space-y-4">
    <div class="rounded-[2rem] bg-white/90 p-5 shadow-sm backdrop-blur md:p-6">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p class="text-xs uppercase tracking-[0.35em] text-brand/60">Data Import</p>
          <h3 class="mt-2 text-2xl font-semibold text-slate-900">CSV 数据导入</h3>
          <p class="mt-2 text-sm text-slate-500">
            支持批量初始化库存，默认缺失到期日会填充为 `2099-12-31`，并支持采购单位换算。
          </p>
        </div>

        <div v-if="isAdmin" class="flex gap-2">
          <button
            type="button"
            class="rounded-2xl border border-slate-200 px-4 py-3 text-sm font-medium text-slate-700"
            :disabled="exporting === 'csv'"
            @click="downloadReport('csv')"
          >
            {{ exporting === "csv" ? "导出中..." : "报表下载 CSV" }}
          </button>
          <button
            type="button"
            class="rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white"
            :disabled="exporting === 'xlsx'"
            @click="downloadReport('xlsx')"
          >
            {{ exporting === "xlsx" ? "导出中..." : "报表下载 Excel" }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="!isAdmin" class="rounded-3xl bg-amber-50 p-6 text-sm text-amber-700 shadow-sm">
      当前账号不是管理员，无法执行导入或报表导出。
    </div>

    <div class="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
      <article class="rounded-[2rem] bg-white/90 p-5 shadow-sm backdrop-blur md:p-6">
        <h4 class="text-lg font-semibold text-slate-900">上传配置</h4>

        <div class="mt-5 space-y-4">
          <label class="block">
            <span class="mb-2 block text-sm font-medium text-slate-700">CSV 文件</span>
            <input
              type="file"
              accept=".csv,text/csv"
              class="block w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm"
              :disabled="!isAdmin"
              @change="onFileChange"
            />
          </label>

          <label class="block">
            <span class="mb-2 block text-sm font-medium text-slate-700">去重策略</span>
            <select
              v-model="mergeMode"
              class="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
              :disabled="!isAdmin"
            >
              <option value="accumulate">累加</option>
              <option value="overwrite">覆盖</option>
            </select>
          </label>

          <div class="grid gap-3 sm:grid-cols-2">
            <button
              type="button"
              class="rounded-2xl border border-slate-200 px-4 py-3 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:opacity-70"
              :disabled="loadingPreview || !isAdmin"
              @click="previewImport"
            >
              {{ loadingPreview ? "预览中..." : "预览前 5 条" }}
            </button>
            <button
              type="button"
              class="rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:opacity-70"
              :disabled="importing || !previewRows.length || !isAdmin"
              @click="executeImport"
            >
              {{ importing ? "导入中..." : "确认保存" }}
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
            当前解析 {{ totalRows }} 条，以下展示前 5 条，请确认映射和单位换算。
          </p>
        </div>

        <div v-if="!previewRows.length" class="px-5 py-8 text-sm text-slate-500 md:px-6">
          选择文件并点击预览后，将在这里显示解析结果。
        </div>
        <div v-else class="overflow-x-auto">
          <table class="min-w-full text-left text-sm">
            <thead class="bg-slate-50 text-xs uppercase tracking-[0.25em] text-slate-400">
              <tr>
                <th class="px-5 py-4 md:px-6">HB 编码</th>
                <th class="px-5 py-4 md:px-6">批号</th>
                <th class="px-5 py-4 md:px-6">原数量</th>
                <th class="px-5 py-4 md:px-6">单位</th>
                <th class="px-5 py-4 md:px-6">最小单位数量</th>
                <th class="px-5 py-4 md:px-6">到期日</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-slate-700">
              <tr v-for="row in previewRows" :key="`${row.row_number}-${row.hb_code}`">
                <td class="px-5 py-4 md:px-6">{{ row.hb_code }}</td>
                <td class="px-5 py-4 md:px-6">{{ row.batch_no }}</td>
                <td class="px-5 py-4 md:px-6">{{ row.quantity }}</td>
                <td class="px-5 py-4 md:px-6">{{ row.unit_type }}</td>
                <td class="px-5 py-4 md:px-6">{{ row.normalized_quantity }}</td>
                <td class="px-5 py-4 md:px-6">{{ row.expiry_date }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </article>
    </div>
  </section>
</template>
