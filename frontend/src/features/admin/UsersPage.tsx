import { useState } from "react";
import { KeyRound, Plus, Search, UserCog } from "lucide-react";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { useAction, useGet } from "../../lib/hooks";
import type { Role, User } from "../../lib/types";
import { fmtDate } from "../../lib/format";
import { Badge, Button, DataTable, DemoBadge, Empty, ErrorBox, Field, Input, Loading, Modal, PageHeader, Select } from "../../components/ui";

function CreateUser({ onClose }: { onClose: () => void }) {
  const [f, setF] = useState({ name: "", email: "", password: "", role: "client", admin_pin: "" });
  const m = useAction(() => api("/users", { body: { ...f, admin_pin: f.role === "admin" ? f.admin_pin : undefined } }), { invalidate: ["users"], success: "Usuario creado", onSuccess: onClose });
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setF({ ...f, [k]: e.target.value });
  return (
    <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); m.mutate(); }}>
      <Field label="Nombre completo"><Input required minLength={2} value={f.name} onChange={set("name")} /></Field>
      <Field label="Correo"><Input type="email" required value={f.email} onChange={set("email")} /></Field>
      <Field label="Contraseña temporal" hint="Mínimo 8 caracteres, con letras y números. El usuario puede cambiarla luego."><Input type="password" required minLength={8} value={f.password} onChange={set("password")} autoComplete="new-password" /></Field>
      <Field label="Rol"><Select value={f.role} onChange={set("role")}><option value="client">Cliente</option><option value="admin">Administrador</option></Select></Field>
      {f.role === "admin" && <Field label="PIN de administrador" hint="Obligatorio para añadir administradores"><Input type="password" inputMode="numeric" required autoComplete="off" value={f.admin_pin} onChange={set("admin_pin")} /></Field>}
      <div className="flex justify-end gap-2"><Button type="button" variant="ghost" onClick={onClose}>Cancelar</Button><Button type="submit" loading={m.isPending}>Crear usuario</Button></div>
    </form>
  );
}

function Reset({ u, onClose }: { u: User; onClose: () => void }) {
  const [pw, setPw] = useState("");
  const m = useAction(() => api(`/users/${u.id}/reset-password`, { body: { new_password: pw } }), { success: "Contraseña restablecida", onSuccess: onClose });
  return (
    <Modal open onClose={onClose} title={`Restablecer contraseña: ${u.name}`}>
      <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); m.mutate(); }}>
        <Field label="Nueva contraseña" hint="Mínimo 8 caracteres, con letras y números"><Input type="password" required minLength={8} value={pw} onChange={(e) => setPw(e.target.value)} autoComplete="new-password" /></Field>
        <div className="flex justify-end gap-2"><Button type="button" variant="ghost" onClick={onClose}>Cancelar</Button><Button type="submit" loading={m.isPending}>Restablecer</Button></div>
      </form>
    </Modal>
  );
}

function Promote({ u, onClose }: { u: User; onClose: () => void }) {
  const [pin, setPin] = useState("");
  const m = useAction(() => api(`/users/${u.id}`, { method: "PATCH", body: { role: "admin", admin_pin: pin } }), { invalidate: ["users"], success: "Ahora es administrador", onSuccess: onClose });
  return (
    <Modal open onClose={onClose} title={`Hacer administrador a ${u.name}`}>
      <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); m.mutate(); }}>
        <Field label="PIN de administrador"><Input type="password" inputMode="numeric" required autoComplete="off" autoFocus value={pin} onChange={(e) => setPin(e.target.value)} /></Field>
        <div className="flex justify-end gap-2"><Button type="button" variant="ghost" onClick={onClose}>Cancelar</Button><Button type="submit" loading={m.isPending}>Confirmar</Button></div>
      </form>
    </Modal>
  );
}

export default function UsersPage() {
  const { user: me } = useAuth();
  const [q, setQ] = useState("");
  const [role, setRole] = useState("");
  const { data, isLoading, error } = useGet<User[]>("users", "/users", { q, role });
  const [creating, setCreating] = useState(false);
  const [reset, setReset] = useState<User | null>(null);
  const [promote, setPromote] = useState<User | null>(null);
  const patch = useAction((v: { id: number; body: Partial<{ role: Role; is_active: boolean }> }) => api(`/users/${v.id}`, { method: "PATCH", body: v.body }), { invalidate: ["users"], success: "Usuario actualizado" });
  return (
    <>
      <PageHeader title="Usuarios" subtitle="Gestiona cuentas y roles. Los clientes no acceden al panel administrativo." actions={<Button onClick={() => setCreating(true)}><Plus className="size-4" /> Nuevo usuario</Button>} />
      <div className="mb-3 flex flex-wrap gap-2">
        <div className="relative min-w-52 flex-1"><Search className="pointer-events-none absolute left-3 top-2.5 size-4 text-mute" /><Input className="pl-9" placeholder="Buscar por nombre o correo" value={q} onChange={(e) => setQ(e.target.value)} /></div>
        <Select className="!w-auto" value={role} onChange={(e) => setRole(e.target.value)}><option value="">Todos los roles</option><option value="client">Clientes</option><option value="admin">Administradores</option></Select>
      </div>
      <ErrorBox error={error} />
      {isLoading ? <Loading /> : !data?.length ? <Empty icon={<UserCog className="size-8" />} title="Sin usuarios" /> : (
        <DataTable head={["Nombre", "Correo", "Rol", "Estado", "Alta", ""]}>
          {data.map((u) => (
            <tr key={u.id} className={u.is_active ? "" : "opacity-60"}>
              <td className="font-medium">{u.name} {u.is_demo && <DemoBadge />}{u.id === me?.id && <Badge tone="cy" className="ml-1.5">tú</Badge>}</td><td className="text-xs">{u.email}</td>
              <td><Badge tone={u.role === "admin" ? "royal" : "cy"}>{u.role === "admin" ? "Administrador" : "Cliente"}</Badge></td>
              <td><Badge tone={u.is_active ? "ok" : "bad"}>{u.is_active ? "Activo" : "Desactivado"}</Badge></td><td className="text-xs">{fmtDate(u.created_at)}</td>
              <td className="whitespace-nowrap text-right">
                {!u.is_demo && <>
                  <Button size="sm" variant="outline" disabled={u.id === me?.id} onClick={() => (u.role === "admin" ? patch.mutate({ id: u.id, body: { role: "client" } }) : setPromote(u))}>{u.role === "admin" ? "Hacer cliente" : "Hacer admin"}</Button>{" "}
                  <Button size="sm" variant="ghost" disabled={u.id === me?.id} onClick={() => patch.mutate({ id: u.id, body: { is_active: !u.is_active } })}>{u.is_active ? "Desactivar" : "Activar"}</Button>
                  <Button size="sm" variant="ghost" onClick={() => setReset(u)} aria-label="Restablecer contraseña" title="Restablecer contraseña"><KeyRound className="size-3.5" /></Button>
                </>}
              </td>
            </tr>
          ))}
        </DataTable>
      )}
      <Modal open={creating} onClose={() => setCreating(false)} title="Nuevo usuario"><CreateUser onClose={() => setCreating(false)} /></Modal>
      {reset && <Reset u={reset} onClose={() => setReset(null)} />}
      {promote && <Promote u={promote} onClose={() => setPromote(null)} />}
    </>
  );
}
