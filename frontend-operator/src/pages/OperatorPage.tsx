/**
 * OperatorPage — DA approval dashboard.
 *
 * Layout: top SummaryBar → full-width DeviationTable → bottom action panel.
 * Clicking any row opens the PDFModal for evidence review.
 *
 * The operator enters the DA ID manually (or via QR/link from accountant).
 * In production, a list of pending DAs would be fetched from /api/v1/da/pending.
 */
import { useState } from 'react'
import { useDAStatus, useDeviationReport, useAuditLog, useApproveDA, useRejectDA } from '@/api/daApi'
import { SummaryBar } from '@/components/SummaryBar'
import { DeviationTable } from '@/components/DeviationTable'
import { PDFModal } from '@/components/PDFModal'
import { JustificationInput } from '@/components/JustificationInput'
import { ApproveRejectButtons } from '@/components/ApproveButton'
import type { AuditLogEntry } from '@/types'

// ── Audit log drawer ──────────────────────────────────────────────────────────

function AuditDrawer({ entries }: { entries: AuditLogEntry[] }) {
  return (
    <div className="border-t border-slate-200 px-6 py-4">
      <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
        Audit Trail
      </h3>
      <ol className="relative border-l border-slate-200 space-y-3 pl-4">
        {entries.map((e) => (
          <li key={e.id} className="relative">
            <span className="absolute -left-[19px] top-0.5 flex h-3 w-3 items-center justify-center rounded-full bg-brand-500 ring-2 ring-white" />
            <p className="text-xs text-slate-800">
              <strong>{e.actor}</strong>
              {e.previous_status && (
                <>
                  {' '}
                  <span className="text-slate-400">{e.previous_status}</span>
                  {' → '}
                </>
              )}
              <span className="font-semibold">{e.new_status}</span>
            </p>
            {e.note && <p className="text-xs text-slate-500 italic">{e.note}</p>}
            <p className="text-xs text-slate-400">
              {new Date(e.created_at).toLocaleString()}
              {e.llm_provider && ` · via ${e.llm_provider}`}
            </p>
          </li>
        ))}
      </ol>
    </div>
  )
}

// ── Input form — enter DA ID ──────────────────────────────────────────────────

function DAIdInput({ onSubmit }: { onSubmit: (id: string) => void }) {
  const [value, setValue] = useState('')
  return (
    <div className="flex-1 flex items-center justify-center bg-slate-50">
      <div className="bg-white rounded-xl shadow-lg p-8 w-full max-w-md space-y-4">
        <h2 className="text-xl font-bold text-slate-800">Operator Approval</h2>
        <p className="text-sm text-slate-500">
          Enter the Disbursement Account ID forwarded by the accountant.
        </p>
        <input
          className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 font-mono"
          placeholder="e.g. 3f8e7a12-…"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && value.trim() && onSubmit(value.trim())}
        />
        <button
          disabled={!value.trim()}
          onClick={() => onSubmit(value.trim())}
          className="w-full py-2 rounded-lg font-semibold text-white bg-brand-500 hover:bg-brand-700 disabled:opacity-40 transition-colors"
        >
          Load DA
        </button>
      </div>
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────

export function OperatorPage() {
  const [daId, setDaId] = useState<string | null>(null)
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null)
  const [justification, setJustification] = useState('')
  const [showPdf, setShowPdf] = useState(false)
  const [showAudit, setShowAudit] = useState(false)

  const { data: da } = useDAStatus(daId)
  const { data: deviation } = useDeviationReport(
    da?.status === 'PENDING_OPERATOR_APPROVAL' ? daId : null
  )
  const { data: auditEntries } = useAuditLog(showAudit ? daId : null)

  const approveMutation = useApproveDA(daId ?? '')
  const rejectMutation = useRejectDA(daId ?? '')
  const isMutating = approveMutation.isPending || rejectMutation.isPending

  function handleRowClick(itemId: string) {
    setSelectedItemId(itemId === selectedItemId ? null : itemId)
    if (deviation?.items.find((i) => i.item_id === itemId)?.bounding_box) {
      setShowPdf(true)
    }
  }

  async function handleApprove() {
    await approveMutation.mutateAsync({ justification })
  }

  async function handleReject() {
    const reason = justification || 'Rejected by operator'
    await rejectMutation.mutateAsync({ reason })
  }

  const isPendingApproval = da?.status === 'PENDING_OPERATOR_APPROVAL'

  return (
    <div className="flex flex-col h-screen bg-slate-100 overflow-hidden">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-3 bg-white border-b border-slate-200 shadow-sm">
        <div className="flex items-center gap-3">
          <span className="text-lg font-bold text-brand-700">OpenDA</span>
          <span className="text-slate-400">|</span>
          <span className="text-sm text-slate-600">Operator Approval</span>
        </div>
        {daId && (
          <div className="flex items-center gap-2 text-xs text-slate-500 font-mono">
            {daId}
          </div>
        )}
      </header>

      {!daId ? (
        <DAIdInput onSubmit={(id) => setDaId(id)} />
      ) : (
        <div className="flex flex-col flex-1 overflow-hidden bg-white">
          {/* Summary */}
          {da && <SummaryBar da={da} />}

          {/* Main content */}
          <div className="flex-1 overflow-y-auto">
            {/* Deviation table */}
            {isPendingApproval && deviation?.items ? (
              <DeviationTable
                items={deviation.items}
                selectedItemId={selectedItemId}
                onSelectItem={handleRowClick}
              />
            ) : da?.status === 'APPROVED' || da?.status === 'PUSHED_TO_ERP' ? (
              <div className="flex items-center justify-center h-40 text-green-600 font-medium text-sm">
                ✓ DA approved and pushed to ERP
              </div>
            ) : da?.status === 'REJECTED' ? (
              <div className="flex items-center justify-center h-40 text-red-600 font-medium text-sm">
                ✗ DA rejected
              </div>
            ) : (
              <div className="flex items-center justify-center h-40 text-slate-400 text-sm">
                DA is {da?.status?.replace(/_/g, ' ')} — not ready for operator review
              </div>
            )}

            {/* Audit log */}
            {showAudit && auditEntries && <AuditDrawer entries={auditEntries} />}
          </div>

          {/* Footer actions */}
          <div className="flex-none border-t border-slate-200 bg-white px-6 py-4 space-y-3">
            <div className="flex items-center gap-4 text-xs">
              <button
                className="text-brand-500 hover:underline"
                onClick={() => setShowPdf(!showPdf)}
              >
                {showPdf ? 'Hide' : 'View'} PDF
              </button>
              <button
                className="text-brand-500 hover:underline"
                onClick={() => setShowAudit(!showAudit)}
              >
                {showAudit ? 'Hide' : 'Show'} audit trail
              </button>
            </div>

            {isPendingApproval && (
              <>
                <JustificationInput
                  value={justification}
                  onChange={setJustification}
                  placeholder="Operator remarks (optional — stored in audit log)…"
                />
                <ApproveRejectButtons
                  onApprove={handleApprove}
                  onReject={handleReject}
                  isPending={isMutating}
                />
                {(approveMutation.isError || rejectMutation.isError) && (
                  <p className="text-sm text-red-600">
                    Action failed — please retry.
                  </p>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {/* PDF Modal */}
      {showPdf && deviation && daId && (
        <PDFModal
          pdfUrl={`/api/v1/da/${daId}/pdf`}
          items={deviation.items}
          selectedItemId={selectedItemId}
          onClose={() => setShowPdf(false)}
        />
      )}
    </div>
  )
}
