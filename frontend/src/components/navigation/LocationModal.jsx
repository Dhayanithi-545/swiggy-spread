import { MapPin, LocateFixed, Briefcase, Home as HomeIcon, Check } from 'lucide-react'
import { Modal } from '../common/Modal.jsx'
import { addresses } from '../../data/user.js'
import { useToast } from '../../context/ToastContext.jsx'

const LABEL_ICONS = { Home: HomeIcon, Work: Briefcase }

export function LocationModal({ open, onClose, current, onSelect }) {
  const toast = useToast()

  return (
    <Modal open={open} onClose={onClose} title="Where should everything land?">
      <button
        type="button"
        className="loc-gps"
        onClick={() => {
          toast('Using your saved Home address — GPS is a live-mode feature.', { type: 'info' })
          onSelect(addresses[0])
        }}
      >
        <LocateFixed size={18} aria-hidden="true" />
        <div>
          <div className="loc-gps__title">Use current location</div>
          <div className="t-caption">Simulated — picks your default saved address</div>
        </div>
      </button>

      <p className="t-label" style={{ margin: '18px 0 10px' }}>Saved addresses</p>
      <ul className="loc-list">
        {addresses.map((a) => {
          const Icon = LABEL_ICONS[a.label] || MapPin
          const active = current?.id === a.id
          return (
            <li key={a.id}>
              <button type="button" className={`loc-item ${active ? 'loc-item--active' : ''}`} onClick={() => onSelect(a)}>
                <span className="loc-item__icon">
                  <Icon size={17} aria-hidden="true" />
                </span>
                <span className="loc-item__body">
                  <span className="loc-item__label">
                    {a.label}
                    {a.isDefault && <span className="badge badge--brand">Default</span>}
                  </span>
                  <span className="t-sub">{a.line}, {a.area} — {a.pincode}</span>
                </span>
                {active && <Check size={17} className="loc-item__check" aria-hidden="true" />}
              </button>
            </li>
          )
        })}
      </ul>
      <p className="t-caption" style={{ marginTop: 16 }}>
        Live mode reads these from your Swiggy account after login. Nothing here edits them.
      </p>
    </Modal>
  )
}
