// Per-restaurant menus. Field names follow the backend's MenuItem
// (name, price, veg) plus UI extras. `role` mirrors portions.role_of():
// main | staple | bread | side | dessert | drink — the planner uses it
// to compose a real spread instead of 3× one dish.

const d = (id, name, price, veg, category, role, opts = {}) => ({
  id,
  name,
  price,
  veg,
  category,
  role,
  spicy: opts.spicy || false,
  bestseller: opts.best || false,
  rating: opts.rating || null,
  votes: opts.votes || null,
  description: opts.desc || '',
  emoji: opts.emoji || null,
})

export const menus = {
  r1: [
    d('r1-1', 'Chettinad Chicken Curry', 340, false, 'Mains', 'main', { spicy: true, best: true, rating: 4.6, votes: 812, desc: 'Slow-cooked in freshly ground Chettinad masala with curry leaves.', emoji: '🍗' }),
    d('r1-2', 'Paneer Butter Masala', 320, true, 'Mains', 'main', { best: true, rating: 4.5, votes: 640, desc: 'Cottage cheese in a silky tomato-cashew gravy.', emoji: '🧀' }),
    d('r1-3', 'Kara Kuzhambu', 260, true, 'Mains', 'main', { spicy: true, rating: 4.3, votes: 210, desc: 'Tangy tamarind gravy with shallots and brinjal.', emoji: '🥘' }),
    d('r1-4', 'Veg Biryani (serves 2)', 380, true, 'Rice', 'staple', { rating: 4.2, votes: 388, desc: 'Seeraga samba rice layered with garden vegetables.', emoji: '🍚' }),
    d('r1-5', 'Chicken Biryani (serves 2)', 480, false, 'Rice', 'staple', { spicy: true, best: true, rating: 4.7, votes: 1204, desc: 'Dindigul-style, with a boiled egg and dalcha.', emoji: '🍛' }),
    d('r1-6', 'Curd Rice (serves 2)', 180, true, 'Rice', 'staple', { rating: 4.4, votes: 156, desc: 'Cooling curd rice with pomegranate and curry-leaf tempering.', emoji: '🍶' }),
    d('r1-7', 'Malabar Parotta (2 pcs)', 90, true, 'Breads', 'bread', { best: true, rating: 4.6, votes: 930, desc: 'Flaky, layered, made to order.', emoji: '🫓' }),
    d('r1-8', 'Butter Naan (2 pcs)', 110, true, 'Breads', 'bread', { rating: 4.3, votes: 245, emoji: '🫓' }),
    d('r1-9', 'Gobi 65', 220, true, 'Starters', 'side', { spicy: true, rating: 4.1, votes: 310, desc: 'Crisp-fried cauliflower tossed with ginger and green chilli.', emoji: '🥦' }),
    d('r1-10', 'Chicken 65', 280, false, 'Starters', 'side', { spicy: true, best: true, rating: 4.5, votes: 720, emoji: '🍗' }),
    d('r1-11', 'Elaneer Payasam', 160, true, 'Desserts', 'dessert', { rating: 4.6, votes: 140, desc: 'Tender coconut kheer, served chilled.', emoji: '🥥' }),
    d('r1-12', 'Rose Milk', 90, true, 'Beverages', 'drink', { rating: 4.2, votes: 95, emoji: '🥤' }),
  ],
  r2: [
    d('r2-1', 'Dindigul Chicken Biryani (serves 2)', 520, false, 'Biryani', 'staple', { spicy: true, best: true, rating: 4.7, votes: 2410, desc: 'The house classic — seeraga samba, cube-cut chicken.', emoji: '🍛' }),
    d('r2-2', 'Mutton Biryani (serves 2)', 640, false, 'Biryani', 'staple', { spicy: true, rating: 4.6, votes: 1130, emoji: '🍖' }),
    d('r2-3', 'Mushroom Biryani (serves 2)', 420, true, 'Biryani', 'staple', { rating: 4.3, votes: 460, desc: 'Button mushrooms, mint, and a whole lot of ghee.', emoji: '🍄' }),
    d('r2-4', 'Andhra Chicken Curry', 360, false, 'Mains', 'main', { spicy: true, rating: 4.4, votes: 520, emoji: '🍲' }),
    d('r2-5', 'Gongura Paneer', 330, true, 'Mains', 'main', { spicy: true, rating: 4.2, votes: 180, desc: 'Paneer in tangy sorrel-leaf gravy.', emoji: '🧀' }),
    d('r2-6', 'Bagara Rice', 240, true, 'Rice', 'staple', { rating: 4.1, votes: 120, emoji: '🍚' }),
    d('r2-7', 'Chicken Fry (boneless)', 310, false, 'Starters', 'side', { spicy: true, best: true, rating: 4.5, votes: 840, emoji: '🍗' }),
    d('r2-8', 'Raita & Brinjal Combo', 90, true, 'Sides', 'side', { rating: 4.0, votes: 88, emoji: '🥗' }),
    d('r2-9', 'Double ka Meetha', 180, true, 'Desserts', 'dessert', { rating: 4.4, votes: 210, desc: 'Hyderabadi bread pudding with saffron.', emoji: '🍮' }),
  ],
  r3: [
    d('r3-1', 'South Indian Full Meals', 220, true, 'Thali', 'main', { best: true, rating: 4.5, votes: 980, desc: 'Sambar, rasam, poriyal, kootu, curd, pickle, papad, payasam.', emoji: '🍱' }),
    d('r3-2', 'Sambar Rice', 150, true, 'Rice', 'staple', { rating: 4.3, votes: 340, emoji: '🍚' }),
    d('r3-3', 'Lemon Rice', 130, true, 'Rice', 'staple', { rating: 4.2, votes: 190, emoji: '🍋' }),
    d('r3-4', 'Kootu Curry', 170, true, 'Mains', 'main', { rating: 4.1, votes: 110, desc: 'Lentils and vegetables in a mild coconut gravy.', emoji: '🥘' }),
    d('r3-5', 'Avial', 180, true, 'Mains', 'main', { rating: 4.4, votes: 150, desc: 'Kerala-style mixed vegetables in coconut and curd.', emoji: '🥗' }),
    d('r3-6', 'Chapati (3 pcs) with Kurma', 160, true, 'Breads', 'bread', { rating: 4.2, votes: 260, emoji: '🫓' }),
    d('r3-7', 'Medu Vada (2 pcs)', 80, true, 'Starters', 'side', { best: true, rating: 4.6, votes: 540, emoji: '🍩' }),
    d('r3-8', 'Sweet Pongal', 120, true, 'Desserts', 'dessert', { rating: 4.5, votes: 175, emoji: '🍯' }),
    d('r3-9', 'Filter Coffee', 60, true, 'Beverages', 'drink', { best: true, rating: 4.8, votes: 700, emoji: '☕' }),
  ],
}

