// Instamart quick-commerce catalog. Snacks and desserts in the plan come
// from here (fast ETA); the backend's mock catalog does the same split.

const p = (id, name, qty, price, mrp, veg, category, emoji, opts = {}) => ({
  id,
  name,
  qty,
  price,
  mrp,
  veg,
  category,
  emoji,
  slot: opts.slot || null, // which course the planner may use it for
  tags: opts.tags || [],
  etaMin: 15,
})

export const instamartCategories = [
  { id: 'chips', label: 'Chips & Namkeen', emoji: '🥔' },
  { id: 'nuts', label: 'Dry Fruits & Nuts', emoji: '🥜' },
  { id: 'ready', label: 'Ready to Heat', emoji: '🍢' },
  { id: 'drinks', label: 'Cold Drinks & Juices', emoji: '🥤' },
  { id: 'icecream', label: 'Ice Creams', emoji: '🍨' },
  { id: 'sweets', label: 'Indian Sweets', emoji: '🍮' },
  { id: 'dairy', label: 'Dairy & Bread', emoji: '🥛' },
  { id: 'fruits', label: 'Fresh Fruits', emoji: '🍎' },
]

export const products = [
  p('im1', 'Salted Potato Chips', 'Family pack · 165 g', 99, 120, true, 'chips', '🥔', { slot: 'snacks', tags: ['crisps'] }),
  p('im2', 'Cream & Onion Chips', '150 g', 89, 110, true, 'chips', '🧅', { slot: 'snacks', tags: ['crisps'] }),
  p('im3', 'Nachos with Salsa Dip Combo', '300 g', 249, 299, true, 'chips', '🌮', { slot: 'snacks', tags: ['crisps'] }),
  p('im4', 'Masala Peanuts', '400 g', 149, 180, true, 'nuts', '🥜', { slot: 'snacks', tags: ['nuts', 'spicy'] }),
  p('im5', 'Roasted Cashews', '250 g', 329, 380, true, 'nuts', '🌰', { slot: 'snacks', tags: ['nuts'] }),
  p('im6', 'Trail Mix Jar', '350 g', 289, 340, true, 'nuts', '🥨', { slot: 'snacks', tags: ['nuts'] }),
  p('im7', 'Paneer Tikka (ready to heat)', '8 pcs · 250 g', 279, 320, true, 'ready', '🧀', { slot: 'snacks', tags: ['spicy'] }),
  p('im8', 'Chicken Cocktail Samosa', '10 pcs · 300 g', 299, 340, false, 'ready', '🥟', { slot: 'snacks', tags: ['spicy'] }),
  p('im9', 'Veg Spring Rolls', '8 pcs · 280 g', 229, 260, true, 'ready', '🌯', { slot: 'snacks', tags: [] }),
  p('im10', 'Cheese Cubes Platter Pack', '200 g', 389, 420, true, 'dairy', '🧀', { slot: 'snacks', tags: [] }),
  p('im11', 'Cola (6 × 300 ml)', '6 pack', 210, 240, true, 'drinks', '🥤', { slot: 'snacks', tags: ['drinks'] }),
  p('im12', 'Mango Juice (1 L)', '1 L', 130, 150, true, 'drinks', '🥭', { slot: 'snacks', tags: ['drinks'] }),
  p('im13', 'Sparkling Lemonade (4 × 250 ml)', '4 pack', 180, 220, true, 'drinks', '🍋', { slot: 'snacks', tags: ['drinks'] }),
  p('im14', 'Vanilla Ice Cream Tub', '700 ml', 289, 350, true, 'icecream', '🍦', { slot: 'dessert', tags: [] }),
  p('im15', 'Belgian Chocolate Ice Cream', '500 ml', 319, 375, true, 'icecream', '🍫', { slot: 'dessert', tags: [] }),
  p('im16', 'Kulfi Sticks (Pack of 4)', '4 × 60 ml', 199, 240, true, 'icecream', '🍡', { slot: 'dessert', tags: [] }),
  p('im17', 'Gulab Jamun Tin', '1 kg · 20 pcs', 229, 275, true, 'sweets', '🍩', { slot: 'dessert', tags: [] }),
  p('im18', 'Rasmalai Cup (4 pcs)', '480 g', 249, 290, true, 'sweets', '🥛', { slot: 'dessert', tags: [] }),
  p('im19', 'Soan Papdi Box', '500 g', 179, 210, true, 'sweets', '🟨', { slot: 'dessert', tags: [] }),
  p('im20', 'Chocolate Brownie Box (6 pcs)', '360 g', 349, 420, true, 'sweets', '🍫', { slot: 'dessert', tags: [] }),
  p('im21', 'Farm Fresh Milk', '1 L', 68, 72, true, 'dairy', '🥛', { tags: [] }),
  p('im22', 'Multigrain Bread', '400 g', 55, 65, true, 'dairy', '🍞', { tags: [] }),
  p('im23', 'Salted Butter', '100 g', 62, 70, true, 'dairy', '🧈', { tags: [] }),
  p('im24', 'Robusta Bananas', '6 pcs', 48, 60, true, 'fruits', '🍌', { tags: [] }),
  p('im25', 'Washington Apples', '4 pcs · ~600 g', 149, 190, true, 'fruits', '🍎', { tags: [] }),
  p('im26', 'Pomegranate', '2 pcs · ~500 g', 129, 160, true, 'fruits', '🍎', { tags: [] }),
  p('im27', 'Hummus & Pita Chips Combo', '250 g', 269, 310, true, 'ready', '🥙', { slot: 'snacks', tags: [] }),
  p('im28', 'Cheese Popcorn Tub', '120 g', 119, 140, true, 'chips', '🍿', { slot: 'snacks', tags: ['crisps'] }),
]

export const getProduct = (id) => products.find((x) => x.id === id)

export const productsByCategory = (catId) =>
  products.filter((x) => x.category === catId)

export const snackPool = products.filter((x) => x.slot === 'snacks')
export const dessertPool = products.filter((x) => x.slot === 'dessert')
