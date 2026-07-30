import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { ArrowLeft, UploadCloud, AlertCircle, CheckCircle2, Save } from 'lucide-react'
import { salariesApi } from '../services'
import { getErrorMessage } from '../services/apiClient'
import { Button, PageHeader } from '../components/ui'
import { clsx, formatMoney } from '../utils/format'

export function SalaryImportPage() {
  const navigate = useNavigate()
  const [previewData, setPreviewData] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [successSummary, setSuccessSummary] = useState<any>(null)

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const selected = e.target.files?.[0]
    if (!selected) return
    setPreviewData(null)
    setLoading(true)

    try {
      const data = await salariesApi.previewImport(selected)
      setPreviewData(data)
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to parse file'))
    } finally {
      setLoading(false)
    }
  }

  async function confirmImport() {
    if (!previewData) return
    setLoading(true)
    try {
      await salariesApi.confirmImport(previewData)
      setSuccessSummary({
        imported: previewData.new_employees.length + previewData.existing_to_update.length,
        updated: previewData.existing_to_update.length,
        newRecords: previewData.new_employees.length,
        duplicates: previewData.duplicates.length,
        rejected: previewData.invalid_rows.length
      })
      toast.success('Salaries imported successfully')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Import failed'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <PageHeader
        title="Import Salaries"
        subtitle="Upload a CSV or PDF file to bulk update employee salaries."
        actions={
          <Button variant="ghost" onClick={() => navigate('/payroll/salaries')} className="gap-2 text-ink-500">
            <ArrowLeft className="h-4 w-4" /> Back to Salaries
          </Button>
        }
      />

      {!previewData && !successSummary && (
        <div className="w-full mt-8">
          <label className="flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-ink-200 bg-white py-24 transition-colors hover:border-brand-400 hover:bg-brand-50/50 dark:border-ink-800 dark:bg-ink-900/50 dark:hover:border-brand-500/50 dark:hover:bg-brand-900/10">
            <div className="mb-6 rounded-full bg-brand-100 p-6 text-brand-600 dark:bg-brand-900/30 dark:text-brand-400">
              <UploadCloud className="h-10 w-10" />
            </div>
            <h3 className="mb-3 text-2xl font-semibold text-ink-900 dark:text-ink-50">Upload Salary File</h3>
            <p className="mb-8 text-center text-base text-ink-500 max-w-lg">
              Supports CSV (Employee ID, Employee Name, Salary) or PDF extracts.
            </p>
            <span className={clsx("inline-flex h-12 items-center justify-center rounded-lg px-6 py-3 text-base font-medium transition-colors bg-white border border-ink-200 text-ink-700 hover:bg-ink-50", loading && "opacity-50 pointer-events-none")}>
              {loading ? 'Processing...' : 'Browse Files'}
            </span>
            <input type="file" accept=".csv,.pdf" className="hidden" onChange={handleFileChange} disabled={loading} />
          </label>
        </div>
      )}

      {successSummary && (
        <div className="mx-auto max-w-3xl mt-8 bg-white dark:bg-ink-900 rounded-2xl shadow-sm border border-ink-200 dark:border-ink-800 p-10 text-center animate-in fade-in zoom-in-95">
          <div className="mx-auto h-20 w-20 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mb-8">
            <CheckCircle2 className="h-10 w-10 text-green-600 dark:text-green-400" />
          </div>
          <h2 className="text-3xl font-bold text-ink-900 dark:text-ink-50 mb-3">Import Successful</h2>
          <p className="text-lg text-ink-500 mb-10">Your salary records have been processed and saved.</p>
          
          <div className="grid grid-cols-2 gap-6 mb-10 text-left">
            <div className="bg-ink-50 dark:bg-ink-950 p-6 rounded-xl border border-ink-100 dark:border-ink-800">
              <p className="text-base font-medium text-ink-500 mb-2">Imported</p>
              <p className="text-4xl font-bold text-ink-900 dark:text-ink-50">{successSummary.imported}</p>
            </div>
            <div className="bg-blue-50 dark:bg-blue-950/20 p-6 rounded-xl border border-blue-100 dark:border-blue-900/30">
              <p className="text-base font-medium text-blue-600 dark:text-blue-400 mb-2">Updated</p>
              <p className="text-4xl font-bold text-blue-700 dark:text-blue-300">{successSummary.updated}</p>
            </div>
            <div className="bg-green-50 dark:bg-green-950/20 p-6 rounded-xl border border-green-100 dark:border-green-900/30">
              <p className="text-base font-medium text-green-600 dark:text-green-400 mb-2">New</p>
              <p className="text-4xl font-bold text-green-700 dark:text-green-300">{successSummary.newRecords}</p>
            </div>
            <div className="bg-red-50 dark:bg-red-950/20 p-6 rounded-xl border border-red-100 dark:border-red-900/30">
              <p className="text-base font-medium text-red-600 dark:text-red-400 mb-2">Duplicates & Rejected</p>
              <p className="text-4xl font-bold text-red-700 dark:text-red-300">{successSummary.duplicates + successSummary.rejected}</p>
            </div>
          </div>
          
          <Button onClick={() => navigate('/payroll/salaries')} className="w-full">
            Back to Employee Salaries
          </Button>
        </div>
      )}

      {previewData && !successSummary && (
        <div className="space-y-6">
          <div className="flex items-center justify-between bg-white dark:bg-ink-900 p-6 rounded-xl border border-ink-200 dark:border-ink-800">
            <div>
              <h3 className="text-lg font-semibold text-ink-900 dark:text-ink-50">Preview Import</h3>
              <p className="text-sm text-ink-500">Review the changes before applying.</p>
            </div>
            <div className="flex gap-3">
              <Button variant="secondary" onClick={() => { setPreviewData(null) }}>Cancel</Button>
              <Button onClick={confirmImport} disabled={loading || (previewData.new_employees.length === 0 && previewData.existing_to_update.length === 0)} className="gap-2">
                <Save className="h-4 w-4" /> Confirm & Save
              </Button>
            </div>
          </div>

          <div className="grid gap-6 md:grid-cols-2">
            {/* New Employees */}
            <div className="bg-white dark:bg-ink-900 p-5 rounded-xl border border-ink-200 dark:border-ink-800">
              <h4 className="flex items-center gap-2 font-semibold text-green-600 dark:text-green-400 mb-4">
                <CheckCircle2 className="h-5 w-5" /> New Records ({previewData.new_employees.length})
              </h4>
              {previewData.new_employees.length > 0 ? (
                <ul className="space-y-2 max-h-60 overflow-y-auto">
                  {previewData.new_employees.map((e: any, i: number) => (
                    <li key={i} className="flex justify-between text-sm py-1 border-b border-ink-100 dark:border-ink-800 last:border-0">
                      <span>{e.employee_id} - {e.employee_name}</span>
                      <span className="font-medium">{formatMoney(e.monthly_salary)}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-ink-500 italic">No new employees to add.</p>
              )}
            </div>

            {/* Updates */}
            <div className="bg-white dark:bg-ink-900 p-5 rounded-xl border border-ink-200 dark:border-ink-800">
              <h4 className="flex items-center gap-2 font-semibold text-blue-600 dark:text-blue-400 mb-4">
                <CheckCircle2 className="h-5 w-5" /> Updates ({previewData.existing_to_update.length})
              </h4>
              {previewData.existing_to_update.length > 0 ? (
                <ul className="space-y-2 max-h-60 overflow-y-auto">
                  {previewData.existing_to_update.map((e: any, i: number) => (
                    <li key={i} className="flex justify-between text-sm py-1 border-b border-ink-100 dark:border-ink-800 last:border-0">
                      <span>{e.employee_id} - {e.employee_name}</span>
                      <span className="font-medium text-ink-500 line-through mr-2">{formatMoney(e.old_salary)}</span>
                      <span className="font-medium">{formatMoney(e.monthly_salary)}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-ink-500 italic">No existing employees to update.</p>
              )}
            </div>
            
            {/* Errors */}
            {(previewData.invalid_rows.length > 0 || previewData.duplicates.length > 0) && (
              <div className="bg-red-50 dark:bg-red-900/10 p-5 rounded-xl border border-red-200 dark:border-red-900/30 md:col-span-2">
                <h4 className="flex items-center gap-2 font-semibold text-red-600 dark:text-red-400 mb-4">
                  <AlertCircle className="h-5 w-5" /> Issues Found
                </h4>
                <div className="space-y-4">
                  {previewData.invalid_rows.length > 0 && (
                    <div>
                      <h5 className="text-sm font-medium text-red-800 dark:text-red-300 mb-2">Invalid Rows ({previewData.invalid_rows.length})</h5>
                      <ul className="list-disc pl-5 text-sm text-red-700 dark:text-red-400 space-y-1">
                        {previewData.invalid_rows.map((r: any, i: number) => (
                          <li key={i}>Row {r.row}: {r.reason} (ID: {r.data.employee_id || 'N/A'})</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {previewData.duplicates.length > 0 && (
                    <div>
                      <h5 className="text-sm font-medium text-red-800 dark:text-red-300 mb-2">Duplicates in file ({previewData.duplicates.length})</h5>
                      <ul className="list-disc pl-5 text-sm text-red-700 dark:text-red-400 space-y-1">
                        {previewData.duplicates.map((r: any, i: number) => (
                          <li key={i}>Row {r.row}: {r.reason} (ID: {r.data.employee_id})</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
