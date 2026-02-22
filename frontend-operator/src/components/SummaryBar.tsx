/**
 * SummaryBar — shows high-level totals and DA metadata at the top of the operator view.
 */
import type { DAStatusResponse } from '@/types'

interface Props {
  da: DAStatusResponse
}

const STATUS_CHIP: Record<string, string> = {
  PENDING_OPERATOR_APPROVAL: 'bg-amber-100 text-amber-800 border-amber-300',
  APPROVED: 'bg-green-100 text-green-800 border-green-300',
  REJECTED: 'bg-red-100 text-red-800 border-red-300',
  PUSHED_TO_ERP: 'bg-cyan-100 text-cyan-800 border-cyan-300',
}

export function SummaryBar({ da }: Props) {
  const delta =
    da.total_actual != null && da.total_estimated != null
      ? da.total_actual - da.total_estimated
      : null

  return (
    <div className="flex flex-wrap items-center gap-4 px-6 py-4 bg-white border-b border-slate-200">
      <div>
        <p className="text-xs text-slate-500">Port Call</p>
        <p className="text-sm font-semibold text-slate-800 font-mono">{da.port_call_id}</p>
      </div>

      <div>
        <p className="text-xs text-slate-500">PDA Estimate</p>
        <p className="text-sm font-semibold text-slate-800">
          {da.total_estimated != null ? `$${da.total_estimated.toFixed(2)}` : '—'}
        </p>
      </div>

      <div>
        <p className="text-xs text-slate-500">FDA Actual</p>
        <p className="text-sm font-semibold text-slate-800">
          {da.total_actual != null ? `$${da.total_actual.toFixed(2)}` : '—'}
        </p>
      </div>

      {delta != null && (
        <div>
          <p className="text-xs text-slate-500">Net variance</p>
          <p
            className={`text-sm font-semibold ${
              Math.abs(delta) > 500 ? 'text-red-600' : 'text-green-600'
            }`}
          >
            {delta >= 0 ? '+' : ''}
            {delta.toFixed(2)}
          </p>
        </div>
      )}

      <div>
        <p className="text-xs text-slate-500">Flagged items</p>
        <p
          className={`text-sm font-semibold ${
            da.flagged_items_count > 0 ? 'text-red-600' : 'text-green-600'
          }`}
        >
          {da.flagged_items_count}
        </p>
      </div>

      <div>
        <p className="text-xs text-slate-500">AI model</p>
        <p className="text-xs text-slate-600 font-mono">{da.llm_provider ?? '—'}</p>
      </div>

      <div className="ml-auto">
        <span
          className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border ${STATUS_CHIP[da.status] ?? 'bg-slate-100 text-slate-600 border-slate-200'}`}
        >
          {da.status.replace(/_/g, ' ')}
        </span>
      </div>
    </div>
  )
}
