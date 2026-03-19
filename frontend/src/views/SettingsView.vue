<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import http, { TOKEN_KEY } from "../api/http";
import { clearStoredUser, getStoredUser } from "../auth/session";

const router = useRouter();
const currentUser = ref(getStoredUser());
const users = ref([]);
const loading = ref(false);
const errorMessage = ref("");

const isAdmin = computed(() => currentUser.value?.role === "admin");

async function loadUsers() {
  if (!isAdmin.value) {
    users.value = [];
    return;
  }

  loading.value = true;
  errorMessage.value = "";

  try {
    const { data } = await http.get("/users");
    users.value = data.data.items || [];
  } catch (error) {
    errorMessage.value = error.response?.data?.msg || "用户列表加载失败";
  } finally {
    loading.value = false;
  }
}

async function logout() {
  localStorage.removeItem(TOKEN_KEY);
  clearStoredUser();
  await router.replace("/login");
}

onMounted(loadUsers);
</script>

<template>
  <section class="space-y-4">
    <article class="rounded-[2rem] bg-white/90 p-5 shadow-sm backdrop-blur md:p-6">
      <p class="text-xs uppercase tracking-[0.35em] text-brand/60">Account</p>
      <h3 class="mt-2 text-2xl font-semibold text-slate-900">用户设置</h3>
      <p class="mt-2 text-sm text-slate-500">
        当前账号信息、登录态管理，以及管理员可见的系统用户清单。
      </p>

      <div class="mt-6 grid gap-4 md:grid-cols-[1fr_auto] md:items-end">
        <div class="grid gap-4 sm:grid-cols-3">
          <div class="rounded-3xl border border-slate-100 bg-slate-50 p-4">
            <p class="text-sm text-slate-500">用户名</p>
            <p class="mt-2 text-lg font-semibold text-slate-900">{{ currentUser?.username || "-" }}</p>
          </div>
          <div class="rounded-3xl border border-slate-100 bg-slate-50 p-4">
            <p class="text-sm text-slate-500">角色</p>
            <p class="mt-2 text-lg font-semibold text-slate-900">{{ currentUser?.role || "-" }}</p>
          </div>
          <div class="rounded-3xl border border-slate-100 bg-slate-50 p-4">
            <p class="text-sm text-slate-500">显示名</p>
            <p class="mt-2 text-lg font-semibold text-slate-900">
              {{ currentUser?.extra_data?.display_name || "未设置" }}
            </p>
          </div>
        </div>

        <button
          type="button"
          class="rounded-2xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-700"
          @click="logout"
        >
          退出登录
        </button>
      </div>
    </article>

    <article
      v-if="isAdmin"
      class="rounded-[2rem] bg-white/90 shadow-sm backdrop-blur"
    >
      <div class="border-b border-slate-100 px-5 py-4 md:px-6">
        <h4 class="text-lg font-semibold text-slate-900">系统用户</h4>
        <p class="mt-1 text-sm text-slate-500">
          系统会默认补齐一组可直接使用的员工账号，避免所有操作都共用 admin。
        </p>
      </div>

      <p v-if="errorMessage" class="px-5 py-4 text-sm text-red-600 md:px-6">{{ errorMessage }}</p>
      <div v-else-if="loading" class="px-5 py-8 text-sm text-slate-500 md:px-6">加载中...</div>
      <div v-else class="divide-y divide-slate-100">
        <div
          v-for="user in users"
          :key="user.id"
          class="px-5 py-4 md:px-6"
        >
          <div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <p class="text-sm font-semibold text-slate-900">
                {{ user.username }}
              </p>
              <p class="mt-1 text-xs text-slate-500">
                {{ user.extra_data?.display_name || "未设置显示名" }}
              </p>
            </div>
            <span
              class="rounded-full px-3 py-1 text-xs font-semibold"
              :class="
                user.role === 'admin'
                  ? 'bg-brand-soft text-brand-dark'
                  : 'bg-slate-100 text-slate-700'
              "
            >
              {{ user.role }}
            </span>
          </div>
        </div>
      </div>

      <div class="border-t border-slate-100 px-5 py-4 text-xs text-slate-500 md:px-6">
        默认账号密码请在交接时妥善保管；当前阶段尚未提供在线改密功能。
      </div>
    </article>
  </section>
</template>
