const FIELDS = [
  { name: "rainfall_mm", label: "Seasonal rainfall (mm)", group: "Weather" },
  { name: "avg_temperature_c", label: "Average temperature (°C)", group: "Weather" },
  { name: "max_temperature_c", label: "Maximum temperature (°C)", group: "Weather" },
  { name: "min_temperature_c", label: "Minimum temperature (°C)", group: "Weather" },
  { name: "soil_ph", label: "Soil pH", group: "Soil" },
  { name: "soil_nitrogen", label: "Soil nitrogen (%)", group: "Soil" },
  { name: "soil_organic_carbon", label: "Soil organic carbon (%)", group: "Soil" },
  { name: "fertilizer_kg_ha", label: "Fertilizer (kg/ha)", group: "Agricultural practices" },
  { name: "planting_day", label: "Planting day (1 = 1 November)", group: "Agricultural practices" },
  { name: "area_ha", label: "Cultivated area (ha)", group: "Farm information" },
];

export const PREDICTION_FIELDS = FIELDS;

export default function PredictionForm({ onSubmit, busy }) {
  const groups = [...new Set(FIELDS.map((field) => field.group))];

  function handleSubmit(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload = {};
    const errors = {};
    FIELDS.forEach((field) => {
      const raw = String(form.get(field.name) ?? "").trim();
      if (raw === "" || Number.isNaN(Number(raw))) {
        errors[field.name] = "Enter a number.";
      } else {
        payload[field.name] = Number(raw);
      }
    });
    onSubmit(payload, errors);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      {groups.map((group) => (
        <fieldset key={group} className="panel">
          <legend className="px-1 text-xs font-semibold uppercase tracking-[0.14em] text-moss">{group}</legend>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            {FIELDS.filter((field) => field.group === group).map((field) => (
              <label key={field.name} className="block text-sm">
                <span className="font-medium text-ink/80">{field.label}</span>
                <input name={field.name} type="number" step="any" required className="input" />
              </label>
            ))}
          </div>
        </fieldset>
      ))}
      <button type="submit" disabled={busy} className="btn-primary">
        {busy ? "Estimating…" : "Estimate yield"}
      </button>
    </form>
  );
}
