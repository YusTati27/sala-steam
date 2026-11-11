import { useState } from "react";
import { CheckCheck, Play, Plus, Wrench } from "lucide-react";
import { api } from "../../lib/api";
import { useAction, useGet } from "../../lib/hooks";
import type { Attention, Equipment, Maintenance } from "../../lib/types";
import { fmtDate, label, toInputDate } from "../../lib/format";
import { Badge, Button, Card, CardTitle, DataTable, DemoBadge, Empty, ErrorBox, Field, Input, Loading, Modal, PageHeader, Select, StatusBadge, Tabs, Textarea } from "../../components/ui";

function MaintForm({ equipment, preset, onClose }: { equipment: Equipment[]; preset?: number; onClose: () => void }) {
  const [f, setF] = useState({ equipment_id: String(preset ?? equipment[0]?.id ?? ""), type: "preventive", status: "scheduled", description: "", scheduled_for: toInputDate(new Date(Date.now() + 7 * 86400000)), performed_at: toInputDate(new Date()), next_due_at: "", cost: "" });
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => setF({ ...f, [k]: e.target.value });
  const m = useAction(() => api("/maintenance", { body: {
    equipment_id: Number(f.equipment_id), type: f.type, status: f.status, description: f.description,
    scheduled_for: f.status === "scheduled" ? f.scheduled_for : null, performed_at: f.status === "scheduled" ? null : f.performed_at,
    next_due_at: f.status === "done" && f.next_due_at ? f.next_due_at : null, cost: f.cost ? Number(f.cost) : null,
  } }), { invalidate: ["maintenance", "equipment", "dashboard", "alerts"], success: "Mantenimiento registrado", onSuccess: onClose });
  return (
    <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); m.mutate(); }}>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Equipo"><Select required value={f.equipment_id} onChange={set("equipment_id")}>{equipment.map((e) => <option key={e.id} value={e.id}>{e.name} ({e.code})</option>)}</Select></Field>
        <Field label="Tipo"><Select value={f.type} onChange={set("type")}><option value="preventive">Preventivo (revisión)</option><option value="corrective">Correctivo (reparación)</option></Select></Field>
        <Field label="¿Qué se registra?"><Select value={f.status} onChange={set("status")}><option value="scheduled">Programar revisión futura</option><option value="in_progress">Iniciar ahora (equipo en mantenimiento)</option><option value="done">Ya realizado</option></Select></Field>
        {f.status === "scheduled" ? <Field label="Fecha programada"><Input type="date" required min={toInputDate(new Date())} value={f.scheduled_for} onChange={set("scheduled_for")} /></Field>
          : <Field label="Fecha de ejecución"><Input type="date" required max={toInputDate(new Date())} value={f.performed_at} onChange={set("performed_at")} /></Field>}
        {f.status === "done" && <Field label="Próxima revisión" hint="Vacío: +90 días si es preventivo"><Input type="date" min={f.performed_at} value={f.next_due_at} onChange={set("next_due_at")} /></Field>}
        <Field label="Costo (opcional)"><Input type="number" min="0" step="0.01" value={f.cost} onChange={set("cost")} /></Field>
      </div>
      <Field label="Descripción del trabajo"><Textarea required minLength={3} value={f.description} onChange={set("description")} /></Field>
      <div className="flex justify-end gap-2"><Button type="button" variant="ghost" onClick={onClose}>Cancelar</Button><Button type="submit" loading={m.isPending}>Guardar</Button></div>
    </form>
  );
}

function Finish({ m, onClose }: { m: Maintenance; onClose: () => void }) {
  const [next, setNext] = useState("");
  const [cost, setCost] = useState(m.cost?.toString() ?? "");
  const a = useAction(() => api(`/maintenance/${m.id}`, { method: "PATCH", body: { status: "done", performed_at: toInputDate(new Date()), next_due_at: next || null, cost: cost ? Number(cost) : null } }),
    { invalidate: ["maintenance", "equipment", "dashboard", "alerts"], success: "Mantenimiento cerrado; el equipo vuelve a estar disponible", onSuccess: onClose });
  return (
    <Modal open onClose={onClose} title="Finalizar mantenimiento">
      <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); a.mutate(); }}>
        <p className="text-sm text-mute">{m.equipment_name}: {m.description}</p>
        <Field label="Próxima revisión" hint="Vacío: +90 días si es preventivo"><Input type="date" min={toInputDate(new Date())} value={next} onChange={(e) => setNext(e.target.value)} /></Field>
        <Field label="Costo"><Input type="number" min="0" step="0.01" value={cost} onChange={(e) => setCost(e.target.value)} /></Field>
        <div className="flex justify-end gap-2"><Button type="button" variant="ghost" onClick={onClose}>Volver</Button><Button type="submit" loading={a.isPending}>Finalizar</Button></div>
      </form>
    </Modal>
  );
}

