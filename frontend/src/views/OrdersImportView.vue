<script setup>
import { computed, ref, watch } from "vue";

import http from "../api/http";

const CHANNEL_OPTIONS = [
  { value: "微信小店", label: "微信小店", template: "wechat_shop", hint: "优先匹配微信小店标准导出模板" },
  { value: "抖音", label: "抖音", template: "generic", hint: "适合整理后的通用订单表" },
  { value: "有赞", label: "有赞", template: "generic", hint: "适合整理后的通用订单表" },
  { value: "淘宝", label: "淘宝", template: "generic", hint: "适合整理后的通用订单表" },
  { value: "天猫", label: "天猫", template: "generic", hint: "适合整理后的通用订单表" },
  { value: "京东", label: "京东", template: "generic", hint: "适合整理后的通用订单表" },
  { value: "拼多多", label: "拼多多", template: "generic", hint: "适合整理后的通用订单表" },
  { value: "菜鸟", label: "菜鸟", template: "cainiao", hint: "适合菜鸟类发货模板" },
  { value: "顺丰", label: "顺丰", template: "shunfeng", hint: "适合顺丰类发货模板" },
  { value: "__custom__", label: "其他渠道", template: "generic", hint: "当预设渠道不匹配时手工输入" },
];

const TEMPLATE_OPTIONS = [
  { value: "wechat_shop", label: "微信小店" },
  { value: "generic", label: "通用" },
  { value: "cainiao", label: "菜鸟" },
  { value: "shunfeng", label: "顺丰" },
];

const ORDER_TEMPLATE_DOCS = {
  generic: {
    label: "通用模板",
    description: "适合你自己整理过的 CSV / Excel。至少要能映射出外部 SKU、数量，以及可选的订单号。",
    requiredMappings: [
      { key: "external_sku_id", label: "外部 SKU", suggestedHeaders: ["external_sku_id", "外部sku", "商品编码", "货号"] },
      { key: "quantity", label: "数量", suggestedHeaders: ["quantity", "数量", "件数"] },
    ],
    optionalMappings: [
      { key: "channel_name", label: "渠道", suggestedHeaders: ["channel_name", "渠道", "平台"] },
      { key: "external_order_no", label: "订单号", suggestedHeaders: ["external_order_no", "订单号", "平台订单号"] },
    ],
    visibleHeaders: [],
  },
  wechat_shop: {
    label: "微信小店",
    description: "按你提供的标准导出表头建立。导入时优先用自定义 SKU / 商品编码做映射，其余 50+ 字段会原样保存在订单 extra_data.row_extra。",
    requiredMappings: [
      { key: "external_order_no", label: "订单号", suggestedHeaders: ["订单号"] },
      { key: "external_sku_id", label: "商品编码 / SKU", suggestedHeaders: ["SKU编码(自定义)", "商品编码(自定义)"] },
      { key: "quantity", label: "商品数量", suggestedHeaders: ["商品数量"] },
    ],
    optionalMappings: [
      { key: "channel_name", label: "渠道", suggestedHeaders: ["默认渠道=微信小店"] },
    ],
    visibleHeaders: [
      "订单号", "订单下单时间", "订单发货时间", "订单确认收货时间", "订单完成结算时间", "订单状态", "发货方式", "收件人姓名",
      "收件人地址", "省", "市", "区", "收件人手机", "买家备注", "商家备注", "打标颜色", "商品总价", "订单实际支付金额",
      "订单实际收款金额", "订单运费", "商品优惠", "跨店优惠", "商品改价", "积分抵扣", "支付方式", "支付时间", "交易单号",
      "物流公司", "快递单号", "技术服务费", "技术服务费（将以人气卡形式返还）", "运费险预计投保费用", "带货方式", "带货账号类型",
      "带货账号昵称", "带货费用渠道", "带货费用类型", "带货费用", "带货佣金率", "礼物单号", "商品名称", "商品编码(平台)",
      "商品编码(自定义)", "SKU编码(自定义)", "商品属性", "商品价格(单件)", "商品实际价格(单件)", "商品实际价格(总共)", "是否预售",
      "商品数量", "商品平台券优惠", "商品平均运费", "定制信息", "定制预览图", "商品发货", "商品售后", "商品已退款金额",
    ],
  },
  cainiao: {
    label: "菜鸟",
    description: "适合菜鸟发货单类模板，通常需要手工确认 SKU 和数量列。",
    requiredMappings: [
      { key: "external_sku_id", label: "外部 SKU", suggestedHeaders: ["external_sku_id", "商品编码", "货号"] },
      { key: "quantity", label: "数量", suggestedHeaders: ["quantity", "数量", "件数"] },
    ],
    optionalMappings: [
      { key: "channel_name", label: "渠道", suggestedHeaders: ["渠道", "平台"] },
      { key: "external_order_no", label: "订单号", suggestedHeaders: ["订单号", "平台订单号"] },
    ],
    visibleHeaders: [],
  },
  shunfeng: {
    label: "顺丰",
    description: "适合顺丰类发货模板，通常需要手工确认 SKU 和数量列。",
    requiredMappings: [
      { key: "external_sku_id", label: "外部 SKU", suggestedHeaders: ["external_sku_id", "商品编码", "货号"] },
      { key: "quantity", label: "数量", suggestedHeaders: ["quantity", "数量", "件数"] },
    ],
    optionalMappings: [
      { key: "channel_name", label: "渠道", suggestedHeaders: ["渠道", "平台"] },
      { key: "external_order_no", label: "订单号", suggestedHeaders: ["订单号", "平台订单号"] },
    ],
    visibleHeaders: [],
  },
};

