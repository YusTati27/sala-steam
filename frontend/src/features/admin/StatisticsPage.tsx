import { useMemo, useState } from "react";
import { AlertOctagon, AlertTriangle, CheckCircle2, Download, Info, Printer as PrinterIcon } from "lucide-react";
import {
  Bar, BarChart, CartesianGrid, Cell, ComposedChart, Legend, Line, Pie, PieChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import clsx from "clsx";
import { download } from "../../lib/api";
import { useGet } from "../../lib/hooks";
import type { Equipment, Insight, Overview } from "../../lib/types";
import { fmtDate, fmtDuration, fmtGrams, fmtNum, fmtPct, label, toInputDate } from "../../lib/format";
import { Button, Card, CardTitle, DataTable, Empty, ErrorBox, Field, KpiCard, Loading, PageHeader, Select, Input, Tabs, DemoBadge } from "../../components/ui";
import { matColor } from "../../components/shared";
import { useRealtime } from "../../lib/realtime";

const C = { ok: "#34d399", bad: "#f87171", mute: "#4b5868", royal: "#2f6bff", cy: "#22d3ee", warn: "#fbbf24" };
const STATUS_COLOR: Record<string, string> = { completed: C.ok, failed: C.bad, cancelled: C.mute, printing: C.royal, queued: C.cy, pending: C.warn };

/* eslint-disable @typescript-eslint/no-explicit-any */
function Tip({ active, payload, label: l, unit = "", extra }: { active?: boolean; payload?: any[]; label?: any; unit?: string; extra?: (row: any) => React.ReactNode }) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  return (
    <div className="rounded-xl border border-line bg-panel2/95 px-3 py-2 text-xs shadow-xl backdrop-blur">
      <div className="mb-1 font-semibold">{l ?? row.name ?? row.label}</div>
      {payload.filter((p) => p.value !== undefined && p.value !== null).map((p) => (
        <div key={p.dataKey} className="flex items-center justify-between gap-4">
          <span className="flex items-center gap-1.5 text-mute"><i className="size-2 rounded-full" style={{ background: p.color || p.fill }} />{p.name}</span>
          <span className="font-medium tabular-nums">{typeof p.value === "number" ? p.value.toLocaleString("es-CO", { maximumFractionDigits: 1 }) : p.value}{unit}</span>
        </div>
      ))}
      {extra && <div className="mt-1 border-t border-line pt-1 text-mute">{extra(row)}</div>}
    </div>
  );
}

const INSIGHT_STYLE = {
  critical: { icon: AlertOctagon, cls: "border-bad/40 bg-bad/8 text-bad" },
  warning: { icon: AlertTriangle, cls: "border-warn/40 bg-warn/8 text-warn" },
  info: { icon: Info, cls: "border-cy/30 bg-cy/6 text-cy" },
  positive: { icon: CheckCircle2, cls: "border-ok/40 bg-ok/8 text-ok" },
};

export function InsightList({ items, limit }: { items: Insight[]; limit?: number }) {
  return (
    <div className="space-y-2">
      {items.slice(0, limit).map((i, k) => {
        const S = INSIGHT_STYLE[i.level];
        return (
          <div key={k} className={clsx("flex gap-3 rounded-xl border p-3", S.cls)}>
            <S.icon className="mt-0.5 size-5 shrink-0" />
            <div className="min-w-0 text-fg">
              <div className="text-sm font-semibold">{i.title}</div>
              {i.detail && <div className="mt-0.5 text-xs text-mute">{i.detail}</div>}
              {i.action && <div className="mt-1 text-xs"><span className="font-medium text-fg">Acción sugerida:</span> <span className="text-mute">{i.action}</span></div>}
            </div>
          </div>
        );
      })}
    </div>
  );
}

const MONTH_NAMES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];
const DOW = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];
const pad = (n: number) => String(n).padStart(2, "0");

function monthsBetween(from: string, to: string) {
  const out: string[] = [];
  let [y, m] = from.slice(0, 7).split("-").map(Number);
  const [ty, tm] = to.slice(0, 7).split("-").map(Number);
  while (y < ty || (y === ty && m <= tm)) {
    out.push(`${y}-${pad(m)}`);
    if (++m > 12) { m = 1; y++; }
  }
  return out;
}

