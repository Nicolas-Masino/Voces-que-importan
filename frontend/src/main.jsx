import { useEffect, useRef, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { createAvatar } from '@bible-strong/avatar-react'
import strobi from './strobi.avatar.json'

// Valida el archivo una sola vez.
const Strobi = createAvatar(strobi)

const TYPING_PAUSE_MS = 2500 // sin teclear: vuelve a reposo
const THINKING_TIMEOUT_MS = 60000 // si el backend nunca responde
const SLEEP_AFTER_MS = 90000 // inactividad total: se duerme
const ERROR_HOLD_MS = 10000
const ERROR_STATE = 'alerting'

// Paneles que, al abrirse, hacen que el avatar se desvanezca (cl.Text en el panel lateral, diálogos).
const PANEL_SELECTORS = [
  '#side-view-title',
  '#side-view-content',
  '[data-testid="element-view"]',
  '[role="dialog"]',
]

function ElisaAvatar() {
  const [view, setView] = useState({ state: 'idle', face: undefined })
  const [look, setLook] = useState(null)
  const [panelOpen, setPanelOpen] = useState(false)
  const avatar = useRef(null)

  // Desvanece el avatar mientras hay un panel abierto y lo recupera al cerrarse.
  // No se desmonta: solo se pausa y se oculta con CSS (clase en <body>).
  useEffect(() => {
    let last = null
    const isShown = (el) => el.getClientRects().length > 0 // montado Y visible

    const check = () => {
      const hit = PANEL_SELECTORS.find((sel) =>
        Array.from(document.querySelectorAll(sel)).some(isShown)
      )
      const open = Boolean(hit)
      if (open === last) return
      last = open
      document.body.classList.toggle('elisa-panel-open', open)
      setPanelOpen(open)
      console.info('[elisa] panel', open ? `abierto (${hit})` : 'cerrado')
    }

    // Altas y bajas de nodos, más un sondeo liviano por si el panel
    // se muestra u oculta cambiando atributos en vez de montarse.
    const observer = new MutationObserver(check)
    observer.observe(document.body, { childList: true, subtree: true })
    const poll = setInterval(check, 500)
    check()

    return () => {
      observer.disconnect()
      clearInterval(poll)
      document.body.classList.remove('elisa-panel-open')
    }
  }, [])

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

    // Pantalla de bienvenida: Strobi centrado hasta el primer mensaje.
    document.body.classList.add('elisa-hero')
    const leaveHero = () => document.body.classList.remove('elisa-hero')
    go('happy', undefined, 5000)

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
      leaveHero()
      clearTimeout(typingTimer)
      setLook(null)
      go('thinking', undefined, THINKING_TIMEOUT_MS)
      avatar.current?.poke('nod')
    }
    const onKeyDown = (e) => {
      markActive()
      const box = e.target.closest?.('#chat-input')
      const text = box ? (box.value ?? box.textContent ?? '') : ''
      if (box && e.key === 'Enter' && !e.shiftKey && text.trim()) onSend()
    }
    const onClick = (e) => {
      markActive()
      if (e.target.closest?.('#chat-submit') ||
          e.target.closest?.('#starters')
      ) onSend()
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

    // El backend avisa de un cl.ErrorMessage (ver avatar_alert en src/emotion.py).
    const onWindowMessage = (e) => {
      const d = e.data
      if (!d || d.source !== 'elisa' || d.event !== 'error') return
      leaveHero()
      clearTimeout(typingTimer)
      setLook(null)
      go(ERROR_STATE, undefined, ERROR_HOLD_MS)
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
    window.addEventListener('message', onWindowMessage)

    return () => {
      document.removeEventListener('input', onInput, opts)
      document.removeEventListener('keydown', onKeyDown, opts)
      document.removeEventListener('click', onClick, opts)
      document.removeEventListener('pointermove', markActive, opts)
      window.removeEventListener('elisa:signal', onSignal)
      window.removeEventListener('message', onWindowMessage)
      leaveHero()
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
      paused={panelOpen}
      followPointer
      size="100%"
      ariaLabel="Strobi, tu acompañante en la conversación"
    />
  )
}

// Texto de bienvenida (se ve solo mientras la pantalla está en modo inicio).
const hero = document.createElement('div')
hero.id = 'elisa-hero'
hero.innerHTML =
  '<h1>¡Hola! Soy Elisa</h1>' +
  '<p class="elisa-hero-question">¿Sobre qué te gustaría hablar?</p>'
document.body.appendChild(hero)

const host = document.createElement('div')
host.id = 'elisa-avatar'
document.body.appendChild(host)
createRoot(host).render(<ElisaAvatar />)

if (!window.__dictationListener) {
  window.__dictationListener = true;

  window.addEventListener('message', (event) => {
    const data = event.data;
    if (!data || data.type !== 'dictation' || !data.text) return;

    const box = document.querySelector('#chat-input');
    if (!box) {
      console.error('Dictation: no se encontró #chat-input');
      return;
    }

    const setter = Object.getOwnPropertyDescriptor(
      window.HTMLTextAreaElement.prototype,
      'value'
    ).set;

    const current = box.value.trim();
    setter.call(box, current ? `${current} ${data.text}` : data.text);
    box.dispatchEvent(new Event('input', { bubbles: true }));
    box.focus();
  });
}
