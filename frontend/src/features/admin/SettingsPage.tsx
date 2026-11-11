import { useState } from "react";
import { FlaskConical, RefreshCw, ShieldCheck, Trash2 } from "lucide-react";
import { api } from "../../lib/api";
import { useAction, useConfig, useGet } from "../../lib/hooks";
import { Badge, Button, Card, CardTitle, Confirm, Field, Input, Loading, PageHeader, Select } from "../../components/ui";

interface SimStatus { records: Record<string, number> }

export default function SettingsPage() {
  const { data: cfg, isLoading } = useConfig();
  const { data: sim } = useGet<SimStatus>("config", "/simulator/status");
  const [hours, setHours] = useState<string>("");
  const [months, setMonths] = useState("6");
  const [dlg, setDlg] = useState<"real" | "clear" | "regen" | null>(null);
  const inv = ["config", "equipment", "filaments", "jobs", "reservations", "maintenance", "users", "stats", "dashboard", "alerts"];
  const setMode = useAction((mode: "demo" | "real") => api("/config/mode", { body: { mode } }), { invalidate: inv, success: "Modo actualizado", onSuccess: () => setDlg(null) });
  const regen = useAction(() => api("/simulator/regenerate", { body: { months: Number(months) } }), { invalidate: inv, success: "Datos de simulación regenerados", onSuccess: () => setDlg(null) });
  const clear = useAction(() => api("/simulator/clear", { method: "POST" }), { invalidate: inv, success: "Datos de simulación eliminados", onSuccess: () => setDlg(null) });
  const save = useAction(() => api("/config/settings", { body: { open_hours_per_day: Number(hours || cfg?.open_hours_per_day) } }), { invalidate: ["config", "stats"], success: "Configuración guardada" });
  if (isLoading || !cfg) return <Loading />;
  return (
    <>
      <PageHeader title="Configuración" subtitle="Modo de datos, simulador y parámetros de la analítica." />
      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <CardTitle hint="El sistema trabaja con datos de demostración o con datos reales, nunca mezclados">Modo de datos</CardTitle>
          <div className="mb-4 flex items-center gap-3">
            <div className="grid size-11 place-items-center rounded-xl bg-warn/12 text-warn"><FlaskConical className="size-6" /></div>
            <div><div className="font-semibold">{cfg.demo ? "Simulador activo" : "Modo real"}</div><div className="text-xs text-mute">{cfg.demo ? "Todos los datos son inventados para demostración." : "Solo se muestran datos que registres tú."}</div></div>
          </div>
          {cfg.demo ? <Button variant="outline" onClick={() => setDlg("real")}><ShieldCheck className="size-4" /> Cambiar a modo real</Button>
            : <Button loading={setMode.isPending} onClick={() => setMode.mutate("demo")}><FlaskConical className="size-4" /> Activar simulador</Button>}
          <p className="mt-3 text-xs text-mute">Al pasar a modo real los datos de simulación se ocultan (no se borran). Los registros que crees en cada modo quedan en ese modo.</p>
        </Card>

        <Card>
          <CardTitle hint="Generación de datos inventados (equipos, usuarios, trabajos, consumos, reservas y mantenimientos)">Simulador</CardTitle>
          {sim && <div className="mb-3 flex flex-wrap gap-1.5">{Object.entries(sim.records).map(([k, v]) => <Badge key={k} tone="mute">{k}: {v}</Badge>)}</div>}
          <div className="flex flex-wrap items-end gap-3">
            <Field label="Historial a generar"><Select value={months} onChange={(e) => setMonths(e.target.value)}>{[3, 6, 9, 12].map((m) => <option key={m} value={m}>{m} meses</option>)}</Select></Field>
            <Button variant="outline" onClick={() => setDlg("regen")}><RefreshCw className="size-4" /> Regenerar</Button>
            <Button variant="danger" onClick={() => setDlg("clear")}><Trash2 className="size-4" /> Borrar datos demo</Button>
          </div>
          <p className="mt-3 text-xs text-mute">En modo simulador las impresiones en curso avanzan solas, se completan y arrancan las siguientes de la cola para que veas el sistema “vivo”.</p>
        </Card>

        <Card>
          <CardTitle hint="Se usa para calcular el porcentaje de utilización de cada impresora">Parámetros de analítica</CardTitle>
          <form className="flex items-end gap-3" onSubmit={(e) => { e.preventDefault(); save.mutate(); }}>
            <Field label="Horas operativas por día"><Input type="number" min="1" max="24" step="0.5" value={hours || cfg.open_hours_per_day} onChange={(e) => setHours(e.target.value)} /></Field>
            <Button type="submit" loading={save.isPending}>Guardar</Button>
          </form>
        </Card>

        <Card>
          <CardTitle hint="Cómo conectar impresoras reales">Integración de hardware</CardTitle>
          <p className="text-sm text-mute">Hoy el avance se registra desde el panel de Trabajos. La arquitectura incluye un adaptador (<code>PrinterAdapter</code>) y un campo «endpoint» por equipo para integrar OctoPrint o Klipper/Moonraker. Requiere red local hacia cada impresora y una API key por equipo; ver <code>docs/INTEGRACION_HARDWARE.md</code>.</p>
        </Card>
      </div>
      <Confirm open={dlg === "real"} title="Cambiar a modo real" text="Dejarás de ver los datos de simulación. Podrás volver a activarlos cuando quieras." confirmLabel="Cambiar a modo real" loading={setMode.isPending} onClose={() => setDlg(null)} onConfirm={() => setMode.mutate("real")} />
      <Confirm open={dlg === "regen"} title="Regenerar simulación" text="Se reemplazarán todos los datos de demostración actuales por un conjunto nuevo. Los datos reales no se tocan." loading={regen.isPending} onClose={() => setDlg(null)} onConfirm={() => regen.mutate()} />
      <Confirm open={dlg === "clear"} danger title="Borrar datos de simulación" text="Se eliminarán de forma permanente todos los datos de demostración. Los datos reales no se tocan." confirmLabel="Borrar" loading={clear.isPending} onClose={() => setDlg(null)} onConfirm={() => clear.mutate()} />
    </>
  );
}
