<script setup>
const entries = [
  {
    date: "2026-03-12",
    title: "Inbound Receipts + Ledger Export",
    detail: "新增入库单据(InboundReceipt/InboundLine)、IN/OUT 流水台账与结存导出(balance_scope=product|batch)。",
  },
  {
    date: "2026-03-10",
    title: "Fly.io Deploy",
    detail: "完成 Fly.io 部署与持久化卷挂载，服务常驻配置与脚本化部署。",
  },
  {
    date: "2026-03-09",
    title: "Stages 1-5 Core",
    detail: "认证、批次库存、单位换算、预占与订单闭环、报表导出等核心能力落地。",
  },
];
</script>

<template>
  <section class="space-y-4">
    <div class="rounded-[2rem] bg-white/90 p-5 shadow-sm backdrop-blur md:p-6">
      <p class="text-xs uppercase tracking-[0.35em] text-brand/60">Changelog</p>
      <h3 class="mt-2 text-2xl font-semibold text-slate-900">更新日志</h3>
      <p class="mt-2 text-sm text-slate-500">记录关键功能变化，便于运营与验收对齐。</p>
    </div>

    <div class="space-y-3">
      <article
        v-for="entry in entries"
        :key="`${entry.date}-${entry.title}`"
        class="rounded-[2rem] bg-white/90 p-5 shadow-sm backdrop-blur md:p-6"
      >
        <div class="flex flex-col gap-2 sm:flex-row sm:items-baseline sm:justify-between">
          <h4 class="text-lg font-semibold text-slate-900">{{ entry.title }}</h4>
          <p class="text-sm text-slate-500">{{ entry.date }}</p>
        </div>
        <p class="mt-3 text-sm text-slate-600">{{ entry.detail }}</p>
      </article>
    </div>
  </section>
</template>

