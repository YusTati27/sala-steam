import { useState } from "react";
import { Cpu, Pencil, Plus, Trash2 } from "lucide-react";
import { api } from "../../lib/api";
import { useAction, useGet } from "../../lib/hooks";
import type { Equipment } from "../../lib/types";
import { fmtDate, label } from "../../lib/format";
import { Badge, Button, Card, Confirm, DataTable, DemoBadge, Empty, ErrorBox, Field, Input, Loading, Modal, PageHeader, Select, StatusBadge, Tabs, Textarea } from "../../components/ui";
import { PrinterCard } from "../../components/shared";
import clsx from "clsx";

const MATS = ["PLA", "PETG", "ABS", "TPU", "ASA", "NYLON"];
const empty = {
  code: "", name: "", model: "", type: "printer_3d", status: "available", build_volume: "", nozzle_mm: "", supported_materials: ["PLA"] as string[],
  acquired_at: "", last_maintenance_at: "", next_maintenance_at: "", hardware_endpoint: "", notes: "",
};

function EquipmentForm({ item, onClose }: { item: Equipment | null; onClose: () => void }) {
  const [f, setF] = useState(item ? {
    code: item.code, name: item.name, model: item.model, type: item.type, status: item.status === "busy" ? "available" : item.status, build_volume: item.build_volume,
    nozzle_mm: item.nozzle_mm?.toString() ?? "", supported_materials: item.supported_materials, acquired_at: item.acquired_at ?? "",
    last_maintenance_at: item.last_maintenance_at ?? "", next_maintenance_at: item.next_maintenance_at ?? "", hardware_endpoint: item.hardware_endpoint ?? "", notes: item.notes ?? "",
  } : empty);
  const set = (k: keyof typeof empty) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => setF({ ...f, [k]: e.target.value });
  const isPrinter = f.type === "printer_3d";
  const m = useAction(() => {
    const body = {
      ...f, nozzle_mm: f.nozzle_mm ? Number(f.nozzle_mm) : null, acquired_at: f.acquired_at || null, last_maintenance_at: f.last_maintenance_at || null,
      next_maintenance_at: f.next_maintenance_at || null, hardware_endpoint: f.hardware_endpoint || null, supported_materials: isPrinter ? f.supported_materials : [],
    };
    return item ? api(`/equipment/${item.id}`, { method: "PATCH", body: item.status === "busy" ? { ...body, status: undefined } : body }) : api("/equipment", { body });
  }, { invalidate: ["equipment", "dashboard", "alerts"], success: item ? "Equipo actualizado" : "Equipo creado", onSuccess: onClose });
  return (
    <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); m.mutate(); }}>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Identificador (código)"><Input required minLength={2} value={f.code} onChange={set("code")} placeholder="IMP-07" /></Field>
        <Field label="Nombre"><Input required minLength={2} value={f.name} onChange={set("name")} /></Field>
        <Field label="Modelo"><Input value={f.model} onChange={set("model")} /></Field>
        <Field label="Tipo"><Select value={f.type} onChange={set("type")}><option value="printer_3d">Impresora 3D</option><option value="tool">Herramienta</option><option value="other">Otro equipo</option></Select></Field>
        <Field label="Estado" hint={item?.status === "busy" ? "Ocupada: el estado lo define el trabajo en curso" : "«Ocupada» se asigna sola al iniciar un trabajo"}>
          <Select value={f.status} onChange={set("status")} disabled={item?.status === "busy"}><option value="available">Disponible</option><option value="maintenance">Mantenimiento</option><option value="out_of_service">Fuera de servicio</option></Select>
        </Field>
        <Field label="Fecha de adquisición"><Input type="date" value={f.acquired_at} onChange={set("acquired_at")} /></Field>
        <Field label="Último mantenimiento"><Input type="date" value={f.last_maintenance_at} onChange={set("last_maintenance_at")} /></Field>
        <Field label="Próximo mantenimiento"><Input type="date" min={f.last_maintenance_at || undefined} value={f.next_maintenance_at} onChange={set("next_maintenance_at")} /></Field>
      </div>
      {isPrinter && (
        <>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Volumen de impresión"><Input value={f.build_volume} onChange={set("build_volume")} placeholder="250×210×220 mm" /></Field>
            <Field label="Boquilla (mm)"><Input type="number" step="0.05" min="0.1" max="2" value={f.nozzle_mm} onChange={set("nozzle_mm")} /></Field>
          </div>
          <Field label="Materiales compatibles">
            <div className="flex flex-wrap gap-2">
              {MATS.map((mt) => {
                const on = f.supported_materials.includes(mt);
                return <button type="button" key={mt} onClick={() => setF({ ...f, supported_materials: on ? f.supported_materials.filter((x) => x !== mt) : [...f.supported_materials, mt] })}
                  className={clsx("rounded-full border px-3 py-1 text-xs", on ? "border-cy/60 bg-cy/15 text-cy" : "border-line text-mute")}>{mt}</button>;
              })}
            </div>
          </Field>
          <Field label="Endpoint de hardware (opcional)" hint="URL de OctoPrint/Moonraker para integración futura. Ver docs/INTEGRACION_HARDWARE.md"><Input value={f.hardware_endpoint} onChange={set("hardware_endpoint")} placeholder="http://192.168.1.50" /></Field>
        </>
      )}
      <Field label="Observaciones"><Textarea maxLength={2000} value={f.notes} onChange={set("notes")} /></Field>
      <div className="flex justify-end gap-2 pt-1"><Button type="button" variant="ghost" onClick={onClose}>Cancelar</Button><Button type="submit" loading={m.isPending}>{item ? "Guardar" : "Crear equipo"}</Button></div>
    </form>
  );
}

