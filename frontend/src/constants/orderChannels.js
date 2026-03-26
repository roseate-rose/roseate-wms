export const SUPPORTED_ORDER_CHANNELS = [
  {
    value: "微信小店",
    label: "微信小店",
    importTemplate: "wechat_shop",
    importHint: "当前已支持微信小店标准导出 CSV",
  },
];

export function getDefaultOrderChannel() {
  return SUPPORTED_ORDER_CHANNELS[0]?.value || "";
}