const selectedFile = ref(null);
const columns = ref([]);
const mapping = ref({});
const previewRows = ref([]);
const totalRows = ref(0);
const validRows = ref(0);
const errorRows = ref(0);
const errors = ref([]);

const selectedChannel = ref("微信小店");
const customChannelName = ref("");
const templateName = ref("wechat_shop");

const loadingPreview = ref(false);
const importing = ref(false);
const errorMessage = ref("");
const successMessage = ref("");

const hasPreview = computed(() => previewRows.value.length > 0 || errors.value.length > 0);
const activeTemplateDoc = computed(() => ORDER_TEMPLATE_DOCS[templateName.value] || ORDER_TEMPLATE_DOCS.generic);
const activeChannelOption = computed(
  () => CHANNEL_OPTIONS.find((item) => item.value === selectedChannel.value) || CHANNEL_OPTIONS[0],
);
const defaultChannelName = computed(() => {
  if (selectedChannel.value === "__custom__") {
    return customChannelName.value.trim();
  }
  return selectedChannel.value.trim();
});
const activeSampleHref = computed(() => (
  templateName.value === "wechat_shop"
    ? "/samples/orders-import-wechat-shop-sample.csv"
    : "/samples/orders-import-generic-sample.csv"
));
const activeSampleLabel = computed(() => (
  templateName.value === "wechat_shop" ? "下载微信小店 CSV 示例" : "下载通用订单 CSV 示例"
));
const mappingStatusRows = computed(() => {
  const template = activeTemplateDoc.value;
  return [...template.requiredMappings, ...template.optionalMappings].map((item) => ({
    ...item,
    selected: mapping.value?.[item.key] || "",
    satisfied: item.key === "channel_name"
      ? Boolean((mapping.value?.channel_name || "").trim() || defaultChannelName.value)
      : Boolean((mapping.value?.[item.key] || "").trim()),
  }));
});

watch(selectedChannel, (value) => {
  const matched = CHANNEL_OPTIONS.find((item) => item.value === value);
  if (!matched) {
    return;
  }
  templateName.value = matched.template;
  if (value !== "__custom__") {
    customChannelName.value = "";
  }
});

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
  formData.append("default_channel_name", defaultChannelName.value);
  formData.append("template", templateName.value);
  return formData;
}