export default function MaintenancePage() {
  const [tab, setTab] = useState("");
  const { data: att } = useGet<Attention[]>("maintenance", "/maintenance/attention");
  const { data, isLoading, error } = useGet<Maintenance[]>("maintenance", "/maintenance", { status: tab });
  const { data: eq } = useGet<Equipment[]>("equipment", "/equipment");
  const [creating, setCreating] = useState<number | true | null>(null);
  const [finish, setFinish] = useState<Maintenance | null>(null);
  const start = useAction((id: number) => api(`/maintenance/${id}`, { method: "PATCH", body: { status: "in_progress" } }), { invalidate: ["maintenance", "equipment", "dashboard", "alerts"], success: "Mantenimiento iniciado: el equipo queda fuera de la cola" });
  return (
    <>
      <PageHeader title="Mantenimiento" subtitle="Preventivo, correctivo y programación de revisiones." actions={<Button onClick={() => setCreating(true)} disabled={!eq?.length}><Plus className="size-4" /> Registrar / programar</Button>} />
      <Card className="mb-5">
        <CardTitle hint="Vencidos, próximos (≤ 14 días) o fuera de servicio">Equipos que requieren atención</CardTitle>
        {!att?.length ? <p className="py-4 text-center text-sm text-ok">Ningún equipo requiere atención por ahora.</p> : (
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
            {att.map((a) => (
              <div key={a.equipment_id} className="flex items-center justify-between gap-2 rounded-xl bg-panel2 p-3">
                <div><div className="text-sm font-medium">{a.name}</div><div className="text-[11px] text-mute">{a.code} · {a.reason === "fuera_de_servicio" ? "Fuera de servicio" : a.reason === "vencido" ? `Venció hace ${-a.days_left!} días` : `En ${a.days_left} días (${fmtDate(a.next_maintenance_at)})`}</div></div>
                <Button size="sm" variant="outline" onClick={() => setCreating(a.equipment_id)}>Programar</Button>
              </div>
            ))}
          </div>
        )}
      </Card>
      <div className="mb-3"><Tabs value={tab} onChange={setTab} items={[{ value: "", label: "Historial completo" }, { value: "scheduled", label: "Programados" }, { value: "in_progress", label: "En curso" }, { value: "done", label: "Realizados" }]} /></div>
      <ErrorBox error={error} />
      {isLoading ? <Loading /> : !data?.length ? <Empty icon={<Wrench className="size-8" />} title="Sin registros de mantenimiento" /> : (
        <DataTable head={["Equipo", "Tipo", "Estado", "Descripción", "Programado", "Realizado", "Próxima", "Costo", ""]}>
          {data.map((m) => (
            <tr key={m.id}>
              <td className="font-medium">{m.equipment_name} {m.is_demo && <DemoBadge />}<div className="font-mono text-[11px] text-mute">{m.equipment_code}</div></td>
              <td><Badge tone={m.type === "preventive" ? "cy" : "warn"}>{label(m.type)}</Badge></td><td><StatusBadge status={m.status} /></td>
              <td className="max-w-64 truncate text-xs" title={m.description}>{m.description}</td><td className="text-xs">{fmtDate(m.scheduled_for)}</td><td className="text-xs">{fmtDate(m.performed_at)}</td><td className="text-xs">{fmtDate(m.next_due_at)}</td>
              <td className="text-xs tabular-nums">{m.cost !== null ? m.cost.toLocaleString("es-CO") : "—"}</td>
              <td className="whitespace-nowrap text-right">
                {m.status === "scheduled" && <Button size="sm" variant="outline" loading={start.isPending && start.variables === m.id} onClick={() => start.mutate(m.id)}><Play className="size-3.5" /> Iniciar</Button>}
                {m.status === "in_progress" && <Button size="sm" onClick={() => setFinish(m)}><CheckCheck className="size-3.5" /> Finalizar</Button>}
              </td>
            </tr>
          ))}
        </DataTable>
      )}
      <Modal open={creating !== null} onClose={() => setCreating(null)} title="Registrar o programar mantenimiento" wide>{creating !== null && eq && <MaintForm equipment={eq} preset={typeof creating === "number" ? creating : undefined} onClose={() => setCreating(null)} />}</Modal>
      {finish && <Finish m={finish} onClose={() => setFinish(null)} />}
    </>
  );
}
