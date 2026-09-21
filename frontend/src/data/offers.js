// Coupons. Grounded in what the backend actually saw live:
//  - Food coupons are LISTED read-only (fetch_food_coupons); applying is
//    left to the human in the Swiggy app.
//  - Agent traffic only sees COD-compatible coupons.
//  - The real Instamart server exposes NO coupon tools, whatever the docs say.

export const foodCoupons = [
  {
    id: 'o1',
    code: 'SPREAD50',
    title: '50% OFF up to ₹100',
    description: 'On your first order from any restaurant this week.',
    minOrder: 199,
    platform: 'food',
    codOnly: true,
    expiresIn: '3 days',
  },
  {
    id: 'o2',
    code: 'PARTY125',
    title: 'Flat ₹125 OFF',
    description: 'On orders above ₹499 — made for group orders.',
    minOrder: 499,
    platform: 'food',
    codOnly: true,
    expiresIn: '6 days',
  },
  {
    id: 'o3',
    code: 'WEEKEND30',
    title: '30% OFF up to ₹150',
    description: 'Friday to Sunday, on dinner-time orders after 7 PM.',
    minOrder: 349,
    platform: 'food',
    codOnly: false,
    expiresIn: '2 days',
  },
  {
    id: 'o4',
    code: 'SWEETTOOTH',
    title: '15% OFF on desserts',
    description: 'Any dessert-first restaurant. Because the evening ends sweet.',
    minOrder: 249,
    platform: 'food',
    codOnly: true,
    expiresIn: '9 days',
  },
  {
    id: 'o5',
    code: 'FEAST200',
    title: 'Flat ₹200 OFF',
    description: 'On orders above ₹999. Big table energy.',
    minOrder: 999,
    platform: 'food',
    codOnly: false,
    expiresIn: '12 days',
  },
]
