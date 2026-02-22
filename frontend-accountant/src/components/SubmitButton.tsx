/**
 * SubmitButton — primary CTA for the accountant to forward the DA to the operator.
 * Disabled while any item is still REQUIRES_REVIEW and untouched.
 */
import { useDAStore } from '@/store/daStore'
import type { DeviationLineItem } from '@/types'

interface Props {
  items: DeviationLineItem[]
  onSubmit: () => void
  isPending: boolean
}

export function SubmitButton({ items, onSubmit, isPending }: Props) {
  const edits = useDAStore((s) => s.edits)

  // Block submission if any flagged item is still in REQUIRES_REVIEW without being touched
  const untouched = items.filter(
    (item) =>
      item.flag_reasons.length > 0 && edits[item.item_id]?.status === 'REQUIRES_REVIEW'
  )

  const blocked = untouched.length > 0

  return (
    <div className="flex flex-col gap-2">
      {blocked && (
        <p className="text-sm text-red-600">
          {untouched.length} item{untouched.length > 1 ? 's' : ''} still require{untouched.length === 1 ? 's' : ''} review.
          Confirm or override each flagged item before submitting.
        </p>
      )}
      <button
        type="button"
        disabled={blocked || isPending}
        onClick={onSubmit}
        className="
          px-6 py-2 rounded-lg font-semibold text-white
          bg-brand-500 hover:bg-brand-700
          disabled:opacity-40 disabled:cursor-not-allowed
          transition-colors
        "
      >
        {isPending ? 'Submitting…' : 'Submit to Operator'}
      </button>
    </div>
  )
}