/** Calendario mensual: columnas = día de la semana, filas = semana del mes; el color indica cuántos trabajos se iniciaron ese día. */
function CalendarHeatmap({ data, from, to }: { data: Overview["demand_by_day"]; from: string; to: string }) {
  const months = useMemo(() => monthsBetween(from, to), [from, to]);
  const [sel, setSel] = useState("");
  const month = months.includes(sel) ? sel : months[months.length - 1];
  const counts = useMemo(() => new Map(data.map((d) => [d.date, d.jobs])), [data]);
  const max = Math.max(1, ...data.map((d) => d.jobs)); // misma escala en todos los meses para poder compararlos
  const [y, m] = month.split("-").map(Number);
  const days = new Date(y, m, 0).getDate();
  const offset = new Date(y, m - 1, 1).getDay(); // 0 = domingo
  const weeks = Math.ceil((offset + days) / 7);
  const today = new Date();
  const todayKey = `${today.getFullYear()}-${pad(today.getMonth() + 1)}-${pad(today.getDate())}`;
  const key = (d: number) => `${month}-${pad(d)}`;
  const monthDays = Array.from({ length: days }, (_, i) => ({ d: i + 1, n: counts.get(key(i + 1)) ?? 0 }));
  const total = monthDays.reduce((s, x) => s + x.n, 0);
  const busiest = monthDays.reduce((a, b) => (b.n > a.n ? b : a), { d: 0, n: 0 });

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <Tabs value={month} onChange={setSel} items={months.map((k) => ({ value: k, label: `${MONTH_NAMES[Number(k.slice(5)) - 1].slice(0, 3)} ${k.slice(2, 4)}` }))} />
        <div className="text-xs text-mute">
          <b className="text-fg">{MONTH_NAMES[m - 1]} {y}</b> · {total} trabajos{busiest.n > 0 && <> · día más cargado: <b className="text-fg">{busiest.d}</b> ({busiest.n})</>}
        </div>
      </div>
      <div className="mx-auto max-w-3xl">
        <div className="grid grid-cols-[4.2rem_repeat(7,minmax(0,1fr))] gap-1.5 text-center text-[11px]">
          <div />
          {DOW.map((d) => <div key={d} className="pb-1 font-medium text-mute">{d}</div>)}
          {Array.from({ length: weeks }, (_, w) => (
            <div key={w} className="contents">
              <div className="flex items-center justify-end pr-2 text-mute">Semana {w + 1}</div>
              {Array.from({ length: 7 }, (_, dow) => {
                const day = w * 7 + dow - offset + 1;
                if (day < 1 || day > days) return <div key={dow} className="h-14 sm:h-16" />;
                const k = key(day);
                const n = counts.get(k) ?? 0;
                const outside = k < from || k > to || k > todayKey;
                const ratio = n / max;
                return (
                  <div key={dow} title={`${DOW[dow]} ${day} de ${MONTH_NAMES[m - 1]}: ${n} trabajo(s)${outside ? " (fuera del período)" : ""}`}
                    className="relative flex h-14 items-center justify-center rounded-lg border border-white/5 text-base font-semibold tabular-nums sm:h-16 sm:text-lg"
                    style={{ background: n ? `rgba(34,211,238,${0.14 + 0.78 * ratio})` : "rgba(255,255,255,0.03)", color: ratio > 0.55 ? "#07090d" : n ? "#e6edf5" : "#4b5868", opacity: outside ? 0.35 : 1 }}>
                    <span className="absolute left-1.5 top-1 text-[10px] font-normal opacity-70">{day}</span>
                    {n || ""}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
        <div className="mt-3 flex items-center justify-center gap-2 text-[11px] text-mute">
          <span>0</span>
          <div className="h-2 w-40 rounded-full" style={{ background: "linear-gradient(90deg, rgba(34,211,238,0.14), rgba(34,211,238,0.92))" }} />
          <span>{max} trabajos/día</span>
        </div>
      </div>
    </div>
  );
}

const PRESETS = [{ v: "30", l: "30 días" }, { v: "90", l: "90 días" }, { v: "180", l: "6 meses" }, { v: "365", l: "12 meses" }, { v: "custom", l: "Personalizado" }];

export default function StatisticsPage() {
  const today = new Date();
  const [preset, setPreset] = useState("180");
  const [from, setFrom] = useState(toInputDate(new Date(Date.now() - 179 * 86400000)));
  const [to, setTo] = useState(toInputDate(today));
  const [printerId, setPrinterId] = useState("");
  const [material, setMaterial] = useState("");
  const [status, setStatus] = useState("");
  const { push } = useRealtime();

  const applyPreset = (v: string) => {
    setPreset(v);
    if (v !== "custom") { setFrom(toInputDate(new Date(Date.now() - (Number(v) - 1) * 86400000))); setTo(toInputDate(new Date())); }
  };
  const params = { date_from: from, date_to: to, printer_id: printerId, material, status };
  const { data, isLoading, error, isFetching } = useGet<Overview>("stats", "/stats/overview", params);
  const { data: printers } = useGet<Equipment[]>("equipment", "/equipment", { type: "printer_3d" });

  const exportCsv = () => download("/jobs/export.csv", { date_from: from, date_to: to, printer_id: printerId, material, status }, `trabajos_${from}_${to}.csv`).catch((e) => push(e.message, "error"));

  const k = data?.kpis;
  const cmp = data?.comparison;
  const materialsInData = data?.materials.map((m) => m.material) ?? [];
  const noData = data && data.kpis.total_jobs === 0;

  return (
    <>
      <PageHeader title="Estadísticas y analítica" subtitle="Indicadores, tendencias y hallazgos para tomar decisiones y armar reportes."
        actions={<><Button variant="outline" onClick={exportCsv}><Download className="size-4" /> CSV</Button><Button variant="outline" onClick={() => window.print()}><PrinterIcon className="size-4" /> Imprimir / PDF</Button></>} />

      {/* Encabezado solo para impresión */}
      <div className="mb-4 hidden print:block">
        <h2 className="text-lg font-bold">Reporte de gestión — Sala STEAM</h2>
        <p className="text-xs">Período: {fmtDate(from)} a {fmtDate(to)} · Filtros: {[printerId && printers?.find((p) => String(p.id) === printerId)?.name, material, status && label(status)].filter(Boolean).join(", ") || "ninguno"} · Generado: {new Date().toLocaleString("es-CO")}</p>
        {data?.demo && <p className="mt-1 text-xs font-bold">⚠ DATOS DE SIMULACIÓN (demostración): no corresponden a la operación real.</p>}
      </div>

      <Card className="no-print mb-5 !p-3">
        <div className="flex flex-wrap items-end gap-3">
          <Tabs value={preset} onChange={applyPreset} items={PRESETS.map((p) => ({ value: p.v, label: p.l }))} />
          {preset === "custom" && <>
            <Field label="Desde"><Input type="date" value={from} max={to} onChange={(e) => setFrom(e.target.value)} /></Field>
            <Field label="Hasta"><Input type="date" value={to} min={from} max={toInputDate(today)} onChange={(e) => setTo(e.target.value)} /></Field>
          </>}
          <Field label="Impresora"><Select value={printerId} onChange={(e) => setPrinterId(e.target.value)}><option value="">Todas</option>{printers?.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</Select></Field>
          <Field label="Material"><Select value={material} onChange={(e) => setMaterial(e.target.value)}><option value="">Todos</option>{["PLA", "PETG", "ABS", "TPU", "ASA", "NYLON"].map((m) => <option key={m}>{m}</option>)}</Select></Field>
          <Field label="Estado"><Select value={status} onChange={(e) => setStatus(e.target.value)}><option value="">Todos</option>{["completed", "failed", "cancelled", "printing", "queued", "pending"].map((s) => <option key={s} value={s}>{label(s)}</option>)}</Select></Field>
          {(printerId || material || status) && <Button variant="ghost" size="sm" onClick={() => { setPrinterId(""); setMaterial(""); setStatus(""); }}>Limpiar filtros</Button>}
          {isFetching && !isLoading && <span className="pb-2 text-xs text-mute">Actualizando…</span>}
        </div>
      </Card>

      <ErrorBox error={error} />
      {isLoading ? <Loading /> : !data || !k ? null : noData ? (
        <Empty title="Sin trabajos en este período" text="Cambia el rango de fechas o quita filtros. Si el sistema está en modo real, aún no hay datos registrados." />
      ) : (
        <div className="space-y-5">
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-3 xl:grid-cols-6">
            <KpiCard label="Trabajos" value={fmtNum(k.total_jobs)} delta={cmp?.total_jobs.delta_pct} sub={cmp ? "% vs. período previo" : `${data.period.days} días`} tone="cy" />
            <KpiCard label="Tasa de éxito" value={fmtPct(k.success_rate)} delta={cmp?.success_rate.delta} sub={cmp ? "pts vs. previo" : `${k.completed} ok / ${k.failed} fallidos`} tone={k.success_rate !== null && k.success_rate >= 90 ? "ok" : k.success_rate !== null && k.success_rate >= 75 ? "warn" : "bad"} />
            <KpiCard label="Filamento usado" value={fmtGrams(k.grams_total)} delta={cmp?.grams_total.delta_pct} deltaGood="down" sub={cmp ? "% vs. previo" : undefined} tone="royal" />
            <KpiCard label="Desperdicio" value={fmtGrams(k.grams_wasted)} sub={`${fmtPct(k.waste_pct)} del consumo`} tone={k.waste_pct !== null && k.waste_pct > 10 ? "bad" : "ok"} />
            <KpiCard label="Horas de impresión" value={`${fmtNum(k.print_hours, 0)} h`} delta={cmp?.print_hours.delta_pct} sub={cmp ? "% vs. previo" : undefined} tone="cy" />
            <KpiCard label="Duración promedio" value={fmtDuration(k.avg_duration_min)} sub={`${fmtGrams(k.avg_grams)} por trabajo`} tone="royal" />
          </div>

          <Card>
            <CardTitle hint="Generados automáticamente a partir de los datos filtrados">Hallazgos clave y acciones sugeridas</CardTitle>
            <InsightList items={data.insights} />
          </Card>

          <div className="grid gap-5 xl:grid-cols-3">
            <Card className="xl:col-span-2">
              <CardTitle hint={`Trabajos por ${{ day: "día", week: "semana", month: "mes" }[data.period.granularity]} y tasa de éxito (línea, eje derecho). Meta: 90 %`}>Trabajos completados, fallidos y pendientes</CardTitle>
              <div className="h-72">
                <ResponsiveContainer>
                  <ComposedChart data={data.jobs_by_period} margin={{ left: -12, right: 4, top: 8 }}>
                    <CartesianGrid vertical={false} />
                    <XAxis dataKey="label" tickLine={false} axisLine={false} interval="preserveStartEnd" minTickGap={18} />
                    <YAxis yAxisId="l" allowDecimals={false} tickLine={false} axisLine={false} />
                    <YAxis yAxisId="r" orientation="right" domain={[0, 100]} unit="%" tickLine={false} axisLine={false} />
                    <Tooltip content={<Tip />} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
                    <Legend iconType="circle" wrapperStyle={{ fontSize: 11 }} />
                    <ReferenceLine yAxisId="r" y={90} stroke={C.ok} strokeDasharray="4 4" opacity={0.6} />
                    <Bar yAxisId="l" dataKey="completed" name="Completados" stackId="a" fill={C.ok} />
                    <Bar yAxisId="l" dataKey="failed" name="Fallidos" stackId="a" fill={C.bad} />
                    <Bar yAxisId="l" dataKey="cancelled" name="Cancelados" stackId="a" fill={C.mute} />
                    <Bar yAxisId="l" dataKey="active" name="Pendientes/en proceso" stackId="a" fill={C.royal} radius={[3, 3, 0, 0]} />
                    <Line yAxisId="r" dataKey="success_rate" name="Tasa de éxito" stroke={C.cy} strokeWidth={2} dot={false} connectNulls unit="%" />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </Card>

            <Card>
              <CardTitle hint="Éxito frente a fallo y estado de todos los trabajos">Distribución por estado</CardTitle>
              <div className="relative h-52">
                <ResponsiveContainer>
                  <PieChart>
                    <Pie data={data.status_distribution.map((s) => ({ ...s, name: label(s.status) }))} dataKey="count" nameKey="name" innerRadius="62%" outerRadius="90%" paddingAngle={2} stroke="none">
                      {data.status_distribution.map((s) => <Cell key={s.status} fill={STATUS_COLOR[s.status] ?? C.mute} />)}
                    </Pie>
                    <Tooltip content={<Tip />} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="pointer-events-none absolute inset-0 grid place-items-center text-center"><div><div className="text-2xl font-semibold tabular-nums">{k.total_jobs}</div><div className="text-[11px] text-mute">trabajos</div></div></div>
              </div>
              <ul className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
                {data.status_distribution.map((s) => <li key={s.status} className="flex items-center justify-between"><span className="flex items-center gap-1.5"><i className="size-2 rounded-full" style={{ background: STATUS_COLOR[s.status] ?? C.mute }} />{label(s.status)}</span><span className="tabular-nums text-mute">{s.count} · {fmtPct((100 * s.count) / k.total_jobs, 0)}</span></li>)}
              </ul>
            </Card>
          </div>

          <div className="grid gap-5 xl:grid-cols-2">
            <Card>
              <CardTitle hint={`Horas de impresión ÷ (días × ${data.assumptions.open_hours_per_day} h operativas). La línea marca el nivel de saturación (70 %)`}>Utilización por impresora</CardTitle>
              <div style={{ height: Math.max(180, data.printers.length * 42) }}>
                <ResponsiveContainer>
                  <BarChart data={data.printers} layout="vertical" margin={{ left: 0, right: 24 }}>
                    <CartesianGrid horizontal={false} />
                    <XAxis type="number" domain={[0, 100]} unit="%" tickLine={false} axisLine={false} />
                    <YAxis type="category" dataKey="name" width={96} tickLine={false} axisLine={false} />
                    <Tooltip cursor={{ fill: "rgba(255,255,255,0.04)" }} content={<Tip unit="%" extra={(r) => `${r.hours} h · ${r.jobs} trabajos · éxito ${r.success_rate ?? "—"}%`} />} />
                    <ReferenceLine x={70} stroke={C.warn} strokeDasharray="4 4" />
                    <Bar dataKey="utilization_pct" name="Utilización" radius={[0, 4, 4, 0]} barSize={18}>
                      {data.printers.map((p) => <Cell key={p.printer_id} fill={p.utilization_pct >= 70 ? C.warn : C.cy} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>

            <Card>
              <CardTitle hint="Proporción de impresiones exitosas y fallidas por equipo; las que más fallan, arriba de la lista de acciones">Éxito vs. fallo por impresora</CardTitle>
              <div style={{ height: Math.max(180, data.printers.length * 42) }}>
                <ResponsiveContainer>
                  <BarChart data={[...data.printers].sort((a, b) => (a.success_rate ?? 100) - (b.success_rate ?? 100))} layout="vertical" stackOffset="expand" margin={{ left: 0, right: 24 }}>
                    <CartesianGrid horizontal={false} />
                    <XAxis type="number" tickFormatter={(v) => `${Math.round(v * 100)}%`} tickLine={false} axisLine={false} />
                    <YAxis type="category" dataKey="name" width={96} tickLine={false} axisLine={false} />
                    <Tooltip cursor={{ fill: "rgba(255,255,255,0.04)" }} content={<Tip />} />
                    <Legend iconType="circle" wrapperStyle={{ fontSize: 11 }} />
                    <Bar dataKey="completed" name="Exitosas" stackId="s" fill={C.ok} barSize={18} />
                    <Bar dataKey="failed" name="Fallidas" stackId="s" fill={C.bad} radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>

          <Card>
            <CardTitle>Detalle por impresora</CardTitle>
            <DataTable head={["Impresora", "Trabajos", "Horas", "Utilización", "Éxito", "Fallidos", "Filamento", "Duración prom."]}>
              {data.printers.map((p) => (
                <tr key={p.printer_id}>
                  <td className="font-medium">{p.name}</td><td className="tabular-nums">{p.jobs}</td><td className="tabular-nums">{fmtNum(p.hours, 1)}</td>
                  <td className="tabular-nums">{fmtPct(p.utilization_pct, 0)}</td>
                  <td className={clsx("tabular-nums font-medium", p.success_rate === null ? "text-mute" : p.success_rate >= 90 ? "text-ok" : p.success_rate >= 75 ? "text-warn" : "text-bad")}>{fmtPct(p.success_rate, 0)}</td>
                  <td className="tabular-nums">{p.failed}</td><td className="tabular-nums">{fmtGrams(p.grams)}</td><td className="text-xs">{fmtDuration(p.avg_duration_min)}</td>
                </tr>
              ))}
            </DataTable>
          </Card>

          <div className="grid gap-5 xl:grid-cols-3">
            <Card className="xl:col-span-2">
              <CardTitle hint="Gramos consumidos por material en cada período; la línea roja es el material perdido en trabajos fallidos o cancelados">Consumo de filamento por período</CardTitle>
              <div className="h-72">
                <ResponsiveContainer>
                  <ComposedChart data={data.consumption_by_period.rows} margin={{ left: -4, right: 4, top: 8 }}>
                    <CartesianGrid vertical={false} />
                    <XAxis dataKey="label" tickLine={false} axisLine={false} interval="preserveStartEnd" minTickGap={18} />
                    <YAxis tickLine={false} axisLine={false} unit=" g" width={52} />
                    <Tooltip content={<Tip unit=" g" />} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
                    <Legend iconType="circle" wrapperStyle={{ fontSize: 11 }} />
                    {data.consumption_by_period.materials.map((m, i, arr) => <Bar key={m} dataKey={m} name={m} stackId="m" fill={matColor(m)} radius={i === arr.length - 1 ? [3, 3, 0, 0] : 0} />)}
                    <Line dataKey="wasted_g" name="Desperdicio" stroke={C.bad} strokeDasharray="5 4" strokeWidth={2} dot={false} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </Card>

            <Card>
              <CardTitle hint="Gramos por material y su tasa de éxito">Material más utilizado</CardTitle>
              <div className="space-y-3">
                {data.materials.map((m) => (
                  <div key={m.material}>
                    <div className="mb-1 flex items-baseline justify-between text-xs"><span className="font-semibold" style={{ color: matColor(m.material) }}>{m.material}</span><span className="tabular-nums text-mute">{fmtGrams(m.grams)} · {fmtPct(m.share_pct, 0)}</span></div>
                    <div className="h-2.5 overflow-hidden rounded-full bg-line"><div className="h-full rounded-full" style={{ width: `${m.share_pct}%`, background: matColor(m.material) }} /></div>
                    <div className="mt-0.5 flex justify-between text-[11px] text-mute"><span>{m.jobs} trabajos</span><span className={clsx(m.success_rate !== null && m.success_rate < 80 && "text-warn")}>éxito {fmtPct(m.success_rate, 0)}</span></div>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          <div className="grid gap-5 xl:grid-cols-2">
            <Card>
              <CardTitle hint="Top 10 por gramos consumidos; la barra usa el color real del filamento">Colores más utilizados</CardTitle>
              <div className="h-72">
                <ResponsiveContainer>
                  <BarChart data={data.colors} layout="vertical" margin={{ left: 0, right: 16 }}>
                    <CartesianGrid horizontal={false} />
                    <XAxis type="number" tickLine={false} axisLine={false} unit=" g" />
                    <YAxis type="category" dataKey="color" width={88} tickLine={false} axisLine={false} />
                    <Tooltip cursor={{ fill: "rgba(255,255,255,0.04)" }} content={<Tip unit=" g" extra={(r) => `${r.jobs} trabajos · ${r.share_pct}% del consumo`} />} />
                    <Bar dataKey="grams" name="Consumo" radius={[0, 4, 4, 0]} barSize={16}>
                      {data.colors.map((c) => <Cell key={c.color} fill={c.hex} stroke="rgba(255,255,255,0.35)" />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>

            <Card>
              <CardTitle hint="Causas registradas en los trabajos fallidos">Por qué fallan las impresiones</CardTitle>
              {data.failure_reasons.length === 0 ? <p className="py-10 text-center text-sm text-mute">Sin fallos con causa registrada en el período.</p> : (
                <div className="h-72">
                  <ResponsiveContainer>
                    <BarChart data={data.failure_reasons} layout="vertical" margin={{ left: 0, right: 16 }}>
                      <CartesianGrid horizontal={false} />
                      <XAxis type="number" allowDecimals={false} tickLine={false} axisLine={false} />
                      <YAxis type="category" dataKey="label" width={130} tickLine={false} axisLine={false} />
                      <Tooltip cursor={{ fill: "rgba(255,255,255,0.04)" }} content={<Tip extra={(r) => `${r.pct}% de los fallos`} />} />
                      <Bar dataKey="count" name="Fallos" fill={C.bad} radius={[0, 4, 4, 0]} barSize={16} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </Card>
          </div>

          <Card>
            <CardTitle hint="Calendario del mes elegido: cada casilla es un día y su número, los trabajos iniciados. Más color = más demanda. Úsalo para dimensionar el personal y abrir reservas en días valle">Demanda por día (calendario)</CardTitle>
            <CalendarHeatmap data={data.demand_by_day} from={data.period.from} to={data.period.to} />
          </Card>

          <div className="grid gap-5 xl:grid-cols-2">
            <Card>
              <CardTitle hint="Existencias actuales ÷ consumo diario de los últimos 60 días">Autonomía del inventario</CardTitle>
              <DataTable head={["Material", "Disponible", "Consumo/día", "Autonomía"]}>
                {data.stock_forecast.map((f) => (
                  <tr key={f.material}>
                    <td className="font-semibold" style={{ color: matColor(f.material) }}>{f.material}</td><td className="tabular-nums">{fmtGrams(f.available_g)}</td><td className="tabular-nums">{fmtGrams(f.daily_g)}</td>
                    <td className={clsx("font-medium tabular-nums", f.days_left === null ? "text-mute" : f.days_left <= 7 ? "text-bad" : f.days_left <= 14 ? "text-warn" : "text-ok")}>{f.days_left === null ? "sin consumo" : f.days_left > 365 ? "más de 1 año" : `~${f.days_left} días`}</td>
                  </tr>
                ))}
              </DataTable>
            </Card>
            <Card>
              <CardTitle hint="Quiénes concentran la demanda de la sala">Usuarios con más trabajos</CardTitle>
              <DataTable head={["Usuario", "Trabajos", "Filamento"]}>
                {data.top_users.map((u) => <tr key={u.name}><td className="font-medium">{u.name}</td><td className="tabular-nums">{u.jobs}</td><td className="tabular-nums">{fmtGrams(u.grams)}</td></tr>)}
              </DataTable>
            </Card>
          </div>

          <Card className="!p-4 text-xs text-mute">
            <div className="mb-1 font-semibold text-fg">Cómo se calculan los indicadores {data.demo && <DemoBadge />}</div>
            <ul className="list-disc space-y-0.5 pl-4">
              <li><b>Tasa de éxito</b>: {data.assumptions.success_rate}. <b>Tasa de completado</b>: {data.assumptions.completion_rate}.</li>
              <li><b>Utilización</b>: {data.assumptions.utilization} (configurable en Configuración).</li>
              <li><b>Desperdicio</b>: gramos consumidos en trabajos fallidos o cancelados. <b>Autonomía</b>: existencias ÷ consumo diario reciente.</li>
              <li>Comparación contra el período anterior de igual duración ({fmtDate(data.period.previous_from)} – {fmtDate(data.period.previous_to)}). Datos generados {new Date(data.generated_at).toLocaleString("es-CO")}.</li>
              {materialsInData.length > 0 && <li>Materiales en el período: {materialsInData.join(", ")}.</li>}
            </ul>
          </Card>
        </div>
      )}
    </>
  );
}
