import { useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import { AlertTriangle, Upload, Loader2, CheckCircle2 } from 'lucide-react'
import { attendanceApi, employeesApi, annotationsApi } from '../services'
import { getErrorMessage } from '../services/apiClient'
import type { AttendanceRecord, DailySummary, Employee, IgnoredAttendanceRecord, AttendanceAnnotation } from '../types/api'
import { DataTable } from '../components/DataTable'
import { Badge, Card, Input, PageHeader, Select, Skeleton, statusTone, Modal, Button } from '../components/ui'
import { useApp } from '../context/AppContext'
import { formatNumber, todayISO, clsx } from '../utils/format'

function FileUploadZone({ onUpload, uploading, success }: { onUpload: (file: File) => void, uploading: boolean, success: boolean }) {
  const [isDragging, setIsDragging] = useState(false)
  
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') setIsDragging(true)
    else if (e.type === 'dragleave') setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      onUpload(e.dataTransfer.files[0])
    }
  }

  return (
    <div 
      onDragEnter={handleDrag} onDragLeave={handleDrag} onDragOver={handleDrag} onDrop={handleDrop}
      className={clsx(
        "relative mb-8 flex flex-col items-center justify-center rounded-2xl border-2 border-dashed p-10 text-center transition-all",
        isDragging ? "border-brand-500 bg-brand-50/50 dark:border-brand-500/50 dark:bg-brand-900/10" 
        : success ? "border-emerald-500/50 bg-emerald-50/50 dark:border-emerald-500/30 dark:bg-emerald-900/10"
        : "border-ink-200 bg-ink-50/50 hover:bg-ink-50 dark:border-ink-800 dark:bg-ink-900/20 dark:hover:bg-ink-900/40"
      )}
    >
      <input
        type="file"
        accept=".csv,.xlsx,.xlsm,.xls"
        className="absolute inset-0 cursor-pointer opacity-0"
        disabled={uploading}
        onChange={(e) => {
          if (e.target.files?.[0]) onUpload(e.target.files[0])
        }}
        title="Upload CSV / Excel"
      />
      
      {uploading ? (
        <>
          <div className="mb-4 rounded-full bg-brand-100 p-3 text-brand-600 dark:bg-brand-900/30 dark:text-brand-400">
            <Loader2 className="h-6 w-6 animate-spin" />
          </div>
          <p className="font-display text-base font-semibold text-ink-900 dark:text-ink-100">Processing records...</p>
          <p className="mt-1 text-sm text-ink-500 dark:text-ink-400">Validating and normalizing attendance data.</p>
        </>
      ) : success ? (
        <>
          <div className="mb-4 rounded-full bg-emerald-100 p-3 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400">
            <CheckCircle2 className="h-6 w-6" />
          </div>
          <p className="font-display text-base font-semibold text-emerald-900 dark:text-emerald-100">Upload Complete</p>
          <p className="mt-1 text-sm text-emerald-700 dark:text-emerald-400">Records have been successfully imported.</p>
        </>
      ) : (
        <>
          <div className="mb-4 rounded-full bg-ink-100 p-3 text-ink-600 dark:bg-ink-800 dark:text-ink-400">
            <Upload className="h-6 w-6" />
          </div>
          <p className="font-display text-base font-semibold text-ink-900 dark:text-ink-100">
            Click or drag file to this area to upload
          </p>
          <p className="mt-1 text-sm text-ink-500 dark:text-ink-400">
            Support for a single or bulk CSV / Excel file.
          </p>
        </>
      )}
    </div>
  )
}

