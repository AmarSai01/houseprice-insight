/**
 * Supported Bengaluru market-history areas.
 * Must stay aligned with backend SUPPORTED_AREAS / market CSV coverage.
 * Map x/y are decorative coordinates for Home Location Intelligence only.
 */
export const MARKET_AREAS = [
  { id: "Devanahalli", label: "Devanahalli", x: 58, y: 16 },
  { id: "Indiranagar", label: "Indiranagar", x: 48, y: 50 },
  { id: "Whitefield", label: "Whitefield", x: 76, y: 44 },
  { id: "Yelahanka", label: "Yelahanka", x: 42, y: 24 },
];

export const MARKET_AREA_IDS = MARKET_AREAS.map((area) => area.id);

export const DEFAULT_MARKET_AREA_ID = "Whitefield";

export const getMarketAreaById = (id) =>
  MARKET_AREAS.find((area) => area.id === id) || null;
