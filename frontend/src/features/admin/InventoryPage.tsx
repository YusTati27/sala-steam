import { useState } from "react";
import { ArrowDownToLine, ArrowUpFromLine, Boxes, Plus, SlidersHorizontal } from "lucide-react";
import { api } from "../../lib/api";
import { useAction, useGet } from "../../lib/hooks";
import type { Filament, Movement } from "../../lib/types";
import { fmtDate, fmtDateTime, fmtGrams, toInputDate } from "../../lib/format";
import { Badge, Button, Card, DataTable, DemoBadge, Empty, ErrorBox, Field, Input, Loading, Modal, PageHeader, Select, StatusBadge, Tabs, Textarea } from "../../components/ui";
import { StockBar, Swatch, matColor } from "../../components/shared";

const COLOR_PRESETS: Record<string, string> = { Negro: "#1A1A1A", Blanco: "#F2F2F2", Rojo: "#D32F2F", Azul: "#1E4FD8", Cian: "#00BCD4", Gris: "#8E8E8E", Verde: "#2E9E4F", Naranja: "#F57C00", Amarillo: "#FACC15", Transparente: "#CFE8EF" };

function NewSpool({ onClose }: { onClose: () => void }) {
  const [f, setF] = useState({ material: "PLA", brand: "", color: "Negro", color_hex: "#1A1A1A", initial_weight_g: "1000", low_stock_threshold_g: "200", acquired_at: toInputDate(new Date()), notes: "" });
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => setF({ ...f, [k]: e.target.value });
  const m = useAction(() => api("/filaments", { body: { ...f, initial_weight_g: Number(f.initial_weight_g), low_stock_threshold_g: Number(f.low_stock_threshold_g), acquired_at: f.acquired_at || null } }),
    { invalidate: ["filaments", "dashboard", "alerts"], success: "Bobina registrada", onSuccess: onClose });
  return (
    <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); m.mutate(); }}>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Material"><Select value={f.material} onChange={set("material")}>{["PLA", "PETG", "ABS", "TPU", "ASA", "NYLON", "OTRO"].map((x) => <option key={x}>{x}</option>)}</Select></Field>
        <Field label="Marca"><Input value={f.brand} onChange={set("brand")} /></Field>
        <Field label="Color">
          <Input required list="colors" value={f.color} onChange={(e) => setF({ ...f, color: e.target.value, color_hex: COLOR_PRESETS[e.target.value] ?? f.color_hex })} />
          <datalist id="colors">{Object.keys(COLOR_PRESETS).map((c) => <option key={c} value={c} />)}</datalist>
        </Field>
        <Field label="Tono (hex)"><div className="flex gap-2"><input type="color" aria-label="Elegir color" value={f.color_hex} onChange={set("color_hex")} className="h-10 w-12 rounded-lg border border-line bg-ink" /><Input value={f.color_hex} onChange={set("color_hex")} pattern="#[0-9A-Fa-f]{6}" /></div></Field>
        <Field label="Peso inicial (g)"><Input type="number" required min="1" max="20000" value={f.initial_weight_g} onChange={set("initial_weight_g")} /></Field>
        <Field label="Alerta de stock bajo (g)"><Input type="number" min="0" value={f.low_stock_threshold_g} onChange={set("low_stock_threshold_g")} /></Field>
        <Field label="Fecha de adquisición"><Input type="date" value={f.acquired_at} onChange={set("acquired_at")} /></Field>
      </div>
      <Field label="Notas"><Textarea value={f.notes} onChange={set("notes")} /></Field>
      <div className="flex justify-end gap-2"><Button type="button" variant="ghost" onClick={onClose}>Cancelar</Button><Button type="submit" loading={m.isPending}>Registrar bobina</Button></div>
    </form>
  );
}

function MovementForm({ f, onClose }: { f: Filament; onClose: () => void }) {
  const [type, setType] = useState<"in" | "out" | "adjust">("in");
  const [grams, setGrams] = useState("");
  const [note, setNote] = useState("");
  const m = useAction(() => api(`/filaments/${f.id}/movements`, { body: { type, grams: Number(grams), note } }), { invalidate: ["filaments", "dashboard", "alerts"], success: "Movimiento registrado", onSuccess: onClose });
  return (
    <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); m.mutate(); }}>
      <p className="text-sm text-mute">{f.material} {f.color} · disponible <b className="text-fg">{fmtGrams(f.available_weight_g)}</b></p>
      <Tabs value={type} onChange={setType} items={[{ value: "in", label: "Entrada" }, { value: "out", label: "Salida" }, { value: "adjust", label: "Ajuste (conteo real)" }]} />
      <Field label={type === "adjust" ? "Peso real medido (g)" : "Gramos"} hint={type === "adjust" ? "Fija el peso disponible tras pesar la bobina" : undefined}><Input type="number" required min="0.1" step="0.1" max={type === "out" ? f.available_weight_g : 20000} value={grams} onChange={(e) => setGrams(e.target.value)} /></Field>
      <Field label="Motivo / nota"><Input value={note} onChange={(e) => setNote(e.target.value)} maxLength={255} /></Field>
      <div className="flex justify-end gap-2"><Button type="button" variant="ghost" onClick={onClose}>Cancelar</Button><Button type="submit" loading={m.isPending}>Registrar</Button></div>
    </form>
  );
}

