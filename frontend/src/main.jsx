import { useEffect, useRef, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { createAvatar } from '@bible-strong/avatar-react'
import strobi from './strobi.avatar.json'

// Valida el archivo una sola vez.
const Strobi = createAvatar(strobi)

const TYPING_PAUSE_MS = 2500 // sin teclear: vuelve a reposo
const THINKING_TIMEOUT_MS = 60000 // si el backend nunca responde
const SLEEP_AFTER_MS = 90000 // inactividad total: se duerme

function ElisaAvatar() {
  const [view, setView] = useState({ state: 'idle', face: undefined })
  const [look, setLook] = useState(null)
  const avatar = useRef(null)

  useEffect(() => {
    const loadedAt = Date.now()
    let current = 'idle'
    let lastActive = Date.now()
    let holdTimer
    let typingTimer

    // Cambia de estado; si hay holdMs, vuelve a idle pasado ese tiempo.
    const go = (state, face, holdMs = 0) => {
      clearTimeout(holdTimer)
      current = state
      setView({ state, face })
      if (holdMs) holdTimer = setTimeout(() => go('idle'), holdMs)
    }

    const markActive = () => {
      lastActive = Date.now()
      if (current === 'sleeping') go('waking', undefined, 1500)
    }

    // La persona escribe: Strobi escucha y mira hacia el cuadro de texto.
    const onInput = (e) => {
      if (!e.target.closest?.('#chat-input')) return
      markActive()
      if (current === 'thinking') return
      go('listening')
      setLook([0, -0.7])
      clearTimeout(typingTimer)
      typingTimer = setTimeout(() => {
        setLook(null)
        if (current === 'listening') go('idle')
      }, TYPING_PAUSE_MS)
    }

    // La persona envía: Strobi asiente y piensa hasta que llegue la respuesta.
    const onSend = () => {
      clearTimeout(typingTimer)
      setLook(null)
      go('thinking', undefined, THINKING_TIMEOUT_MS)
      avatar.current?.poke('nod')
    }
    const onKeyDown = (e) => {
      markActive()
      const box = e.target.closest?.('#chat-input')
      if (box && e.key === 'Enter' && !e.shiftKey && box.textContent.trim()) onSend()
    }
    const onClick = (e) => {
      markActive()
      if (e.target.closest?.('#chat-submit')) onSend()
    }

    // El backend informa la emoción detectada (ver public/elements/AvatarSignal.jsx).
    const onSignal = (e) => {
      const d = e.detail || {}
      if (d.ts && d.ts < loadedAt) return // ignora el historial al recargar
      clearTimeout(typingTimer)
      setLook(null)
      go(d.state || 'idle', d.face || undefined, d.hold_ms || 8000)
      avatar.current?.poke('nod')
    }

    const sleepCheck = setInterval(() => {
      if (current === 'idle' && Date.now() - lastActive > SLEEP_AFTER_MS) go('sleeping')
    }, 5000)

    const opts = { capture: true }
    document.addEventListener('input', onInput, opts)
    document.addEventListener('keydown', onKeyDown, opts)
    document.addEventListener('click', onClick, opts)
    document.addEventListener('pointermove', markActive, { capture: true, passive: true })
    window.addEventListener('elisa:signal', onSignal)

    return () => {
      document.removeEventListener('input', onInput, opts)
      document.removeEventListener('keydown', onKeyDown, opts)
      document.removeEventListener('click', onClick, opts)
      document.removeEventListener('pointermove', markActive, opts)
      window.removeEventListener('elisa:signal', onSignal)
      clearInterval(sleepCheck)
      clearTimeout(holdTimer)
      clearTimeout(typingTimer)
    }
  }, [])

  return (
    <Strobi
      ref={avatar}
      state={view.state}
      face={view.face}
      lookAt={look}
      followPointer
      size="100%"
      ariaLabel="Strobi, tu acompañante en la conversación"
    />
  )
}

const host = document.createElement('div')
host.id = 'elisa-avatar'
document.body.appendChild(host)
createRoot(host).render(<ElisaAvatar />)
