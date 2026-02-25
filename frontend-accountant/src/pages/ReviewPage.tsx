/**
 * ReviewPage — 50/50 split layout:
 *   LEFT  → PDF viewer with bbox overlays
 *   RIGHT → scrollable list of ItemForm cards + submit button
 *
 * Flow:
 *   1. Accountant fills the upload form (PDA JSON + FDA PDF)
 *   2. Page polls until AI_PROCESSING finishes
 *   3. Once PENDING_ACCOUNTANT_REVIEW, loads deviation report
 *   4. Accountant reviews each flagged item, then submits to operator
 */
import { useEffect } from 'react'
import { useDAStore } from '@/store/daStore'
import {
  useDAStatus,
  useDeviationReport,
  useUploadDA,
  useSubmitToOperator,
} from '@/api/daApi'
import { PDFViewer } from '@/components/PDFViewer'
import { ItemForm } from '@/components/ItemForm'
import { SubmitButton } from '@/components/SubmitButton'
import type { SubmitPayload } from '@/types'

// ── Status banner ────────────────────────────────────────────────────────────

function StatusBanner({ status }: { status: string }) {
  const colors: Record<string, string> = {
    UPLOADING: 'bg-slate-100 text-slate-700',
    AI_PROCESSING: 'bg-blue-100 text-blue-700',
    PENDING_ACCOUNTANT_REVIEW: 'bg-amber-100 text-amber-800',
    PENDING_OPERATOR_APPROVAL: 'bg-purple-100 text-purple-800',
    APPROVED: 'bg-green-100 text-green-800',
    REJECTED: 'bg-red-100 text-red-800',
    PUSHED_TO_ERP: 'bg-cyan-100 text-cyan-800',
  }
  return (
    <div className={`flex items-center px-4 py-2 rounded-lg text-sm font-medium ${colors[status] ?? 'bg-slate-50'}`}>
      {status === 'AI_PROCESSING' && (
        <svg className="animate-spin -ml-0.5 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
        </svg>
      )}
      {status.replace(/_/g, ' ')}
    </div>
  )
}

// ── Upload form ───────────────────────────────────────────────────────────────

