import { useMemo, useState } from "react";
import { CalendarPlus, Printer, Search, X } from "lucide-react";
import clsx from "clsx";
import { api } from "../../lib/api";
import { useAction, useGet } from "../../lib/hooks";
import type { Equipment, Filament, Job, MaterialSummary, Reservation, Slot } from "../../lib/types";
import { fmtDateTime, fmtDuration, fmtGrams, fmtNum, fmtTime, label, REASON_LABEL, toInputDate } from "../../lib/format";
import { Badge, Button, Card, CardTitle, DataTable, Empty, ErrorBox, Field, Input, Loading, Modal, PageHeader, Select, StatusBadge, Tabs, Textarea } from "../../components/ui";
import { JobEta, JobProgress, MaterialCell, PrinterCard, StockBar, Swatch, matColor } from "../../components/shared";

/* ---------- A. Disponibilidad de impresoras ---------- */
export function AvailabilityPage() {
  const { data, isLoading, error } = useGet<Equipment[]>("equipment", "/equipment", { type: "printer_3d" });
  const { data: mats } = useGet<MaterialSummary[]>("filaments", "/filaments/summary");
  const { data: mine } = useGet<Job[]>("jobs", "/jobs/mine");
  const counts = useMemo(() => {
    const c = { available: 0, busy: 0, maintenance: 0, out_of_service: 0 };
    data?.forEach((p) => (c[p.status] += 1));
    return c;
  }, [data]);
  return (
    <>
      <PageHeader title="Disponibilidad de impresoras" subtitle="Estado en tiempo real de las impresoras 3D de la sala." />
      <ErrorBox error={error} />
      {isLoading ? <Loading /> : (
        <>
          <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {([["available", "Disponibles", "text-ok"], ["busy", "Ocupadas", "text-[#7aa2ff]"], ["maintenance", "Mantenimiento", "text-warn"], ["out_of_service", "Fuera de servicio", "text-bad"]] as const).map(([k, l, c]) => (
              <Card key={k} className="!p-3"><div className="text-xs text-mute">{l}</div><div className={clsx("text-2xl font-semibold tabular-nums", c)}>{counts[k]}</div></Card>
            ))}
          </div>
          {mine && mine.length > 0 && (
            <Card className="mb-5">
              <CardTitle hint="Tus trabajos activos">Mis impresiones en curso</CardTitle>
              <div className="space-y-2">
                {mine.slice(0, 4).map((j) => (
                  <div key={j.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-panel2 p-3">
                    <div><div className="text-sm font-medium">{j.project_name}</div><div className="text-xs text-mute">{j.printer_name ?? "Sin impresora asignada"} · {j.queue_position ? `posición ${j.queue_position}` : ""}</div></div>
                    <div className="flex items-center gap-4"><StatusBadge status={j.status} /><JobProgress j={j} /><JobEta j={j} /></div>
                  </div>
                ))}
              </div>
            </Card>
          )}
          {data?.length === 0 ? <Empty icon={<Printer className="size-8" />} title="Aún no hay impresoras registradas" text="El administrador debe registrar los equipos de la sala." /> : (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{data?.map((p) => <PrinterCard key={p.id} p={p} />)}</div>
          )}
          {mats && mats.length > 0 && (
            <div className="mt-6">
              <h2 className="mb-3 text-sm font-semibold text-mute">Materiales disponibles</h2>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {mats.map((m) => (
                  <Card key={m.material} className="!p-3">
                    <div className="flex items-center justify-between"><span className="font-semibold" style={{ color: matColor(m.material) }}>{m.material}</span><StatusBadge status={m.status} /></div>
                    <div className="mt-1 text-lg font-semibold tabular-nums">{fmtGrams(m.available_g)}</div>
                    <div className="text-[11px] text-mute">{m.colors.length} colores</div>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </>
  );
}

/* ---------- B. Inventario de filamentos ---------- */
export function FilamentsPage() {
  const { data, isLoading, error } = useGet<Filament[]>("filaments", "/filaments");
  const { data: summary } = useGet<MaterialSummary[]>("filaments", "/filaments/summary");
  const [mat, setMat] = useState("all");
  const rows = (data ?? []).filter((f) => mat === "all" || f.material === mat);
  return (
    <>
      <PageHeader title="Inventario de filamentos" subtitle="Material y color disponibles para tus impresiones." />
      <ErrorBox error={error} />
      <div className="mb-4"><Tabs value={mat} onChange={setMat} items={[{ value: "all", label: "Todos", count: data?.length }, ...(summary ?? []).map((s) => ({ value: s.material, label: s.material }))]} /></div>
      {isLoading ? <Loading /> : rows.length === 0 ? <Empty title="No hay filamentos registrados" /> : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {rows.map((f) => (
            <Card key={f.id} className="!p-4">
              <div className="mb-2 flex items-center justify-between">
                <div className="flex items-center gap-2"><Swatch hex={f.color_hex} size={22} /><div><div className="text-sm font-semibold">{f.color}</div><div className="text-[11px] text-mute">{f.brand || "—"}</div></div></div>
                <span className="rounded-md px-1.5 py-0.5 text-[11px] font-semibold" style={{ color: matColor(f.material), background: matColor(f.material) + "1f" }}>{f.material}</span>
              </div>
              <StockBar f={f} />
              <div className="mt-2 flex items-center justify-between"><span className="text-sm font-medium tabular-nums">{fmtGrams(f.available_weight_g)}</span><StatusBadge status={f.stock_status} /></div>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}

/* ---------- C. Cola de impresión ---------- */
export function QueuePage() {
  const { data, isLoading, error } = useGet<Job[]>("jobs", "/jobs/queue");
  const printing = data?.filter((j) => j.status === "printing") ?? [];
  const waiting = data?.filter((j) => j.status !== "printing") ?? [];
  return (
    <>
      <PageHeader title="Cola de impresión" subtitle="Trabajos en proceso y en espera. Tus trabajos aparecen marcados con ★." />
      <ErrorBox error={error} />
      {isLoading ? <Loading /> : (
        <div className="space-y-6">
          <section>
            <h2 className="mb-2 text-sm font-semibold text-mute">En proceso ({printing.length})</h2>
            {printing.length === 0 ? <Empty title="No hay impresiones en curso" /> : (
              <DataTable head={["Proyecto", "Impresora", "Material", "Progreso", "Termina"]}>
                {printing.map((j) => (
                  <tr key={j.id} className={clsx(j.is_mine && "bg-cy/5")}>
                    <td className="font-medium">{j.is_mine && <span className="text-cy">★ </span>}{j.project_name}</td>
                    <td>{j.printer_name}</td><td><MaterialCell j={j} /></td><td><JobProgress j={j} /></td><td><JobEta j={j} /></td>
                  </tr>
                ))}
              </DataTable>
            )}
          </section>
          <section>
            <h2 className="mb-2 text-sm font-semibold text-mute">En espera ({waiting.length})</h2>
            {waiting.length === 0 ? <Empty title="La cola está vacía" text="Cuando el administrador registre trabajos aparecerán aquí." /> : (
              <DataTable head={["Pos.", "Proyecto", "Impresora", "Estado", "Duración est.", "Fin estimado"]}>
                {waiting.map((j) => (
                  <tr key={j.id} className={clsx(j.is_mine && "bg-cy/5")}>
                    <td className="tabular-nums text-cy">{j.queue_position ?? "—"}</td>
                    <td className="font-medium">{j.is_mine && <span className="text-cy">★ </span>}{j.project_name}</td>
                    <td>{j.printer_name ?? <span className="text-mute">Por asignar</span>}</td>
                    <td><StatusBadge status={j.status} /></td><td className="text-xs">{fmtDuration(j.estimated_minutes)}</td><td><JobEta j={j} /></td>
                  </tr>
                ))}
              </DataTable>
            )}
          </section>
        </div>
      )}
    </>
  );
}

/* ---------- D. Reservas ---------- */
function ReservationForm({ printers, onClose }: { printers: Equipment[]; onClose: () => void }) {
  const tomorrow = new Date(Date.now() + 86400000);
  const [printerId, setPrinterId] = useState<number>(printers.find((p) => p.status !== "out_of_service")?.id ?? printers[0]?.id ?? 0);
  const [day, setDay] = useState(toInputDate(tomorrow));
  const [start, setStart] = useState("10:00");
  const [hours, setHours] = useState("2");
  const [purpose, setPurpose] = useState("");
  const { data: slots } = useGet<Slot[]>("reservations", "/reservations/availability", { printer_id: printerId, day }, [], !!printerId);
  const s = new Date(`${day}T${start}`);
  const e = new Date(s.getTime() + Number(hours) * 3600000);
  const m = useAction(() => api("/reservations", { body: { printer_id: printerId, start_at: s.toISOString(), end_at: e.toISOString(), purpose } }),
    { invalidate: ["reservations", "dashboard"], success: "Solicitud enviada. Queda pendiente de aprobación.", onSuccess: onClose });
  return (
    <form className="space-y-3" onSubmit={(ev) => { ev.preventDefault(); m.mutate(); }}>
      <Field label="Impresora">
        <Select value={printerId} onChange={(ev) => setPrinterId(Number(ev.target.value))}>
          {printers.map((p) => <option key={p.id} value={p.id} disabled={p.status === "out_of_service" || p.status === "maintenance"}>{p.name} — {label(p.status)}</option>)}
        </Select>
      </Field>
      <div className="grid grid-cols-3 gap-3">
        <Field label="Fecha"><Input type="date" required min={toInputDate(new Date())} value={day} onChange={(ev) => setDay(ev.target.value)} /></Field>
        <Field label="Hora inicio"><Input type="time" required step={900} value={start} onChange={(ev) => setStart(ev.target.value)} /></Field>
        <Field label="Duración"><Select value={hours} onChange={(ev) => setHours(ev.target.value)}>{["0.5", "1", "1.5", "2", "3", "4", "6", "8"].map((h) => <option key={h} value={h}>{h} h</option>)}</Select></Field>
      </div>
      <div className="rounded-xl bg-panel2 p-3 text-xs">
        <div className="mb-1 font-medium text-mute">Franjas ocupadas ese día</div>
        {slots?.length ? slots.map((sl, i) => <div key={i} className="flex justify-between"><span>{fmtTime(sl.start_at)} – {fmtTime(sl.end_at)}</span><span className="text-mute">{sl.is_mine ? "Tuya · " : ""}{label(sl.status)}</span></div>) : <span className="text-ok">Sin reservas: todo el día libre.</span>}
      </div>
      <Field label="Motivo (opcional)"><Textarea maxLength={255} value={purpose} onChange={(ev) => setPurpose(ev.target.value)} placeholder="Ej. Prototipo del proyecto final" /></Field>
      <p className="text-xs text-mute">Reserva: {fmtDateTime(s.toISOString())} → {fmtTime(e.toISOString())}</p>
      <div className="flex justify-end gap-2 pt-1"><Button type="button" variant="ghost" onClick={onClose}>Cancelar</Button><Button type="submit" loading={m.isPending}>Solicitar reserva</Button></div>
    </form>
  );
}

export function ReservationsPage() {
  const { data, isLoading, error } = useGet<Reservation[]>("reservations", "/reservations/mine");
  const { data: printers } = useGet<Equipment[]>("equipment", "/equipment", { type: "printer_3d" });
  const [open, setOpen] = useState(false);
  const cancel = useAction((id: number) => api(`/reservations/${id}/cancel`, { method: "POST" }), { invalidate: ["reservations", "dashboard"], success: "Reserva cancelada" });
  const now = Date.now();
  return (
    <>
      <PageHeader title="Mis reservas" subtitle="Solicita turnos en las impresoras. El administrador debe aprobarlos." actions={<Button onClick={() => setOpen(true)} disabled={!printers?.length}><CalendarPlus className="size-4" /> Nueva reserva</Button>} />
      <ErrorBox error={error} />
      {isLoading ? <Loading /> : !data?.length ? <Empty icon={<CalendarPlus className="size-8" />} title="Aún no tienes reservas" text="Pulsa «Nueva reserva» para solicitar un turno." /> : (
        <DataTable head={["Impresora", "Inicio", "Fin", "Estado", "Motivo", "Nota del admin", ""]}>
          {data.map((r) => (
            <tr key={r.id}>
              <td className="font-medium">{r.printer_name}</td><td className="text-xs">{fmtDateTime(r.start_at)}</td><td className="text-xs">{fmtDateTime(r.end_at)}</td>
              <td><StatusBadge status={r.status} /></td><td className="max-w-48 truncate text-xs text-mute">{r.purpose || "—"}</td><td className="max-w-48 truncate text-xs text-mute">{r.admin_note || "—"}</td>
              <td>{(r.status === "pending" || r.status === "approved") && new Date(r.start_at).getTime() > now && (
                <Button size="sm" variant="danger" loading={cancel.isPending && cancel.variables === r.id} onClick={() => cancel.mutate(r.id)}><X className="size-3.5" /> Cancelar</Button>)}</td>
            </tr>
          ))}
        </DataTable>
      )}
      <Modal open={open} onClose={() => setOpen(false)} title="Solicitar reserva" wide>{printers && <ReservationForm printers={printers} onClose={() => setOpen(false)} />}</Modal>
    </>
  );
}

/* ---------- E. Historial personal ---------- */
export function HistoryPage() {
  const { data, isLoading, error } = useGet<Job[]>("jobs", "/jobs/mine", { history: true });
  const [q, setQ] = useState("");
  const [st, setSt] = useState("all");
  const rows = (data ?? []).filter((j) => (st === "all" || j.status === st) && j.project_name.toLowerCase().includes(q.toLowerCase()));
  const done = data?.filter((j) => j.status === "completed" || j.status === "failed") ?? [];
  const ok = done.filter((j) => j.status === "completed").length;
  return (
    <>
      <PageHeader title="Mi historial" subtitle="Impresiones que has realizado en la sala." />
      <ErrorBox error={error} />
      {data && data.length > 0 && (
        <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Card className="!p-3"><div className="text-xs text-mute">Trabajos</div><div className="text-2xl font-semibold tabular-nums">{data.length}</div></Card>
          <Card className="!p-3"><div className="text-xs text-mute">Exitosos</div><div className="text-2xl font-semibold tabular-nums text-ok">{ok}{done.length ? <span className="ml-1 text-xs text-mute">({Math.round((100 * ok) / done.length)}%)</span> : null}</div></Card>
          <Card className="!p-3"><div className="text-xs text-mute">Filamento usado</div><div className="text-2xl font-semibold tabular-nums">{fmtGrams(data.reduce((s, j) => s + j.grams_used, 0))}</div></Card>
          <Card className="!p-3"><div className="text-xs text-mute">Tiempo de impresión</div><div className="text-2xl font-semibold tabular-nums">{fmtNum(data.reduce((s, j) => s + (j.duration_min ?? 0), 0) / 60, 1)} h</div></Card>
        </div>
      )}
      <div className="mb-3 flex flex-wrap gap-2">
        <div className="relative min-w-48 flex-1"><Search className="pointer-events-none absolute left-3 top-2.5 size-4 text-mute" /><Input className="pl-9" placeholder="Buscar proyecto" value={q} onChange={(e) => setQ(e.target.value)} /></div>
        <Select className="!w-auto" value={st} onChange={(e) => setSt(e.target.value)}><option value="all">Todos los estados</option>{["completed", "failed", "cancelled"].map((s) => <option key={s} value={s}>{label(s)}</option>)}</Select>
      </div>
      {isLoading ? <Loading /> : rows.length === 0 ? <Empty title="Sin trabajos para mostrar" /> : (
        <DataTable head={["Fecha", "Proyecto", "Impresora", "Material", "Duración", "Filamento", "Resultado"]}>
          {rows.map((j) => (
            <tr key={j.id}>
              <td className="text-xs">{fmtDateTime(j.started_at ?? j.created_at)}</td><td className="font-medium">{j.project_name}</td><td>{j.printer_name ?? "—"}</td>
              <td><MaterialCell j={j} /></td><td className="text-xs">{fmtDuration(j.duration_min)}</td><td className="text-xs tabular-nums">{fmtGrams(j.grams_used)}</td>
              <td><StatusBadge status={j.status} />{j.failure_reason && <div className="mt-0.5 text-[11px] text-mute">{REASON_LABEL[j.failure_reason] ?? j.failure_reason}</div>}</td>
            </tr>
          ))}
        </DataTable>
      )}
      <Badge tone="mute" className="mt-3">Se muestran hasta 300 trabajos recientes</Badge>
    </>
  );
}