menus.r4 = [
  d('r4-1', 'Butter Chicken', 420, false, 'Mains', 'main', { best: true, rating: 4.5, votes: 1320, desc: 'Char-grilled chicken folded into a buttery tomato gravy.', emoji: '🍗' }),
  d('r4-2', 'Paneer Tikka Masala', 380, true, 'Mains', 'main', { rating: 4.4, votes: 610, emoji: '🧀' }),
  d('r4-3', 'Dal Makhani', 290, true, 'Mains', 'main', { best: true, rating: 4.6, votes: 890, desc: 'Black lentils simmered overnight on the tandoor coals.', emoji: '🥘' }),
  d('r4-4', 'Jeera Rice', 220, true, 'Rice', 'staple', { rating: 4.2, votes: 230, emoji: '🍚' }),
  d('r4-5', 'Hyderabadi Veg Biryani (serves 2)', 400, true, 'Rice', 'staple', { rating: 4.1, votes: 340, emoji: '🍛' }),
  d('r4-6', 'Butter Naan (2 pcs)', 100, true, 'Breads', 'bread', { best: true, rating: 4.5, votes: 1100, emoji: '🫓' }),
  d('r4-7', 'Garlic Naan (2 pcs)', 120, true, 'Breads', 'bread', { rating: 4.4, votes: 480, emoji: '🧄' }),
  d('r4-8', 'Tandoori Platter (half)', 460, false, 'Starters', 'side', { spicy: true, rating: 4.3, votes: 350, emoji: '🍢' }),
  d('r4-9', 'Paneer Malai Tikka', 340, true, 'Starters', 'side', { rating: 4.4, votes: 280, emoji: '🧀' }),
  d('r4-10', 'Gulab Jamun (2 pcs)', 120, true, 'Desserts', 'dessert', { rating: 4.5, votes: 320, emoji: '🍩' }),
]

