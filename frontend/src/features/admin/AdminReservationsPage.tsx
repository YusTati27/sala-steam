import { useState } from "react";
import { Check, CalendarClock, X, CheckCheck } from "lucide-react";
import { api } from "../../lib/api";
import { useAction, useGet } from "../../lib/hooks";
import type { Reservation } from "../../lib/types";
import { fmtDateTime } from "../../lib/format";
import { Button, DataTable, DemoBadge, Empty, ErrorBox, Input, Loading, Modal, PageHeader, StatusBadge, Tabs } from "../../components/ui";

function Decision({ r, decision, onClose }: { r: Reservation; decision: "approve" | "reject" | "complete"; onClose: () => void }) {
  const [note, setNote] = useState("");
  const m = useAction(() => api(`/reservations/${r.id}/decision`, { body: { decision, admin_note: note } }), { invalidate: ["reservations", "dashboard", "alerts"], success: "Reserva actualizada", onSuccess: onClose });
  const t = { approve: "Aprobar reserva", reject: "Rechazar reserva", complete: "Marcar como completada" }[decision];
  return (
    <Modal open onClose={onClose} title={t}>
      <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); m.mutate(); }}>
        <p className="text-sm text-mute"><b className="text-fg">{r.user_name}</b> · {r.printer_name}<br />{fmtDateTime(r.start_at)} → {fmtDateTime(r.end_at)}</p>
        <label className="block text-xs text-mute">Nota para el usuario (opcional)<Input className="mt-1" maxLength={255} value={note} onChange={(e) => setNote(e.target.value)} /></label>
        <div className="flex justify-end gap-2"><Button type="button" variant="ghost" onClick={onClose}>Volver</Button><Button type="submit" variant={decision === "reject" ? "danger" : "primary"} loading={m.isPending}>{t}</Button></div>
      </form>
    </Modal>
  );
}

export default function AdminReservationsPage() {
  const [status, setStatus] = useState("pending");
  const { data, isLoading, error } = useGet<Reservation[]>("reservations", "/reservations", { status });
  const [dlg, setDlg] = useState<{ r: Reservation; d: "approve" | "reject" | "complete" } | null>(null);
  const cancel = useAction((id: number) => api(`/reservations/${id}/cancel`, { method: "POST" }), { invalidate: ["reservations", "dashboard"], success: "Reserva cancelada" });
  return (
    <>
      <PageHeader title="Reservas" subtitle="Aprueba, rechaza o gestiona las solicitudes de los usuarios." />
      <div className="mb-4"><Tabs value={status} onChange={setStatus} items={[["pending", "Pendientes"], ["approved", "Aprobadas"], ["completed", "Completadas"], ["rejected", "Rechazadas"], ["cancelled", "Canceladas"]].map(([value, l]) => ({ value, label: l }))} /></div>
      <ErrorBox error={error} />
      {isLoading ? <Loading /> : !data?.length ? <Empty icon={<CalendarClock className="size-8" />} title="No hay reservas en este estado" /> : (
        <DataTable head={["Usuario", "Impresora", "Inicio", "Fin", "Estado", "Motivo", ""]}>
          {data.map((r) => (
            <tr key={r.id}>
              <td className="font-medium">{r.user_name} {r.is_demo && <DemoBadge />}</td><td>{r.printer_name}</td><td className="text-xs">{fmtDateTime(r.start_at)}</td><td className="text-xs">{fmtDateTime(r.end_at)}</td>
              <td><StatusBadge status={r.status} /></td><td className="max-w-48 truncate text-xs text-mute" title={r.purpose}>{r.purpose || "—"}</td>
              <td className="whitespace-nowrap text-right">
                {r.status === "pending" && <><Button size="sm" onClick={() => setDlg({ r, d: "approve" })}><Check className="size-3.5" /> Aprobar</Button> <Button size="sm" variant="danger" onClick={() => setDlg({ r, d: "reject" })}><X className="size-3.5" /> Rechazar</Button></>}
                {r.status === "approved" && <><Button size="sm" variant="outline" onClick={() => setDlg({ r, d: "complete" })}><CheckCheck className="size-3.5" /> Completar</Button> <Button size="sm" variant="ghost" onClick={() => cancel.mutate(r.id)} aria-label="Cancelar"><X className="size-3.5 text-bad" /></Button></>}
              </td>
            </tr>
          ))}
        </DataTable>
      )}
      {dlg && <Decision r={dlg.r} decision={dlg.d} onClose={() => setDlg(null)} />}
    </>
  );
}
