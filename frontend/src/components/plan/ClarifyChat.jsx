import { useEffect, useRef, useState } from 'react'
import { CornerDownLeft, Sparkles } from 'lucide-react'
import {
  parseRequest, nextQuestion, applyAnswer, checkGuardrail, MAX_QUESTIONS,
} from '../../utils/planner.js'

// The clarify loop as a conversation. Mirrors conversation.py:
// ask ONLY what changes the outcome, cap at 3 questions, every question
// ships with a default so pressing enter is a valid answer, and every
// reply goes through the guardrail — replies are user input too.

function AgentBubble({ children, delay = 0 }) {
  return (
    <div className="chat-msg chat-msg--agent" style={{ animationDelay: `${delay}ms` }}>
      <span className="chat-msg__avatar" aria-hidden="true">
        <Sparkles size={14} />
      </span>
      <div className="chat-msg__bubble">{children}</div>
    </div>
  )
}

function UserBubble({ children }) {
  return (
    <div className="chat-msg chat-msg--user">
      <div className="chat-msg__bubble">{children}</div>
    </div>
  )
}

export function ClarifyChat({ initialText, onComplete, onBlocked }) {
  const [req, setReq] = useState(null)
  const [asked, setAsked] = useState([])
  const [question, setQuestion] = useState(null)
  const [log, setLog] = useState([])
  const [typing, setTyping] = useState(false)
  const [input, setInput] = useState('')
  const endRef = useRef(null)
  const inputRef = useRef(null)
  const doneRef = useRef(false)

  // boot: guardrail, parse, first question
  useEffect(() => {
    const verdict = checkGuardrail(initialText)
    if (!verdict.allowed) {
      onBlocked(verdict.reason)
      return
    }
    const parsed = parseRequest(initialText)
    const first = nextQuestion(parsed, [])
    setReq(parsed)
    setLog([{ role: 'user', text: initialText }])
    if (!first) {
      doneRef.current = true
      setTyping(true)
      const t = setTimeout(() => onComplete(parsed), 700)
      return () => clearTimeout(t)
    }
    setTyping(true)
    const t = setTimeout(() => {
      setTyping(false)
      setQuestion(first)
      setLog((l) => [...l, { role: 'agent', question: first }])
    }, 550)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialText])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [log, typing])

  const answer = (text) => {
    if (!question || doneRef.current) return
    const shown = text.trim() || `${question.default} (default)`

    const verdict = checkGuardrail(text)
    if (!verdict.allowed) {
      onBlocked(verdict.reason)
      return
    }

    const nextReq = applyAnswer(req, question, text)
    const nextAsked = [...asked, question.field]
    setLog((l) => [...l, { role: 'user', text: shown }])
    setReq(nextReq)
    setAsked(nextAsked)
    setQuestion(null)
    setInput('')

    const upcoming = nextQuestion(nextReq, nextAsked)
    setTyping(true)
    setTimeout(() => {
      if (upcoming) {
        setTyping(false)
        setQuestion(upcoming)
        setLog((l) => [...l, { role: 'agent', question: upcoming }])
        inputRef.current?.focus()
      } else {
        doneRef.current = true
        onComplete(nextReq)
      }
    }, 600)
  }

  return (
    <div className="chat">
      <div className="chat__log">
        {log.map((entry, i) =>
          entry.role === 'user' ? (
            <UserBubble key={i}>{entry.text}</UserBubble>
          ) : (
            <AgentBubble key={i}>
              <p className="chat-q__text">{entry.question.text}</p>
              {entry.question.why && <p className="chat-q__why">{entry.question.why}</p>}
            </AgentBubble>
          ),
        )}
        {typing && (
          <div className="chat-msg chat-msg--agent">
            <span className="chat-msg__avatar" aria-hidden="true">
              <Sparkles size={14} />
            </span>
            <div className="chat-msg__bubble chat-typing" aria-label="Spread is thinking">
              <i /><i /><i />
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {question && (
        <div className="chat__composer anim-fade-up">
          <div className="chat__options" role="group" aria-label="Quick answers">
            {(question.options || []).map((opt) => (
              <button key={opt} type="button" className="chat__option" onClick={() => answer(opt)}>
                {opt}
              </button>
            ))}
          </div>
          <form
            className="chat__inputrow"
            onSubmit={(e) => {
              e.preventDefault()
              answer(input)
            }}
          >
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={`Type an answer — enter uses “${question.default}”`}
              aria-label={question.text}
              autoFocus
            />
            <button type="submit" className="chat__send" aria-label="Send answer">
              <CornerDownLeft size={17} aria-hidden="true" />
            </button>
          </form>
          <p className="t-caption chat__cap">
            Question {asked.length + 1} of at most {MAX_QUESTIONS} — anything else I'll assume out loud.
          </p>
        </div>
      )}
    </div>
  )
}
