import { useState } from "react";
import { CheckCheck, ClipboardList, ListPlus, Play, Plus, Search, XCircle, Ban } from "lucide-react";
import { api } from "../../lib/api";
import { useAction, useGet } from "../../lib/hooks";
import type { Equipment, Filament, Job, User } from "../../lib/types";
import { fmtDateTime, fmtDuration, fmtGrams, label, REASON_LABEL, toInputDateTime } from "../../lib/format";
import { Button, Confirm, DataTable, DemoBadge, Empty, ErrorBox, Field, Input, Loading, Modal, PageHeader, Select, StatusBadge, Tabs, Textarea } from "../../components/ui";
import { JobEta, JobProgress, MaterialCell } from "../../components/shared";

function JobForm({ onClose }: { onClose: () => void }) {
  const { data: users } = useGet<User[]>("users", "/users");
  const { data: printers } = useGet<Equipment[]>("equipment", "/equipment", { type: "printer_3d" });
  const { data: fils } = useGet<Filament[]>("filaments", "/filaments");
  const now = new Date();
  const [f, setF] = useState({ user_id: "", project_name: "", printer_id: "", filament_id: "", grams_estimated: "50", estimated_minutes: "120", status: "pending",
    started_at: toInputDateTime(new Date(now.getTime() - 3 * 3600000)), finished_at: toInputDateTime(new Date(now.getTime() - 3600000)), grams_used: "", failure_reason: "other", notes: "" });
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => setF({ ...f, [k]: e.target.value });
  const printer = printers?.find((p) => String(p.id) === f.printer_id);
  const compatible = fils?.filter((x) => x.stock_status !== "empty" && (!printer || !printer.supported_materials.length || printer.supported_materials.includes(x.material)));
  const hist = f.status === "completed" || f.status === "failed";
  const m = useAction(() => api("/jobs", { body: {
    user_id: Number(f.user_id), project_name: f.project_name, printer_id: f.printer_id ? Number(f.printer_id) : null, filament_id: f.filament_id ? Number(f.filament_id) : null,
    grams_estimated: Number(f.grams_estimated), estimated_minutes: Number(f.estimated_minutes), status: f.status, notes: f.notes,
    ...(hist ? { started_at: new Date(f.started_at).toISOString(), finished_at: new Date(f.finished_at).toISOString(), grams_used: f.grams_used ? Number(f.grams_used) : null, failure_reason: f.status === "failed" ? f.failure_reason : null } : {}),
  } }), { invalidate: ["jobs", "equipment", "filaments", "dashboard", "stats", "alerts"], success: "Trabajo registrado", onSuccess: onClose });
  return (
    <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); m.mutate(); }}>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Usuario responsable"><Select required value={f.user_id} onChange={set("user_id")}><option value="">Seleccionar…</option>{users?.filter((u) => u.is_active).map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}</Select></Field>
        <Field label="Nombre del proyecto"><Input required minLength={2} value={f.project_name} onChange={set("project_name")} /></Field>
        <Field label="Impresora"><Select value={f.printer_id} onChange={set("printer_id")}><option value="">Sin asignar</option>{printers?.map((p) => <option key={p.id} value={p.id} disabled={p.status === "out_of_service"}>{p.name} — {label(p.status)}</option>)}</Select></Field>
        <Field label="Filamento" hint={printer ? `Compatibles con ${printer.name}` : undefined}><Select value={f.filament_id} onChange={set("filament_id")}><option value="">Sin asignar</option>{compatible?.map((x) => <option key={x.id} value={x.id}>{x.material} {x.color} — {fmtGrams(x.available_weight_g)}</option>)}</Select></Field>
        <Field label="Filamento estimado (g)"><Input type="number" required min="1" max="5000" step="0.1" value={f.grams_estimated} onChange={set("grams_estimated")} /></Field>
        <Field label="Duración estimada (min)"><Input type="number" required min="1" value={f.estimated_minutes} onChange={set("estimated_minutes")} /></Field>
        <Field label="Estado inicial" hint="Los estados «completado/fallido» sirven para registrar trabajos ya realizados"><Select value={f.status} onChange={set("status")}>
          <option value="pending">Pendiente</option><option value="queued">En cola</option><option value="printing">En proceso (iniciar ya)</option><option value="completed">Completado (histórico)</option><option value="failed">Fallido (histórico)</option></Select></Field>
      </div>
      {hist && (
        <div className="grid gap-3 rounded-xl bg-panel2 p-3 sm:grid-cols-2">
          <Field label="Inicio"><Input type="datetime-local" required max={toInputDateTime(now)} value={f.started_at} onChange={set("started_at")} /></Field>
          <Field label="Fin"><Input type="datetime-local" required min={f.started_at} max={toInputDateTime(now)} value={f.finished_at} onChange={set("finished_at")} /></Field>
          <Field label="Filamento realmente usado (g)" hint="Vacío = estimado"><Input type="number" min="0" step="0.1" value={f.grams_used} onChange={set("grams_used")} /></Field>
          {f.status === "failed" && <Field label="Causa del fallo"><Select value={f.failure_reason} onChange={set("failure_reason")}>{Object.entries(REASON_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</Select></Field>}
        </div>
      )}
      <Field label="Notas"><Textarea value={f.notes} onChange={set("notes")} /></Field>
      <div className="flex justify-end gap-2"><Button type="button" variant="ghost" onClick={onClose}>Cancelar</Button><Button type="submit" loading={m.isPending}>Registrar trabajo</Button></div>
    </form>
  );
}

