<template>
  <section class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
    <article
      class="rounded-3xl bg-white/85 p-5 shadow-sm backdrop-blur"
      v-for="card in [
        { title: '待入库批次', value: '12' },
        { title: '今日出库单', value: '8' },
        { title: '近效期预警', value: '3' },
        { title: '库存 SKU', value: '124' }
      ]"
      :key="card.title"
    >
      <p class="text-sm text-slate-500">{{ card.title }}</p>
      <p class="mt-3 text-3xl font-semibold text-slate-900">{{ card.value }}</p>
    </article>
  </section>
</template>
