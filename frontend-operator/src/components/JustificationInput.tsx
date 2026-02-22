/**
 * JustificationInput — operator remarks textarea before approving or rejecting.
 */

interface Props {
  value: string
  onChange: (v: string) => void
  placeholder?: string
  rows?: number
}

export function JustificationInput({
  value,
  onChange,
  placeholder = 'Add remarks for audit trail (optional)…',
  rows = 3,
}: Props) {
  return (
    <textarea
      rows={rows}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none"
    />
  )
}
