/**
 * ApproveButton + RejectButton — terminal action buttons for the operator.
 */

interface ApproveProps {
  onApprove: () => void
  onReject: () => void
  isPending: boolean
}

export function ApproveRejectButtons({ onApprove, onReject, isPending }: ApproveProps) {
  return (
    <div className="flex gap-3">
      <button
        type="button"
        disabled={isPending}
        onClick={onReject}
        className="
          flex-1 px-4 py-2 rounded-lg font-semibold text-red-700
          border border-red-300 bg-red-50 hover:bg-red-100
          disabled:opacity-40 disabled:cursor-not-allowed
          transition-colors
        "
      >
        {isPending ? '…' : 'Reject'}
      </button>

      <button
        type="button"
        disabled={isPending}
        onClick={onApprove}
        className="
          flex-1 px-4 py-2 rounded-lg font-semibold text-white
          bg-green-600 hover:bg-green-700
          disabled:opacity-40 disabled:cursor-not-allowed
          transition-colors
        "
      >
        {isPending ? 'Processing…' : 'Approve & Push to ERP'}
      </button>
    </div>
  )
}
