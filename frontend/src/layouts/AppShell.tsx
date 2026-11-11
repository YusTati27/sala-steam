import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import clsx from "clsx";
import {
  Activity, Bell, BarChart3, Boxes, CalendarClock, CalendarDays, ClipboardList, Cpu, FlaskConical, History, KeyRound, LayoutDashboard,
  ListOrdered, LogOut, Menu, Printer, Settings, Users, Wrench, X,
} from "lucide-react";
import { useAuth } from "../lib/auth";
import { useConfig, useGet, useAction } from "../lib/hooks";
import { useRealtime } from "../lib/realtime";
import { api } from "../lib/api";
import type { Alert } from "../lib/types";
import { Badge, Button, Field, Input, Modal } from "../components/ui";

const CLIENT_NAV = [
  { to: "/", label: "Disponibilidad", icon: Printer, end: true },
  { to: "/filamentos", label: "Filamentos", icon: Boxes },
  { to: "/cola", label: "Cola de impresión", icon: ListOrdered },
  { to: "/reservas", label: "Reservas", icon: CalendarDays },
  { to: "/historial", label: "Mi historial", icon: History },
];
const ADMIN_NAV = [
  { to: "/admin", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/admin/equipos", label: "Equipos", icon: Cpu },
  { to: "/admin/inventario", label: "Inventario", icon: Boxes },
  { to: "/admin/trabajos", label: "Trabajos", icon: ClipboardList },
  { to: "/admin/reservas", label: "Reservas", icon: CalendarClock },
  { to: "/admin/mantenimiento", label: "Mantenimiento", icon: Wrench },
  { to: "/admin/estadisticas", label: "Estadísticas", icon: BarChart3 },
  { to: "/admin/usuarios", label: "Usuarios", icon: Users },
  { to: "/admin/configuracion", label: "Configuración", icon: Settings },
];

function Logo() {
  return (
    <div className="flex items-center gap-2.5">
      <div className="grid size-9 place-items-center rounded-xl bg-gradient-to-br from-cy to-royal text-ink shadow-[0_0_20px_-4px_var(--color-cy)]">
        <Activity className="size-5" />
      </div>
      <div className="leading-tight">
        <div className="text-sm font-semibold tracking-tight">Sala STEAM</div>
        <div className="text-[10px] uppercase tracking-widest text-mute">Gestión</div>
      </div>
    </div>
  );
}

function ChangePassword({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [cur, setCur] = useState("");
  const [next, setNext] = useState("");
  const m = useAction(() => api("/auth/change-password", { body: { current_password: cur, new_password: next } }), {
    success: "Contraseña actualizada",
    onSuccess: () => { setCur(""); setNext(""); onClose(); },
  });
  return (
    <Modal open={open} onClose={onClose} title="Cambiar contraseña">
      <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); m.mutate(); }}>
        <Field label="Contraseña actual"><Input type="password" required value={cur} onChange={(e) => setCur(e.target.value)} autoComplete="current-password" /></Field>
        <Field label="Nueva contraseña" hint="Mínimo 8 caracteres, con letras y números"><Input type="password" required minLength={8} value={next} onChange={(e) => setNext(e.target.value)} autoComplete="new-password" /></Field>
        <div className="flex justify-end gap-2 pt-2"><Button type="button" variant="ghost" onClick={onClose}>Cancelar</Button><Button type="submit" loading={m.isPending}>Guardar</Button></div>
      </form>
    </Modal>
  );
}

