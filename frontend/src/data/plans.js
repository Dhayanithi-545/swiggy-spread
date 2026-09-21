// Past plans — what the "My plans" page shows before the user makes any.
// Shapes match utils/planner.js buildPlan() output so PlanDetail renders
// both seeded history and freshly generated plans identically.

export const seedPlans = [
  {
    id: 'plan-seed-1',
    createdAt: 'Sat, 14 Sep · 6:41 PM',
    request: '6 friends Saturday 8pm, budget 3000, 2 are vegetarian',
    status: 'carts-filled',
    guests: 6,
    budget: 3000,
    total: 2760,
    leftover: 240,
    assumptions: [],
    notes: [
      'Dinner from Vasantha Aavaram — best of 4 candidates checked (real mains, role variety, 4.5★).',
      'Held ₹3,000 across 3 carts. ₹240 left unspent — honest beats absurd.',
    ],
    courses: [
      {
        slot: 'snacks',
        platform: 'instamart',
        vendorName: 'Instamart',
        eatAt: 1140, // 7:00 PM in minutes
        orderAt: 1110,
        etaMin: 15,
        bufferMin: 15,
        subtotal: 640,
        items: [
          { id: 'im10', name: 'Cheese Cubes Platter Pack', price: 389, qty: 1, veg: true, emoji: '🧀' },
          { id: 'im1', name: 'Salted Potato Chips', price: 99, qty: 1, veg: true, emoji: '🥔' },
          { id: 'im4', name: 'Masala Peanuts', price: 149, qty: 1, veg: true, emoji: '🥜' },
        ],
      },
      {
        slot: 'dinner',
        platform: 'food',
        vendorName: 'Vasantha Aavaram',
        vendorId: 'r1',
        eatAt: 1200,
        orderAt: 1142,
        etaMin: 38,
        bufferMin: 20,
        subtotal: 1590,
        items: [
          { id: 'r1-2', name: 'Paneer Butter Masala', price: 320, qty: 2, veg: true, emoji: '🧀' },
          { id: 'r1-5', name: 'Chicken Biryani (serves 2)', price: 480, qty: 1, veg: false, emoji: '🍛' },
          { id: 'r1-4', name: 'Veg Biryani (serves 2)', price: 380, qty: 1, veg: true, emoji: '🍚' },
          { id: 'r1-7', name: 'Malabar Parotta (2 pcs)', price: 90, qty: 1, veg: true, emoji: '🫓' },
        ],
      },
      {
        slot: 'dessert',
        platform: 'instamart',
        vendorName: 'Instamart',
        eatAt: 1260,
        orderAt: 1230,
        etaMin: 15,
        bufferMin: 15,
        subtotal: 530,
        items: [
          { id: 'im14', name: 'Vanilla Ice Cream Tub', price: 289, qty: 1, veg: true, emoji: '🍦' },
          { id: 'im18', name: 'Rasmalai Cup (4 pcs)', price: 249, qty: 1, veg: true, emoji: '🥛' },
        ],
      },
    ],
  },
  {
    id: 'plan-seed-2',
    createdAt: 'Wed, 11 Sep · 7:58 PM',
    request: 'order dinner for 4 tonight, budget 1200',
    status: 'completed',
    guests: 4,
    budget: 1200,
    total: 1130,
    leftover: 70,
    assumptions: ['assumed 8:00 PM on the table'],
    notes: ['Dinner only — you asked for dinner, you got dinner.'],
    courses: [
      {
        slot: 'dinner',
        platform: 'food',
        vendorName: 'Tandoor Trails',
        vendorId: 'r4',
        eatAt: 1200,
        orderAt: 1142,
        etaMin: 38,
        bufferMin: 20,
        subtotal: 1130,
        items: [
          { id: 'r4-3', name: 'Dal Makhani', price: 290, qty: 1, veg: true, emoji: '🥘' },
          { id: 'r4-1', name: 'Butter Chicken', price: 420, qty: 1, veg: false, emoji: '🍗' },
          { id: 'r4-4', name: 'Jeera Rice', price: 220, qty: 1, veg: true, emoji: '🍚' },
          { id: 'r4-6', name: 'Butter Naan (2 pcs)', price: 100, qty: 2, veg: true, emoji: '🫓' },
        ],
      },
    ],
  },
  {
    id: 'plan-seed-3',
    createdAt: 'Sun, 8 Sep · 4:12 PM',
    request: 'need a cake and ice cream for 8, around 600',
    status: 'draft',
    guests: 8,
    budget: 600,
    total: 548,
    leftover: 52,
    assumptions: ['assumed 8:00 PM on the table'],
    notes: ['Dessert only.'],
    courses: [
      {
        slot: 'dessert',
        platform: 'instamart',
        vendorName: 'Instamart',
        eatAt: 1200,
        orderAt: 1170,
        etaMin: 15,
        bufferMin: 15,
        subtotal: 548,
        items: [
          { id: 'im20', name: 'Chocolate Brownie Box (6 pcs)', price: 349, qty: 1, veg: true, emoji: '🍫' },
          { id: 'im16', name: 'Kulfi Sticks (Pack of 4)', price: 199, qty: 1, veg: true, emoji: '🍡' },
        ],
      },
    ],
  },
]

export const planStatusMeta = {
  'carts-filled': { label: 'Carts filled', tone: 'green' },
  completed: { label: 'Completed', tone: 'neutral' },
  draft: { label: 'Draft', tone: 'amber' },
}
