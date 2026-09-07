export const MOCK_REPORTS = [
  {
    id: "REP-2026-08-001",
    date: "2026-08-28T09:15:00Z",
    productName: "Premium Basmati Rice 5kg",
    status: "pass",
    officer: "Inspector Sharma",
    location: "Supermarket A, Sector 42",
    image: "https://images.unsplash.com/photo-1586201375761-83865001e8ac?auto=format&fit=crop&q=80&w=800",
    declarations: {
      mrp: { present: true, value: "₹ 450.00" },
      netQuantity: { present: true, value: "5 kg" },
      mfgDate: { present: true, value: "07/2026" },
      address: { present: true, value: "Agro Foods Ltd, Delhi" },
      consumerCare: { present: true, value: "1800-111-222" },
    },
    violations: [],
  },
  {
    id: "REP-2026-08-002",
    date: "2026-08-27T14:30:00Z",
    productName: "Organic Honey 500g",
    status: "fail",
    officer: "Inspector Sharma",
    location: "Organic Store, Market Road",
    image: "https://images.unsplash.com/photo-1587049352847-4d4b126a71d5?auto=format&fit=crop&q=80&w=800",
    declarations: {
      mrp: { present: true, value: "₹ 299.00" },
      netQuantity: { present: false, value: null },
      mfgDate: { present: true, value: "06/2026" },
      address: { present: true, value: "Nature Farm, Punjab" },
      consumerCare: { present: false, value: null },
    },
    violations: [
      "Missing Net Quantity declaration",
      "Missing Consumer Care details",
    ],
  },
  {
    id: "REP-2026-08-003",
    date: "2026-08-26T11:45:00Z",
    productName: "Refined Sunflower Oil 1L",
    status: "review",
    officer: "Inspector Verma",
    location: "Daily Needs Grocers",
    image: "https://images.unsplash.com/photo-1620706857370-e1b9770e8bb1?auto=format&fit=crop&q=80&w=800",
    declarations: {
      mrp: { present: true, value: "₹ 150.00" },
      netQuantity: { present: true, value: "1 L" },
      mfgDate: { present: true, value: "08/2026" },
      address: { present: true, value: "Oil Mills, Gujarat" },
      consumerCare: { present: true, value: "care@oilmills.com" },
    },
    violations: [
      "Font size of MRP appears smaller than prescribed limits.",
    ],
  },
];

export const MOCK_DASHBOARD_STATS = {
  totalInspections: 142,
  compliant: 110,
  nonCompliant: 24,
  manualReview: 8,
};

export const MOCK_BOUNDING_BOXES = [
  { x: 10, y: 15, width: 25, height: 8, label: "MRP" },
  { x: 10, y: 25, width: 30, height: 8, label: "Net Qty" },
  { x: 60, y: 15, width: 35, height: 15, label: "Address" },
];
