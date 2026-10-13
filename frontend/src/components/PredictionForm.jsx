import { useEffect, useState } from "react";
import FarmLocationPicker from "./FarmLocationPicker";
import { previewEnvironmentalData } from "../services/predictionService";

const MANUAL_FIELDS = [
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

export const PREDICTION_FIELDS = MANUAL_FIELDS;

export default function PredictionForm({ onSubmit, busy }) {
  const [selectedLocation, setSelectedLocation] = useState(null);
  const [areaHa, setAreaHa] = useState("");
  const [plantingDate, setPlantingDate] = useState("2023-11-15");
  const [fertilizerRate, setFertilizerRate] = useState("");
  const [manualMode, setManualMode] = useState(false);

  // Environmental preview state
  const [envPreview, setEnvPreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState("");

  // Manual field override values
  const [manualOverrides, setManualOverrides] = useState({});

  // When location changes and is confirmed, fetch environmental data preview
  useEffect(() => {
    if (selectedLocation?.confirmed && selectedLocation.latitude && selectedLocation.longitude) {
      let active = true;
      setPreviewLoading(true);
      setPreviewError("");

      previewEnvironmentalData({
        latitude: selectedLocation.latitude,
        longitude: selectedLocation.longitude,
        planting_date: plantingDate,
        season_year: 2023,
      })
        .then((res) => {
          if (active) {
            setEnvPreview(res);
            setPreviewLoading(false);
          }
        })
        .catch((err) => {
          if (active) {
            setPreviewError("Could not retrieve automatic environmental preview. You can enter values manually.");
            setPreviewLoading(false);
          }
        });

      return () => {
        active = false;
      };
    } else {
      setEnvPreview(null);
    }
  }, [selectedLocation?.confirmed, selectedLocation?.latitude, selectedLocation?.longitude, plantingDate]);

  function handleManualChange(fieldName, value) {
    setManualOverrides((prev) => ({ ...prev, [fieldName]: value }));
  }

  function handleSubmit(event) {
    event.preventDefault();
    const payload = {};
    const errors = {};

    const locationConfirmed = selectedLocation?.confirmed;

    // Validate location if using location-based workflow
    if (selectedLocation) {
      payload.location = {
        latitude: selectedLocation.latitude,
        longitude: selectedLocation.longitude,
        location_selection_method: selectedLocation.selectionMethod || "manual_map_selection",
        confirmed: Boolean(selectedLocation.confirmed),
        description: selectedLocation.isWithinStudyArea
          ? "Macheke, Mashonaland East, Zimbabwe"
          : "Farm location outside study area",
      };
      if (!locationConfirmed) {
        errors.location = "Please click 'Confirm This Farm Location' to verify your farm point.";
      }
    } else {
      errors.location = "Select and confirm your farm location.";
    }

    // Validate Area (Required in all modes)
    const rawArea = String(areaHa).trim();
    if (rawArea === "" || Number.isNaN(Number(rawArea)) || Number(rawArea) <= 0) {
      errors.area_ha = "Enter a cultivated area in hectares.";
    } else {
      payload.area_ha = Number(rawArea);
    }

    // Planting date and day
    if (plantingDate) {
      payload.planting_date = plantingDate;
    }

    // Fertilizer rate (optional - missing value workflow imputes median)
    const rawFert = String(fertilizerRate).trim();
    if (rawFert !== "") {
      if (Number.isNaN(Number(rawFert)) || Number(rawFert) < 0) {
        errors.fertilizer_kg_ha = "Enter a valid positive number for fertilizer.";
      } else {
        payload.fertilizer_kg_ha = Number(rawFert);
      }
    }

    // In manual mode OR when location is not confirmed, check and include manual fields
    MANUAL_FIELDS.forEach((field) => {
      const formVal = manualOverrides[field.name];
      if (formVal !== undefined && formVal !== "") {
        payload[field.name] = Number(formVal);
      } else if (!locationConfirmed) {
        // If location is not confirmed, report missing numeric fields for backwards compatibility
        errors[field.name] = "Enter a number or confirm your farm location.";
      }
    });

    onSubmit(payload, errors);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6" noValidate>
      {/* 1. Farm Location Selection Component */}
      <FarmLocationPicker
        onLocationChange={(loc) => setSelectedLocation(loc)}
        selectedLocation={selectedLocation}
      />

      {/* 2. Farmer Management Inputs (Reduced Farmer Inputs) */}
      <div className="panel space-y-4">
        <div>
          <span className="text-xs font-semibold uppercase tracking-[0.14em] text-moss">Farm Management</span>
          <h2 className="text-lg font-semibold text-ink">Crop &amp; Field Information</h2>
          <p className="text-xs text-ink/65">
            Only provide information that cannot be derived from satellite and geospatial records.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          {/* Crop (Default to Maize) */}
          <label className="block text-sm">
            <span className="font-medium text-ink/80">Crop Type</span>
            <input
              type="text"
              value="Maize (Zea mays)"
              readOnly
              disabled
              className="input bg-black/[0.03] text-ink/70 cursor-not-allowed"
            />
            <span className="mt-1 block text-[11px] text-ink/50">
              The project model is calibrated for summer maize.
            </span>
          </label>

          {/* Farm Area in Hectares */}
          <label className="block text-sm">
            <span className="font-medium text-ink/80">Cultivated Area (ha) *</span>
            <input
              name="area_ha"
              type="number"
              step="any"
              min="0.01"
              max="100"
              required
              value={areaHa}
              onChange={(e) => {
                setAreaHa(e.target.value);
                handleManualChange("area_ha", e.target.value);
              }}
              placeholder="e.g. 2.5"
              className="input"
            />
            <span className="mt-1 block text-[11px] text-ink/50">
              Used solely to calculate total production tonnes from predicted yield.
            </span>
          </label>

          {/* Planting Date */}
          <label className="block text-sm">
            <span className="font-medium text-ink/80">Planting Date</span>
            <input
              name="planting_date"
              type="date"
              value={plantingDate}
              onChange={(e) => setPlantingDate(e.target.value)}
              className="input"
            />
            <span className="mt-1 block text-[11px] text-ink/50">
              Maize planting window (Nov–Jan). Day 1 is 1 November.
            </span>
          </label>

          {/* Fertilizer Rate (Optional) */}
          <label className="block text-sm">
            <span className="font-medium text-ink/80">Fertilizer Rate (kg/ha)</span>
            <input
              name="fertilizer_kg_ha"
              type="number"
              step="any"
              min="0"
              max="1000"
              value={fertilizerRate}
              onChange={(e) => {
                setFertilizerRate(e.target.value);
                handleManualChange("fertilizer_kg_ha", e.target.value);
              }}
              placeholder="Leave blank if unknown"
              className="input"
            />
            <span className="mt-1 block text-[11px] text-ink/50">
              Optional. If left blank, regional training median (150 kg/ha) is imputed.
            </span>
          </label>
        </div>
      </div>

      {/* 3. Automatic Environmental Data Preview */}
      {selectedLocation?.confirmed && (
        <div className="panel space-y-3 bg-[#f8fbf7] border border-leaf/20">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <span className="text-xs font-semibold uppercase tracking-[0.14em] text-leaf">
                Automatic Geospatial Acquisition
              </span>
              <h3 className="text-sm font-semibold text-ink">Environmental Data Preview</h3>
            </div>
            {previewLoading && (
              <span className="text-xs text-moss font-medium flex items-center gap-1.5">
                <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-leaf border-r-transparent" />
                Retrieving environmental records…
              </span>
            )}
          </div>

          {previewError && <p className="text-xs text-clay">{previewError}</p>}

          {envPreview && (
            <div className="space-y-3">
              <div className="grid gap-3 sm:grid-cols-3">
                {/* Rainfall */}
                <div className="rounded-xl bg-white p-3 ring-1 ring-black/5">
                  <span className="text-[11px] text-ink/55 uppercase font-medium">Seasonal Rainfall</span>
                  <p className="mt-1 font-semibold text-base text-ink">
                    {envPreview.environmental_data.rainfall_mm} <span className="text-xs text-ink/60">mm</span>
                  </p>
                  <span className="text-[10px] text-moss block mt-0.5">Source: CHIRPS 2.0 (0.05°)</span>
                </div>

                {/* Temperatures */}
                <div className="rounded-xl bg-white p-3 ring-1 ring-black/5">
                  <span className="text-[11px] text-ink/55 uppercase font-medium">Seasonal Temperatures</span>
                  <p className="mt-1 font-semibold text-base text-ink">
                    {envPreview.environmental_data.avg_temperature_c} <span className="text-xs text-ink/60">°C avg</span>
                  </p>
                  <span className="text-[10px] text-moss block mt-0.5">
                    Max: {envPreview.environmental_data.max_temperature_c}°C | Min: {envPreview.environmental_data.min_temperature_c}°C (NASA POWER)
                  </span>
                </div>

                {/* Soil */}
                <div className="rounded-xl bg-white p-3 ring-1 ring-black/5">
                  <span className="text-[11px] text-ink/55 uppercase font-medium">Topsoil Properties (0-5cm)</span>
                  <p className="mt-1 font-semibold text-base text-ink">
                    pH {envPreview.environmental_data.soil_ph}
                  </p>
                  <span className="text-[10px] text-moss block mt-0.5">
                    N: {(envPreview.environmental_data.soil_nitrogen * 100).toFixed(2)}% | SOC: {envPreview.environmental_data.soil_organic_carbon}% (SoilGrids 250m)
                  </span>
                </div>
              </div>

              {/* Data quality warnings */}
              {envPreview.data_quality?.warnings?.length > 0 && (
                <div className="rounded-lg bg-amber-500/10 p-2.5 text-[11px] text-ink/80 space-y-1">
                  {envPreview.data_quality.warnings.map((w, idx) => (
                    <p key={idx}>ℹ️ {w}</p>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* 4. Advanced / Manual Environmental Overrides Collapsible */}
      <div className="rounded-2xl border border-line bg-white p-4">
        <button
          type="button"
          onClick={() => setManualMode(!manualMode)}
          className="flex w-full items-center justify-between text-xs font-semibold uppercase tracking-[0.12em] text-ink/75 hover:text-ink"
        >
          <span>Manual Environmental Overrides (Advanced)</span>
          <span>{manualMode ? "▲ Hide" : "▼ Show"}</span>
        </button>

        {manualMode && (
          <div className="mt-4 pt-3 border-t border-line space-y-3">
            <p className="text-xs text-ink/65">
              Enter custom values if you have on-site meteorological measurements or certified soil laboratory analyses.
            </p>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {MANUAL_FIELDS.filter((f) => f.name !== "area_ha" && f.name !== "fertilizer_kg_ha").map((field) => (
                <label key={field.name} className="block text-xs">
                  <span className="font-medium text-ink/80">{field.label}</span>
                  <input
                    name={field.name}
                    type="number"
                    step="any"
                    value={manualOverrides[field.name] || ""}
                    onChange={(e) => handleManualChange(field.name, e.target.value)}
                    placeholder="Auto from location"
                    className="input text-xs py-2 mt-1"
                  />
                </label>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Submit Button */}
      <div>
        <button type="submit" disabled={busy} className="btn-primary w-full sm:w-auto px-6 py-3">
          {busy ? "Estimating…" : "Estimate yield"}
        </button>
      </div>
    </form>
  );
}
