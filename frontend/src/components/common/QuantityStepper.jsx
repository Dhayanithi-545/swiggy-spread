import { Minus, Plus } from 'lucide-react'

// The ADD / − 2 + control on every dish and product. `qty === 0`
// renders the ADD button; anything else the stepper.
export function QuantityStepper({ qty = 0, onAdd, onInc, onDec, size = 'md' }) {
  if (qty === 0) {
    return (
      <button type="button" className={`stepper-add stepper-add--${size}`} onClick={onAdd}>
        ADD
      </button>
    )
  }
  return (
    <div className={`stepper stepper--${size}`}>
      <button type="button" onClick={onDec} aria-label="Decrease quantity">
        <Minus size={14} aria-hidden="true" />
      </button>
      <span aria-live="polite">{qty}</span>
      <button type="button" onClick={onInc} aria-label="Increase quantity">
        <Plus size={14} aria-hidden="true" />
      </button>
    </div>
  )
}
