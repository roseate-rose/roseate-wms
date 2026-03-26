function toFiniteNumber(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : 0;
}

function trimTrailingZeros(text) {
  return text.replace(/\.0+$/, "").replace(/(\.\d*?[1-9])0+$/, "$1");
}

function formatDecimal(value, digits = 6) {
  const numeric = toFiniteNumber(value);
  const rounded = Math.round((numeric + Number.EPSILON) * 10 ** digits) / 10 ** digits;
  return trimTrailingZeros(rounded.toFixed(digits));
}

function formatQuantityWithUnit(value, unit) {
  const formatted = formatDecimal(value);
  return unit ? `${formatted} ${unit}` : formatted;
}

function formatBoundQuantity(value, productLike) {
  const baseUnit = productLike?.base_unit || productLike?.unit || "";
  const purchaseUnit = productLike?.purchase_unit || "";
  const conversionRate = Number(productLike?.conversion_rate || 0);
  const baseText = formatQuantityWithUnit(value, baseUnit);

  if (!purchaseUnit || !baseUnit || !conversionRate || conversionRate <= 0 || purchaseUnit === baseUnit) {
    return baseText;
  }

  return `${baseText} (${formatQuantityWithUnit(toFiniteNumber(value) / conversionRate, purchaseUnit)})`;
}

export { formatBoundQuantity, formatDecimal, formatQuantityWithUnit };
