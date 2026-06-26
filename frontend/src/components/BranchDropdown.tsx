import { useEffect, useMemo, useRef, useState } from 'react'

interface BranchDropdownProps {
  branches: string[]
  selected: string | null
  onSelect: (branch: string) => void
  loading: boolean
}

export function BranchDropdown({ branches, selected, onSelect, loading }: BranchDropdownProps) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [highlighted, setHighlighted] = useState(0)
  const wrapperRef = useRef<HTMLDivElement | null>(null)
  const inputRef = useRef<HTMLInputElement | null>(null)

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase()
    if (!normalized) {
      return branches
    }

    return branches.filter((branch) => branch.toLowerCase().includes(normalized))
  }, [branches, query])

  useEffect(() => {
    const onClickOutside = (event: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
        setOpen(false)
        setQuery('')
      }
    }

    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  useEffect(() => {
    if (open) {
      setHighlighted(0)
      inputRef.current?.focus()
    }
  }, [open])

  useEffect(() => {
    if (highlighted >= filtered.length) {
      setHighlighted(Math.max(filtered.length - 1, 0))
    }
  }, [filtered.length, highlighted])

  const onKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setHighlighted((previous) => Math.min(previous + 1, Math.max(filtered.length - 1, 0)))
      return
    }

    if (event.key === 'ArrowUp') {
      event.preventDefault()
      setHighlighted((previous) => Math.max(previous - 1, 0))
      return
    }

    if (event.key === 'Enter' && filtered[highlighted]) {
      event.preventDefault()
      onSelect(filtered[highlighted])
      setOpen(false)
      setQuery('')
      return
    }

    if (event.key === 'Escape') {
      event.preventDefault()
      setOpen(false)
      setQuery('')
    }
  }

  return (
    <div className="relative w-full" ref={wrapperRef}>
      <button
        type="button"
        className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-left text-sm shadow-sm transition hover:border-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-500"
        onClick={() => setOpen((previous) => !previous)}
      >
        {selected || 'Select branch'}
      </button>

      {open && (
        <div className="absolute z-20 mt-2 w-full rounded-md border border-slate-300 bg-white shadow-lg">
          <div className="border-b border-slate-200 p-2">
            <input
              ref={inputRef}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={onKeyDown}
              className="w-full rounded-md border border-slate-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-slate-500"
              placeholder="Search branches"
            />
          </div>

          <ul className="max-h-56 overflow-y-auto py-1 text-sm">
            {loading && <li className="px-3 py-2 text-slate-500">Loading branches...</li>}
            {!loading && filtered.length === 0 && <li className="px-3 py-2 text-slate-500">No branches match</li>}
            {!loading &&
              filtered.map((branch, index) => (
                <li key={branch}>
                  <button
                    type="button"
                    className={`w-full px-3 py-2 text-left transition ${
                      index === highlighted ? 'bg-slate-100 text-slate-900' : 'text-slate-700 hover:bg-slate-100'
                    }`}
                    onMouseEnter={() => setHighlighted(index)}
                    onClick={() => {
                      onSelect(branch)
                      setOpen(false)
                      setQuery('')
                    }}
                  >
                    {branch}
                  </button>
                </li>
              ))}
          </ul>
        </div>
      )}
    </div>
  )
}