menus.r5 = [
  d('r5-1', 'Kothu Parotta (chicken)', 240, false, 'Mains', 'main', { spicy: true, best: true, rating: 4.4, votes: 760, desc: 'Chopped parotta stir-fried with chicken, egg and salna.', emoji: '🥡' }),
  d('r5-2', 'Kothu Parotta (veg)', 190, true, 'Mains', 'main', { spicy: true, rating: 4.2, votes: 300, emoji: '🥡' }),
  d('r5-3', 'Chilli Parotta', 180, true, 'Mains', 'main', { spicy: true, rating: 4.1, votes: 240, emoji: '🌶️' }),
  d('r5-4', 'Malabar Parotta (2 pcs) + Salna', 110, true, 'Breads', 'bread', { best: true, rating: 4.5, votes: 980, emoji: '🫓' }),
  d('r5-5', 'Egg Parotta', 160, false, 'Mains', 'main', { rating: 4.3, votes: 410, emoji: '🍳' }),
  d('r5-6', 'Chicken Salna (gravy only)', 140, false, 'Sides', 'side', { spicy: true, rating: 4.2, votes: 190, emoji: '🍲' }),
  d('r5-7', 'Bread Halwa', 110, true, 'Desserts', 'dessert', { best: true, rating: 4.6, votes: 350, emoji: '🍞' }),
]

menus.r6 = [
  d('r6-1', 'Margherita (medium)', 320, true, 'Pizzas', 'main', { rating: 4.3, votes: 850, desc: 'House marinara, fresh mozzarella, basil.', emoji: '🍕' }),
  d('r6-2', 'Farmhouse Feast (medium)', 440, true, 'Pizzas', 'main', { best: true, rating: 4.4, votes: 620, emoji: '🍕' }),
  d('r6-3', 'Peri Peri Chicken (medium)', 520, false, 'Pizzas', 'main', { spicy: true, best: true, rating: 4.5, votes: 940, emoji: '🍕' }),
  d('r6-4', 'BBQ Paneer (medium)', 460, true, 'Pizzas', 'main', { rating: 4.2, votes: 380, emoji: '🍕' }),
  d('r6-5', 'Garlic Breadsticks', 160, true, 'Sides', 'side', { best: true, rating: 4.4, votes: 1100, emoji: '🥖' }),
  d('r6-6', 'Cheesy Dip Duo', 90, true, 'Sides', 'side', { rating: 4.1, votes: 260, emoji: '🧀' }),
  d('r6-7', 'Choco Lava Cake', 130, true, 'Desserts', 'dessert', { best: true, rating: 4.6, votes: 890, emoji: '🍫' }),
  d('r6-8', 'Cold Coffee (400ml)', 150, true, 'Beverages', 'drink', { rating: 4.0, votes: 170, emoji: '🥤' }),
]

