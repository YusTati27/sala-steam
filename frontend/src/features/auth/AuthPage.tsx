import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { Activity, Printer, BarChart3, CalendarDays } from "lucide-react";
import { useAuth } from "../../lib/auth";
import { Button, Field, Input } from "../../components/ui";

export default function AuthPage() {
  const { user, login, register } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to={user.role === "admin" ? "/admin" : "/"} replace />;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const u = mode === "login" ? await login(form.email, form.password) : await register(form.name, form.email, form.password);
      navigate(u.role === "admin" ? "/admin" : "/", { replace: true });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [k]: e.target.value });

  return (
    <div className="grid min-h-full lg:grid-cols-2">
      <div className="relative hidden flex-col justify-between overflow-hidden border-r border-line p-10 lg:flex">
        <div className="absolute -left-20 top-1/3 size-96 rounded-full bg-royal/20 blur-3xl" />
        <div className="absolute -right-10 bottom-0 size-80 rounded-full bg-cy/10 blur-3xl" />
        <div className="relative flex items-center gap-3">
          <div className="grid size-11 place-items-center rounded-xl bg-gradient-to-br from-cy to-royal text-ink"><Activity className="size-6" /></div>
          <span className="text-lg font-semibold">Sala STEAM</span>
        </div>
        <div className="relative max-w-md space-y-6">
          <h1 className="text-4xl font-semibold leading-tight tracking-tight">Todo lo que pasa en la sala, <span className="bg-gradient-to-r from-cy to-royal bg-clip-text text-transparent">en un solo lugar.</span></h1>
          <ul className="space-y-3 text-sm text-mute">
            <li className="flex items-center gap-3"><Printer className="size-5 text-cy" /> Consulta qué impresoras están libres y cuándo se liberan.</li>
            <li className="flex items-center gap-3"><CalendarDays className="size-5 text-cy" /> Reserva tu turno y sigue el avance de tus impresiones.</li>
            <li className="flex items-center gap-3"><BarChart3 className="size-5 text-cy" /> Analítica de uso, consumo y fallos para tomar decisiones.</li>
          </ul>
        </div>
        <p className="relative text-xs text-mute">Plataforma de gestión de recursos de la sala STEAM universitaria.</p>
      </div>
      <div className="flex items-center justify-center p-6">
        <form onSubmit={submit} className="animate-fade-up w-full max-w-sm space-y-4">
          <div className="lg:hidden mb-6 flex items-center gap-3"><div className="grid size-10 place-items-center rounded-xl bg-gradient-to-br from-cy to-royal text-ink"><Activity className="size-5" /></div><span className="font-semibold">Sala STEAM</span></div>
          <div>
            <h2 className="text-2xl font-semibold tracking-tight">{mode === "login" ? "Iniciar sesión" : "Crear cuenta de estudiante"}</h2>
            <p className="mt-1 text-sm text-mute">{mode === "login" ? "Ingresa con tu correo institucional." : "Las cuentas nuevas son de tipo Cliente."}</p>
          </div>
          {mode === "register" && <Field label="Nombre completo"><Input required minLength={2} value={form.name} onChange={set("name")} autoComplete="name" /></Field>}
          <Field label="Correo electrónico"><Input type="email" required value={form.email} onChange={set("email")} autoComplete="email" /></Field>
          <Field label="Contraseña" hint={mode === "register" ? "Mínimo 8 caracteres, con letras y números" : undefined}>
            <Input type="password" required value={form.password} onChange={set("password")} autoComplete={mode === "login" ? "current-password" : "new-password"} />
          </Field>
          {error && <p role="alert" className="rounded-xl border border-bad/40 bg-bad/10 p-2.5 text-sm text-bad">{error}</p>}
          <Button type="submit" loading={busy} className="w-full">{mode === "login" ? "Entrar" : "Registrarme"}</Button>
          <p className="text-center text-sm text-mute">
            {mode === "login" ? "¿No tienes cuenta?" : "¿Ya tienes cuenta?"}{" "}
            <button type="button" className="font-medium text-cy hover:underline" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}>
              {mode === "login" ? "Regístrate" : "Inicia sesión"}
            </button>
          </p>
        </form>
      </div>
    </div>
  );
}
