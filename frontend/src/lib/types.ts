export type Role = "client" | "admin";
export interface User {
  id: number;
  name: string;
  email: string;
  role: Role;
  is_active: boolean;
  is_demo: boolean;
  created_at: string;
}
export interface Config {
  mode: "demo" | "real";
  demo: boolean;
  simulator_enabled: boolean;
  open_hours_per_day: number;
  utc_offset_hours: number;
}

export type EquipmentStatus = "available" | "busy" | "maintenance" | "out_of_service";
export interface CurrentJob {
  id: number;
  project_name: string;
  progress_pct: number;
  estimated_end_at: string | null;
  is_mine: boolean;
}
export interface Equipment {
  id: number;
  code: string;
  name: string;
  model: string;
  type: "printer_3d" | "tool" | "other";
  status: EquipmentStatus;
  build_volume: string;
  nozzle_mm: number | null;
  supported_materials: string[];
  specs: Record<string, unknown>;
  hardware_endpoint: string | null;
  acquired_at: string | null;
  last_maintenance_at: string | null;
  next_maintenance_at: string | null;
  notes: string | null;
  is_demo: boolean;
  current_job: CurrentJob | null;
  available_at: string | null;
  queue_length: number;
  queue_clear_at: string | null;
  maintenance_days_left: number | null;
}

export interface Filament {
  id: number;
  code: string;
  material: string;
  brand: string;
  color: string;
  color_hex: string;
  initial_weight_g: number | null;
  available_weight_g: number;
  consumed_g: number | null;
  low_stock_threshold_g: number | null;
  acquired_at: string | null;
  is_active: boolean;
  is_demo: boolean;
  stock_status: "available" | "low" | "empty";
  notes: string | null;
}
export interface MaterialSummary {
  material: string;
  available_g: number;
  spools: number;
  colors: string[];
  status: "available" | "low" | "empty";
}
export interface Movement {
  id: number;
  filament_id: number;
  filament: string;
  type: "in" | "out" | "adjust";
  grams: number;
  balance_after_g: number;
  note: string;
  job_id: number | null;
  created_at: string;
}

export type JobStatus = "pending" | "queued" | "printing" | "completed" | "cancelled" | "failed";
export interface Job {
  id: number;
  user_id: number;
  user_name: string | null;
  project_name: string;
  printer_id: number | null;
  printer_name: string | null;
  filament_id: number | null;
  material: string | null;
  color: string | null;
  color_hex: string | null;
  status: JobStatus;
  grams_estimated: number;
  grams_used: number;
  estimated_minutes: number;
  progress_pct: number;
  queue_position: number | null;
  estimated_end_at: string | null;
  failure_reason: string | null;
  notes: string | null;
  is_mine: boolean;
  is_demo: boolean;
  created_at: string;
  queued_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  duration_min: number | null;
}

export type ReservationStatus = "pending" | "approved" | "rejected" | "cancelled" | "completed";
export interface Reservation {
  id: number;
  user_id: number;
  user_name: string | null;
  printer_id: number;
  printer_name: string | null;
  start_at: string;
  end_at: string;
  status: ReservationStatus;
  purpose: string;
  admin_note: string;
  is_mine: boolean;
  is_demo: boolean;
  created_at: string;
}
export interface Slot {
  start_at: string;
  end_at: string;
  status: string;
  is_mine: boolean;
}

export interface Maintenance {
  id: number;
  equipment_id: number;
  equipment_name: string;
  equipment_code: string;
  type: "preventive" | "corrective";
  status: "scheduled" | "in_progress" | "done";
  description: string;
  scheduled_for: string | null;
  performed_at: string | null;
  next_due_at: string | null;
  cost: number | null;
  is_demo: boolean;
}
export interface Attention {
  equipment_id: number;
  name: string;
  code: string;
  status: string;
  reason: "vencido" | "proximo" | "fuera_de_servicio";
  days_left: number | null;
  next_maintenance_at: string | null;
}
export interface Alert {
  type: string;
  severity: "critical" | "warning" | "info";
  title: string;
  detail: string;
  entity: string;
  entity_id: number | null;
}

export interface Kpis {
  total_jobs: number;
  completed: number;
  failed: number;
  cancelled: number;
  active: number;
  success_rate: number | null;
  completion_rate: number | null;
  grams_total: number;
  grams_wasted: number;
  waste_pct: number | null;
  print_hours: number;
  avg_duration_min: number | null;
  avg_grams: number | null;
}
export interface Insight {
  level: "critical" | "warning" | "info" | "positive";
  title: string;
  detail: string;
  action: string;
}
export interface PeriodRow {
  period: string;
  label: string;
  completed: number;
  failed: number;
  cancelled: number;
  active: number;
  total: number;
  success_rate: number | null;
}
export interface Overview {
  demo: boolean;
  period: { from: string; to: string; days: number; granularity: "day" | "week" | "month"; previous_from: string; previous_to: string };
  assumptions: { open_hours_per_day: number; utilization: string; success_rate: string; completion_rate: string };
  kpis: Kpis;
  comparison: Record<string, { current: number | null; previous: number | null; delta: number | null; delta_pct: number | null }> | null;
  status_distribution: { status: string; count: number }[];
  jobs_by_period: PeriodRow[];
  consumption_by_period: { materials: string[]; rows: ({ period: string; label: string; total_g: number; wasted_g: number } & Record<string, number | string>)[] };
  printers: {
    printer_id: number;
    name: string;
    jobs: number;
    completed: number;
    failed: number;
    hours: number;
    utilization_pct: number;
    success_rate: number | null;
    grams: number;
    avg_duration_min: number | null;
  }[];
  materials: { material: string; grams: number; jobs: number; share_pct: number; success_rate: number | null; failed: number; waste_pct: number | null }[];
  colors: { color: string; hex: string; grams: number; jobs: number; share_pct: number }[];
  failure_reasons: { reason: string; label: string; count: number; pct: number }[];
  demand_heatmap: { weekday: number; hour: number; jobs: number }[];
  stock_forecast: { material: string; available_g: number; daily_g: number; days_left: number | null }[];
  top_users: { name: string; jobs: number; grams: number }[];
  insights: Insight[];
  generated_at: string;
}
export interface Dashboard {
  demo: boolean;
  printers: { total: number; available: number; busy: number; maintenance: number; out_of_service: number };
  jobs: { completed: number; failed: number; cancelled: number; pending: number; printing: number; completion_pct: number | null };
  maintenance_alerts: number;
  low_stock: number;
  pending_reservations: number;
  last_30_days: {
    kpis: Kpis;
    comparison: Overview["comparison"];
    series: PeriodRow[];
    granularity: string;
    insights: Insight[];
  };
  alerts: Alert[];
  printing_now: { printer: string; project: string; progress_pct: number }[];
}
