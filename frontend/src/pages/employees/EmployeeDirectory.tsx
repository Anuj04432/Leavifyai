import { useState, useEffect, FormEvent, ChangeEvent } from "react";
import {
  Users,
  Search,
  Plus,
  Upload,
  Building2,
  Mail,
  Loader2,
  CheckCircle2,
  AlertCircle,
  X,
  CreditCard,
  TrendingUp,
  Cpu,
  Layers,
  Sparkles,
  ArrowRight,
  Trash2,
  Pencil,
  ShieldCheck,
  Copy,
} from "lucide-react";
import { api } from "../../lib/api";
import { useAuthStore } from "../../store/authStore";
import Navbar from "../../components/layout/Navbar";

interface Department {
  id: string;
  name: string;
  code?: string;
}

interface Employee {
  id: string;
  employee_code: string;
  first_name: string;
  last_name: string;
  email: string;
  designation?: string | null;
  employment_type?: string | null;
  is_active: boolean;
  salary_basic: number | string;
  paypal_email: string | null;
  department_name?: string | null;
  department_id?: string | null;
  role?: string | null;
  permissions?: Record<string, boolean>;
}

interface RolePermissions {
  can_handle_paypal: boolean;
  can_run_payroll: boolean;
  can_approve_leaves: boolean;
  can_manage_roster: boolean;
  can_manage_policies: boolean;
}

const DEFAULT_ROLE_PERMISSIONS: Record<string, RolePermissions> = {
  ceo: {
    can_handle_paypal: true,
    can_run_payroll: true,
    can_approve_leaves: true,
    can_manage_roster: true,
    can_manage_policies: true,
  },
  admin: {
    can_handle_paypal: false,
    can_run_payroll: false,
    can_approve_leaves: true,
    can_manage_roster: true,
    can_manage_policies: true,
  },
  finance_manager: {
    can_handle_paypal: true,
    can_run_payroll: true,
    can_approve_leaves: false,
    can_manage_roster: false,
    can_manage_policies: false,
  },
  hr_manager: {
    can_handle_paypal: false,
    can_run_payroll: true,
    can_approve_leaves: true,
    can_manage_roster: true,
    can_manage_policies: false,
  },
  hr: {
    can_handle_paypal: false,
    can_run_payroll: true,
    can_approve_leaves: true,
    can_manage_roster: true,
    can_manage_policies: false,
  },
  content_manager: {
    can_handle_paypal: false,
    can_run_payroll: false,
    can_approve_leaves: false,
    can_manage_roster: false,
    can_manage_policies: true,
  },
  manager: {
    can_handle_paypal: false,
    can_run_payroll: false,
    can_approve_leaves: true,
    can_manage_roster: false,
    can_manage_policies: false,
  },
  employee: {
    can_handle_paypal: false,
    can_run_payroll: false,
    can_approve_leaves: false,
    can_manage_roster: false,
    can_manage_policies: false,
  },
};

const CAPABILITIES_LIST = [
  {
    key: "can_manage_roster",
    label: "Handle Employments (Add, Edit, and Remove Employees)",
    description: "Authority to add new personnel, update profiles, and remove/deactivate employee records",
  },
  {
    key: "can_handle_paypal",
    label: "Authorize & Disburse PayPal Transactions",
    description: "Execute PayPal sandbox batch payouts (Finance / Senior Posts)",
  },
  {
    key: "can_run_payroll",
    label: "Calculate & Lock Organization Payroll",
    description: "Run monthly deterministic payroll batches and deductions",
  },
  {
    key: "can_approve_leaves",
    label: "Triage & Approve Leave Requests",
    description: "Review employee leave requests against OKF policy guidelines",
  },
  {
    key: "can_manage_policies",
    label: "Manage Company OKF Policies",
    description: "Upload and modify company leave and operational policy documents",
  },
];

interface AnalyzeResult {
  total_rows: number;
  detected_columns: string[];
  mapped_fields: Record<string, string>;
  missing_fields: string[];
  sample_preview: Record<string, any>[];
}