function UploadForm({ onUploaded }: { onUploaded: (daId: string, url: string) => void }) {
  const upload = useUploadDA()
  const setPdfUrl = useDAStore((s) => s.setPdfUrl)

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)

    // The backend expects pda_json as a plain JSON string (Form field), not a file.
    // Read the selected JSON file and replace the File entry with its text content.
    const pdaFile = fd.get('pda_json') as File | null
    if (pdaFile && pdaFile.size > 0) {
      const text = await pdaFile.text()
      fd.set('pda_json', text)
    }

    const file = fd.get('fda_pdf') as File | null
    if (file) {
      const objectUrl = URL.createObjectURL(file)
      setPdfUrl(objectUrl)
    }
    const result = await upload.mutateAsync(fd)
    onUploaded(result.da_id, '')
  }

  return (
    <div className="flex-1 flex items-center justify-center bg-slate-50">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-lg bg-white rounded-xl shadow-lg p-8 space-y-5"
      >
        <h2 className="text-xl font-bold text-slate-800">Upload Disbursement Account</h2>

        <div>
          <label htmlFor="pda_json" className="block text-sm font-medium text-slate-700 mb-1">
            PDA (JSON file)
          </label>
          <input
            id="pda_json"
            name="pda_json"
            type="file"
            accept=".json,application/json"
            required
            className="w-full text-sm text-slate-600 file:mr-3 file:py-1.5 file:px-4 file:rounded-md file:border-0 file:bg-brand-50 file:text-brand-700 file:font-medium hover:file:bg-brand-100 cursor-pointer"
          />
        </div>

        <div>
          <label htmlFor="fda_pdf" className="block text-sm font-medium text-slate-700 mb-1">
            FDA PDF
          </label>
          <input
            id="fda_pdf"
            name="fda_pdf"
            type="file"
            accept="application/pdf"
            required
            className="w-full text-sm text-slate-600 file:mr-3 file:py-1.5 file:px-4 file:rounded-md file:border-0 file:bg-brand-50 file:text-brand-700 file:font-medium hover:file:bg-brand-100 cursor-pointer"
          />
        </div>

        {upload.isError && (
          <p className="text-sm text-red-600">
            {(upload.error as Error).message ?? 'Upload failed'}
          </p>
        )}

        <button
          type="submit"
          disabled={upload.isPending}
          className="w-full py-2 rounded-lg font-semibold text-white bg-brand-500 hover:bg-brand-700 disabled:opacity-40 transition-colors"
        >
          {upload.isPending ? 'Uploading…' : 'Upload & Analyse'}
        </button>
      </form>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function ReviewPage() {
  const activeDAId = useDAStore((s) => s.activeDAId)
  const setActiveDAId = useDAStore((s) => s.setActiveDAId)
  const pdfUrl = useDAStore((s) => s.pdfUrl)
  const initEdits = useDAStore((s) => s.initEdits)
  const edits = useDAStore((s) => s.edits)

  const { data: daStatus } = useDAStatus(activeDAId)
  const { data: deviation } = useDeviationReport(
    daStatus?.status === 'PENDING_ACCOUNTANT_REVIEW' ? activeDAId : null
  )

  const submit = useSubmitToOperator(activeDAId ?? '')

  // Initialise edit state once deviation report loads
  useEffect(() => {
    if (deviation?.items) initEdits(deviation.items)
  }, [deviation?.items, initEdits])

  function handleUploaded(daId: string) {
    setActiveDAId(daId)
  }

  async function handleSubmit() {
    if (!deviation) return
    const payload: SubmitPayload = {
      items: Object.entries(edits).map(([item_id, edit]) => ({
        item_id,
        status: edit.status,
        accountant_note: edit.accountant_note,
      })),
    }
    await submit.mutateAsync(payload)
  }

  const isReviewable = daStatus?.status === 'PENDING_ACCOUNTANT_REVIEW'
  const isProcessing =
    daStatus?.status === 'UPLOADING' || daStatus?.status === 'AI_PROCESSING'

  return (
    <div className="flex flex-col h-screen bg-slate-100">
      {/* Top nav */}
      <header className="flex items-center justify-between px-6 py-3 bg-white border-b border-slate-200 shadow-sm">
        <div className="flex items-center gap-3">
          <span className="text-lg font-bold text-brand-700">OpenDA</span>
          <span className="text-slate-400">|</span>
          <span className="text-sm text-slate-600">Accountant Review</span>
        </div>
        {daStatus && (
          <div className="flex items-center gap-4">
            <StatusBanner status={daStatus.status} />
            {daStatus.flagged_items_count > 0 && (
              <span className="text-xs font-medium text-red-600 bg-red-50 border border-red-200 px-2 py-1 rounded-full">
                {daStatus.flagged_items_count} flagged
              </span>
            )}
            <span className="text-xs text-slate-500 font-mono">{activeDAId?.slice(0, 8)}</span>
          </div>
        )}
      </header>

      {/* Body */}
      {!activeDAId ? (
        <UploadForm onUploaded={handleUploaded} />
      ) : (
        <div className="flex flex-1 overflow-hidden">
          {/* LEFT — PDF viewer */}
          <div className="w-1/2 border-r border-slate-200 overflow-hidden p-3 bg-slate-50">
            {pdfUrl ? (
              <PDFViewer pdfUrl={pdfUrl} items={deviation?.items ?? []} />
            ) : (
              <div className="flex items-center justify-center h-full text-slate-400 text-sm">
                PDF preview not available
              </div>
            )}
          </div>

          {/* RIGHT — item list + submit */}
          <div className="w-1/2 flex flex-col overflow-hidden">
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {isProcessing && (
                <div className="flex flex-col items-center justify-center h-full gap-3 text-slate-500">
                  <svg className="animate-spin h-8 w-8 text-brand-500" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                  <p className="text-sm font-medium">AI is processing the FDA document…</p>
                  <p className="text-xs">This typically takes 30–90 seconds.</p>
                </div>
              )}

              {isReviewable &&
                deviation?.items?.map((item) => (
                  <ItemForm key={item.item_id} item={item} />
                ))}

              {daStatus?.status === 'PENDING_OPERATOR_APPROVAL' && (
                <div className="flex items-center justify-center h-32 text-slate-500 text-sm">
                  ✓ Submitted to operator — awaiting approval
                </div>
              )}

              {(daStatus?.status === 'APPROVED' || daStatus?.status === 'PUSHED_TO_ERP') && (
                <div className="flex items-center justify-center h-32 text-green-600 text-sm font-medium">
                  ✓ Approved and pushed to ERP
                </div>
              )}

              {daStatus?.status === 'REJECTED' && (
                <div className="flex items-center justify-center h-32 text-red-600 text-sm font-medium">
                  ✗ Disbursement account rejected
                </div>
              )}
            </div>

            {/* Footer actions */}
            {isReviewable && deviation?.items && (
              <div className="flex-none p-4 border-t border-slate-200 bg-white">
                <div className="flex items-center justify-between mb-3 text-xs text-slate-600">
                  <span>
                    Total estimated: <strong>${deviation.total_estimated?.toFixed(2)}</strong>
                  </span>
                  <span>
                    Total actual: <strong>${deviation.total_actual?.toFixed(2)}</strong>
                  </span>
                </div>
                <SubmitButton
                  items={deviation.items}
                  onSubmit={handleSubmit}
                  isPending={submit.isPending}
                />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
