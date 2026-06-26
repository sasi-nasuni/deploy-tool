import { useEffect, useState } from 'react'

interface TokenModalProps {
  message: string
  onSubmit: (token: string) => Promise<void>
  onClose: () => void
}

export function TokenModal({ message, onSubmit, onClose }: TokenModalProps) {
  const [token, setToken] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    setToken('')
  }, [message])

  const handleSubmit = async () => {
    if (!token.trim() || submitting) {
      return
    }

    setSubmitting(true)
    try {
      await onSubmit(token)
      onClose()
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-96 rounded-lg bg-white p-6 shadow-xl">
        <p className="mb-4 text-gray-700">{message}</p>
        <input
          type="text"
          placeholder="Paste token here"
          className="mb-4 w-full rounded border px-3 py-2 font-mono text-sm"
          value={token}
          onChange={(event) => setToken(event.target.value)}
          disabled={submitting}
        />
        <button
          className="w-full rounded bg-blue-600 py-2 text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-400"
          onClick={() => void handleSubmit()}
          disabled={!token.trim() || submitting}
        >
          {submitting ? 'Submitting…' : 'Submit'}
        </button>
      </div>
    </div>
  )
}
