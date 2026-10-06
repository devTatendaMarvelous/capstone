import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const axis = { stroke: "#8aa094", fontSize: 12 };
const grid = "#e7eee8";
const tip = { borderRadius: 12, border: "1px solid #e2e8e3", fontSize: 12 };

export function TimeChart({ data }) {
  if (!data?.length) return null;
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data}>
        <CartesianGrid stroke={grid} vertical={false} />
        <XAxis dataKey="date" tick={axis} axisLine={false} tickLine={false} />
        <YAxis allowDecimals={false} tick={axis} axisLine={false} tickLine={false} />
        <Tooltip contentStyle={tip} />
        <Bar dataKey="count" fill="#14613f" name="Predictions" radius={[8, 8, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function YieldBins({ data }) {
  if (!data?.length) return null;
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data}>
        <CartesianGrid stroke={grid} vertical={false} />
        <XAxis dataKey="label" tick={axis} axisLine={false} tickLine={false} />
        <YAxis allowDecimals={false} tick={axis} axisLine={false} tickLine={false} />
        <Tooltip contentStyle={tip} />
        <Bar dataKey="count" fill="#c4a15a" name="Predictions" radius={[8, 8, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function ImportanceChart({ data }) {
  const rows = (data || []).filter((item) => Number(item.importance_mean) > 0).slice(0, 5);
  if (!rows.length) return null;
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={rows} layout="vertical" margin={{ left: 16 }}>
        <CartesianGrid stroke={grid} horizontal={false} />
        <XAxis type="number" tick={axis} axisLine={false} tickLine={false} />
        <YAxis type="category" dataKey="feature" width={140} tick={axis} axisLine={false} tickLine={false} />
        <Tooltip contentStyle={tip} />
        <Bar dataKey="importance_mean" fill="#3d6b54" name="Importance" radius={[0, 8, 8, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function SeasonChart({ data }) {
  if (!data?.length) return null;
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data}>
        <CartesianGrid stroke={grid} vertical={false} />
        <XAxis dataKey="season" tick={axis} axisLine={false} tickLine={false} />
        <YAxis tick={axis} axisLine={false} tickLine={false} />
        <Tooltip contentStyle={tip} />
        <Bar dataKey="mean_yield_t_ha" fill="#2f6f8f" name="Mean yield (t/ha)" radius={[8, 8, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function RainChart({ data }) {
  if (!data?.length) return null;
  return (
    <ResponsiveContainer width="100%" height={260}>
      <ScatterChart>
        <CartesianGrid stroke={grid} />
        <XAxis dataKey="rainfall_mm" name="Rainfall" unit=" mm" tick={axis} axisLine={false} tickLine={false} />
        <YAxis dataKey="yield_t_ha" name="Yield" unit=" t/ha" tick={axis} axisLine={false} tickLine={false} />
        <Tooltip cursor={{ strokeDasharray: "3 3" }} contentStyle={tip} />
        <Scatter data={data} fill="#14613f" name="Record" />
      </ScatterChart>
    </ResponsiveContainer>
  );
}
