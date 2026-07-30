import { useEffect, useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import { Upload, Plus, Pencil, Save, X, Trash2, CheckCircle2, AlertCircle } from 'lucide-react'
import { salariesApi } from '../services'
import { getErrorMessage } from '../services/apiClient'
import { DataTable } from '../components/DataTable'
import { Button, Input, PageHeader, Skeleton } from '../components/ui'
import { formatMoney, clsx } from '../utils/format'

type SalaryRow = {
  id: number
  employee_id: string
  employee_name: string
  department?: string
  monthly_salary: number
  effective_from: string | null
}

function AddSalaryModal({ onClose, onSave }: { onClose: () => void, onSave: (data: any) => Promise<void> }) {
  const [empId, setEmpId] = useState('')
  const [empName, setEmpName] = useState('')
  const [salary, setSalary] = useState('')
  const [date, setDate] = useState('')
  const [loading, setLoading] = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!empId || !salary) {
      toast.error('Employee ID and Salary are required')
      return
    }
    const val = Number(salary)
    if (isNaN(val) || val <= 0) {
      toast.error('Salary must be a positive number')
      return
    }
    setLoading(true)
    try {
      await onSave({ employee_id: empId, employee_name: empName, monthly_salary: val, effective_from: date || null })
      onClose()
    } catch (e) {
      // handled
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm transition-all duration-300">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl dark:bg-ink-900 border border-ink-100 dark:border-ink-800 animate-in fade-in zoom-in-95">
        <div className="mb-6 flex items-center justify-between">
          <h3 className="text-xl font-bold text-ink-900 dark:text-ink-50">Add Salary</h3>
          <button onClick={onClose} className="rounded-full p-2 text-ink-500 hover:bg-ink-100 hover:text-ink-700 dark:hover:bg-ink-800 dark:hover:text-ink-300 transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>
        <form onSubmit={submit} className="space-y-5">
          <div>
            <label className="mb-1.5 block text-sm font-semibold text-ink-700 dark:text-ink-300">Employee ID *</label>
            <Input required value={empId} onChange={e => setEmpId(e.target.value)} placeholder="e.g. EMP001" className="bg-ink-50 dark:bg-ink-950" />
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-semibold text-ink-700 dark:text-ink-300">Employee Name</label>
            <Input value={empName} onChange={e => setEmpName(e.target.value)} placeholder="e.g. John Doe" className="bg-ink-50 dark:bg-ink-950" />
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-semibold text-ink-700 dark:text-ink-300">Monthly Salary *</label>
            <Input required type="number" min="1" step="0.01" value={salary} onChange={e => setSalary(e.target.value)} placeholder="50000" className="bg-ink-50 dark:bg-ink-950" />
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-semibold text-ink-700 dark:text-ink-300">Effective From</label>
            <Input type="date" value={date} onChange={e => setDate(e.target.value)} className="bg-ink-50 dark:bg-ink-950" />
          </div>
          <div className="mt-8 flex justify-end gap-3 pt-2">
            <Button type="button" variant="secondary" onClick={onClose} disabled={loading} className="px-5">Cancel</Button>
            <Button type="submit" disabled={loading} className="px-6">Save Salary</Button>
          </div>
        </form>
      </div>
    </div>
  )
}