async function previewImport() {
  if (!selectedFile.value) {
    errorMessage.value = "请先选择 CSV / Excel 文件";
    return;
  }
  if (!defaultChannelName.value) {
    errorMessage.value = "请先选择渠道";
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
  if (!defaultChannelName.value) {
    errorMessage.value = "请先选择渠道";
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
        支持 CSV / Excel。通过映射适配微信小店、菜鸟、顺丰等模板，未映射列会写入订单 extra_data，便于未来对接物流商 API。
      </p>
    </div>

    <div class="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
      <article class="rounded-[2rem] bg-white/90 p-5 shadow-sm backdrop-blur md:p-6">
        <h4 class="text-lg font-semibold text-slate-900">上传与映射</h4>

        <div class="mt-5 space-y-4">
          <div class="grid gap-4 sm:grid-cols-2">
            <label class="block">
              <span class="mb-2 block text-sm font-medium text-slate-700">渠道</span>
              <select
                v-model="selectedChannel"
                class="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
              >
                <option
                  v-for="option in CHANNEL_OPTIONS"
                  :key="option.value"
                  :value="option.value"
                >
                  {{ option.label }}
                </option>
              </select>
              <p class="mt-2 text-xs text-slate-500">{{ activeChannelOption.hint }}</p>
            </label>
            <label class="block">
              <span class="mb-2 block text-sm font-medium text-slate-700">模板标识</span>
              <select
                v-model="templateName"
                class="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
              >
                <option
                  v-for="option in TEMPLATE_OPTIONS"
                  :key="option.value"
                  :value="option.value"
                >
                  {{ option.label }}
                </option>
              </select>
              <p class="mt-2 text-xs text-slate-500">渠道会自动推荐模板；如表头已整理，也可以手工切换。</p>
            </label>
          </div>

          <label v-if="selectedChannel === '__custom__'" class="block">
            <span class="mb-2 block text-sm font-medium text-slate-700">自定义渠道名称</span>
            <input
              v-model="customChannelName"
              type="text"
              class="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
              placeholder="例如 视频号 / 线下门店"
            />
          </label>

          <label class="block">
            <span class="mb-2 block text-sm font-medium text-slate-700">文件</span>
            <input
              type="file"
              accept=".csv,.xlsx,.xls,text/csv,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              class="block w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm"
              @change="onFileChange"
            />
          </label>

          <div class="rounded-[1.5rem] border border-brand/10 bg-brand-soft/30 p-4">
            <p class="text-sm font-semibold text-slate-900">模板说明：{{ activeTemplateDoc.label }}</p>
            <p class="mt-1 text-sm text-slate-600">{{ activeTemplateDoc.description }}</p>
            <div class="mt-3 flex flex-wrap gap-3">
              <span class="rounded-full bg-white px-3 py-1 text-xs font-semibold text-brand-dark">
                默认渠道：{{ defaultChannelName || "待填写" }}
              </span>
              <a
                :href="activeSampleHref"
                download
                class="inline-flex items-center rounded-full border border-brand/20 bg-white px-3 py-1 text-xs font-semibold text-brand-dark transition hover:border-brand hover:text-brand"
              >
                {{ activeSampleLabel }}
              </a>
            </div>

            <div class="mt-4 space-y-3">
              <div>
                <p class="text-xs uppercase tracking-[0.25em] text-slate-400">关键映射</p>
                <div class="mt-2 space-y-2">
                  <div
                    v-for="item in mappingStatusRows"
                    :key="item.key"
                    class="flex flex-col gap-2 rounded-2xl border border-white/70 bg-white/80 px-4 py-3"
                  >
                    <div class="flex items-center justify-between gap-3">
                      <p class="text-sm font-medium text-slate-800">{{ item.label }}</p>
                      <span
                        class="rounded-full px-3 py-1 text-xs font-semibold"
                        :class="item.satisfied ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'"
                      >
                        {{ item.satisfied ? `已识别：${item.selected || defaultChannelName}` : "待确认" }}
                      </span>
                    </div>
                    <p class="text-xs text-slate-500">建议表头：{{ item.suggestedHeaders.join(" / ") }}</p>
                  </div>
                </div>
              </div>

              <div v-if="activeTemplateDoc.visibleHeaders.length">
                <p class="text-xs uppercase tracking-[0.25em] text-slate-400">模板字段清单</p>
                <div class="mt-2 flex flex-wrap gap-2">
                  <span
                    v-for="header in activeTemplateDoc.visibleHeaders"
                    :key="header"
                    class="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs text-slate-700"
                  >
                    {{ header }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div v-if="columns.length" class="rounded-[1.5rem] border border-slate-100 bg-slate-50 p-4">
            <p class="text-sm font-semibold text-slate-900">字段映射</p>
            <p class="mt-1 text-xs text-slate-500">必须映射 external_sku_id 和 quantity；channel_name 可选，不映射时将使用上方选择的渠道。</p>

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