export default function EquipmentPage() {
  const { data, isLoading, error } = useGet<Equipment[]>("equipment", "/equipment");
  const [tab, setTab] = useState("printer_3d");
  const [view, setView] = useState<"cards" | "table">("table");
  const [edit, setEdit] = useState<Equipment | null | "new">(null);
  const [del, setDel] = useState<Equipment | null>(null);
  const remove = useAction((id: number) => api(`/equipment/${id}`, { method: "DELETE" }), { invalidate: ["equipment", "dashboard"], success: "Equipo eliminado", onSuccess: () => setDel(null) });
  const rows = (data ?? []).filter((e) => tab === "all" || (tab === "printer_3d" ? e.type === "printer_3d" : e.type !== "printer_3d"));
  return (
    <>
      <PageHeader title="Gestión de equipos" subtitle="Impresoras 3D, herramientas y otros equipos de la sala."
        actions={<><Tabs value={view} onChange={setView} items={[{ value: "table", label: "Tabla" }, { value: "cards", label: "Tarjetas" }]} /><Button onClick={() => setEdit("new")}><Plus className="size-4" /> Nuevo equipo</Button></>} />
      <div className="mb-4"><Tabs value={tab} onChange={setTab} items={[{ value: "printer_3d", label: "Impresoras 3D", count: data?.filter((e) => e.type === "printer_3d").length }, { value: "tools", label: "Herramientas y otros", count: data?.filter((e) => e.type !== "printer_3d").length }, { value: "all", label: "Todos" }]} /></div>
      <ErrorBox error={error} />
      {isLoading ? <Loading /> : rows.length === 0 ? <Empty icon={<Cpu className="size-8" />} title="No hay equipos" text="Registra el primero con «Nuevo equipo»." /> : view === "cards" ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{rows.map((p) => <PrinterCard key={p.id} p={p} />)}</div>
      ) : (
        <DataTable head={["ID", "Nombre", "Modelo", "Estado", "Adquirido", "Últ. mant.", "Próx. mant.", "Observaciones", ""]}>
          {rows.map((e) => {
            const left = e.maintenance_days_left;
            return (
              <tr key={e.id}>
                <td className="font-mono text-xs">{e.code}</td>
                <td className="font-medium">{e.name} {e.is_demo && <DemoBadge />}<div className="text-[11px] text-mute">{label(e.type)}</div></td>
                <td className="text-xs">{e.model || "—"}</td><td><StatusBadge status={e.status} /></td>
                <td className="text-xs">{fmtDate(e.acquired_at)}</td><td className="text-xs">{fmtDate(e.last_maintenance_at)}</td>
                <td className="text-xs">{fmtDate(e.next_maintenance_at)}{left !== null && <Badge tone={left < 0 ? "bad" : left <= 14 ? "warn" : "mute"} className="ml-1.5">{left < 0 ? `vencido ${-left}d` : `${left}d`}</Badge>}</td>
                <td className="max-w-52 truncate text-xs text-mute" title={e.notes ?? ""}>{e.notes || "—"}</td>
                <td className="whitespace-nowrap text-right"><Button size="sm" variant="ghost" onClick={() => setEdit(e)} aria-label="Editar"><Pencil className="size-3.5" /></Button><Button size="sm" variant="ghost" onClick={() => setDel(e)} aria-label="Eliminar"><Trash2 className="size-3.5 text-bad" /></Button></td>
              </tr>
            );
          })}
        </DataTable>
      )}
      <Modal open={edit !== null} onClose={() => setEdit(null)} title={edit === "new" ? "Nuevo equipo" : "Editar equipo"} wide>
        {edit !== null && <EquipmentForm key={edit === "new" ? "n" : edit.id} item={edit === "new" ? null : edit} onClose={() => setEdit(null)} />}
      </Modal>
      <Confirm open={!!del} danger title="Eliminar equipo" text={`¿Eliminar «${del?.name}»? Si tiene trabajos, reservas o mantenimientos asociados no se podrá borrar: márcalo como fuera de servicio.`}
        confirmLabel="Eliminar" loading={remove.isPending} onClose={() => setDel(null)} onConfirm={() => del && remove.mutate(del.id)} />
      <Card className="mt-5 !p-3 text-xs text-mute">El estado «Ocupada» se calcula solo: una impresora pasa a ocupada cuando inicia un trabajo y vuelve a disponible al terminar, fallar o cancelarse.</Card>
    </>
  );
}
