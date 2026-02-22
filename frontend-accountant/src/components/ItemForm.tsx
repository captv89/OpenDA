/**
 * ItemForm — editable row for a single deviation line item.
 * Shows PDA vs FDA values, variance, AI flags, and lets the accountant
 * set the review status and add a note.
 */
import { useDAStore } from '@/store/daStore'
import { FlagBadge } from './FlagBadge'
import type { DeviationLineItem, ItemStatus } from '@/types'

const STATUS_OPTIONS: { value: ItemStatus; label: string }[] = [
  { value: 'REQUIRES_REVIEW', label: 'Requires review' },
  { value: 'CONFIRMED', label: 'Confirmed — accept FDA amount' },
  { value: 'OVERRIDDEN', label: 'Override — use PDA amount' },
]

interface Props {
  item: DeviationLineItem
}

export function ItemForm({ item }: Props) {
  const focusedItemId = useDAStore((s) => s.focusedItemId)
  const focusItem = useDAStore((s) => s.focusItem)
  const edits = useDAStore((s) => s.edits)
  const setItemStatus = useDAStore((s) => s.setItemStatus)
  const setItemNote = useDAStore((s) => s.setItemNote)
  const setCurrentPage = useDAStore((s) => s.setCurrentPage)

  const edit = edits[item.item_id] ?? { status: item.status, accountant_note: '' }
  const isFocused = focusedItemId === item.item_id
  const hasBBox = !!item.bounding_box

  function handleFocus() {
    focusItem(item.item_id)
    if (hasBBox && item.bounding_box) {
      setCurrentPage(item.bounding_box.page)
    }
  }

  const varianceColor =
    item.flag_reasons.includes('HIGH_DEVIATION')
      ? 'text-red-600 font-semibold'
      : 'text-slate-700'

  return (
    <div
      onClick={handleFocus}
      className={`
        p-4 rounded-lg border transition-shadow cursor-pointer
        ${isFocused ? 'border-brand-500 shadow-md bg-blue-50' : 'border-slate-200 bg-white hover:shadow-sm'}
      `}
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <div>
          <p className="text-sm font-medium text-slate-800">{item.description}</p>
          <p className="text-xs text-slate-500 uppercase tracking-wide">{item.category}</p>
        </div>
        <FlagBadge reasons={item.flag_reasons} status={edit.status} />
      </div>

      {/* Values grid */}
      <div className="grid grid-cols-3 gap-2 mb-3 text-xs">
        <div>
          <p className="text-slate-500">PDA estimate</p>
          <p className="font-mono font-medium">{item.pda_value != null ? `$${item.pda_value.toFixed(2)}` : '—'}</p>
        </div>
        <div>
          <p className="text-slate-500">FDA actual</p>
          <p className="font-mono font-medium">{item.fda_value != null ? `$${item.fda_value.toFixed(2)}` : '—'}</p>
        </div>
        <div>
          <p className="text-slate-500">Variance</p>
          <p className={`font-mono ${varianceColor}`}>
            {item.abs_variance != null
              ? `$${item.abs_variance.toFixed(2)} (${item.pct_variance?.toFixed(1)}%)`
              : '—'}
          </p>
        </div>
      </div>

      {/* Confidence bar */}
      {item.confidence_score != null && (
        <div className="mb-3">
          <div className="flex justify-between text-xs text-slate-500 mb-0.5">
            <span>AI confidence</span>
            <span>{(item.confidence_score * 100).toFixed(0)}%</span>
          </div>
          <div className="h-1.5 rounded-full bg-slate-200 overflow-hidden">
            <div
              ref={(el) => { if (el) el.style.width = `${item.confidence_score! * 100}%` }}
              className={`h-full rounded-full transition-all ${
                item.confidence_score >= 0.85
                  ? 'bg-green-500'
                  : item.confidence_score >= 0.6
                    ? 'bg-amber-400'
                    : 'bg-red-500'
              }`}
            />
          </div>
        </div>
      )}

      {/* Review controls — only shown when item is focused or flagged */}
      {(isFocused || item.flag_reasons.length > 0) && (
        <div className="space-y-2 pt-2 border-t border-slate-100">
          <select
            value={edit.status}
            aria-label="Item status"
            title="Item status"
            onChange={(e) => setItemStatus(item.item_id, e.target.value as ItemStatus)}
            onClick={(e) => e.stopPropagation()}
            className="w-full text-sm border border-slate-300 rounded-md px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            {STATUS_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
          <textarea
            rows={2}
            placeholder="Add accountant note (optional)…"
            value={edit.accountant_note}
            onChange={(e) => setItemNote(item.item_id, e.target.value)}
            onClick={(e) => e.stopPropagation()}
            className="w-full text-sm border border-slate-300 rounded-md px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none"
          />
        </div>
      )}
    </div>
  )
}