menus.r7 = [
  d('r7-1', 'Veg Hakka Noodles', 240, true, 'Noodles', 'staple', { rating: 4.1, votes: 420, emoji: '🍜' }),
  d('r7-2', 'Chicken Schezwan Noodles', 290, false, 'Noodles', 'staple', { spicy: true, best: true, rating: 4.4, votes: 680, emoji: '🍜' }),
  d('r7-3', 'Veg Fried Rice', 230, true, 'Rice', 'staple', { rating: 4.0, votes: 310, emoji: '🍚' }),
  d('r7-4', 'Chilli Chicken (dry)', 320, false, 'Starters', 'side', { spicy: true, best: true, rating: 4.5, votes: 900, emoji: '🌶️' }),
  d('r7-5', 'Gobi Manchurian', 250, true, 'Starters', 'side', { rating: 4.2, votes: 520, emoji: '🥦' }),
  d('r7-6', 'Paneer in Hot Garlic Sauce', 310, true, 'Mains', 'main', { spicy: true, rating: 4.1, votes: 220, emoji: '🧄' }),
  d('r7-7', 'Sweet Corn Soup', 160, true, 'Soups', 'side', { rating: 4.0, votes: 150, desc: 'A side, not a meal — the planner knows.', emoji: '🥣' }),
  d('r7-8', 'Darsaan with Ice Cream', 190, true, 'Desserts', 'dessert', { rating: 4.3, votes: 130, emoji: '🍯' }),
]

menus.r8 = [
  d('r8-1', 'Ghee Roast Dosa', 140, true, 'Dosas', 'main', { best: true, rating: 4.7, votes: 1500, desc: 'Paper-crisp, roasted in A2 ghee.', emoji: '🥞' }),
  d('r8-2', 'Masala Dosa', 120, true, 'Dosas', 'main', { best: true, rating: 4.6, votes: 1900, emoji: '🥞' }),
  d('r8-3', 'Podi Idli (6 pcs)', 110, true, 'Tiffin', 'main', { rating: 4.5, votes: 640, emoji: '🍘' }),
  d('r8-4', 'Onion Uttapam', 130, true, 'Tiffin', 'main', { rating: 4.3, votes: 380, emoji: '🧅' }),
  d('r8-5', 'Mini Tiffin Combo', 190, true, 'Tiffin', 'main', { best: true, rating: 4.6, votes: 720, desc: 'Idli, vada, pongal, mini dosa, coffee.', emoji: '🍱' }),
  d('r8-6', 'Medu Vada (3 pcs)', 90, true, 'Sides', 'side', { rating: 4.4, votes: 410, emoji: '🍩' }),
  d('r8-7', 'Kesari Bath', 100, true, 'Desserts', 'dessert', { rating: 4.5, votes: 230, emoji: '🍮' }),
  d('r8-8', 'Filter Coffee (strong)', 70, true, 'Beverages', 'drink', { best: true, rating: 4.8, votes: 1100, emoji: '☕' }),
]

menus.r9 = [
  d('r9-1', 'Malai Kulfi Stick', 90, true, 'Kulfi', 'dessert', { best: true, rating: 4.7, votes: 620, emoji: '🍡' }),
  d('r9-2', 'Sitaphal Ice Cream (500ml)', 280, true, 'Tubs', 'dessert', { rating: 4.6, votes: 340, desc: 'Custard apple, real fruit pulp.', emoji: '🍨' }),
  d('r9-3', 'Belgian Chocolate Tub (500ml)', 320, true, 'Tubs', 'dessert', { best: true, rating: 4.7, votes: 780, emoji: '🍫' }),
  d('r9-4', 'Hot Brownie with Ice Cream', 210, true, 'Plated', 'dessert', { best: true, rating: 4.6, votes: 910, emoji: '🍰' }),
  d('r9-5', 'Rabri Falooda', 180, true, 'Plated', 'dessert', { rating: 4.4, votes: 260, emoji: '🥛' }),
  d('r9-6', 'Fresh Fruit Custard', 150, true, 'Plated', 'dessert', { rating: 4.2, votes: 140, emoji: '🍓' }),
]

