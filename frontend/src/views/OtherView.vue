<script setup>
import { computed } from "vue";

import { getStoredRole } from "../auth/session";

const role = getStoredRole();
const isAdmin = role === "admin";

const items = computed(() => {
  const base = [
    {
      title: "入库",
      desc: "H5 扫码入库，支持单位换算与快速映射。",
      to: "/inbound",
      tag: "H5",
    },
    {
      title: "批量入库导入",
      desc: "上传表格批量入库，支持列映射以适配不同模板。",
      to: "/inbound-import",
      tag: "Web",
    },
    {
      title: "出库",
      desc: "后续阶段入口或操作汇总。",
      to: "/outbound",
      tag: "WIP",
    },
    {
      title: "批量订单导入",
      desc: "上传菜鸟/顺丰等模板并映射字段，批量锁定 FIFO 库存。",
      to: "/orders-import",
      tag: "Web",
    },
    {
      title: "数据管理",
      desc: "CSV 导入预览与确认保存，管理员可导出报表。",
      to: "/data",
      tag: "Web",
    },
    {
      title: "渠道映射",
      desc: "绑定外部 SKU 与内部 HB 编码。",
      to: "/channels",
      tag: "Web",
    },
    {
      title: "更新日志",
      desc: "查看关键功能更新与验收节点。",
      to: "/changelog",
      tag: "Info",
    },
    {
      title: "设置",
      desc: "查看当前账号、退出登录；管理员可查看系统用户列表。",
      to: "/settings",
      tag: "Account",
    },
  ];

  if (isAdmin) {
    base.splice(4, 0, {
      title: "财务统计",
      desc: "管理员入口，后续可接入统计指标与成本分析。",
      to: "/finance",
      tag: "Admin",
    });
  }

  return base;
});
</script>

<template>
  <section class="space-y-4">
    <div class="rounded-[2rem] bg-white/90 p-5 shadow-sm backdrop-blur md:p-6">
      <p class="text-xs uppercase tracking-[0.35em] text-brand/60">More</p>
      <h3 class="mt-2 text-2xl font-semibold text-slate-900">其他</h3>
      <p class="mt-2 text-sm text-slate-500">将非主流程能力集中在这里，保持导航简洁。</p>
    </div>

    <div class="grid gap-4 md:grid-cols-2">
      <RouterLink
        v-for="item in items"
        :key="item.to"
        :to="item.to"
        class="group rounded-[2rem] bg-white/90 p-6 shadow-sm backdrop-blur transition hover:-translate-y-[1px] hover:shadow-md"
      >
        <div class="flex items-start justify-between gap-3">
          <div>
            <h4 class="text-lg font-semibold text-slate-900">{{ item.title }}</h4>
            <p class="mt-2 text-sm text-slate-600">{{ item.desc }}</p>
          </div>
          <span
            class="rounded-full bg-brand-soft px-3 py-1 text-xs font-semibold text-brand-dark"
          >
            {{ item.tag }}
          </span>
        </div>
        <p class="mt-4 text-sm font-medium text-brand-dark group-hover:text-brand">
          打开
        </p>
      </RouterLink>
    </div>
  </section>
</template>
