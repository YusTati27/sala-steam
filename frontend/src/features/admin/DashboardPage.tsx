import { useNavigate } from "react-router-dom";
import { AlertTriangle, Boxes, CheckCircle2, Clock, Cpu, Hourglass, PackageMinus, Percent, Power, Wrench, XCircle, ArrowRight } from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import clsx from "clsx";
import { useGet } from "../../lib/hooks";
import type { Dashboard, Equipment } from "../../lib/types";
import { fmtGrams, fmtPct } from "../../lib/format";
import { Button, Card, CardTitle, ErrorBox, KpiCard, Loading, PageHeader, ProgressBar } from "../../components/ui";
import { InsightList } from "./StatisticsPage";

export default function DashboardPage() {
  const navigate = useNavigate();
  const { data: d, isLoading, error } = useGet<Dashboard>("dashboard", "/stats/dashboard");
  const { data: printers } = useGet<Equipment[]>("equipment", "/equipment", { type: "printer_3d" });
  if (isLoading) return <Loading />;
  if (error || !d) return <ErrorBox error={error} />;
  const k = d.last_30_days.kpis;
  const cmp = d.last_30_days.comparison;
  const printing = printers?.filter((p) => p.current_job) ?? [];

  return (
    <>
      <PageHeader title="Panel principal" subtitle="Resumen operativo de la sala STEAM." actions={<Button variant="outline" onClick={() => navigate("/admin/estadisticas")}>Ver analítica completa <ArrowRight className="size-4" /></Button>} />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
        <KpiCard label="Total de impresoras" value={d.printers.total} icon={<Cpu className="size-4" />} tone="cy" onClick={() => navigate("/admin/equipos")} />
        <KpiCard label="Disponibles" value={d.printers.available} icon={<Power className="size-4" />} tone="ok" sub={`${d.printers.total ? Math.round((100 * d.printers.available) / d.printers.total) : 0}% de la flota`} />
        <KpiCard label="Ocupadas" value={d.printers.busy} icon={<Clock className="size-4" />} tone="royal" sub={d.printers.maintenance ? `+${d.printers.maintenance} en mantenimiento` : undefined} />
        <KpiCard label="Fuera de servicio" value={d.printers.out_of_service} icon={<XCircle className="size-4" />} tone={d.printers.out_of_service ? "bad" : "ok"} />
        <KpiCard label="Trabajos completados" value={d.jobs.completed} icon={<CheckCircle2 className="size-4" />} tone="ok" sub={`${d.jobs.failed} fallidos`} onClick={() => navigate("/admin/trabajos")} />
        <KpiCard label="Trabajos pendientes" value={d.jobs.pending} icon={<Hourglass className="size-4" />} tone="warn" sub={`${d.jobs.printing} en proceso`} onClick={() => navigate("/admin/trabajos")} />
        <KpiCard label="% completados" value={fmtPct(d.jobs.completion_pct)} icon={<Percent className="size-4" />} tone="cy" sub="sobre trabajos cerrados" />
        <KpiCard label="Alertas de mantenimiento" value={d.maintenance_alerts} icon={<Wrench className="size-4" />} tone={d.maintenance_alerts ? "warn" : "ok"} onClick={() => navigate("/admin/mantenimiento")} />
        <KpiCard label="Inventario bajo" value={d.low_stock} icon={<PackageMinus className="size-4" />} tone={d.low_stock ? "bad" : "ok"} sub="bobinas bajas o agotadas" onClick={() => navigate("/admin/inventario")} />
        <KpiCard label="Reservas por aprobar" value={d.pending_reservations} icon={<Boxes className="size-4" />} tone={d.pending_reservations ? "warn" : "cy"} onClick={() => navigate("/admin/reservas")} />
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardTitle hint={`Últimos 30 días · éxito ${fmtPct(k.success_rate)}${cmp ? ` (${cmp.success_rate.delta! >= 0 ? "+" : ""}${cmp.success_rate.delta} pts vs. 30 días previos)` : ""} · ${fmtGrams(k.grams_total)} de filamento`}>Actividad reciente</CardTitle>
          <div className="h-60">
            <ResponsiveContainer>
              <BarChart data={d.last_30_days.series} margin={{ left: -20, right: 4 }}>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="label" tickLine={false} axisLine={false} interval="preserveStartEnd" minTickGap={22} />
                <YAxis allowDecimals={false} tickLine={false} axisLine={false} />
                <Tooltip cursor={{ fill: "rgba(255,255,255,0.04)" }} contentStyle={{ background: "#141a22", border: "1px solid #1f2833", borderRadius: 12, fontSize: 12 }} />
                <Bar dataKey="completed" name="Completados" stackId="a" fill="#34d399" />
                <Bar dataKey="failed" name="Fallidos" stackId="a" fill="#f87171" />
                <Bar dataKey="cancelled" name="Cancelados" stackId="a" fill="#4b5868" />
                <Bar dataKey="active" name="Activos" stackId="a" fill="#2f6bff" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card>
          <CardTitle hint="Se actualiza en vivo">Imprimiendo ahora</CardTitle>
          {printing.length === 0 ? <p className="py-8 text-center text-sm text-mute">No hay impresiones en curso.</p> : (
            <div className="space-y-3">
              {printing.map((p) => (
                <div key={p.id}>
                  <div className="mb-1 flex justify-between text-xs"><span className="font-medium">{p.name}</span><span className="tabular-nums text-cy">{Math.round(p.current_job!.progress_pct)}%</span></div>
                  <ProgressBar value={p.current_job!.progress_pct} />
                  <div className="mt-0.5 truncate text-[11px] text-mute">{p.current_job!.project_name}</div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-2">
        <Card>
          <CardTitle hint="Resumen de lo más importante de los últimos 30 días" right={<Button size="sm" variant="ghost" onClick={() => navigate("/admin/estadisticas")}>Más</Button>}>Hallazgos</CardTitle>
          <InsightList items={d.last_30_days.insights} />
        </Card>
        <Card>
          <CardTitle hint="Requieren atención">Alertas</CardTitle>
          {d.alerts.length === 0 ? <p className="flex items-center justify-center gap-2 py-8 text-sm text-ok"><CheckCircle2 className="size-4" /> Todo en orden</p> : (
            <ul className="space-y-1.5">
              {d.alerts.map((a, i) => (
                <li key={i} className="flex items-start gap-2.5 rounded-xl bg-panel2 p-2.5">
                  <AlertTriangle className={clsx("mt-0.5 size-4 shrink-0", a.severity === "critical" ? "text-bad" : a.severity === "warning" ? "text-warn" : "text-cy")} />
                  <div><div className="text-sm font-medium">{a.title}</div>{a.detail && <div className="text-xs text-mute">{a.detail}</div>}</div>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </>
  );
}
