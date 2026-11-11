import { lazy, Suspense, type ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./lib/auth";
import type { Role } from "./lib/types";
import AppShell from "./layouts/AppShell";
import AuthPage from "./features/auth/AuthPage";
import { AvailabilityPage, FilamentsPage, HistoryPage, QueuePage, ReservationsPage } from "./features/client/ClientPages";
import { Loading } from "./components/ui";

const DashboardPage = lazy(() => import("./features/admin/DashboardPage"));
const EquipmentPage = lazy(() => import("./features/admin/EquipmentPage"));
const InventoryPage = lazy(() => import("./features/admin/InventoryPage"));
const JobsPage = lazy(() => import("./features/admin/JobsPage"));
const AdminReservationsPage = lazy(() => import("./features/admin/AdminReservationsPage"));
const MaintenancePage = lazy(() => import("./features/admin/MaintenancePage"));
const StatisticsPage = lazy(() => import("./features/admin/StatisticsPage"));
const UsersPage = lazy(() => import("./features/admin/UsersPage"));
const SettingsPage = lazy(() => import("./features/admin/SettingsPage"));

/** Protege rutas por rol. El backend también valida: esto solo evita mostrar pantallas que fallarían. */
function Guard({ role, children }: { role: Role; children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <Loading />;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== role) return <Navigate to={user.role === "admin" ? "/admin" : "/"} replace />;
  return <>{children}</>;
}

function Authed() {
  const { user, loading } = useAuth();
  if (loading) return <Loading />;
  if (!user) return <Navigate to="/login" replace />;
  return <AppShell />;
}

export default function App() {
  return (
    <Suspense fallback={<Loading />}>
      <Routes>
        <Route path="/login" element={<AuthPage />} />
        <Route element={<Authed />}>
          <Route path="/" element={<Guard role="client"><AvailabilityPage /></Guard>} />
          <Route path="/filamentos" element={<Guard role="client"><FilamentsPage /></Guard>} />
          <Route path="/cola" element={<Guard role="client"><QueuePage /></Guard>} />
          <Route path="/reservas" element={<Guard role="client"><ReservationsPage /></Guard>} />
          <Route path="/historial" element={<Guard role="client"><HistoryPage /></Guard>} />
          <Route path="/admin" element={<Guard role="admin"><DashboardPage /></Guard>} />
          <Route path="/admin/equipos" element={<Guard role="admin"><EquipmentPage /></Guard>} />
          <Route path="/admin/inventario" element={<Guard role="admin"><InventoryPage /></Guard>} />
          <Route path="/admin/trabajos" element={<Guard role="admin"><JobsPage /></Guard>} />
          <Route path="/admin/reservas" element={<Guard role="admin"><AdminReservationsPage /></Guard>} />
          <Route path="/admin/mantenimiento" element={<Guard role="admin"><MaintenancePage /></Guard>} />
          <Route path="/admin/estadisticas" element={<Guard role="admin"><StatisticsPage /></Guard>} />
          <Route path="/admin/usuarios" element={<Guard role="admin"><UsersPage /></Guard>} />
          <Route path="/admin/configuracion" element={<Guard role="admin"><SettingsPage /></Guard>} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}