export function SalariesPage() {
  const [rows, setRows] = useState<SalaryRow[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  
  // drafts maps employee_id to the draft string value
  const [drafts, setDrafts] = useState<Record<string, string>>({})
  const [showAdd, setShowAdd] = useState(false)
  const [saving, setSaving] = useState(false)

  async function load() {
    setLoading(true)
    try {
      const data = await salariesApi.list()
      setRows(data as any)
      setDrafts({})
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to load salaries'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const { configured, missing } = useMemo(() => {
    let c = 0, m = 0
    rows.forEach(r => {
      if (r.monthly_salary > 0) c++
      else m++
    })
    return { configured: c, missing: m }
  }, [rows])

  const filteredRows = useMemo(() => {
    const s = search.toLowerCase()
    return rows.filter(r => 
      (r.employee_name || '').toLowerCase().includes(s) || 
      r.employee_id.toLowerCase().includes(s) ||
      (r.department || '').toLowerCase().includes(s) ||
      r.monthly_salary.toString().includes(s)
    )
  }, [rows, search])

  async function saveAll() {
    const updates = []
    for (const [empId, valStr] of Object.entries(drafts)) {
      const val = Number(valStr)
      if (isNaN(val) || val <= 0) {
        toast.error(`Invalid salary for ${empId}. Must be > 0.`)
        return
      }
      const row = rows.find(r => r.employee_id === empId)
      if (row) {
        updates.push({
          id: row.id,
          employee_id: row.employee_id,
          employee_name: row.employee_name,
          monthly_salary: val
        })
      }
    }

    if (updates.length === 0) return

    setSaving(true)
    try {
      await salariesApi.bulkUpdate(updates)
      toast.success(`Saved ${updates.length} salaries`)
      await load()
    } catch (e) {
      toast.error(getErrorMessage(e, 'Failed to save salaries'))
    } finally {
      setSaving(false)
    }
  }

  async function handleAdd(data: any) {
    try {
      await salariesApi.create(data)
      toast.success('Salary added')
      await load()
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to add salary'))
      throw error
    }
  }

  async function handleDelete(id: number) {
    if (!confirm('Are you sure you want to delete this salary override?')) return
    try {
      await salariesApi.delete(id)
      toast.success('Salary deleted')
      load()
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to delete salary'))
    }
  }

  const hasDrafts = Object.keys(drafts).length > 0

  return (
    <div className="space-y-6">
      <PageHeader
        title="Employee Salaries"
        subtitle="Manage flat monthly salaries for payroll generation."
        actions={
          <div className="flex gap-3">
            <Link to="/payroll/salaries/import">
              <Button variant="secondary" className="gap-2 shadow-sm font-medium">
                <Upload className="h-4 w-4" /> Import Salaries
              </Button>
            </Link>
            <Button onClick={() => setShowAdd(true)} className="gap-2 shadow-sm font-medium bg-brand-600 hover:bg-brand-700">
              <Plus className="h-4 w-4" /> Add Salary
            </Button>
          </div>
        }
      />

      {showAdd && (
        <AddSalaryModal onClose={() => setShowAdd(false)} onSave={handleAdd} />
      )}

      <div className="grid gap-6 mb-8" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))' }}>
        <div className="rounded-xl border border-ink-200 bg-white p-6 shadow-sm dark:border-ink-800 dark:bg-ink-950 flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-ink-500 dark:text-ink-400">Total Employees</p>
            <p className="text-4xl font-display font-bold text-ink-900 dark:text-ink-50 mt-1">{rows.length}</p>
          </div>
          <div className="h-14 w-14 rounded-full bg-brand-100 flex items-center justify-center dark:bg-brand-900/30">
            <CheckCircle2 className="h-8 w-8 text-brand-600 dark:text-brand-400" />
          </div>
        </div>
        <div className="rounded-xl border border-green-200 bg-green-50 p-6 shadow-sm dark:border-green-900/30 dark:bg-green-950/20 flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-green-700 dark:text-green-400">Configured</p>
            <p className="text-4xl font-display font-bold text-green-700 dark:text-green-400 mt-1">{configured}</p>
          </div>
          <div className="h-14 w-14 rounded-full bg-green-200/50 flex items-center justify-center dark:bg-green-900/50">
            <CheckCircle2 className="h-8 w-8 text-green-600 dark:text-green-400" />
          </div>
        </div>
        <div className={clsx("rounded-xl border p-6 shadow-sm flex items-center justify-between transition-colors", missing > 0 ? "border-red-200 bg-red-50 dark:border-red-900/30 dark:bg-red-950/20" : "border-ink-200 bg-white dark:border-ink-800 dark:bg-ink-950")}>
          <div>
            <p className={clsx("text-sm font-medium", missing > 0 ? "text-red-700 dark:text-red-400" : "text-ink-500 dark:text-ink-400")}>Missing</p>
            <p className={clsx("text-4xl font-display font-bold mt-1", missing > 0 ? "text-red-700 dark:text-red-400" : "text-ink-900 dark:text-ink-50")}>{missing}</p>
          </div>
          <div className={clsx("h-14 w-14 rounded-full flex items-center justify-center", missing > 0 ? "bg-red-200/50 dark:bg-red-900/50" : "bg-ink-100 dark:bg-ink-800")}>
            <AlertCircle className={clsx("h-8 w-8", missing > 0 ? "text-red-600 dark:text-red-400" : "text-ink-400")} />
          </div>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div className="w-full max-w-md">
          <Input 
            placeholder="Search ID, Name, Dept, or Salary..." 
            value={search} 
            onChange={e => setSearch(e.target.value)}
            className="shadow-sm" 
          />
        </div>
        {hasDrafts && (
          <div className="flex items-center gap-3 animate-in fade-in slide-in-from-right-4">
            <span className="text-sm font-medium text-brand-600 dark:text-brand-400">
              {Object.keys(drafts).length} unsaved {Object.keys(drafts).length === 1 ? 'change' : 'changes'}
            </span>
            <Button variant="secondary" onClick={() => setDrafts({})} className="shadow-sm">Discard</Button>
            <Button onClick={saveAll} disabled={saving} className="shadow-sm gap-2">
              <Save className="h-4 w-4" /> {saving ? 'Saving...' : 'Save All Changes'}
            </Button>
          </div>
        )}
      </div>

      {loading ? (
        <Skeleton className="h-96 w-full rounded-xl" />
      ) : (
        <div className="rounded-xl border border-ink-200 bg-white shadow-sm overflow-hidden dark:border-ink-800 dark:bg-ink-950">
          <DataTable
            rows={filteredRows}
            rowKey={(r) => r.employee_id}
            emptyTitle="No employees found"
            emptyDescription="Try adjusting your search query."
            columns={[
              {
                key: 'employee_id',
                header: 'Emp ID',
                sortable: true,
                sortValue: (r) => r.employee_id,
                render: (r) => <span className="font-semibold text-ink-900 dark:text-ink-50">{r.employee_id}</span>,
              },
              {
                key: 'employee_name',
                header: 'Name',
                sortable: true,
                sortValue: (r) => r.employee_name || '',
                render: (r) => (
                  <div className="flex flex-col">
                    <span className="font-medium">{r.employee_name || <span className="text-ink-400 italic">Unknown</span>}</span>
                    {r.department && <span className="text-xs text-ink-500">{r.department}</span>}
                  </div>
                ),
              },
              {
                key: 'status',
                header: 'Status',
                sortable: true,
                sortValue: (r) => r.monthly_salary > 0 ? 1 : 0,
                render: (r) => r.monthly_salary > 0 ? (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-green-50 px-2.5 py-0.5 text-xs font-semibold text-green-700 ring-1 ring-inset ring-green-600/20 dark:bg-green-500/10 dark:text-green-400 dark:ring-green-500/20">
                    <span className="h-1.5 w-1.5 rounded-full bg-green-500"></span> Configured
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-red-50 px-2.5 py-0.5 text-xs font-semibold text-red-700 ring-1 ring-inset ring-red-600/10 dark:bg-red-500/10 dark:text-red-400 dark:ring-red-500/20">
                    ❌ Not Configured
                  </span>
                ),
              },
              {
                key: 'monthly_salary',
                header: 'Monthly Salary',
                sortable: true,
                sortValue: (r) => r.monthly_salary,
                render: (r) => {
                  const draftVal = drafts[r.employee_id]
                  const isEditing = draftVal !== undefined
                  
                  if (isEditing) {
                    return (
                      <div className="flex items-center gap-2">
                        <Input 
                          type="number" 
                          min="1"
                          value={draftVal} 
                          onChange={e => setDrafts(prev => ({ ...prev, [r.employee_id]: e.target.value }))} 
                          className="w-32 py-1 h-8 text-sm"
                          autoFocus
                        />
                        <button 
                          onClick={() => {
                            const newDrafts = { ...drafts }
                            delete newDrafts[r.employee_id]
                            setDrafts(newDrafts)
                          }} 
                          className="p-1 text-ink-400 hover:text-ink-600 rounded hover:bg-ink-100 dark:hover:bg-ink-800"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                    )
                  }
                  
                  return (
                    <span className={clsx("font-medium", r.monthly_salary > 0 ? "text-ink-900 dark:text-ink-50" : "text-ink-400")}>
                      {r.monthly_salary > 0 ? formatMoney(r.monthly_salary) : '-'}
                    </span>
                  )
                },
              },
              {
                key: 'effective_from',
                header: 'Effective Date',
                sortable: true,
                sortValue: (r) => r.effective_from || '',
                render: (r) => <span className="text-ink-600 dark:text-ink-300">{r.effective_from ? new Date(r.effective_from).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }) : '-'}</span>,
              },
              {
                key: 'actions',
                header: '',
                sortable: false,
                render: (r) => (
                  <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    {drafts[r.employee_id] === undefined && (
                      <button 
                        onClick={() => setDrafts(prev => ({ ...prev, [r.employee_id]: r.monthly_salary > 0 ? String(r.monthly_salary) : '' }))}
                        className="p-1.5 text-ink-500 hover:text-brand-600 hover:bg-brand-50 rounded-md dark:hover:bg-brand-900/30 transition-colors"
                        title="Edit Salary"
                      >
                        <Pencil className="h-4 w-4" />
                      </button>
                    )}
                    {r.id > 0 && drafts[r.employee_id] === undefined && (
                      <button 
                        onClick={() => handleDelete(r.id)}
                        className="p-1.5 text-ink-500 hover:text-red-600 hover:bg-red-50 rounded-md dark:hover:bg-red-900/30 transition-colors"
                        title="Delete Salary"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                ),
              }
            ]}
          />
        </div>
      )}
    </div>
  )
}
