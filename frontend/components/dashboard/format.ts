export const money = (
  value: number | null | undefined,
) =>
  value == null
    ? "—"
    : new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 2,
      }).format(value);

export const number = (
  value: number | null | undefined,
) =>
  value == null
    ? "—"
    : new Intl.NumberFormat("en-IN", {
        maximumFractionDigits: 2,
      }).format(value);