function Movements({ filamentId }: { filamentId?: number }) {
  const { data, isLoading } = useGet<Movement[]>("filaments", "/filaments/movements/all", { limit: 150, filament_id: filamentId });
  if (isLoading) return <Loading />;
  if (!data?.length) return <Empty title="Sin movimientos" />;
  return (
    <DataTable head={["Fecha", "Bobina", "Tipo", "Gramos", "Saldo", "Detalle"]}>
      {data.map((m) => (
        <tr key={m.id}>
          <td className="text-xs">{fmtDateTime(m.created_at)}</td><td className="text-xs">{m.filament}</td>
          <td><Badge tone={m.type === "in" ? "ok" : m.type === "out" ? "royal" : "warn"}>{m.type === "in" ? "Entrada" : m.type === "out" ? "Salida" : "Ajuste"}</Badge></td>
          <td className="tabular-nums">{m.type === "in" ? "+" : m.type === "out" ? "−" : "="}{Math.round(m.grams)} g</td><td className="tabular-nums">{Math.round(m.balance_after_g)} g</td><td className="max-w-64 truncate text-xs text-mute" title={m.note}>{m.note || "—"}</td>
        </tr>
      ))}
    </DataTable>
  );
}

export default function InventoryPage() {
  const [tab, setTab] = useState<"spools" | "movements">("spools");
  const [showInactive, setShowInactive] = useState(false);
  const [mat, setMat] = useState("");
  const { data, isLoading, error } = useGet<Filament[]>("filaments", "/filaments", { include_inactive: showInactive, material: mat });
  const [creating, setCreating] = useState(false);
  const [moving, setMoving] = useState<Filament | null>(null);
  const [history, setHistory] = useState<Filament | null>(null);
  const low = data?.filter((f) => f.is_active && f.stock_status !== "available") ?? [];
  return (
    <>
      <PageHeader title="Inventario de filamentos" subtitle="Control de bobinas, existencias y consumo." actions={<Button onClick={() => setCreating(true)}><Plus className="size-4" /> Nueva bobina</Button>} />
      <ErrorBox error={error} />
      {low.length > 0 && <Card className="mb-4 border-warn/40 !p-3 text-sm text-warn">{low.length} bobina(s) con inventario bajo o agotado: {low.map((f) => `${f.material} ${f.color}`).join(", ")}.</Card>}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Tabs value={tab} onChange={setTab} items={[{ value: "spools", label: "Bobinas" }, { value: "movements", label: "Entradas y salidas" }]} />
        {tab === "spools" && <>
          <Select className="!w-auto" value={mat} onChange={(e) => setMat(e.target.value)}><option value="">Todos los materiales</option>{["PLA", "PETG", "ABS", "TPU", "ASA", "NYLON"].map((m) => <option key={m}>{m}</option>)}</Select>
          <label className="flex items-center gap-2 text-xs text-mute"><input type="checkbox" checked={showInactive} onChange={(e) => setShowInactive(e.target.checked)} /> Incluir bobinas retiradas</label>
        </>}
      </div>
      {tab === "movements" ? <Movements /> : isLoading ? <Loading /> : !data?.length ? <Empty icon={<Boxes className="size-8" />} title="No hay bobinas registradas" /> : (
        <DataTable head={["Código", "Material", "Color", "Inicial", "Disponible", "Consumido", "Adquirida", "Estado", ""]}>
          {data.map((f) => (
            <tr key={f.id} className={f.is_active ? "" : "opacity-50"}>
              <td className="font-mono text-xs">{f.code} {f.is_demo && <DemoBadge />}</td>
              <td className="font-semibold" style={{ color: matColor(f.material) }}>{f.material}<div className="text-[11px] font-normal text-mute">{f.brand}</div></td>
              <td><span className="inline-flex items-center gap-1.5 text-xs"><Swatch hex={f.color_hex} />{f.color}</span></td>
              <td className="tabular-nums text-xs">{fmtGrams(f.initial_weight_g)}</td>
              <td className="min-w-36"><div className="mb-1 text-xs font-medium tabular-nums">{fmtGrams(f.available_weight_g)}</div><StockBar f={f} /></td>
              <td className="tabular-nums text-xs">{fmtGrams(f.consumed_g)}</td><td className="text-xs">{fmtDate(f.acquired_at)}</td>
              <td>{f.is_active ? <StatusBadge status={f.stock_status} /> : <Badge>Retirada</Badge>}</td>
              <td className="whitespace-nowrap text-right">
                <Button size="sm" variant="outline" onClick={() => setMoving(f)}><SlidersHorizontal className="size-3.5" /> Movimiento</Button>
                <Button size="sm" variant="ghost" onClick={() => setHistory(f)} aria-label="Historial de consumo" title="Historial de consumo"><ArrowDownToLine className="size-3.5" /><ArrowUpFromLine className="size-3.5" /></Button>
              </td>
            </tr>
          ))}
        </DataTable>
      )}
      <Modal open={creating} onClose={() => setCreating(false)} title="Registrar bobina" wide><NewSpool onClose={() => setCreating(false)} /></Modal>
      <Modal open={!!moving} onClose={() => setMoving(null)} title="Registrar movimiento">{moving && <MovementForm f={moving} onClose={() => setMoving(null)} />}</Modal>
      <Modal open={!!history} onClose={() => setHistory(null)} title={history ? `Historial: ${history.material} ${history.color} (${history.code})` : ""} wide>{history && <Movements filamentId={history.id} />}</Modal>
    </>
  );
}