function AlertsBell() {
  const [open, setOpen] = useState(false);
  const { data } = useGet<Alert[]>("alerts", "/alerts");
  const navigate = useNavigate();
  const crit = data?.filter((a) => a.severity !== "info").length ?? 0;
  const go = (a: Alert) => {
    setOpen(false);
    navigate({ equipment: "/admin/mantenimiento", filament: "/admin/inventario", reservation: "/admin/reservas", job: "/admin/trabajos" }[a.entity] ?? "/admin");
  };
  return (
    <div className="relative">
      <button onClick={() => setOpen((o) => !o)} aria-label="Alertas" className="relative rounded-xl border border-line bg-panel2 p-2 text-mute hover:text-fg">
        <Bell className="size-5" />
        {crit > 0 && <span className="absolute -right-1 -top-1 grid min-w-4 place-items-center rounded-full bg-bad px-1 text-[10px] font-bold text-ink">{crit}</span>}
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-30" onClick={() => setOpen(false)} />
          <div className="animate-fade-up absolute right-0 z-40 mt-2 w-80 max-w-[88vw] rounded-2xl border border-line bg-panel p-2 shadow-2xl">
            <div className="px-2 py-1.5 text-xs font-semibold text-mute">Alertas ({data?.length ?? 0})</div>
            <div className="max-h-96 space-y-1 overflow-y-auto">
              {data?.length === 0 && <p className="px-2 py-6 text-center text-xs text-mute">Todo en orden ✓</p>}
              {data?.map((a, i) => (
                <button key={i} onClick={() => go(a)} className="flex w-full gap-2 rounded-xl p-2 text-left hover:bg-panel2">
                  <span className={clsx("mt-1.5 size-2 shrink-0 rounded-full", a.severity === "critical" ? "bg-bad" : a.severity === "warning" ? "bg-warn" : "bg-cy")} />
                  <span><span className="block text-xs font-medium">{a.title}</span>{a.detail && <span className="block text-[11px] text-mute">{a.detail}</span>}</span>
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default function AppShell() {
  const { user, logout } = useAuth();
  const { data: config } = useConfig();
  const { live, toasts, dismiss } = useRealtime();
  const [menu, setMenu] = useState(false);
  const [pw, setPw] = useState(false);
  const navigate = useNavigate();
  if (!user) return null;
  const isAdmin = user.role === "admin";
  const nav = isAdmin ? ADMIN_NAV : CLIENT_NAV;

  const sidebar = (
    <nav className="flex h-full flex-col gap-1 p-3">
      <div className="mb-4 flex items-center justify-between px-2 pt-1">
        <Logo />
        <button className="rounded-lg p-1 text-mute lg:hidden" onClick={() => setMenu(false)} aria-label="Cerrar menú"><X className="size-5" /></button>
      </div>
      {nav.map((n) => (
        <NavLink key={n.to} to={n.to} end={n.end} onClick={() => setMenu(false)}
          className={({ isActive }) => clsx("group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition",
            isActive ? "bg-gradient-to-r from-cy/15 to-royal/20 text-cy shadow-[inset_2px_0_0_var(--color-cy)]" : "text-mute hover:bg-panel2 hover:text-fg")}>
          <n.icon className="size-[18px]" /> {n.label}
        </NavLink>
      ))}
      <div className="mt-auto rounded-xl border border-line bg-panel2 p-3">
        <div className="truncate text-sm font-medium">{user.name}</div>
        <div className="truncate text-[11px] text-mute">{user.email}</div>
        <Badge tone={isAdmin ? "royal" : "cy"} className="mt-2">{isAdmin ? "Administrador" : "Cliente"}</Badge>
        <button onClick={() => { setMenu(false); setPw(true); }} className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg border border-line px-2 py-1.5 text-xs text-mute hover:border-cy/50 hover:text-fg">
          <KeyRound className="size-3.5" /> Cambiar contraseña
        </button>
      </div>
    </nav>
  );

  return (
    <div className="flex min-h-full">
      <aside className="no-print sticky top-0 hidden h-screen w-64 shrink-0 border-r border-line bg-panel/70 backdrop-blur lg:block">{sidebar}</aside>
      {menu && (
        <div className="no-print fixed inset-0 z-40 lg:hidden" onClick={() => setMenu(false)}>
          <div className="absolute inset-0 bg-black/70" />
          <aside className="animate-fade-up absolute inset-y-0 left-0 w-72 max-w-[85vw] border-r border-line bg-panel" onClick={(e) => e.stopPropagation()}>{sidebar}</aside>
        </div>
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="no-print sticky top-0 z-30 flex items-center gap-3 border-b border-line bg-ink/80 px-4 py-3 backdrop-blur">
          <button className="rounded-xl border border-line bg-panel2 p-2 text-mute lg:hidden" onClick={() => setMenu(true)} aria-label="Abrir menú"><Menu className="size-5" /></button>
          <div className="lg:hidden"><Logo /></div>
          <div className="ml-auto flex items-center gap-2">
            {config?.demo && (
              <button onClick={() => isAdmin && navigate("/admin/configuracion")} title="Todos los datos mostrados son de demostración">
                <Badge tone="warn" className="animate-pulse-soft px-2.5 py-1"><FlaskConical className="size-3.5" /> SIMULADOR</Badge>
              </button>
            )}
            <span title={live ? "Actualización en vivo activa" : "Sin conexión en vivo"} className="hidden items-center gap-1.5 text-[11px] text-mute sm:flex">
              <span className={clsx("size-2 rounded-full", live ? "bg-ok animate-pulse-soft" : "bg-mute")} /> {live ? "En vivo" : "Sin conexión"}
            </span>
            {isAdmin && <AlertsBell />}
            <button onClick={() => setPw(true)} aria-label="Cambiar contraseña" title="Cambiar contraseña" className="rounded-xl border border-line bg-panel2 p-2 text-mute hover:text-fg"><KeyRound className="size-5" /></button>
            <button onClick={() => { logout(); navigate("/login"); }} aria-label="Cerrar sesión" title="Cerrar sesión" className="rounded-xl border border-line bg-panel2 p-2 text-mute hover:text-bad"><LogOut className="size-5" /></button>
          </div>
        </header>
        {config?.demo && (
          <div className="no-print border-b border-warn/20 bg-warn/8 px-4 py-1.5 text-center text-[11px] text-warn">
            Modo simulador: los equipos, usuarios, trabajos y consumos que ves son <b>datos inventados de demostración</b>, no información real de la sala.
          </div>
        )}
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-5 sm:px-6 sm:py-7"><Outlet /></main>
      </div>
      <div className="no-print fixed bottom-4 right-4 z-[60] flex w-80 max-w-[calc(100vw-2rem)] flex-col gap-2">
        {toasts.map((t) => (
          <div key={t.id} role="status" onClick={() => dismiss(t.id)}
            className={clsx("animate-fade-up cursor-pointer rounded-xl border bg-panel px-3 py-2.5 text-sm shadow-xl",
              t.level === "error" ? "border-bad/50 text-bad" : t.level === "success" ? "border-ok/50 text-ok" : "border-cy/40 text-fg")}>
            {t.text}
          </div>
        ))}
      </div>
      <ChangePassword open={pw} onClose={() => setPw(false)} />
    </div>
  );
}
