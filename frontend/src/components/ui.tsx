import { useEffect, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from "react";
import clsx from "clsx";
import { AlertTriangle, ArrowDownRight, ArrowUpRight, Loader2, X } from "lucide-react";
import { label } from "../lib/format";

export function Card({ className, children, ...rest }: { className?: string; children: ReactNode } & React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={clsx("print-card animate-fade-up rounded-2xl border border-line bg-panel/90 p-4 sm:p-5 backdrop-blur", className)} {...rest}>
      {children}
    </div>
  );
}

export function CardTitle({ children, hint, right }: { children: ReactNode; hint?: string; right?: ReactNode }) {
  return (
    <div className="mb-3 flex items-start justify-between gap-3">
      <div>
        <h3 className="text-sm font-semibold text-fg">{children}</h3>
        {hint && <p className="mt-0.5 text-xs text-mute">{hint}</p>}
      </div>
      {right}
    </div>
  );
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-xl font-semibold tracking-tight sm:text-2xl">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-mute">{subtitle}</p>}
      </div>
      {actions && <div className="no-print flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" | "danger" | "outline"; size?: "sm" | "md"; loading?: boolean };
export function Button({ variant = "primary", size = "md", loading, className, children, disabled, ...rest }: BtnProps) {
  return (
    <button
      disabled={disabled || loading}
      className={clsx(
        "inline-flex items-center justify-center gap-2 rounded-xl font-medium transition active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50",
        size === "sm" ? "px-3 py-1.5 text-xs" : "px-4 py-2 text-sm",
        variant === "primary" && "bg-gradient-to-r from-cy to-royal text-ink hover:brightness-110",
        variant === "outline" && "border border-line bg-panel2 text-fg hover:border-cy/50",
        variant === "ghost" && "text-mute hover:bg-panel2 hover:text-fg",
        variant === "danger" && "border border-bad/40 bg-bad/10 text-bad hover:bg-bad/20",
        className,
      )}
      {...rest}
    >
      {loading && <Loader2 className="size-4 animate-spin" />}
      {children}
    </button>
  );
}

const inputCls =
  "w-full rounded-xl border border-line bg-ink/70 px-3 py-2 text-sm text-fg placeholder:text-mute/60 focus:border-cy/60 focus:outline-none disabled:opacity-50";

export function Field({ label: l, hint, error, children }: { label: string; hint?: string; error?: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-mute">{l}</span>
      {children}
      {hint && !error && <span className="mt-1 block text-[11px] text-mute/80">{hint}</span>}
      {error && <span className="mt-1 block text-[11px] text-bad">{error}</span>}
    </label>
  );
}
export const Input = (p: InputHTMLAttributes<HTMLInputElement>) => <input {...p} className={clsx(inputCls, p.className)} />;
export const Select = (p: SelectHTMLAttributes<HTMLSelectElement>) => <select {...p} className={clsx(inputCls, p.className)} />;
export const Textarea = (p: TextareaHTMLAttributes<HTMLTextAreaElement>) => <textarea {...p} className={clsx(inputCls, "min-h-20", p.className)} />;

const TONES: Record<string, string> = {
  ok: "bg-ok/12 text-ok border-ok/30",
  warn: "bg-warn/12 text-warn border-warn/30",
  bad: "bg-bad/12 text-bad border-bad/30",
  cy: "bg-cy/12 text-cy border-cy/30",
  royal: "bg-royal/15 text-[#7aa2ff] border-royal/40",
  mute: "bg-panel2 text-mute border-line",
};
export function Badge({ tone = "mute", children, className }: { tone?: keyof typeof TONES; children: ReactNode; className?: string }) {
  return <span className={clsx("inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-0.5 text-[11px] font-medium", TONES[tone], className)}>{children}</span>;
}

const STATUS_TONE: Record<string, keyof typeof TONES> = {
  available: "ok", busy: "royal", maintenance: "warn", out_of_service: "bad",
  pending: "warn", queued: "cy", printing: "royal", completed: "ok", cancelled: "mute", failed: "bad",
  approved: "ok", rejected: "bad", low: "warn", empty: "bad", scheduled: "cy", in_progress: "royal", done: "ok",
  preventive: "cy", corrective: "warn",
};
export function StatusBadge({ status }: { status: string }) {
  const tone = STATUS_TONE[status] ?? "mute";
  return (
    <Badge tone={tone}>
      {(status === "printing" || status === "busy") && <span className="size-1.5 animate-pulse-soft rounded-full bg-current" />}
      {label(status)}
    </Badge>
  );
}

export function DemoBadge({ className }: { className?: string }) {
  return <Badge tone="warn" className={className}>DEMO</Badge>;
}

export function ProgressBar({ value, tone = "cy", className }: { value: number; tone?: "cy" | "ok" | "warn" | "bad"; className?: string }) {
  const color = { cy: "from-cy to-royal", ok: "from-ok to-cy", warn: "from-warn to-warn", bad: "from-bad to-bad" }[tone];
  return (
    <div role="progressbar" aria-valuenow={Math.round(value)} aria-valuemin={0} aria-valuemax={100} className={clsx("h-2 overflow-hidden rounded-full bg-line", className)}>
      <div className={clsx("h-full rounded-full bg-gradient-to-r transition-all duration-700", color)} style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
    </div>
  );
}

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={clsx("size-5 animate-spin text-cy", className)} />;
}
export function Loading({ text = "Cargando…" }: { text?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-sm text-mute">
      <Spinner /> {text}
    </div>
  );
}
export function ErrorBox({ error }: { error: Error | null | undefined }) {
  if (!error) return null;
  return (
    <div className="flex items-center gap-2 rounded-xl border border-bad/40 bg-bad/10 p-3 text-sm text-bad">
      <AlertTriangle className="size-4 shrink-0" /> {error.message}
    </div>
  );
}
export function Empty({ icon, title, text, action }: { icon?: ReactNode; title: string; text?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-2xl border border-dashed border-line px-4 py-10 text-center">
      {icon && <div className="text-mute">{icon}</div>}
      <p className="text-sm font-medium">{title}</p>
      {text && <p className="max-w-sm text-xs text-mute">{text}</p>}
      {action}
    </div>
  );
}

