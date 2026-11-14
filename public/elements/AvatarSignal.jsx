import { useEffect } from 'react'

// Elemento invisible: traslada la emoción detectada por el backend al avatar.
// `props` es global en los elementos personalizados de Chainlit.
export default function AvatarSignal() {
  useEffect(() => {
    window.dispatchEvent(new CustomEvent('elisa:signal', { detail: props }))
  }, [props?.ts])
  return null
}