export function AttendancePage() {
  const { pushActivity, bumpInsightsRefresh } = useApp()
  const [date, setDate] = useState(todayISO())
  const [department, setDepartment] = useState('all')
  const [status, setStatus] = useState('all')
  const [search, setSearch] = useState('')
  const [rows, setRows] = useState<AttendanceRecord[]>([])
  const [employees, setEmployees] = useState<Employee[]>([])
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadSuccess, setUploadSuccess] = useState(false)
  const [uploadWarnings, setUploadWarnings] = useState<IgnoredAttendanceRecord[]>([])
  const [summaryIgnored, setSummaryIgnored] = useState<IgnoredAttendanceRecord[]>([])

  const [annotationModalOpen, setAnnotationModalOpen] = useState(false)
  const [selectedRecord, setSelectedRecord] = useState<AttendanceRecord | null>(null)
  const [annotationType, setAnnotationType] = useState('Sick Leave')
  const [annotationNotes, setAnnotationNotes] = useState('')
  const [savingAnnotation, setSavingAnnotation] = useState(false)
  
  const ANNOTATION_OPTIONS = [
    'Sick Leave', 'Casual Leave', 'Approved Leave', 'Medical Leave',
    'Personal Leave', 'Emergency', 'Official Duty', 'Work From Home',
    'Training', 'Half Day', 'Other'
  ]


  const employeeDept = useMemo(() => {
    const map = new Map<string, string>()
    for (const emp of employees) {
      map.set(emp.employee_code, emp.department || 'Unassigned')
    }
    return map
  }, [employees])

  async function load(workDate = date) {
    setLoading(true)
    try {
      const [records, emps, summary, annotations] = await Promise.all([
        attendanceApi.records(workDate),
        employeesApi.list(),
        attendanceApi.dailySummary(workDate).catch(() => null as DailySummary | null),
        annotationsApi.list(workDate).catch(() => [] as AttendanceAnnotation[])
      ])
      
      const enrichedRecords = records.map(r => {
        const emp = emps.find(e => e.employee_code === r.employee_code)
        if (emp) {
            const ann = annotations.find(a => a.employee_id === emp.id)
            if (ann) {
                return { ...r, annotation: ann }
            }
        }
        return r
      })
      
      setRows(enrichedRecords)
      setEmployees(emps)
      setSummaryIgnored(summary?.details?.ignored_records || [])
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to load attendance records'))
      setRows([])
      setSummaryIgnored([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load(date)
  }, [date])

  const departmentOptions = useMemo(() => {
    return [...new Set(employees.map((e) => e.department || 'Unassigned'))].sort()
  }, [employees])

  const enriched = useMemo(
    () =>
      rows.map((row) => ({
        ...row,
        department: row.employee_code ? employeeDept.get(row.employee_code) || 'Unassigned' : 'Unassigned',
      })),
    [employeeDept, rows],
  )

  const filtered = useMemo(() => {
    return enriched.filter((row) => {
      const matchesStatus = status === 'all' || row.status === status
      const matchesDept = department === 'all' || row.department === department
      const hay = `${row.employee_code ?? ''} ${row.employee_name ?? ''} ${row.department}`.toLowerCase()
      const matchesSearch = !search || hay.includes(search.toLowerCase())
      return matchesStatus && matchesSearch && matchesDept
    })
  }, [department, enriched, search, status])

  async function handleSaveAnnotation() {
    if (!selectedRecord) return
    const emp = employees.find(e => e.employee_code === selectedRecord.employee_code)
    if (!emp) return
    setSavingAnnotation(true)
    try {
      await annotationsApi.upsert(emp.id, date, annotationType, annotationNotes)
      toast.success('Annotation saved')
      setAnnotationModalOpen(false)
      await load(date)
    } catch (e) {
      toast.error(getErrorMessage(e, 'Failed to save annotation'))
    } finally {
      setSavingAnnotation(false)
    }
  }
  
  async function handleDeleteAnnotation() {
    if (!selectedRecord || !selectedRecord.annotation) return
    setSavingAnnotation(true)
    try {
      await annotationsApi.delete(selectedRecord.annotation.id)
      toast.success('Annotation deleted')
      setAnnotationModalOpen(false)
      await load(date)
    } catch (e) {
      toast.error(getErrorMessage(e, 'Failed to delete annotation'))
    } finally {
      setSavingAnnotation(false)
    }
  }

  const warningRows = uploadWarnings.length ? uploadWarnings : summaryIgnored

  async function onUpload(file?: File | null) {
    if (!file) return
    setUploading(true)
    setUploadSuccess(false)
    try {
      const result = await attendanceApi.upload(file)
      const ignored = result.ignored_records || []
      setUploadWarnings(ignored)
      const processed = result.imported + result.upserted
      const employees = result.employees_processed ?? processed
      
      setUploadSuccess(true)
      setTimeout(() => setUploadSuccess(false), 3000)

      toast.success(
        `Attendance Upload Completed — Employees: ${employees}, Records: ${processed}, Ignored: ${result.ignored ?? 0}`,
      )
      pushActivity({
        type: 'upload',
        title: 'Attendance uploaded',
        detail: `${file.name}: employees ${employees}, records ${processed}, ignored ${result.ignored ?? 0}`,
      })
      if (result.salary_warnings?.length) {
        toast.error(`${result.salary_warnings.length} salary warning(s) — set salaries in Employees or the directory file`)
      }
      if (result.errors?.length) toast.error(`${result.errors.length} row warning(s)`)
      bumpInsightsRefresh()
      await load(date)
    } catch (error) {
      toast.error(getErrorMessage(error, 'Upload failed'))
    } finally {
      setUploading(false)
    }
  }

  return (
    <div>
      <PageHeader
        title="Attendance & Import"
        subtitle="Bulk import biometric CSV/Excel exports or seamlessly review API-normalized attendance logs."
      />

      <FileUploadZone onUpload={onUpload} uploading={uploading} success={uploadSuccess} />

      {warningRows.length > 0 && (
        <Card className="mb-8 overflow-hidden border-rose-200 p-0 shadow-sm ring-1 ring-inset ring-rose-500/20 dark:border-rose-900/50 dark:ring-rose-500/20">
          <div className="flex items-center gap-3 border-b border-rose-200/50 bg-rose-50/80 px-6 py-4 dark:border-rose-900/50 dark:bg-rose-950/40">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-rose-100 text-rose-700 dark:bg-rose-900/50 dark:text-rose-400">
              <AlertTriangle className="h-4 w-4" />
            </div>
            <div>
              <h2 className="font-display text-[15px] font-semibold text-rose-900 dark:text-rose-100">Upload Warnings Detected</h2>
              <p className="text-[13px] font-medium text-rose-700 dark:text-rose-400">{warningRows.length} ignored records due to missing employee mapping.</p>
            </div>
          </div>
          <div className="max-h-[240px] overflow-y-auto bg-white p-6 dark:bg-ink-950">
            <ul className="space-y-3">
              {warningRows.map((item) => (
                <li key={`${item.employee_code}-${item.work_date || ''}`} className="flex items-start gap-3 rounded-xl bg-rose-50/50 px-4 py-3 dark:bg-rose-950/20">
                  <div className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-rose-400 dark:bg-rose-600" />
                  <div>
                    <p className="text-[13px] font-semibold text-rose-900 dark:text-rose-100">Employee ID {item.employee_code} not found</p>
                    <p className="mt-1 text-xs text-rose-700 dark:text-rose-400">
                      Attendance record ignored. Register this employee before re-importing. Reason: {item.reason}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </Card>
      )}

      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <label className="mb-1.5 block text-[13px] font-medium text-ink-700 dark:text-ink-300">Date</label>
          <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </div>
        <div>
          <label className="mb-1.5 block text-[13px] font-medium text-ink-700 dark:text-ink-300">Status</label>
          <Select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="all">All statuses</option>
            <option value="present">Present</option>
            <option value="absent">Absent</option>
            <option value="leave">Leave</option>
            <option value="missing_checkout">Missing checkout</option>
            <option value="weekly_off">Weekly off</option>
            <option value="holiday">Holiday</option>
          </Select>
        </div>
        <div>
          <label className="mb-1.5 block text-[13px] font-medium text-ink-700 dark:text-ink-300">Department</label>
          <Select value={department} onChange={(e) => setDepartment(e.target.value)}>
            <option value="all">All departments</option>
            {departmentOptions.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <label className="mb-1.5 block text-[13px] font-medium text-ink-700 dark:text-ink-300">Search</label>
          <Input
            placeholder="Employee ID or name"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {loading ? (
        <Skeleton className="h-[400px]" />
      ) : (
        <DataTable
          rows={filtered}
          rowKey={(r) => r.id}
          emptyTitle="No attendance records"
          emptyDescription="Upload a biometric export or choose another date."
          columns={[
            {
              key: 'code',
              header: 'Employee ID',
              sortable: true,
              sortValue: (r) => r.employee_code || '',
              render: (r) => <span className="font-mono text-xs">{r.employee_code}</span>,
            },
            {
              key: 'name',
              header: 'Name',
              sortable: true,
              sortValue: (r) => r.employee_name || '',
              render: (r) => r.employee_name,
            },
            {
              key: 'department',
              header: 'Department',
              sortable: true,
              sortValue: (r) => r.department,
              render: (r) => r.department,
            },
            {
              key: 'in',
              header: 'Check In',
              render: (r) => r.check_in || '—',
            },
            {
              key: 'out',
              header: 'Check Out',
              render: (r) => r.check_out || '—',
            },
            {
              key: 'hours',
              header: 'Work Hours',
              sortable: true,
              sortValue: (r) => Number(r.work_duration_hours || 0),
              render: (r) => formatNumber(r.work_duration_hours),
            },
            {
              key: 'break',
              header: 'Break Hours',
              render: (r) => formatNumber(r.break_duration_hours),
            },
            {
              key: 'status',
              header: 'Status',
              sortable: true,
              sortValue: (r) => r.status,
              render: (r) => <Badge tone={statusTone(r.status)}>{r.status.replace(/_/g, ' ')}</Badge>,
            },
            {
              key: 'reason',
              header: 'Reason',
              render: (r) => (
                <div 
                  className="cursor-pointer hover:opacity-80 transition-opacity"
                  onClick={() => {
                    setSelectedRecord(r)
                    if (r.annotation) {
                      setAnnotationType(r.annotation.annotation_type)
                      setAnnotationNotes(r.annotation.notes || '')
                    } else {
                      setAnnotationType('Sick Leave')
                      setAnnotationNotes('')
                    }
                    setAnnotationModalOpen(true)
                  }}
                >
                  {r.annotation ? (
                    <Badge tone="sky">
                      {r.annotation.annotation_type}
                    </Badge>
                  ) : (
                    <span className="text-xs text-ink-400 hover:text-ink-600 dark:hover:text-ink-300 underline underline-offset-2 decoration-dotted">
                      Add Reason
                    </span>
                  )}
                </div>
              ),
            },
          ]}
        />
      )}
      <Modal
        title={selectedRecord?.annotation ? "Edit Reason" : "Add Reason"}
        isOpen={annotationModalOpen}
        onClose={() => setAnnotationModalOpen(false)}
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-ink-700 dark:text-ink-300 mb-1">
              Employee: {selectedRecord?.employee_name} ({selectedRecord?.employee_code})
            </label>
            <label className="block text-sm font-medium text-ink-700 dark:text-ink-300 mb-1 mt-4">
              Reason Type
            </label>
            <Select 
              value={annotationType} 
              onChange={(e) => setAnnotationType(e.target.value)}
              className="w-full"
            >
              {ANNOTATION_OPTIONS.map(opt => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
            </Select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-ink-700 dark:text-ink-300 mb-1">
              Notes (Required if 'Other')
            </label>
            <textarea
              className="w-full rounded-lg border border-ink-300 bg-white px-3 py-2 text-sm text-ink-900 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:border-ink-700 dark:bg-ink-950 dark:text-ink-100 placeholder-ink-400"
              rows={3}
              value={annotationNotes}
              onChange={(e) => setAnnotationNotes(e.target.value)}
              placeholder="Optional details..."
            />
          </div>
          
          <div className="flex justify-end gap-3 pt-4">
            {selectedRecord?.annotation && (
              <Button 
                variant="secondary" 
                className="text-rose-600 border-rose-200 hover:bg-rose-50 mr-auto"
                onClick={handleDeleteAnnotation}
                disabled={savingAnnotation}
              >
                Delete
              </Button>
            )}
            <Button variant="secondary" onClick={() => setAnnotationModalOpen(false)} disabled={savingAnnotation}>
              Cancel
            </Button>
            <Button 
              onClick={handleSaveAnnotation} 
              disabled={savingAnnotation || (annotationType === 'Other' && !annotationNotes.trim())}
            >
              {savingAnnotation ? 'Saving...' : 'Save Reason'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
