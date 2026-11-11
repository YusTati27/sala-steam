import clsx from "clsx";
import { Clock, Layers, Wrench } from "lucide-react";
import type { Equipment, Filament, Job } from "../lib/types";
import { fmtDateTime, fmtDuration, fmtGrams, fmtRelative, label } from "../lib/format";
import { Badge, Card, DemoBadge, ProgressBar, StatusBadge } from "./ui";

export const MATERIAL_COLOR: Record<string, string> = { PLA: "#22d3ee", PETG: "#2f6bff", ABS: "#fbbf24", TPU: "#a78bfa", ASA: "#fb7185", NYLON: "#34d399", OTRO: "#8a97a8" };
export const matColor = (m: string) => MATERIAL_COLOR[m] ?? "#8a97a8";

export function Swatch({ hex, size = 14 }: { hex: string; size?: number }) {
  return <span className="inline-block shrink-0 rounded-full border border-white/25" style={{ width: size, height: size, background: hex }} />;
}

export function PrinterCard({ p }: { p: Equipment }) {
  const job = p.current_job;
  return (
    <Card className="flex flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2"><h3 className="truncate font-semibold">{p.name}</h3>{p.is_demo && <DemoBadge />}</div>
          <p className="truncate text-xs text-mute">{p.model || "—"} · {p.code}</p>
        </div>
        <StatusBadge status={p.status} />
      </div>
      <div className="flex flex-wrap gap-1.5">
        {p.supported_materials.map((m) => <Badge key={m} tone="mute"><span className="size-1.5 rounded-full" style={{ background: matColor(m) }} />{m}</Badge>)}
        {p.build_volume && <Badge tone="mute"><Layers className="size-3" />{p.build_volume}</Badge>}
        {p.nozzle_mm && <Badge tone="mute">Boquilla {p.nozzle_mm} mm</Badge>}
      </div>
      {job ? (
        <div className="rounded-xl bg-panel2 p-3">
          <div className="mb-1.5 flex items-center justify-between text-xs">
            <span className="truncate font-medium">{job.is_mine ? "★ " : ""}{job.project_name}</span>
            <span className="tabular-nums text-cy">{Math.round(job.progress_pct)}%</span>
          </div>
          <ProgressBar value={job.progress_pct} />
          <p className="mt-1.5 text-[11px] text-mute">Termina {fmtRelative(job.estimated_end_at)} · {fmtDateTime(job.estimated_end_at)}</p>
        </div>
      ) : p.status === "available" ? (
        <p className="rounded-xl bg-ok/8 p-3 text-xs text-ok">Libre ahora{p.queue_length > 0 ? ` · ${p.queue_length} en espera` : ""}</p>
      ) : (
        <p className="flex items-center gap-1.5 rounded-xl bg-panel2 p-3 text-xs text-mute"><Wrench className="size-3.5" />{label(p.status)} — sin fecha de disponibilidad</p>
      )}
      {(p.status === "available" || p.status === "busy") && (
        <div className="mt-auto flex items-center justify-between border-t border-line pt-2.5 text-[11px] text-mute">
          <span className="flex items-center gap-1"><Clock className="size-3" />{p.status === "busy" ? `Libre ${fmtRelative(p.available_at)}` : "Disponible ya"}</span>
          {p.queue_length > 0 && <span>Cola libre {fmtRelative(p.queue_clear_at)}</span>}
        </div>
      )}
    </Card>
  );
}

export function StockBar({ f }: { f: Filament }) {
  const pct = f.initial_weight_g ? (f.available_weight_g / f.initial_weight_g) * 100 : Math.min(100, f.available_weight_g / 10);
  return <ProgressBar value={pct} tone={f.stock_status === "available" ? "cy" : f.stock_status === "low" ? "warn" : "bad"} />;
}

export function JobProgress({ j }: { j: Job }) {
  if (j.status === "printing") return <div className="w-32"><ProgressBar value={j.progress_pct} /><span className="text-[11px] tabular-nums text-mute">{Math.round(j.progress_pct)}%</span></div>;
  return <span className="text-xs text-mute">—</span>;
}

export function JobEta({ j }: { j: Job }) {
  if (j.status === "printing" || j.status === "queued") return <span className="text-xs">{fmtRelative(j.estimated_end_at)}<span className="block text-[11px] text-mute">{fmtDateTime(j.estimated_end_at)}</span></span>;
  if (j.finished_at) return <span className="text-xs text-mute">{fmtDateTime(j.finished_at)}</span>;
  return <span className="text-xs text-mute">~{fmtDuration(j.estimated_minutes)}</span>;
}

export function MaterialCell({ j }: { j: Pick<Job, "material" | "color" | "color_hex"> }) {
  if (!j.material) return <span className="text-mute">—</span>;
  return <span className="inline-flex items-center gap-1.5 text-xs"><Swatch hex={j.color_hex ?? "#888"} />{j.material} {j.color}</span>;
}

export const gramsText = fmtGrams;
export { clsx };
