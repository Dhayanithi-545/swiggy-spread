import { Link } from 'react-router-dom'
import { FoodImage } from '../common/FoodImage.jsx'

export function CategoryCard({ category }) {
  return (
    <Link
      to={`/search?q=${encodeURIComponent(category.query)}`}
      className="catcard"
      aria-label={`Browse ${category.label}`}
    >
      <FoodImage emoji={category.emoji} gradient={category.gradient} name={category.label} ratio="square" className="catcard__img" />
      <span className="catcard__label">{category.label}</span>
    </Link>
  )
}