menus.r10 = [
  d('r10-1', 'Chicken Shawarma Roll', 160, false, 'Shawarma', 'main', { best: true, rating: 4.4, votes: 1300, emoji: '🌯' }),
  d('r10-2', 'Shawarma Plate with Fries', 260, false, 'Shawarma', 'main', { rating: 4.3, votes: 520, emoji: '🍟' }),
  d('r10-3', 'Al Faham (quarter)', 290, false, 'Grill', 'main', { spicy: true, best: true, rating: 4.5, votes: 740, desc: 'Charcoal-grilled Arabian chicken with garlic mayo.', emoji: '🍗' }),
  d('r10-4', 'Kuboos (2 pcs)', 50, true, 'Breads', 'bread', { rating: 4.1, votes: 210, emoji: '🫓' }),
  d('r10-5', 'Hummus with Pita', 180, true, 'Sides', 'side', { rating: 4.2, votes: 160, emoji: '🥙' }),
  d('r10-6', 'Falafel Roll', 140, true, 'Shawarma', 'main', { rating: 4.0, votes: 190, emoji: '🧆' }),
  d('r10-7', 'Kunafa Slice', 220, true, 'Desserts', 'dessert', { best: true, rating: 4.6, votes: 380, emoji: '🍮' }),
]

menus.r11 = [
  d('r11-1', 'Gulab Jamun (6 pcs)', 180, true, 'Sweets', 'dessert', { best: true, rating: 4.6, votes: 540, emoji: '🍩' }),
  d('r11-2', 'Rasmalai (4 pcs)', 240, true, 'Sweets', 'dessert', { best: true, rating: 4.7, votes: 690, emoji: '🥛' }),
  d('r11-3', 'Mysore Pak (250g)', 210, true, 'Sweets', 'dessert', { rating: 4.5, votes: 310, desc: 'Ghee-heavy, melts before you chew.', emoji: '🟨' }),
  d('r11-4', 'Carrot Halwa (250g)', 190, true, 'Sweets', 'dessert', { rating: 4.4, votes: 220, emoji: '🥕' }),
  d('r11-5', 'Badam Kheer (500ml)', 220, true, 'Sweets', 'dessert', { rating: 4.3, votes: 130, emoji: '🥜' }),
  d('r11-6', 'Assorted Sweets Box (500g)', 380, true, 'Boxes', 'dessert', { best: true, rating: 4.5, votes: 260, emoji: '🎁' }),
]

menus.r12 = [
  d('r12-1', 'Classic Chicken Burger', 180, false, 'Burgers', 'main', { best: true, rating: 4.2, votes: 880, emoji: '🍔' }),
  d('r12-2', 'Crispy Paneer Burger', 160, true, 'Burgers', 'main', { rating: 4.1, votes: 420, emoji: '🍔' }),
  d('r12-3', 'Double Smash Burger', 260, false, 'Burgers', 'main', { best: true, rating: 4.4, votes: 610, emoji: '🍔' }),
  d('r12-4', 'Peri Peri Fries', 120, true, 'Sides', 'side', { spicy: true, rating: 4.3, votes: 730, emoji: '🍟' }),
  d('r12-5', 'Onion Rings', 110, true, 'Sides', 'side', { rating: 4.0, votes: 180, emoji: '🧅' }),
  d('r12-6', 'Oreo Thickshake', 170, true, 'Beverages', 'drink', { rating: 4.2, votes: 290, emoji: '🥤' }),
  d('r12-7', 'Brownie Sundae', 150, true, 'Desserts', 'dessert', { rating: 4.3, votes: 200, emoji: '🍫' }),
]

export const getMenu = (restaurantId) => menus[restaurantId] || []

export const menuCategories = (restaurantId) => [
  ...new Set(getMenu(restaurantId).map((i) => i.category)),
]

// Flat dish list across restaurants — the frontend twin of Swiggy's
// search_menu tool, which returns dishes across restaurants in one call.
export const allDishes = Object.entries(menus).flatMap(([rid, items]) =>
  items.map((i) => ({ ...i, restaurantId: rid })),
)
