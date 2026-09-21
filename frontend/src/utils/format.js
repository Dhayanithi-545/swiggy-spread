// Shared formatting helpers — money, time, counts.

export const inr = (n) => '₹' + Math.round(n).toLocaleString('en-IN')

export const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v))

// Minutes-from-midnight -> "7:02 PM". The planner works entirely in
// minutes so timing math stays integer and testable.
export function fmtTime(mins) {
  const m = ((Math.round(mins) % 1440) + 1440) % 1440
  let h = Math.floor(m / 60)
  const mm = String(m % 60).padStart(2, '0')
  const ap = h >= 12 ? 'PM' : 'AM'
  h = h % 12 || 12
  return `${h}:${mm} ${ap}`
}

export function plural(n, one, many) {
  return `${n} ${n === 1 ? one : many || one + 's'}`
}

export function etaLabel(mins) {
  return `${mins}–${mins + 5} mins`
}

// Stable tiny hash so the same name always gets the same gradient tile.
export function hashCode(str) {
  let h = 0
  for (let i = 0; i < str.length; i++) {
    h = (Math.imul(31, h) + str.charCodeAt(i)) | 0
  }
  return Math.abs(h)
}
