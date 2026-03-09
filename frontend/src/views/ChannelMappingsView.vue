<script setup>
import { onMounted, reactive, ref } from "vue";

import http from "../api/http";

const loading = ref(false);
const saving = ref(false);
const errorMessage = ref("");
const mappings = ref([]);

const form = reactive({
  channel_name: "",
  external_sku_id: "",
  hb_code: "",
  extra_data_text: "",
});

async function loadMappings() {
  loading.value = true;
  errorMessage.value = "";

  try {
    const { data } = await http.get("/channel-mappings");
    mappings.value = data.data.items || [];
  } catch (error) {
    errorMessage.value = error.response?.data?.msg || "渠道映射加载失败";
  } finally {
    loading.value = false;
  }
}

async function createMapping() {
  saving.value = true;
  errorMessage.value = "";

  let extraData = {};
  if (form.extra_data_text.trim()) {
    try {
      extraData = JSON.parse(form.extra_data_text);
    } catch {
      errorMessage.value = "扩展字段必须是合法 JSON";
      saving.value = false;
      return;
    }
  }

  try {
    await http.post("/channel-mappings", {
      channel_name: form.channel_name.trim(),
      external_sku_id: form.external_sku_id.trim(),
      hb_code: form.hb_code.trim(),
      extra_data: extraData,
    });

    form.channel_name = "";
    form.external_sku_id = "";
    form.hb_code = "";
    form.extra_data_text = "";
    await loadMappings();
  } catch (error) {
    errorMessage.value = error.response?.data?.msg || "映射创建失败";
  } finally {
    saving.value = false;
  }
}

onMounted(loadMappings);
</script>

<template>
  <section class="space-y-4">
    <div class="rounded-[2rem] bg-white/90 p-5 shadow-sm backdrop-blur md:p-6">
      <p class="text-xs uppercase tracking-[0.35em] text-brand/60">Channels</p>
      <h3 class="mt-2 text-2xl font-semibold text-slate-900">渠道映射管理</h3>
      <p class="mt-2 text-sm text-slate-500">手动维护外部 SKU 与内部 `hb_code` 的绑定关系，供渠道单据回流识别。</p>
    </div>

    <div class="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
      <article class="rounded-[2rem] bg-white/90 p-5 shadow-sm backdrop-blur md:p-6">
        <h4 class="text-lg font-semibold text-slate-900">新增映射</h4>

        <form class="mt-5 space-y-4" @submit.prevent="createMapping">
          <label class="block">
            <span class="mb-2 block text-sm font-medium text-slate-700">渠道名称</span>
            <input
              v-model="form.channel_name"
              type="text"
              class="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
              placeholder="抖音 / 有赞"
            />
          </label>

          <label class="block">
            <span class="mb-2 block text-sm font-medium text-slate-700">外部 SKU ID</span>
            <input
              v-model="form.external_sku_id"
              type="text"
              class="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
              placeholder="DY-889900"
            />
          </label>

          <label class="block">
            <span class="mb-2 block text-sm font-medium text-slate-700">内部 HB 编码</span>
            <input
              v-model="form.hb_code"
              type="text"
              class="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
              placeholder="HB6001"
            />
          </label>

          <label class="block">
            <span class="mb-2 block text-sm font-medium text-slate-700">扩展字段 JSON</span>
            <textarea
              v-model="form.extra_data_text"
              rows="4"
              class="w-full rounded-2xl border border-slate-200 px-4 py-3 font-mono text-sm outline-none transition focus:border-brand"
              placeholder='{"shop_name":"官方旗舰店"}'
            />
          </label>

          <p v-if="errorMessage" class="text-sm text-red-600">{{ errorMessage }}</p>

          <button
            type="submit"
            class="w-full rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:opacity-70"
            :disabled="saving"
          >
            {{ saving ? "保存中..." : "保存映射" }}
          </button>
        </form>
      </article>

      <article class="rounded-[2rem] bg-white/90 shadow-sm backdrop-blur">
        <div class="border-b border-slate-100 px-5 py-4 md:px-6">
          <h4 class="text-lg font-semibold text-slate-900">已绑定映射</h4>
        </div>

        <div v-if="loading" class="px-5 py-8 text-sm text-slate-500 md:px-6">加载中...</div>
        <div v-else-if="!mappings.length" class="px-5 py-8 text-sm text-slate-500 md:px-6">
          暂无映射，请先录入。
        </div>
        <div v-else class="divide-y divide-slate-100">
          <div
            v-for="mapping in mappings"
            :key="mapping.id"
            class="px-5 py-4 md:px-6"
          >
            <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p class="text-sm font-semibold text-slate-900">
                  {{ mapping.channel_name }} · {{ mapping.external_sku_id }}
                </p>
                <p class="mt-1 text-xs text-slate-500">内部商品 {{ mapping.hb_code }}</p>
              </div>
              <span class="rounded-full bg-brand-soft px-3 py-1 text-xs font-medium text-brand-dark">
                已绑定
              </span>
            </div>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>
