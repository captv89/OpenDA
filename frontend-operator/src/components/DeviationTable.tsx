/**
 * DeviationTable — read-only summary table for the operator.
 * Shows every line item with PDA vs FDA values, variance, accountant decision, and note.
 */
import type { DeviationLineItem, FlagReason, ItemStatus } from '@/types'

const FLAG_LABELS: Record<FlagReason, string> = {
  LOW_CONFIDENCE: 'Low conf.',
  MISSING_PDA_LINE: 'No PDA line',
  HIGH_DEVIATION: 'High deviation',
  MISSING_FROM_FDA: 'Missing FDA',
}

const STATUS_CHIP: Record<ItemStatus, string> = {
  OK: 'bg-green-50 text-green-700 border-green-200',
  REQUIRES_REVIEW: 'bg-orange-50 text-orange-700 border-orange-200',
  CONFIRMED: 'bg-blue-50 text-blue-700 border-blue-200',
  OVERRIDDEN: 'bg-slate-50 text-slate-600 border-slate-200',
}

interface Props {
  items: DeviationLineItem[]
  onSelectItem: (itemId: string) => void
  selectedItemId: string | null
}

export function DeviationTable({ items, onSelectItem, selectedItemId }: Props) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="bg-slate-50 text-xs text-slate-500 uppercase tracking-wide">
            <th className="text-left px-4 py-2.5 font-medium">Description</th>
            <th className="text-left px-4 py-2.5 font-medium">Category</th>
            <th className="text-right px-4 py-2.5 font-medium">PDA ($)</th>
            <th className="text-right px-4 py-2.5 font-medium">FDA ($)</th>
            <th className="text-right px-4 py-2.5 font-medium">Var. ($)</th>
            <th className="text-right px-4 py-2.5 font-medium">Var. (%)</th>
            <th className="px-4 py-2.5 font-medium">Status</th>
            <th className="px-4 py-2.5 font-medium">Flags</th>
            <th className="px-4 py-2.5 font-medium">Accountant note</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {items.map((item) => {
            const isSelected = selectedItemId === item.item_id
            const isFlagged = item.flag_reasons.length > 0
            return (
              <tr
                key={item.item_id}
                onClick={() => onSelectItem(item.item_id)}
                className={`
                  cursor-pointer transition-colors
                  ${isSelected ? 'bg-blue-50' : isFlagged ? 'bg-amber-50/40 hover:bg-amber-50' : 'hover:bg-slate-50'}
                `}
              >
                <td className="px-4 py-2.5 max-w-xs">
                  <p className="truncate font-medium text-slate-800">{item.description}</p>
                </td>
                <td className="px-4 py-2.5 text-slate-600 whitespace-nowrap">
                  {item.category}
                </td>
                <td className="px-4 py-2.5 text-right font-mono text-slate-700">
                  {item.pda_value != null ? item.pda_value.toFixed(2) : '—'}
                </td>
                <td className="px-4 py-2.5 text-right font-mono text-slate-700">
                  {item.fda_value != null ? item.fda_value.toFixed(2) : '—'}
                </td>
                <td
                  className={`px-4 py-2.5 text-right font-mono font-medium ${
                    (item.abs_variance ?? 0) > 500
                      ? 'text-red-600'
                      : (item.abs_variance ?? 0) > 0
                        ? 'text-amber-600'
                        : 'text-slate-700'
                  }`}
                >
                  {item.abs_variance != null ? item.abs_variance.toFixed(2) : '—'}
                </td>
                <td
                  className={`px-4 py-2.5 text-right font-mono font-medium ${
                    (item.pct_variance ?? 0) > 10
                      ? 'text-red-600'
                      : (item.pct_variance ?? 0) > 0
                        ? 'text-amber-600'
                        : 'text-slate-700'
                  }`}
                >
                  {item.pct_variance != null ? `${item.pct_variance.toFixed(1)}%` : '—'}
                </td>
                <td className="px-4 py-2.5">
                  <span
                    className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium border ${STATUS_CHIP[item.status]}`}
                  >
                    {item.status.replace(/_/g, ' ')}
                  </span>
                </td>
                <td className="px-4 py-2.5">
                  <div className="flex gap-1 flex-wrap">
                    {item.flag_reasons.map((r) => (
                      <span
                        key={r}
                        className="inline-flex px-1.5 py-0.5 rounded text-xs font-medium bg-red-50 text-red-700 border border-red-200"
                      >
                        {FLAG_LABELS[r]}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="px-4 py-2.5 max-w-xs">
                  <p className="text-xs text-slate-600 truncate italic">
                    {item.accountant_note || '—'}
                  </p>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