export function Modal({ open, onClose, title, children, wide }: { open: boolean; onClose: () => void; title: string; children: ReactNode; wide?: boolean }) {
  useEffect(() => {
    if (!open) return;
    const h = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="no-print fixed inset-0 z-50 flex items-end justify-center bg-black/70 p-0 backdrop-blur-sm sm:items-center sm:p-4" onMouseDown={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onMouseDown={(e) => e.stopPropagation()}
        className={clsx("animate-fade-up max-h-[92vh] w-full overflow-y-auto rounded-t-2xl border border-line bg-panel p-5 shadow-2xl sm:rounded-2xl", wide ? "sm:max-w-2xl" : "sm:max-w-md")}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-semibold">{title}</h2>
          <button onClick={onClose} aria-label="Cerrar" className="rounded-lg p-1 text-mute hover:bg-panel2 hover:text-fg">
            <X className="size-5" />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function Confirm({ open, title, text, confirmLabel = "Confirmar", danger, loading, onConfirm, onClose }: {
  open: boolean; title: string; text: string; confirmLabel?: string; danger?: boolean; loading?: boolean; onConfirm: () => void; onClose: () => void;
}) {
  return (
    <Modal open={open} onClose={onClose} title={title}>
      <p className="text-sm text-mute">{text}</p>
      <div className="mt-5 flex justify-end gap-2">
        <Button variant="ghost" onClick={onClose}>Volver</Button>
        <Button variant={danger ? "danger" : "primary"} loading={loading} onClick={onConfirm}>{confirmLabel}</Button>
      </div>
    </Modal>
  );
}

export function KpiCard({ label: l, value, sub, icon, tone = "cy", delta, deltaGood = "up", onClick }: {
  label: string; value: ReactNode; sub?: ReactNode; icon?: ReactNode; tone?: "cy" | "ok" | "warn" | "bad" | "royal";
  delta?: number | null; deltaGood?: "up" | "down"; onClick?: () => void;
}) {
  const toneCls = { cy: "text-cy bg-cy/10", ok: "text-ok bg-ok/10", warn: "text-warn bg-warn/10", bad: "text-bad bg-bad/10", royal: "text-[#7aa2ff] bg-royal/15" }[tone];
  const good = delta === null || delta === undefined || delta === 0 ? null : (delta > 0) === (deltaGood === "up");
  const Tag = onClick ? "button" : "div";
  return (
    <Tag onClick={onClick} className={clsx("print-card animate-fade-up rounded-2xl border border-line bg-panel/90 p-4 text-left", onClick && "transition hover:border-cy/40")}>
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium text-mute">{l}</span>
        {icon && <span className={clsx("rounded-lg p-1.5", toneCls)}>{icon}</span>}
      </div>
      <div className="mt-2 text-2xl font-semibold tabular-nums tracking-tight sm:text-[1.7rem]">{value}</div>
      <div className="mt-1 flex min-h-4 flex-wrap items-center gap-x-2 text-[11px] text-mute">
        {delta !== null && delta !== undefined && (
          <span className={clsx("inline-flex items-center gap-0.5 font-medium", good === null ? "text-mute" : good ? "text-ok" : "text-bad")}>
            {delta >= 0 ? <ArrowUpRight className="size-3" /> : <ArrowDownRight className="size-3" />}
            {Math.abs(delta).toLocaleString("es-CO", { maximumFractionDigits: 1 })}
          </span>
        )}
        {sub}
      </div>
    </Tag>
  );
}

export function DataTable({ head, children, className }: { head: string[]; children: ReactNode; className?: string }) {
  return (
    <div className={clsx("overflow-x-auto rounded-xl border border-line", className)}>
      <table className="w-full min-w-max text-left text-sm">
        <thead className="bg-panel2 text-[11px] uppercase tracking-wide text-mute">
          <tr>{head.map((h) => <th key={h} className="px-3 py-2 font-medium">{h}</th>)}</tr>
        </thead>
        <tbody className="divide-y divide-line [&_td]:px-3 [&_td]:py-2.5">{children}</tbody>
      </table>
    </div>
  );
}

export function Tabs<T extends string>({ value, onChange, items }: { value: T; onChange: (v: T) => void; items: { value: T; label: string; count?: number }[] }) {
  return (
    <div className="no-print flex gap-1 overflow-x-auto rounded-xl border border-line bg-panel p-1">
      {items.map((i) => (
        <button key={i.value} onClick={() => onChange(i.value)}
          className={clsx("whitespace-nowrap rounded-lg px-3 py-1.5 text-xs font-medium transition", value === i.value ? "bg-gradient-to-r from-cy/20 to-royal/25 text-cy" : "text-mute hover:text-fg")}>
          {i.label}{i.count !== undefined && <span className="ml-1.5 text-[10px] opacity-70">{i.count}</span>}
        </button>
      ))}
    </div>
  );
}
