import { useState } from 'react'
import { Copy, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface CopyButtonProps {
  getText: () => string
}

export function CopyButton({ getText }: CopyButtonProps) {
  const [copied, setCopied] = useState(false)

  async function handleClick() {
    await navigator.clipboard.writeText(getText())
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <Button variant="outline" size="sm" onClick={handleClick} className="gap-1.5">
      {copied ? <Check size={13} /> : <Copy size={13} />}
      {copied ? 'Copied' : 'Copy'}
    </Button>
  )
}