export default function EmployeeDirectory() {
  const { user } = useAuthStore();

  const [employees, setEmployees] = useState<Employee[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedDept, setSelectedDept] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  // Modals
  const [showAddModal, setShowAddModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);

  // Add Employee Form State
  const [formData, setFormData] = useState({
    employee_code: "",
    first_name: "",
    last_name: "",
    work_email: "",
    initial_password: "",
    designation: "",
    employment_type: "full_time",
    base_salary: 75000,
    salary_currency: "USD",
    paypal_email: "",
    department_id: "",
    role: "employee",
    permissions: {
      can_handle_paypal: false,
      can_run_payroll: false,
      can_approve_leaves: false,
      can_manage_roster: false,
      can_manage_policies: false,
    },
  });
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Newly Created Credentials Card State
  const [createdCredentials, setCreatedCredentials] = useState<{
    name: string;
    email: string;
    role: string;
    permissions?: Record<string, boolean>;
    tempPassword?: string;
  } | null>(null);

  // Import State
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<AnalyzeResult | null>(null);
  const [importResult, setImportResult] = useState<{
    imported: number;
    errors: string[];
  } | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // Edit Employee State
  const [editingEmployee, setEditingEmployee] = useState<Employee | null>(null);
  const [editFormData, setEditFormData] = useState({
    first_name: "",
    last_name: "",
    designation: "",
    department_id: "",
    employment_type: "full_time",
    salary_basic: 0,
    paypal_email: "",
    role: "employee",
    is_active: true,
    permissions: {
      can_handle_paypal: false,
      can_run_payroll: false,
      can_approve_leaves: false,
      can_manage_roster: false,
      can_manage_policies: false,
    },
  });
  const [editSubmitting, setEditSubmitting] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  // Corporate Domain
  const companyDomain =
    user?.company_domain ||
    (user?.email?.includes("@") ? user.email.split("@")[1] : "company.workforce.io");

  const autoCorporateEmail = `${
    formData.first_name.toLowerCase().replace(/[^a-z0-9]/g, "") || "first"
  }.${
    formData.last_name.toLowerCase().replace(/[^a-z0-9]/g, "") || "last"
  }@${companyDomain}`;

  const fetchEmployees = async () => {
    try {
      setLoading(true);
      const params: Record<string, string> = {
        page_size: "100",
      };
      if (search) params.search = search;
      if (selectedDept) params.department_id = selectedDept;
      if (statusFilter !== "") {
        params.is_active = statusFilter;
        params.status = statusFilter;
      }

      const res = await api.get("/employees/", { params });
      setEmployees(res.data.items || []);
    } catch (err) {
      console.error("Failed to fetch employees", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchDepartments = async () => {
    try {
      const res = await api.get("/departments/");
      setDepartments(Array.isArray(res.data) ? res.data : res.data.items || []);
    } catch (err) {
      console.error("Failed to fetch departments", err);
    }
  };

  useEffect(() => {
    fetchDepartments();
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchEmployees();
    }, 200);
    return () => clearTimeout(timer);
  }, [search, selectedDept, statusFilter]);

  const handleOpenEdit = (emp: Employee) => {
    setEditingEmployee(emp);
    const existingPerms =
      emp.permissions ||
      DEFAULT_ROLE_PERMISSIONS[emp.role || "employee"] ||
      DEFAULT_ROLE_PERMISSIONS.employee;
    setEditFormData({
      first_name: emp.first_name,
      last_name: emp.last_name,
      designation: emp.designation || "",
      department_id: emp.department_id || "",
      employment_type: emp.employment_type || "full_time",
      salary_basic: Number(emp.salary_basic || 0),
      paypal_email: emp.paypal_email || "",
      role: emp.role || "employee",
      is_active: emp.is_active,
      permissions: {
        can_handle_paypal: !!existingPerms.can_handle_paypal,
        can_run_payroll: !!existingPerms.can_run_payroll,
        can_approve_leaves: !!existingPerms.can_approve_leaves,
        can_manage_roster: !!existingPerms.can_manage_roster,
        can_manage_policies: !!existingPerms.can_manage_policies,
      },
    });
    setEditError(null);
  };

  const handleUpdateEmployee = async (e: FormEvent) => {
    e.preventDefault();
    if (!editingEmployee) return;
    setEditSubmitting(true);
    setEditError(null);
    try {
      const payload: any = {
        first_name: editFormData.first_name,
        last_name: editFormData.last_name,
        designation: editFormData.designation || null,
        department_id: editFormData.department_id || null,
        employment_type: editFormData.employment_type,
        salary_basic: Number(editFormData.salary_basic || 0),
        paypal_email: editFormData.paypal_email || null,
        role: editFormData.role,
        permissions: editFormData.permissions,
        is_active: editFormData.is_active,
      };
      await api.put(`/employees/${editingEmployee.id}`, payload);
      setEditingEmployee(null);
      await fetchEmployees();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setEditError(typeof detail === "string" ? detail : "Failed to update employee.");
    } finally {
      setEditSubmitting(false);
    }
  };

  const handleDeleteEmployee = async (id: string, name: string) => {
    if (!window.confirm(`Are you sure you want to remove ${name} from the directory? This will purge or deactivate their personnel profile.`)) {
      return;
    }
    try {
      setDeletingId(id);
      await api.delete(`/employees/${id}`);
      await fetchEmployees();
    } catch (err) {
      console.error("Failed to remove employee", err);
      alert("Failed to remove employee. Please try again.");
    } finally {
      setDeletingId(null);
    }
  };

  const handleCreateEmployee = async (e: FormEvent) => {
    e.preventDefault();
    setFormSubmitting(true);
    setFormError(null);

    try {
      const payload: any = {
        employee_code: formData.employee_code || undefined,
        first_name: formData.first_name,
        last_name: formData.last_name,
        email: formData.work_email || undefined,
        initial_password: formData.initial_password.trim() || undefined,
        designation: formData.designation || undefined,
        employment_type: formData.employment_type,
        salary_basic: Number(formData.base_salary || 0),
        department_id: formData.department_id || undefined,
        paypal_email: formData.paypal_email || undefined,
        role: formData.role || "employee",
        permissions: formData.permissions,
      };

      const res = await api.post("/employees/", payload);
      const created = res.data;
      const actualPassword =
        created.initial_password ||
        formData.initial_password.trim() ||
        `Welcome@${(created.employee_code || "EMP").replace("-", "")}`;
      setCreatedCredentials({
        name: `${created.first_name} ${created.last_name}`,
        email: created.email,
        role: created.role,
        permissions: created.permissions || formData.permissions,
        tempPassword: actualPassword,
      });
      setShowAddModal(false);
      setFormData({
        employee_code: "",
        first_name: "",
        last_name: "",
        work_email: "",
        initial_password: "",
        designation: "",
        employment_type: "full_time",
        base_salary: 75000,
        salary_currency: "USD",
        paypal_email: "",
        department_id: "",
        role: "employee",
        permissions: {
          can_handle_paypal: false,
          can_run_payroll: false,
          can_approve_leaves: false,
          can_manage_roster: false,
          can_manage_policies: false,
        },
      });
      fetchEmployees();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setFormError(typeof detail === "string" ? detail : "Failed to create employee.");
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleFileSelect = async (file: File) => {
    setImportFile(file);
    setImportResult(null);
    setAnalysisResult(null);
    setAnalyzing(true);

    const data = new FormData();
    data.append("file", file);

    try {
      const res = await api.post("/employees/analyze-import", data, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setAnalysisResult(res.data);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setImportResult({
        imported: 0,
        errors: [typeof detail === "string" ? detail : "Failed to analyze file."],
      });
    } finally {
      setAnalyzing(false);
    }
  };

  const executeImport = async (autoGenerate: boolean) => {
    if (!importFile) return;

    setImporting(true);
    setImportResult(null);

    const data = new FormData();
    data.append("file", importFile);

    try {
      const res = await api.post(`/employees/import?auto_generate_missing=${autoGenerate}`, data, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setImportResult({
        imported: res.data.successful_count,
        errors: (res.data.errors || []).map((e: any) => `Row ${e.row}: ${e.error}`),
      });
      await fetchEmployees();
      await fetchDepartments();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setImportResult({
        imported: 0,
        errors: [typeof detail === "string" ? detail : "Import failed."],
      });
    } finally {
      setImporting(false);
    }
  };

  const isHrOrAdmin =
    user?.role === "ceo" ||
    user?.role === "super_admin" ||
    user?.role === "admin" ||
    user?.role === "hr" ||
    user?.role === "hr_manager" ||
    user?.role === "finance_manager" ||
    !!user?.permissions?.can_manage_roster;

  // Telemetry Calculations for the Asymmetric Side Panel
  const totalSalaries = employees.reduce(
    (acc, emp) => acc + Number(emp.salary_basic || 0),
    0
  );
  const paypalConfiguredCount = employees.filter((e) => !!e.paypal_email).length;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans antialiased">
      <Navbar />

      {/* Main Content Area */}
      <main className="flex-1 p-6 max-w-7xl w-full mx-auto space-y-6">
        {/* Title & Action Row */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              <Users className="w-5 h-5 text-indigo-400" />
              Employee Directory
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Workforce records, department assignments, and payout endpoints.
            </p>
          </div>

          {isHrOrAdmin && (
            <div className="flex items-center gap-2.5">
              <button
                onClick={() => {
                  setShowImportModal(true);
                  setImportResult(null);
                  setImportFile(null);
                }}
                className="px-3.5 py-1.5 bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-200 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer"
              >
                <Upload className="w-3.5 h-3.5 text-slate-400" />
                Import CSV
              </button>

              <button
                onClick={() => {
                  setShowAddModal(true);
                  setFormError(null);
                }}
                className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                Add Employee
              </button>
            </div>
          )}
        </div>

        {/* PASS 1: Asymmetric Structural Layout (8 Cols Main Table, 4 Cols Context Rail) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Main 8-Column Roster Area */}
          <div className="lg:col-span-8 space-y-4">
            {/* Search & Filter Toolbar */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 flex flex-col sm:flex-row gap-2.5">
              <div className="flex-1 relative">
                <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search by name, employee code, email..."
                  className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 outline-none transition"
                />
              </div>

              <div className="flex gap-2">
                <select
                  value={selectedDept}
                  onChange={(e) => setSelectedDept(e.target.value)}
                  className="bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 outline-none"
                >
                  <option value="">All Departments</option>
                  {departments.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
                </select>

                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 outline-none"
                >
                  <option value="">All Statuses</option>
                  <option value="true">Active</option>
                  <option value="false">Inactive</option>
                </select>
              </div>
            </div>

            {/* Employee Table */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
              {loading ? (
                <div className="p-12 text-center text-slate-400 flex flex-col items-center justify-center gap-2">
                  <Loader2 className="w-5 h-5 animate-spin text-indigo-400 motion-reduce:animate-none" />
                  <span className="text-xs font-medium">Querying Neon Postgres database…</span>
                </div>
              ) : employees.length === 0 ? (
                <div className="p-12 text-center text-slate-400">
                  <Users className="w-8 h-8 mx-auto text-slate-600 mb-2" />
                  <p className="text-xs font-semibold text-slate-300">No personnel records found</p>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    Adjust search criteria or create a new employee profile.
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-950/70 border-b border-slate-800 text-slate-400 text-xs">
                      <tr>
                        <th className="py-2.5 px-4 font-semibold">Employee</th>
                        <th className="py-2.5 px-4 font-semibold">Code</th>
                        <th className="py-2.5 px-4 font-semibold">Department</th>
                        <th className="py-2.5 px-4 font-semibold">Role</th>
                        <th className="py-2.5 px-4 font-semibold">Base Salary</th>
                        <th className="py-2.5 px-4 font-semibold">PayPal Payout</th>
                        <th className="py-2.5 px-4 font-semibold">Status</th>
                        <th className="py-2.5 px-4 font-semibold text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/80 text-slate-300">
                      {employees.map((emp) => (
                        <tr key={emp.id} className="hover:bg-slate-800/40 transition-colors">
                          <td className="py-3 px-4">
                            <div className="font-semibold text-white">
                              {emp.first_name} {emp.last_name}
                            </div>
                            <div className="text-[11px] text-slate-400 font-mono flex items-center gap-1 mt-0.5">
                              <Mail className="w-3 h-3 text-slate-500 shrink-0" />
                              {emp.email}
                            </div>
                          </td>
                          <td className="py-3 px-4 font-mono text-indigo-400 font-semibold text-[11px]">
                            {emp.employee_code}
                          </td>
                          <td className="py-3 px-4">
                            <span className="inline-flex items-center gap-1.5 text-slate-300">
                              <Building2 className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                              {emp.department_name || "General"}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-slate-300">
                            <div>{emp.designation || "Staff"}</div>
                            <div className="flex items-center gap-1.5 mt-0.5">
                              <span className="text-xs text-slate-400 capitalize">
                                {(emp.employment_type || "full_time").replace("_", " ")}
                              </span>
                              <span className="text-slate-600">•</span>
                              <span
                                className={`px-1.5 py-0.5 rounded text-xs capitalize font-medium ${
                                  emp.role === "ceo"
                                    ? "bg-amber-500/10 text-amber-300 border border-amber-500/20"
                                    : emp.role === "super_admin"
                                    ? "bg-purple-500/10 text-purple-400 border border-purple-500/20"
                                    : emp.role === "finance_manager" || emp.role === "ir_manager"
                                    ? "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                                    : emp.role === "hr" || emp.role === "hr_manager"
                                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                    : emp.role === "content_manager"
                                    ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20"
                                    : emp.role === "admin"
                                    ? "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20"
                                    : "bg-slate-800 text-slate-400 border border-slate-700/60"
                                }`}
                              >
                                {(emp.role || "employee").replace("_", " ")}
                              </span>
                              {emp.permissions?.can_manage_roster && (
                                <span className="px-1.5 py-0.5 rounded text-[10px] bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 font-medium">
                                  Employment Manager
                                </span>
                              )}
                              {emp.permissions?.can_handle_paypal && (
                                <span className="px-1.5 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 font-medium">
                                  PayPal Auth
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="py-3 px-4 font-mono font-medium text-slate-200">
                            ${Number(emp.salary_basic || 0).toLocaleString()} USD
                          </td>
                          <td className="py-3 px-4">
                            {emp.paypal_email ? (
                              <span className="text-emerald-400 font-mono text-xs">
                                {emp.paypal_email}
                              </span>
                            ) : (
                              <span className="text-slate-600 italic text-xs">Unlinked</span>
                            )}
                          </td>
                          <td className="py-3 px-4">
                            <span
                              className={`px-2 py-0.5 rounded text-xs font-medium ${
                                emp.is_active
                                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                  : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                              }`}
                            >
                              {emp.is_active ? "Active" : "Inactive"}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-right">
                            {isHrOrAdmin ? (
                              <div className="flex items-center justify-end gap-1">
                                <button
                                  type="button"
                                  onClick={() => handleOpenEdit(emp)}
                                  title="Edit employee profile"
                                  className="p-1.5 rounded-lg text-slate-400 hover:text-indigo-400 hover:bg-indigo-500/10 transition-colors cursor-pointer"
                                >
                                  <Pencil className="w-4 h-4" />
                                </button>
                                <button
                                  type="button"
                                  onClick={() =>
                                    handleDeleteEmployee(
                                      emp.id,
                                      `${emp.first_name} ${emp.last_name}`
                                    )
                                  }
                                  disabled={deletingId === emp.id}
                                  title="Remove employee record"
                                  className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors disabled:opacity-50 cursor-pointer"
                                >
                                  {deletingId === emp.id ? (
                                    <Loader2 className="w-4 h-4 animate-spin text-rose-400" />
                                  ) : (
                                    <Trash2 className="w-4 h-4" />
                                  )}
                                </button>
                              </div>
                            ) : (
                              <span className="text-slate-600 text-xs italic">View Only</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          {/* PASS 1: Asymmetric 4-Column Contextual Intelligence Rail */}
          <div className="lg:col-span-4 space-y-4">
            {/* Card 1: Live Workforce Telemetry */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <span className="text-xs font-semibold text-white flex items-center gap-1.5">
                  <TrendingUp className="w-3.5 h-3.5 text-indigo-400" />
                  Workforce Metrics
                </span>
                <span className="text-xs text-emerald-400 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse motion-reduce:animate-none" />
                  Live
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3 pt-1">
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800/80">
                  <div className="text-xs text-slate-400 font-medium">Headcount</div>
                  <div className="text-xl font-bold text-white mt-1 font-mono">
                    {employees.length}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Personnel records</div>
                </div>

                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800/80">
                  <div className="text-xs text-slate-400 font-medium">Monthly Run</div>
                  <div className="text-xl font-bold text-white mt-1 font-mono">
                    ${Math.round(totalSalaries / 12).toLocaleString()}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Base commitment</div>
                </div>
              </div>

              <div className="pt-2">
                <div className="flex items-center justify-between text-xs text-slate-300 mb-1">
                  <span>PayPal Payouts Coverage</span>
                  <span className="font-mono text-indigo-400">
                    {employees.length > 0
                      ? Math.round((paypalConfiguredCount / employees.length) * 100)
                      : 0}
                    %
                  </span>
                </div>
                <div className="w-full bg-slate-950 rounded-full h-1.5 border border-slate-800">
                  <div
                    className="bg-indigo-600 h-1.5 rounded-full"
                    style={{
                      width: `${
                        employees.length > 0
                          ? (paypalConfiguredCount / employees.length) * 100
                          : 0
                      }%`,
                    }}
                  />
                </div>
              </div>
            </div>

            {/* Card 2: Settlement & Integration Pipeline */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
              <div className="text-xs font-semibold text-white flex items-center gap-1.5 pb-2 border-b border-slate-800">
                <CreditCard className="w-3.5 h-3.5 text-indigo-400" />
                Settlement Rails
              </div>

              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950 border border-slate-800/80">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-emerald-400" />
                    <span className="text-white font-medium">PayPal Payouts API</span>
                  </div>
                  <span className="font-mono text-[10px] text-slate-400">Sandbox v1</span>
                </div>

                <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950 border border-slate-800/80">
                  <div className="flex items-center gap-2">
                    <Cpu className="w-3.5 h-3.5 text-indigo-400" />
                    <span className="text-white font-medium">Neon PostgreSQL</span>
                  </div>
                  <span className="font-mono text-[10px] text-emerald-400">pgvector 18.6</span>
                </div>

                <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950 border border-slate-800/80">
                  <div className="flex items-center gap-2">
                    <Layers className="w-3.5 h-3.5 text-slate-400" />
                    <span className="text-white font-medium">Active Departments</span>
                  </div>
                  <span className="font-mono text-[10px] text-indigo-400">
                    {departments.length} configured
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Add Employee Modal (Solid Dark Theme, No Glassmorphism) */}
      {showAddModal && (
        <div className="fixed inset-0 bg-slate-950/90 z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 overflow-y-auto max-h-[90vh]">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Plus className="w-4 h-4 text-indigo-400" />
                Add New Employee Profile
              </h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="text-slate-400 hover:text-white cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {formError && (
              <div className="mt-3 p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg text-rose-300 text-xs">
                {formError}
              </div>
            )}

            <form onSubmit={handleCreateEmployee} className="mt-4 space-y-3.5 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">
                    Employee Code *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="EMP-1001"
                    value={formData.employee_code}
                    onChange={(e) =>
                      setFormData({ ...formData, employee_code: e.target.value })
                    }
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-slate-200 outline-none focus:border-indigo-500 font-mono"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">
                    Department
                  </label>
                  <select
                    value={formData.department_id}
                    onChange={(e) =>
                      setFormData({ ...formData, department_id: e.target.value })
                    }
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-slate-200 outline-none focus:border-indigo-500"
                  >
                    <option value="">Select Department</option>
                    {departments.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">
                    First Name *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="Priya"
                    value={formData.first_name}
                    onChange={(e) =>
                      setFormData({ ...formData, first_name: e.target.value })
                    }
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-slate-200 outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">
                    Last Name *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="Nair"
                    value={formData.last_name}
                    onChange={(e) =>
                      setFormData({ ...formData, last_name: e.target.value })
                    }
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-slate-200 outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">
                    WorkforceAI Corporate Email
                  </label>
                  <input
                    type="email"
                    placeholder={autoCorporateEmail}
                    value={formData.work_email}
                    onChange={(e) =>
                      setFormData({ ...formData, work_email: e.target.value })
                    }
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-slate-200 outline-none focus:border-indigo-500 font-mono text-xs"
                  />
                  <div className="text-[10px] text-slate-500 mt-1">
                    Auto-derived on @{companyDomain}
                  </div>
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">
                    Initial Login Password
                  </label>
                  <input
                    type="text"
                    placeholder="Auto (Welcome@...)"
                    value={formData.initial_password}
                    onChange={(e) =>
                      setFormData({ ...formData, initial_password: e.target.value })
                    }
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-slate-200 outline-none focus:border-indigo-500 font-mono text-xs"
                  />
                  <div className="text-[10px] text-slate-500 mt-1">
                    Min 8 chars, or leave empty for auto
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">
                    Designation *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="Principal Engineer"
                    value={formData.designation}
                    onChange={(e) =>
                      setFormData({ ...formData, designation: e.target.value })
                    }
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-slate-200 outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">
                    Employment Type
                  </label>
                  <select
                    value={formData.employment_type}
                    onChange={(e) =>
                      setFormData({ ...formData, employment_type: e.target.value })
                    }
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-slate-200 outline-none focus:border-indigo-500"
                  >
                    <option value="full_time">Full Time</option>
                    <option value="part_time">Part Time</option>
                    <option value="contract">Contract</option>
                    <option value="intern">Intern</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">
                    Base Salary ($) *
                  </label>
                  <input
                    type="number"
                    required
                    min={0}
                    value={formData.base_salary}
                    onChange={(e) =>
                      setFormData({ ...formData, base_salary: Number(e.target.value) })
                    }
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-slate-200 outline-none focus:border-indigo-500 font-mono"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">
                    PayPal Payout Email
                  </label>
                  <input
                    type="email"
                    placeholder="priya.sandbox@paypal.com"
                    value={formData.paypal_email}
                    onChange={(e) =>
                      setFormData({ ...formData, paypal_email: e.target.value })
                    }
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-slate-200 outline-none focus:border-indigo-500 font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">
                  System Access Role
                </label>
                <select
                  value={formData.role}
                  onChange={(e) => {
                    const newRole = e.target.value;
                    const defaults =
                      DEFAULT_ROLE_PERMISSIONS[newRole] ||
                      DEFAULT_ROLE_PERMISSIONS.employee;
                    setFormData({
                      ...formData,
                      role: newRole,
                      permissions: { ...defaults },
                    });
                  }}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-slate-200 outline-none focus:border-indigo-500 font-mono text-[11px]"
                >
                  <option value="employee">Employee / Candidate (Self-Service Portal)</option>
                  <option value="manager">Lead / Manager (Team Leave Approvals)</option>
                  <option value="hr_manager">HR Manager (Leaves, Payroll Calculation, Roster)</option>
                  <option value="finance_manager">Finance Department Manager (PayPal Payouts & Payroll)</option>
                  <option value="content_manager">Content Manager (OKF Company Policies)</option>
                  <option value="admin">Administrator (Organization Management)</option>
                  <option value="ceo">CEO (Universal Executive Authority)</option>
                </select>
              </div>

              {/* Granular Capabilities & Permissions Matrix */}
              <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl space-y-2">
                <div className="flex items-center justify-between pb-1.5 border-b border-slate-800/80">
                  <span className="text-slate-200 font-semibold text-xs flex items-center gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
                    Assigned Capabilities (What this person can do)
                  </span>
                  <span className="text-[10px] text-slate-500 font-mono">
                    {Object.values(formData.permissions).filter(Boolean).length} / {CAPABILITIES_LIST.length} enabled
                  </span>
                </div>
                <div className="space-y-1.5 pt-0.5">
                  {CAPABILITIES_LIST.map((cap) => (
                    <label
                      key={cap.key}
                      className="flex items-start gap-2.5 p-2 rounded-lg hover:bg-slate-900 cursor-pointer border border-transparent hover:border-slate-800/60 transition"
                    >
                      <input
                        type="checkbox"
                        checked={!!formData.permissions[cap.key as keyof typeof formData.permissions]}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            permissions: {
                              ...formData.permissions,
                              [cap.key]: e.target.checked,
                            },
                          })
                        }
                        className="mt-0.5 rounded border-slate-700 bg-slate-900 text-indigo-600 focus:ring-0 cursor-pointer"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="text-slate-200 font-medium text-[11px] leading-tight">
                          {cap.label}
                        </div>
                        <div className="text-[10px] text-slate-500 leading-tight mt-0.5">
                          {cap.description}
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              <div className="pt-3 flex justify-end gap-2.5 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium transition cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium flex items-center gap-1.5 transition cursor-pointer"
                >
                  {formSubmitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Create Record
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Employee Modal */}
      {editingEmployee && (
        <div className="fixed inset-0 bg-slate-950/90 z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 overflow-y-auto max-h-[90vh]">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Pencil className="w-4 h-4 text-indigo-400" />
                Edit Profile: {editingEmployee.first_name} {editingEmployee.last_name}
              </h3>
              <button
                onClick={() => setEditingEmployee(null)}
                className="text-slate-400 hover:text-white cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {editError && (
              <div className="mt-3 p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg text-rose-300 text-xs">
                {editError}
              </div>
            )}

            <form onSubmit={handleUpdateEmployee} className="mt-4 space-y-3.5 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">
                    First Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={editFormData.first_name}
                    onChange={(e) =>
                      setEditFormData({ ...editFormData, first_name: e.target.value })
                    }
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-slate-200 outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">
                    Last Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={editFormData.last_name}
                    onChange={(e) =>
                      setEditFormData({ ...editFormData, last_name: e.target.value })
                    }
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-slate-200 outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">
                    Designation / Title
                  </label>
                  <input
                    type="text"
                    placeholder="Senior Engineer"
                    value={editFormData.designation}
                    onChange={(e) =>
                      setEditFormData({ ...editFormData, designation: e.target.value })
                    }
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-slate-200 outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">
                    Department
                  </label>
                  <select
                    value={editFormData.department_id}
                    onChange={(e) =>
                      setEditFormData({ ...editFormData, department_id: e.target.value })
                    }
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-slate-200 outline-none focus:border-indigo-500"
                  >
                    <option value="">No Department</option>
                    {departments.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">
                    Base Salary ($) *
                  </label>
                  <input
                    type="number"
                    required
                    min={0}
                    value={editFormData.salary_basic}
                    onChange={(e) =>
                      setEditFormData({
                        ...editFormData,
                        salary_basic: Number(e.target.value),
                      })
                    }
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-slate-200 outline-none focus:border-indigo-500 font-mono"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">
                    Employment Type
                  </label>
                  <select
                    value={editFormData.employment_type}
                    onChange={(e) =>
                      setEditFormData({
                        ...editFormData,
                        employment_type: e.target.value,
                      })
                    }
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-slate-200 outline-none focus:border-indigo-500"
                  >
                    <option value="full_time">Full Time</option>
                    <option value="part_time">Part Time</option>
                    <option value="contract">Contract</option>
                    <option value="intern">Intern</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">
                    PayPal Payout Email
                  </label>
                  <input
                    type="email"
                    placeholder="worker.sandbox@paypal.com"
                    value={editFormData.paypal_email}
                    onChange={(e) =>
                      setEditFormData({ ...editFormData, paypal_email: e.target.value })
                    }
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-slate-200 outline-none focus:border-indigo-500 font-mono"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">
                    Employment Status
                  </label>
                  <select
                    value={editFormData.is_active ? "true" : "false"}
                    onChange={(e) =>
                      setEditFormData({
                        ...editFormData,
                        is_active: e.target.value === "true",
                      })
                    }
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-slate-200 outline-none focus:border-indigo-500"
                  >
                    <option value="true">Active</option>
                    <option value="false">Inactive</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">
                  System Access Role
                </label>
                <select
                  value={editFormData.role}
                  onChange={(e) => {
                    const newRole = e.target.value;
                    const defaults =
                      DEFAULT_ROLE_PERMISSIONS[newRole] ||
                      DEFAULT_ROLE_PERMISSIONS.employee;
                    setEditFormData({
                      ...editFormData,
                      role: newRole,
                      permissions: { ...defaults },
                    });
                  }}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-slate-200 outline-none focus:border-indigo-500 font-mono text-[11px]"
                >
                  <option value="employee">Employee / Candidate (Self-Service Portal)</option>
                  <option value="manager">Lead / Manager (Team Leave Approvals)</option>
                  <option value="hr_manager">HR Manager (Leaves, Payroll Calculation, Roster)</option>
                  <option value="finance_manager">Finance Department Manager (PayPal Payouts & Payroll)</option>
                  <option value="content_manager">Content Manager (OKF Company Policies)</option>
                  <option value="admin">Administrator (Organization Management)</option>
                  <option value="ceo">CEO (Universal Executive Authority)</option>
                </select>
              </div>

              {/* Granular Capabilities & Permissions Matrix */}
              <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl space-y-2">
                <div className="flex items-center justify-between pb-1.5 border-b border-slate-800/80">
                  <span className="text-slate-200 font-semibold text-xs flex items-center gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
                    Assigned Capabilities (What this person can do)
                  </span>
                  <span className="text-[10px] text-slate-500 font-mono">
                    {Object.values(editFormData.permissions).filter(Boolean).length} / {CAPABILITIES_LIST.length} enabled
                  </span>
                </div>
                <div className="space-y-1.5 pt-0.5">
                  {CAPABILITIES_LIST.map((cap) => (
                    <label
                      key={cap.key}
                      className="flex items-start gap-2.5 p-2 rounded-lg hover:bg-slate-900 cursor-pointer border border-transparent hover:border-slate-800/60 transition"
                    >
                      <input
                        type="checkbox"
                        checked={!!editFormData.permissions[cap.key as keyof typeof editFormData.permissions]}
                        onChange={(e) =>
                          setEditFormData({
                            ...editFormData,
                            permissions: {
                              ...editFormData.permissions,
                              [cap.key]: e.target.checked,
                            },
                          })
                        }
                        className="mt-0.5 rounded border-slate-700 bg-slate-900 text-indigo-600 focus:ring-0 cursor-pointer"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="text-slate-200 font-medium text-[11px] leading-tight">
                          {cap.label}
                        </div>
                        <div className="text-[10px] text-slate-500 leading-tight mt-0.5">
                          {cap.description}
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              <div className="pt-3 flex justify-end gap-2.5 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setEditingEmployee(null)}
                  className="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium transition cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={editSubmitting}
                  className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium flex items-center gap-1.5 transition cursor-pointer"
                >
                  {editSubmitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Newly Provisioned Credentials Modal */}
      {createdCredentials && (
        <div className="fixed inset-0 bg-slate-950/90 z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-indigo-500/30 rounded-xl max-w-md w-full p-6 space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white tracking-tight">
                  Corporate Identity Provisioned
                </h3>
                <p className="text-xs text-slate-400">
                  WorkforceAI email and login issued for {createdCredentials.name}
                </p>
              </div>
            </div>

            <div className="bg-slate-950 border border-slate-800 rounded-xl p-3.5 space-y-3">
              <div>
                <span className="text-[10px] uppercase font-semibold text-slate-500 block mb-1">
                  Assigned Corporate Login Email
                </span>
                <div className="flex items-center justify-between bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg font-mono text-xs text-indigo-300">
                  <span className="truncate">{createdCredentials.email}</span>
                  <button
                    type="button"
                    onClick={() => navigator.clipboard.writeText(createdCredentials.email)}
                    title="Copy email"
                    className="ml-2 text-slate-400 hover:text-white"
                  >
                    <Copy className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              <div>
                <span className="text-[10px] uppercase font-semibold text-slate-500 block mb-1">
                  Temporary Master Password
                </span>
                <div className="flex items-center justify-between bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg font-mono text-xs text-amber-300">
                  <span>{createdCredentials.tempPassword}</span>
                  <button
                    type="button"
                    onClick={() =>
                      navigator.clipboard.writeText(createdCredentials.tempPassword || "")
                    }
                    title="Copy password"
                    className="ml-2 text-slate-400 hover:text-white"
                  >
                    <Copy className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs">
                <span className="text-slate-400 font-medium">System Role:</span>
                <span className="font-semibold text-white capitalize">
                  {createdCredentials.role.replace("_", " ")}
                </span>
              </div>
            </div>

            <p className="text-[11px] text-slate-400 leading-relaxed">
              No personal email was used. The member can immediately log in to WorkforceAI using this corporate email and temporary password.
            </p>

            <button
              type="button"
              onClick={() => setCreatedCredentials(null)}
              className="w-full py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold transition cursor-pointer"
            >
              Done & Return to Directory
            </button>
          </div>
        </div>
      )}

      {/* AI Smart CSV/Excel Import Modal */}
      {showImportModal && (
        <div className="fixed inset-0 bg-slate-950/90 z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-xl w-full p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                  <Sparkles className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">Smart Roster Ingestion & Column Harmonizer</h3>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Upload any CSV or Excel file. AI automatically structures columns and normalizes records.
                  </p>
                </div>
              </div>
              <button
                onClick={() => {
                  setShowImportModal(false);
                  setImportFile(null);
                  setAnalysisResult(null);
                  setImportResult(null);
                }}
                className="text-slate-400 hover:text-white cursor-pointer p-1 rounded-lg hover:bg-slate-800 transition-colors motion-reduce:transition-none"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-4 text-xs">
              {/* File Upload Zone */}
              <div className="border border-dashed border-slate-800 hover:border-slate-700 rounded-xl p-5 text-center cursor-pointer bg-slate-950">
                <input
                  type="file"
                  accept=".csv, .xlsx, .xls"
                  onChange={(e: ChangeEvent<HTMLInputElement>) => {
                    if (e.target.files && e.target.files[0]) {
                      handleFileSelect(e.target.files[0]);
                    }
                  }}
                  className="w-full text-xs text-slate-400 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-indigo-600 file:text-white hover:file:bg-indigo-500 cursor-pointer"
                />
                <span className="text-[11px] text-slate-500 block mt-2">
                  Accepts standard or non-standard CSV / Excel rosters.
                </span>
              </div>

              {/* Analyzing State */}
              {analyzing && (
                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-center gap-2.5 text-indigo-400">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="text-xs text-slate-300">
                    AI is analyzing column headers and structure…
                  </span>
                </div>
              )}

              {/* Analysis Result Card */}
              {analysisResult && (
                <div className="space-y-3">
                  {/* Found stats */}
                  <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between text-xs">
                    <span className="text-slate-400">Total Records Discovered:</span>
                    <span className="font-bold text-white font-mono">{analysisResult.total_rows} employees</span>
                  </div>

                  {/* Column mappings */}
                  <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-2">
                    <span className="text-xs text-slate-400 font-semibold block">
                      Auto-Harmonized Column Mappings
                    </span>
                    <div className="flex flex-wrap gap-1.5 max-h-32 overflow-y-auto">
                      {Object.entries(analysisResult.mapped_fields).map(([orig, target]) => (
                        <div
                          key={orig}
                          className="px-2 py-1 rounded bg-slate-900 border border-slate-800 text-[10px] font-mono flex items-center gap-1.5"
                        >
                          <span className="text-slate-400">{orig}</span>
                          <ArrowRight className="w-2.5 h-2.5 text-indigo-400" />
                          <span className="text-indigo-300 font-bold">{target}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Missing Columns Pop-up Alert */}
                  {analysisResult.missing_fields.length > 0 && (
                    <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-200 space-y-2">
                      <div className="flex items-center gap-2 font-bold text-xs text-amber-300">
                        <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
                        <span>Missing Required Columns Detected</span>
                      </div>
                      <p className="text-[11px] text-amber-300/80 leading-relaxed">
                        The file is missing:{" "}
                        <span className="font-mono font-semibold text-white">
                          {analysisResult.missing_fields.join(", ")}
                        </span>
                        . Would you like our AI to auto-generate unique corporate emails, infer designations from department/experience, and configure sandbox PayPal emails?
                      </p>
                      <div className="flex items-center gap-2 pt-1">
                        <button
                          type="button"
                          onClick={() => executeImport(true)}
                          disabled={importing}
                          className="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs flex items-center gap-1.5 transition-colors motion-reduce:transition-none cursor-pointer shadow-sm disabled:opacity-50 whitespace-nowrap"
                        >
                          {importing ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin motion-reduce:animate-none" />
                          ) : (
                            <Sparkles className="w-3.5 h-3.5 text-indigo-200" />
                          )}
                          Auto-Generate & Import Roster
                        </button>
                        <button
                          type="button"
                          onClick={() => executeImport(false)}
                          disabled={importing}
                          className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium text-xs transition-colors motion-reduce:transition-none cursor-pointer disabled:opacity-50 whitespace-nowrap"
                        >
                          Continue Without Generating
                        </button>
                      </div>
                    </div>
                  )}

                  {/* No missing columns: direct confirm */}
                  {analysisResult.missing_fields.length === 0 && (
                    <div className="pt-2 flex justify-end">
                      <button
                        type="button"
                        onClick={() => executeImport(true)}
                        disabled={importing}
                        className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs flex items-center gap-1.5 transition cursor-pointer shadow-sm"
                      >
                        {importing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                        Confirm & Import {analysisResult.total_rows} Records
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* Import Results */}
              {importResult && (
                <div
                  className={`p-3.5 rounded-xl text-xs space-y-1.5 ${
                    importResult.errors.length > 0 && importResult.imported === 0
                      ? "bg-rose-500/10 border border-rose-500/20 text-rose-300"
                      : "bg-emerald-500/10 border border-emerald-500/20 text-emerald-300"
                  }`}
                >
                  <div className="flex items-center gap-2 font-bold">
                    {importResult.imported > 0 ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    ) : (
                      <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                    )}
                    Successfully provisioned {importResult.imported} employees into the directory.
                  </div>
                  {importResult.errors.length > 0 && (
                    <div className="text-[11px] text-slate-400 pt-1">
                      <span className="font-semibold text-rose-400 block mb-0.5">Warnings / Skipped:</span>
                      <ul className="list-disc pl-4 space-y-0.5 max-h-24 overflow-y-auto">
                        {importResult.errors.slice(0, 5).map((err, i) => (
                          <li key={i}>{err}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="pt-3 flex justify-end gap-2 border-t border-slate-800">
              <button
                type="button"
                onClick={() => {
                  setShowImportModal(false);
                  setImportFile(null);
                  setAnalysisResult(null);
                  setImportResult(null);
                }}
                className="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium text-xs transition cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
