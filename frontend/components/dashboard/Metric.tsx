export default function Metric({
  label,
  value,
  positive,
}: {
  label: string;
  value: string;
  positive?: boolean;
}) {
  return (
    <div className="border border-line bg-panel p-5">
      <p className="text-sm text-muted">{label}</p>

      <p
        className={`mt-2 text-2xl font-semibold ${
          positive === undefined
            ? ""
            : positive
              ? "text-accent"
              : "text-red-400"
        }`}
      >
        {value}
      </p>
    </div>
  );
}
