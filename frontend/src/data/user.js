// Profile mock data — the shape a logged-in Swiggy Builders Club user
// would have. Static; no auth calls in the frontend.

export const user = {
  name: 'Pratik Ganer',
  phone: '+91 98•••• ••42',
  email: 'pratik@example.com',
  memberSince: 'March 2025',
}

export const addresses = [
  {
    id: 'a1',
    label: 'Home',
    line: '14, 2nd Cross Street, Sakthi Nagar',
    area: 'Pallavaram, Chennai',
    pincode: '600043',
    isDefault: true,
  },
  {
    id: 'a2',
    label: 'Work',
    line: 'Block C, Olympia Tech Park',
    area: 'Guindy, Chennai',
    pincode: '600032',
    isDefault: false,
  },
]

export const defaultPreferences = {
  vegOnly: false,
  avoidSpice: false,
  defaultGuests: 4,
  defaultBudgetPerHead: 250,
}
