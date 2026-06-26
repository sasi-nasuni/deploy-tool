import { useMemo, useState } from 'react'

interface FilerIPInputProps {
  value: string
  onChange: (nextValue: string) => void
}

const IPV4_REGEX =
  /^((25[0-5]|2[0-4]\d|[01]?\d?\d)\.){3}(25[0-5]|2[0-4]\d|[01]?\d?\d)$/

export function isValidIPv4(value: string): boolean {
  return IPV4_REGEX.test(value)
}

export function FilerIPInput({ value, onChange }: FilerIPInputProps) {
  const [touched, setTouched] = useState(false)

  const showError = useMemo(() => touched && value.length > 0 && !isValidIPv4(value), [touched, value])

  return (
    <div>
      <input
        type="text"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onBlur={() => setTouched(true)}
        placeholder="10.0.0.100"
        className={`w-full rounded-md border bg-white px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 ${
          showError
            ? 'border-red-500 focus:border-red-500 focus:ring-red-400'
            : 'border-slate-300 focus:border-slate-500 focus:ring-slate-500'
        }`}
      />
      {showError && <p className="mt-1 text-xs text-red-600">Enter a valid IPv4 address.</p>}
    </div>
  )
}