type Dialog = { job: Job; action: "complete" | "fail" | "cancel" | "start" } | null;

function ActionDialog({ d, onClose }: { d: NonNullable<Dialog>; onClose: () => void }) {
  const [grams, setGrams] = useState("");
  const [reason, setReason] = useState("adhesion");
  const [force, setForce] = useState(false);
  const m = useAction(() => api(`/jobs/${d.job.id}/transition`, { body: { action: d.action, grams_used: grams ? Number(grams) : undefined, failure_reason: d.action === "fail" ? reason : undefined, ignore_reservations: force } }),
    { invalidate: ["jobs", "equipment", "filaments", "dashboard", "stats", "alerts"], success: "Trabajo actualizado", onSuccess: onClose });
  const j = d.job;
  const titles = { complete: "Completar trabajo", fail: "Marcar como fallido", cancel: "Cancelar trabajo", start: "Iniciar impresión" };
  return (
    <Modal open onClose={onClose} title={titles[d.action]}>
      <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); m.mutate(); }}>
        <p className="text-sm text-mute"><b className="text-fg">{j.project_name}</b> · {j.printer_name ?? "sin impresora"}</p>
        {d.action === "fail" && <Field label="Causa del fallo"><Select value={reason} onChange={(e) => setReason(e.target.value)}>{Object.entries(REASON_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</Select></Field>}
        {(d.action === "complete" || d.action === "fail" || (d.action === "cancel" && j.status === "printing")) && (
          <Field label="Filamento realmente usado (g)" hint={`Vacío = ${d.action === "complete" ? `estimado (${j.grams_estimated} g)` : `proporcional al avance (${Math.round(j.progress_pct)}%)`}`}><Input type="number" min="0" step="0.1" value={grams} onChange={(e) => setGrams(e.target.value)} /></Field>
        )}
        {d.action === "start" && <label className="flex items-start gap-2 text-xs text-mute"><input type="checkbox" className="mt-0.5" checked={force} onChange={(e) => setForce(e.target.checked)} /> Ignorar reservas aprobadas que se crucen (solo si el titular lo autoriza)</label>}
        {d.action === "cancel" && <p className="text-xs text-warn">Esta acción no se puede deshacer.</p>}
        <div className="flex justify-end gap-2"><Button type="button" variant="ghost" onClick={onClose}>Volver</Button><Button type="submit" variant={d.action === "cancel" || d.action === "fail" ? "danger" : "primary"} loading={m.isPending}>{titles[d.action]}</Button></div>
      </form>
    </Modal>
  );
}

function RowActions({ j, run }: { j: Job; run: (d: NonNullable<Dialog>) => void }) {
  const queue = useAction(() => api(`/jobs/${j.id}/transition`, { body: { action: "queue" } }), { invalidate: ["jobs", "equipment", "dashboard"], success: "Trabajo puesto en cola" });
  const progress = useAction((v: number) => api(`/jobs/${j.id}`, { method: "PATCH", body: { progress_pct: v } }), { invalidate: ["jobs", "equipment", "dashboard"] });
  return (
    <div className="flex flex-wrap items-center justify-end gap-1">
      {j.status === "pending" && <Button size="sm" variant="outline" disabled={!j.printer_id} title={j.printer_id ? "" : "Asigne una impresora"} loading={queue.isPending} onClick={() => queue.mutate()}><ListPlus className="size-3.5" /> En cola</Button>}
      {(j.status === "pending" || j.status === "queued") && <Button size="sm" variant="outline" onClick={() => run({ job: j, action: "start" })}><Play className="size-3.5" /> Iniciar</Button>}
      {j.status === "printing" && <>
        <select aria-label="Avance" className="rounded-lg border border-line bg-ink px-1.5 py-1 text-xs" value="" onChange={(e) => e.target.value && progress.mutate(Number(e.target.value))}><option value="">Avance…</option>{[10, 25, 50, 75, 90].map((v) => <option key={v} value={v}>{v}%</option>)}</select>
        <Button size="sm" onClick={() => run({ job: j, action: "complete" })}><CheckCheck className="size-3.5" /> Completar</Button>
        <Button size="sm" variant="danger" onClick={() => run({ job: j, action: "fail" })}><XCircle className="size-3.5" /> Falló</Button>
      </>}
      {(j.status === "pending" || j.status === "queued" || j.status === "printing") && <Button size="sm" variant="ghost" onClick={() => run({ job: j, action: "cancel" })} aria-label="Cancelar" title="Cancelar"><Ban className="size-3.5 text-bad" /></Button>}
    </div>
  );
}

