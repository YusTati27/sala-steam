const dtf = new Intl.DateTimeFormat("es-CO", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
const df = new Intl.DateTimeFormat("es-CO", { day: "2-digit", month: "short", year: "numeric" });
const tf = new Intl.DateTimeFormat("es-CO", { hour: "2-digit", minute: "2-digit" });

export const fmtDateTime = (iso: string | null | undefined) => (iso ? dtf.format(new Date(iso)) : "—");
export const fmtTime = (iso: string | null | undefined) => (iso ? tf.format(new Date(iso)) : "—");
export const fmtDate = (iso: string | null | undefined) => (iso ? df.format(new Date(iso.length <= 10 ? iso + "T12:00:00" : iso)) : "—");

export function fmtDuration(min: number | null | undefined) {
  if (min === null || min === undefined) return "—";
  const m = Math.round(min);
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  const r = m % 60;
  return r ? `${h} h ${r} min` : `${h} h`;
}

/** "en 2 h 10 min" / "hace 5 min" */
export function fmtRelative(iso: string | null | undefined) {
  if (!iso) return "—";
  const diff = (new Date(iso).getTime() - Date.now()) / 60000;
  const abs = Math.abs(diff);
  const txt = abs < 1 ? "ahora" : fmtDuration(abs);
  if (abs < 1) return txt;
  return diff >= 0 ? `en ${txt}` : `hace ${txt}`;
}

export const fmtNum = (n: number | null | undefined, digits = 0) =>
  n === null || n === undefined ? "—" : n.toLocaleString("es-CO", { maximumFractionDigits: digits });
export const fmtPct = (n: number | null | undefined, digits = 1) => (n === null || n === undefined ? "—" : `${n.toLocaleString("es-CO", { maximumFractionDigits: digits })}%`);
export const fmtGrams = (g: number | null | undefined) => (g === null || g === undefined ? "—" : g >= 1000 ? `${(g / 1000).toLocaleString("es-CO", { maximumFractionDigits: 2 })} kg` : `${Math.round(g)} g`);

export const toInputDate = (d: Date) => {
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
};
export const toInputDateTime = (d: Date) => `${toInputDate(d)}T${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;

export const STATUS_LABEL: Record<string, string> = {
  available: "Disponible",
  busy: "Ocupada",
  maintenance: "Mantenimiento",
  out_of_service: "Fuera de servicio",
  pending: "Pendiente",
  queued: "En cola",
  printing: "En proceso",
  completed: "Completado",
  cancelled: "Cancelado",
  failed: "Fallido",
  approved: "Aprobada",
  rejected: "Rechazada",
  low: "Bajo",
  empty: "Agotado",
  scheduled: "Programado",
  in_progress: "En curso",
  done: "Realizado",
  preventive: "Preventivo",
  corrective: "Correctivo",
  printer_3d: "Impresora 3D",
  tool: "Herramienta",
  other: "Otro",
};
export const label = (s: string) => STATUS_LABEL[s] ?? s;

export const REASON_LABEL: Record<string, string> = {
  adhesion: "Mala adhesión",
  nozzle_clog: "Boquilla obstruida",
  filament_issue: "Problema de filamento",
  warping: "Deformación (warping)",
  power_outage: "Corte de energía",
  user_error: "Error de diseño/usuario",
  other: "Otro",
};

export const WEEKDAYS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];
