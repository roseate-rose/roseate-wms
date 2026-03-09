<script setup>
import { reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import http, { TOKEN_KEY } from "../api/http";

const route = useRoute();
const router = useRouter();

const form = reactive({
  username: "",
  password: "",
});
const errorMessage = ref("");
const loading = ref(false);

async function submitLogin() {
  errorMessage.value = "";
  loading.value = true;

  try {
    const { data } = await http.post("/auth/login", form);
    localStorage.setItem(TOKEN_KEY, data.data.token);

    await router.replace(route.query.redirect || "/");
  } catch (error) {
    errorMessage.value = error.response?.data?.msg || "登录失败，请检查用户名或密码";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="flex min-h-screen items-center justify-center px-4 py-10">
    <div class="w-full max-w-md rounded-[2rem] bg-white/90 p-8 shadow-xl shadow-brand/10 backdrop-blur">
      <p class="text-xs uppercase tracking-[0.4em] text-brand/60">Roseate</p>
      <h1 class="mt-4 text-3xl font-semibold text-brand-dark">仓库登录</h1>
      <p class="mt-2 text-sm text-slate-500">移动端扫码作业与桌面管理共用同一套认证。</p>

      <form class="mt-8 space-y-4" @submit.prevent="submitLogin">
        <label class="block">
          <span class="mb-2 block text-sm font-medium text-slate-700">用户名</span>
          <input
            v-model="form.username"
            type="text"
            class="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
            placeholder="admin"
          />
        </label>

        <label class="block">
          <span class="mb-2 block text-sm font-medium text-slate-700">密码</span>
          <input
            v-model="form.password"
            type="password"
            class="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand"
            placeholder="请输入密码"
          />
        </label>

        <p v-if="errorMessage" class="text-sm text-red-600">
          {{ errorMessage }}
        </p>

        <button
          type="submit"
          class="w-full rounded-2xl bg-brand px-4 py-3 text-sm font-semibold text-white transition hover:bg-brand-dark disabled:cursor-not-allowed disabled:opacity-70"
          :disabled="loading"
        >
          {{ loading ? "登录中..." : "登录" }}
        </button>
      </form>
    </div>
  </div>
</template>
