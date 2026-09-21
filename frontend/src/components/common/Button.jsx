import { forwardRef } from 'react'
import { Link } from 'react-router-dom'

// One button, five voices. `to` renders a router Link, `href` an anchor,
// otherwise a real <button>. Variants: primary | secondary | ghost |
// dark | danger. Sizes: sm | md | lg.
export const Button = forwardRef(function Button(
  { variant = 'primary', size = 'md', to, href, icon: Icon, children, className = '', block = false, ...rest },
  ref,
) {
  const cls = [
    'btn',
    `btn--${variant}`,
    `btn--${size}`,
    block ? 'btn--block' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ')

  const content = (
    <>
      {Icon && <Icon size={size === 'sm' ? 15 : 17} aria-hidden="true" />}
      {children}
    </>
  )

  if (to) {
    return (
      <Link ref={ref} to={to} className={cls} {...rest}>
        {content}
      </Link>
    )
  }
  if (href) {
    return (
      <a ref={ref} href={href} className={cls} {...rest}>
        {content}
      </a>
    )
  }
  return (
    <button ref={ref} type="button" className={cls} {...rest}>
      {content}
    </button>
  )
})