export default function JobsPage() {
  const [status, setStatus] = useState("");
  const [q, setQ] = useState("");
  const [page, setPage] = useState(0);
  const [creating, setCreating] = useState(false);
  const [dlg, setDlg] = useState<Dialog>(null);
  const size = 20;
  const { data, isLoading, error } = useGet<{ items: Job[]; total: number }>("jobs", "/jobs", { status, q, limit: size, offset: page * size });
  return (
    <>
      <PageHeader title="Trabajos de impresión" subtitle="Registro, cola e historial de todos los trabajos." actions={<Button onClick={() => setCreating(true)}><Plus className="size-4" /> Registrar trabajo</Button>} />
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <Tabs value={status} onChange={(v) => { setStatus(v); setPage(0); }} items={[{ value: "", label: "Todos" }, ...["pending", "queued", "printing", "completed", "failed", "cancelled"].map((s) => ({ value: s, label: label(s) }))]} />
        <div className="relative min-w-52 flex-1"><Search className="pointer-events-none absolute left-3 top-2.5 size-4 text-mute" /><Input className="pl-9" placeholder="Buscar proyecto o usuario" value={q} onChange={(e) => { setQ(e.target.value); setPage(0); }} /></div>
      </div>
      <ErrorBox error={error} />
      {isLoading ? <Loading /> : !data?.items.length ? <Empty icon={<ClipboardList className="size-8" />} title="No hay trabajos con estos filtros" /> : (
        <>
          <DataTable head={["#", "Proyecto", "Usuario", "Impresora", "Material", "Estado", "Avance", "Gramos", "Duración", "Inicio / fin", ""]}>
            {data.items.map((j) => (
              <tr key={j.id}>
                <td className="text-xs text-mute">{j.id}</td>
                <td className="max-w-48 truncate font-medium" title={j.project_name}>{j.project_name} {j.is_demo && <DemoBadge />}{j.queue_position && <span className="ml-1 text-[11px] text-cy">pos. {j.queue_position}</span>}</td>
                <td className="text-xs">{j.user_name}</td><td className="text-xs">{j.printer_name ?? <span className="text-mute">—</span>}</td><td><MaterialCell j={j} /></td>
                <td><StatusBadge status={j.status} />{j.failure_reason && <div className="mt-0.5 text-[11px] text-mute">{REASON_LABEL[j.failure_reason]}</div>}</td>
                <td><JobProgress j={j} /></td><td className="text-xs tabular-nums">{j.grams_used ? fmtGrams(j.grams_used) : `~${fmtGrams(j.grams_estimated)}`}</td>
                <td className="text-xs">{fmtDuration(j.duration_min ?? j.estimated_minutes)}</td>
                <td className="text-xs">{j.started_at ? fmtDateTime(j.started_at) : "—"}<div className="text-mute"><JobEta j={j} /></div></td>
                <td><RowActions j={j} run={setDlg} /></td>
              </tr>
            ))}
          </DataTable>
          <div className="mt-3 flex items-center justify-between text-xs text-mute">
            <span>{data.total} trabajos · página {page + 1} de {Math.max(1, Math.ceil(data.total / size))}</span>
            <div className="flex gap-2"><Button size="sm" variant="outline" disabled={page === 0} onClick={() => setPage(page - 1)}>Anterior</Button><Button size="sm" variant="outline" disabled={(page + 1) * size >= data.total} onClick={() => setPage(page + 1)}>Siguiente</Button></div>
          </div>
        </>
      )}
      <Modal open={creating} onClose={() => setCreating(false)} title="Registrar trabajo" wide><JobForm onClose={() => setCreating(false)} /></Modal>
      {dlg && (dlg.action === "cancel" && dlg.job.status !== "printing" ? (
        <CancelSimple job={dlg.job} onClose={() => setDlg(null)} />
      ) : <ActionDialog d={dlg} onClose={() => setDlg(null)} />)}
    </>
  );
}

function CancelSimple({ job, onClose }: { job: Job; onClose: () => void }) {
  const m = useAction(() => api(`/jobs/${job.id}/transition`, { body: { action: "cancel" } }), { invalidate: ["jobs", "equipment", "dashboard", "stats"], success: "Trabajo cancelado", onSuccess: onClose });
  return <Confirm open danger title="Cancelar trabajo" text={`¿Cancelar «${job.project_name}»? No se puede deshacer.`} confirmLabel="Cancelar trabajo" loading={m.isPending} onClose={onClose} onConfirm={() => m.mutate()} />;
}
