import { useState, useEffect, FormEvent, ChangeEvent } from "react";
import {
  Users,
  Search,
  Plus,
  Upload,
  LogOut,
  Building2,
  Mail,
  DollarSign,
  Loader2,
  CheckCircle2,
  AlertCircle,
  X,
} from "lucide-react";
import { api } from "../../lib/api";
import { useAuthStore } from "../../store/authStore";
import { useNavigate } from "react-router-dom";

interface Department {
  id: string;
  name: string;
  code: string;
}

interface Employee {
  id: string;
  employee_code: string;
  first_name: string;
  last_name: string;
  work_email: string;
  designation: string;
  employment_type: string;
  status: string;
  base_salary: number;
  salary_currency: string;
  paypal_email: string | null;
  department?: Department | null;
}

export default function EmployeeDirectory() {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();

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
    designation: "",
    employment_type: "full_time",
    base_salary: 75000,
    salary_currency: "USD",
    paypal_email: "",
    department_id: "",
  });
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Import State
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<{
    imported: number;
    errors: string[];
  } | null>(null);

  const fetchEmployees = async () => {
    try {
      setLoading(true);
      const params: Record<string, string> = {};
      if (search) params.search = search;
      if (selectedDept) params.department_id = selectedDept;
      if (statusFilter) params.status = statusFilter;

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
      setDepartments(res.data.items || []);
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

  const handleCreateEmployee = async (e: FormEvent) => {
    e.preventDefault();
    setFormSubmitting(true);
    setFormError(null);

    try {
      const payload: any = {
        ...formData,
        base_salary: Number(formData.base_salary),
        department_id: formData.department_id || undefined,
        paypal_email: formData.paypal_email || undefined,
      };

      await api.post("/employees/", payload);
      setShowAddModal(false);
      setFormData({
        employee_code: "",
        first_name: "",
        last_name: "",
        work_email: "",
        designation: "",
        employment_type: "full_time",
        base_salary: 75000,
        salary_currency: "USD",
        paypal_email: "",
        department_id: "",
      });
      fetchEmployees();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setFormError(typeof detail === "string" ? detail : "Failed to create employee.");
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleImportSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!importFile) return;

    setImporting(true);
    setImportResult(null);

    const data = new FormData();
    data.append("file", importFile);

    try {
      const res = await api.post("/employees/import", data, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setImportResult({
        imported: res.data.imported_count,
        errors: res.data.errors || [],
      });
      fetchEmployees();
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

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const isHrOrAdmin = user?.role === "admin" || user?.role === "hr";

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Top Navbar */}
      <header className="h-16 border-b border-slate-800 bg-slate-900/60 backdrop-blur px-6 flex items-center justify-between sticky top-0 z-30">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-indigo-600/20 border border-indigo-500/30 text-indigo-400 flex items-center justify-center font-bold">
            W
          </div>
          <div>
            <span className="font-bold text-white text-base">WorkforceAI</span>
            <span className="text-xs text-slate-400 block -mt-1">Personnel & Payroll</span>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="text-right hidden sm:block">
            <div className="text-sm font-semibold text-slate-200">
              {user?.full_name || user?.email}
            </div>
            <div className="text-xs">
              <span className="px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 uppercase font-semibold text-[10px]">
                {user?.role}
              </span>
            </div>
          </div>

          <button
            onClick={handleLogout}
            title="Log out"
            className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 p-6 max-w-7xl w-full mx-auto space-y-6">
        {/* Page Title & Actions */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2.5">
              <Users className="w-6 h-6 text-indigo-400" />
              Employee Directory
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Manage workforce records, department assignments, and payout settings.
            </p>
          </div>

          {isHrOrAdmin && (
            <div className="flex items-center gap-3">
              <button
                onClick={() => {
                  setShowImportModal(true);
                  setImportResult(null);
                  setImportFile(null);
                }}
                className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-xl text-xs font-semibold text-slate-200 flex items-center gap-2 transition"
              >
                <Upload className="w-4 h-4 text-slate-400" />
                Import CSV
              </button>

              <button
                onClick={() => {
                  setShowAddModal(true);
                  setFormError(null);
                }}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold flex items-center gap-2 shadow-lg shadow-indigo-600/25 transition"
              >
                <Plus className="w-4 h-4" />
                Add Employee
              </button>
            </div>
          )}
        </div>

        {/* Filter / Search Bar */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 flex flex-col md:flex-row gap-3">
          <div className="flex-1 relative">
            <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by name, employee code, email, designation..."
              className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl pl-10 pr-4 py-2 text-xs text-slate-200 placeholder-slate-500 outline-none"
            />
          </div>

          <div className="flex gap-3">
            <select
              value={selectedDept}
              onChange={(e) => setSelectedDept(e.target.value)}
              className="bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none"
            >
              <option value="">All Departments</option>
              {departments.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.code})
                </option>
              ))}
            </select>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none"
            >
              <option value="">All Statuses</option>
              <option value="active">Active</option>
              <option value="on_leave">On Leave</option>
              <option value="suspended">Suspended</option>
              <option value="terminated">Terminated</option>
            </select>
          </div>
        </div>

        {/* Employee Table */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
          {loading ? (
            <div className="p-12 text-center text-slate-400 flex flex-col items-center justify-center gap-3">
              <Loader2 className="w-6 h-6 animate-spin text-indigo-400" />
              <span className="text-xs">Loading employee records...</span>
            </div>
          ) : employees.length === 0 ? (
            <div className="p-12 text-center text-slate-400">
              <Users className="w-10 h-10 mx-auto text-slate-600 mb-2" />
              <p className="text-sm font-semibold text-slate-300">No employees found</p>
              <p className="text-xs text-slate-500 mt-1">
                Try adjusting your search criteria or add new employees above.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950/60 border-b border-slate-800 text-slate-400 uppercase font-semibold tracking-wider">
                  <tr>
                    <th className="py-3 px-4">Employee</th>
                    <th className="py-3 px-4">Code</th>
                    <th className="py-3 px-4">Department</th>
                    <th className="py-3 px-4">Designation</th>
                    <th className="py-3 px-4">Base Salary</th>
                    <th className="py-3 px-4">PayPal Payout</th>
                    <th className="py-3 px-4">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-300">
                  {employees.map((emp) => (
                    <tr key={emp.id} className="hover:bg-slate-800/30 transition">
                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-white">
                          {emp.first_name} {emp.last_name}
                        </div>
                        <div className="text-[11px] text-slate-400 flex items-center gap-1 mt-0.5">
                          <Mail className="w-3 h-3 text-slate-500" />
                          {emp.work_email}
                        </div>
                      </td>
                      <td className="py-3.5 px-4 font-mono text-indigo-400 font-semibold">
                        {emp.employee_code}
                      </td>
                      <td className="py-3.5 px-4">
                        <span className="inline-flex items-center gap-1 text-slate-300">
                          <Building2 className="w-3 h-3 text-slate-500" />
                          {emp.department?.name || "Unassigned"}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-slate-300">
                        {emp.designation}
                        <span className="block text-[10px] text-slate-500 uppercase">
                          {emp.employment_type.replace("_", " ")}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 font-semibold text-slate-200">
                        ${emp.base_salary.toLocaleString()} {emp.salary_currency}
                      </td>
                      <td className="py-3.5 px-4 text-slate-400">
                        {emp.paypal_email ? (
                          <span className="text-emerald-400 font-mono text-[11px]">
                            {emp.paypal_email}
                          </span>
                        ) : (
                          <span className="text-slate-600 italic">Not configured</span>
                        )}
                      </td>
                      <td className="py-3.5 px-4">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase ${
                            emp.status === "active"
                              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                              : emp.status === "on_leave"
                              ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                              : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                          }`}
                        >
                          {emp.status.replace("_", " ")}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>

      {/* Add Employee Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl overflow-y-auto max-h-[90vh]">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Plus className="w-5 h-5 text-indigo-400" />
                Add New Employee
              </h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {formError && (
              <div className="mt-4 p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-300 text-xs">
                {formError}
              </div>
            )}

            <form onSubmit={handleCreateEmployee} className="mt-4 space-y-4 text-xs">
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
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 outline-none focus:border-indigo-500"
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
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 outline-none focus:border-indigo-500"
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
                    placeholder="Aarav"
                    value={formData.first_name}
                    onChange={(e) =>
                      setFormData({ ...formData, first_name: e.target.value })
                    }
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">
                    Last Name *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="Patel"
                    value={formData.last_name}
                    onChange={(e) =>
                      setFormData({ ...formData, last_name: e.target.value })
                    }
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">
                  Work Email *
                </label>
                <input
                  type="email"
                  required
                  placeholder="aarav.patel@workforceai.local"
                  value={formData.work_email}
                  onChange={(e) =>
                    setFormData({ ...formData, work_email: e.target.value })
                  }
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">
                    Designation *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="Software Engineer"
                    value={formData.designation}
                    onChange={(e) =>
                      setFormData({ ...formData, designation: e.target.value })
                    }
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 outline-none focus:border-indigo-500"
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
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 outline-none focus:border-indigo-500"
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
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">
                    PayPal Payout Email
                  </label>
                  <input
                    type="email"
                    placeholder="aarav.sandbox@paypal.com"
                    value={formData.paypal_email}
                    onChange={(e) =>
                      setFormData({ ...formData, paypal_email: e.target.value })
                    }
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="pt-3 flex justify-end gap-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium shadow-lg shadow-indigo-600/25 flex items-center gap-2 transition"
                >
                  {formSubmitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Create Employee
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* CSV Import Modal */}
      {showImportModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Upload className="w-5 h-5 text-indigo-400" />
                Bulk Import Employees
              </h3>
              <button
                onClick={() => setShowImportModal(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleImportSubmit} className="mt-4 space-y-4 text-xs">
              <p className="text-slate-400 leading-relaxed">
                Upload a CSV or Excel file containing columns:{" "}
                <code className="text-indigo-300 bg-slate-950 px-1 py-0.5 rounded">
                  employee_code, first_name, last_name, work_email, designation, base_salary, paypal_email
                </code>
              </p>

              <div className="border-2 border-dashed border-slate-800 hover:border-slate-700 rounded-2xl p-6 text-center cursor-pointer bg-slate-950/40">
                <input
                  type="file"
                  accept=".csv, .xlsx, .xls"
                  onChange={(e: ChangeEvent<HTMLInputElement>) => {
                    if (e.target.files && e.target.files[0]) {
                      setImportFile(e.target.files[0]);
                    }
                  }}
                  className="w-full text-xs text-slate-400 file:mr-3 file:py-1.5 file:px-3 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-indigo-600 file:text-white hover:file:bg-indigo-500 cursor-pointer"
                />
              </div>

              {importResult && (
                <div
                  className={`p-3.5 rounded-xl text-xs ${
                    importResult.errors.length > 0
                      ? "bg-amber-500/10 border border-amber-500/20 text-amber-300"
                      : "bg-emerald-500/10 border border-emerald-500/20 text-emerald-300"
                  }`}
                >
                  <div className="flex items-center gap-2 font-semibold">
                    {importResult.errors.length === 0 ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    ) : (
                      <AlertCircle className="w-4 h-4 text-amber-400" />
                    )}
                    Imported {importResult.imported} records successfully.
                  </div>
                  {importResult.errors.length > 0 && (
                    <ul className="list-disc pl-5 mt-2 space-y-0.5 text-[11px]">
                      {importResult.errors.slice(0, 5).map((err, i) => (
                        <li key={i}>{err}</li>
                      ))}
                      {importResult.errors.length > 5 && (
                        <li>...and {importResult.errors.length - 5} more issues</li>
                      )}
                    </ul>
                  )}
                </div>
              )}

              <div className="pt-2 flex justify-end gap-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowImportModal(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium transition"
                >
                  Close
                </button>
                <button
                  type="submit"
                  disabled={!importFile || importing}
                  className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium shadow-lg shadow-indigo-600/25 flex items-center gap-2 transition"
                >
                  {importing && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Upload & Import
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
