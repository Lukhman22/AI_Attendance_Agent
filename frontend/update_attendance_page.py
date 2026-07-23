import re
from pathlib import Path

path = Path("/Users/mohammedlukhmaan/Desktop/AI_Attendance_Agent/frontend/src/pages/AttendancePage.tsx")
content = path.read_text()

# 1. Imports
content = content.replace(
    "import { attendanceApi, employeesApi } from '../services'",
    "import { attendanceApi, employeesApi, annotationsApi } from '../services'"
)
content = content.replace(
    "import type { AttendanceRecord, DailySummary, Employee, IgnoredAttendanceRecord } from '../types/api'",
    "import type { AttendanceRecord, DailySummary, Employee, IgnoredAttendanceRecord, AttendanceAnnotation } from '../types/api'"
)
content = content.replace(
    "import { Badge, Card, Input, PageHeader, Select, Skeleton, statusTone } from '../components/ui'",
    "import { Badge, Card, Input, PageHeader, Select, Skeleton, statusTone, Modal, Button } from '../components/ui'"
)

# 2. State for Annotations
state_add = """  const [summaryIgnored, setSummaryIgnored] = useState<IgnoredAttendanceRecord[]>([])

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
"""
content = content.replace("  const [summaryIgnored, setSummaryIgnored] = useState<IgnoredAttendanceRecord[]>([])", state_add)

# 3. Load annotations
load_old = """      const [records, emps, summary] = await Promise.all([
        attendanceApi.records(workDate),
        employeesApi.list(),
        attendanceApi.dailySummary(workDate).catch(() => null as DailySummary | null),
      ])
      setRows(records)"""
load_new = """      const [records, emps, summary, annotations] = await Promise.all([
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
      
      setRows(enrichedRecords)"""
content = content.replace(load_old, load_new)

# 4. Save annotation handler
handlers = """  async function handleSaveAnnotation() {
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
"""
content = content.replace("  const warningRows = uploadWarnings.length ? uploadWarnings : summaryIgnored", handlers + "\n  const warningRows = uploadWarnings.length ? uploadWarnings : summaryIgnored")

# 5. Add Reason Column
column_old = """            {
              key: 'status',
              header: 'Status',
              sortable: true,
              sortValue: (r) => r.status,
              render: (r) => <Badge tone={statusTone(r.status)}>{r.status.replace(/_/g, ' ')}</Badge>,
            },"""
column_new = """            {
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
                    <Badge tone="info" className="bg-brand-100 text-brand-800 dark:bg-brand-900/40 dark:text-brand-300">
                      {r.annotation.annotation_type}
                    </Badge>
                  ) : (
                    <span className="text-xs text-ink-400 hover:text-ink-600 dark:hover:text-ink-300 underline underline-offset-2 decoration-dotted">
                      Add Reason
                    </span>
                  )}
                </div>
              ),
            },"""
content = content.replace(column_old, column_new)

# 6. Add Modal Component
modal_html = """      <Modal
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
                variant="outline" 
                className="text-rose-600 border-rose-200 hover:bg-rose-50 mr-auto"
                onClick={handleDeleteAnnotation}
                disabled={savingAnnotation}
              >
                Delete
              </Button>
            )}
            <Button variant="outline" onClick={() => setAnnotationModalOpen(false)} disabled={savingAnnotation}>
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
    </div>"""

content = content.replace("    </div>\n  )\n}", modal_html + "\n  )\n}")

path.write_text(content)
print("Updated AttendancePage.tsx")
