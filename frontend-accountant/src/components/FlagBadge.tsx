/**
 * FlagBadge — small coloured pill indicating AI flag reason(s).
 */
import type { FlagReason, ItemStatus } from '@/types'

const REASON_LABEL: Record<FlagReason, string> = {
  LOW_CONFIDENCE: 'Low confidence',
  MISSING_PDA_LINE: 'Not in PDA',
  HIGH_DEVIATION: 'High deviation',
  MISSING_FROM_FDA: 'Missing from FDA',
}

const REASON_COLOR: Record<FlagReason, string> = {
  LOW_CONFIDENCE: 'bg-amber-100 text-amber-800 border-amber-300',
  MISSING_PDA_LINE: 'bg-purple-100 text-purple-800 border-purple-300',
  HIGH_DEVIATION: 'bg-red-100 text-red-800 border-red-300',
  MISSING_FROM_FDA: 'bg-orange-100 text-orange-800 border-orange-300',
}

const STATUS_COLOR: Record<ItemStatus, string> = {
  OK: 'bg-green-100 text-green-800 border-green-300',
  REQUIRES_REVIEW: 'bg-orange-100 text-orange-800 border-orange-300',
  CONFIRMED: 'bg-blue-100 text-blue-800 border-blue-300',
  OVERRIDDEN: 'bg-slate-100 text-slate-600 border-slate-300',
}

interface Props {
  reasons: FlagReason[]
  status: ItemStatus
}

export function FlagBadge({ reasons, status }: Props) {
  return (
    <div className="flex flex-wrap gap-1">
      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${STATUS_COLOR[status]}`}>
        {status.replace(/_/g, ' ')}
      </span>
      {reasons.map((r) => (
        <span
          key={r}
          className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${REASON_COLOR[r]}`}
        >
          {REASON_LABEL[r]}
        </span>
      ))}
    </div>
  )
}
