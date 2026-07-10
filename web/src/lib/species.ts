// Presentation metadata for the biodiversity views. The backend stores only the
// scientific name / IUCN status / endemic flag, so common names, taxon groups and
// short blurbs live here (the sample dataset is a fixed set of Malagasy endemics;
// unknown taxa fall back to a genus-keyword heuristic).

export interface SpeciesMeta {
  common: string;
  group: string;
  blurb: string;
  /** Flat tile colours used when no photo is available: soft background + icon colour. */
  tile: { bg: string; fg: string };
}

const TILE = {
  forest: { bg: "#e3efe5", fg: "#2e7d32" },
  dry: { bg: "#f1eadb", fg: "#8d6e2f" },
  reptile: { bg: "#ddefed", fg: "#0f766e" },
  plant: { bg: "#e7f1df", fg: "#558b2f" },
  night: { bg: "#e9e8f4", fg: "#5b52a8" },
};

const CATALOG: Record<string, SpeciesMeta> = {
  "Indri indri": { common: "Indri", group: "Lemur", blurb: "Largest living lemur; its song carries for kilometres through eastern rainforest.", tile: TILE.forest },
  "Lemur catta": { common: "Ring-tailed lemur", group: "Lemur", blurb: "Iconic striped-tail lemur of the south; highly social troops.", tile: TILE.dry },
  "Propithecus diadema": { common: "Diademed sifaka", group: "Lemur", blurb: "Vividly coloured sifaka that leaps between rainforest trunks.", tile: TILE.forest },
  "Daubentonia madagascariensis": { common: "Aye-aye", group: "Lemur", blurb: "Nocturnal lemur that taps wood to find grubs with an elongated finger.", tile: TILE.night },
  "Microcebus murinus": { common: "Grey mouse lemur", group: "Lemur", blurb: "One of the world's smallest primates; fits in a human palm.", tile: TILE.night },
  "Furcifer pardalis": { common: "Panther chameleon", group: "Reptile", blurb: "Brilliantly colour-shifting chameleon of the north and east.", tile: TILE.reptile },
  "Uroplatus phantasticus": { common: "Satanic leaf-tailed gecko", group: "Reptile", blurb: "Master of camouflage that mimics a dead leaf, veins and all.", tile: TILE.reptile },
  "Brookesia micra": { common: "Micro chameleon", group: "Reptile", blurb: "Among the tiniest reptiles on Earth — adults span a fingertip.", tile: TILE.reptile },
  "Adansonia grandidieri": { common: "Grandidier's baobab", group: "Tree", blurb: "The grandest Malagasy baobab, lining the famous Avenue in Menabe.", tile: TILE.dry },
  "Ravenala madagascariensis": { common: "Traveller's palm", group: "Plant", blurb: "Fan-shaped national emblem of Madagascar.", tile: TILE.plant },
};

const FALLBACKS: { test: RegExp; meta: SpeciesMeta }[] = [
  { test: /lemur|cebus|propithecus|indri|daubentonia|eulemur|hapalemur/i, meta: { common: "Lemur", group: "Lemur", blurb: "Endemic Malagasy primate.", tile: TILE.forest } },
  { test: /furcifer|brookesia|chamaeleo|calumma/i, meta: { common: "Chameleon", group: "Reptile", blurb: "Colour-changing endemic reptile.", tile: TILE.reptile } },
  { test: /uroplatus|phelsuma|gecko/i, meta: { common: "Gecko", group: "Reptile", blurb: "Endemic gecko.", tile: TILE.reptile } },
  { test: /adansonia|baobab/i, meta: { common: "Baobab", group: "Tree", blurb: "Iconic Malagasy tree.", tile: TILE.dry } },
  { test: /ravenala|palm|arecaceae/i, meta: { common: "Palm", group: "Plant", blurb: "Endemic plant.", tile: TILE.plant } },
];

export function speciesMeta(scientificName: string): SpeciesMeta {
  if (CATALOG[scientificName]) return CATALOG[scientificName];
  for (const f of FALLBACKS) if (f.test.test(scientificName)) return f.meta;
  return { common: "Endemic species", group: "Other", blurb: "Recorded in Madagascar.", tile: TILE.plant };
}

// IUCN status → readable label + severity order (for sorting/coloring).
export const IUCN_LABEL: Record<string, string> = {
  CR: "Critically endangered", EN: "Endangered", VU: "Vulnerable",
  NT: "Near threatened", LC: "Least concern", DD: "Data deficient", NA: "Not assessed",
};
export const IUCN_ORDER = ["CR", "EN", "VU", "NT", "LC", "DD", "NA"];
export const IUCN_COLOR: Record<string, string> = {
  CR: "#c62828", EN: "#ef6c00", VU: "#f59e0b", NT: "#9e9d24", LC: "#2e7d32", DD: "#78909c", NA: "#78909c",
};
export const statusKey = (s: string | null | undefined) => (s && IUCN_LABEL[s] ? s : "NA");

// Shared categorical palette for charts (cohesive with the brand).
export const CHART = {
  green: "#2e7d32",
  greenLight: "#7cb342",
  amber: "#ef6c00",
  water: "#0284c7",
  teal: "#0f9d92",
  violet: "#6d5bd0",
  grid: "#e5ede7",
  gbif: "#2e7d32",
  inaturalist: "#0284c7",
  upload: "#6d5bd0",
};

// Best-effort real photo from the iNaturalist taxa API (auth-free, CORS-open).
// Cached per name; resolves to null when offline or no match (UI falls back to
// the taxon icon tile so it always looks intentional).
const photoCache = new Map<string, Promise<string | null>>();
export function speciesPhotoUrl(scientificName: string): Promise<string | null> {
  const cached = photoCache.get(scientificName);
  if (cached) return cached;
  const p = (async () => {
    try {
      const res = await fetch(
        `https://api.inaturalist.org/v1/taxa?q=${encodeURIComponent(scientificName)}&per_page=1&rank=species`,
        { headers: { Accept: "application/json" } }
      );
      if (!res.ok) return null;
      const data = await res.json();
      const photo = data?.results?.[0]?.default_photo;
      const url: string | undefined = photo?.medium_url || photo?.square_url;
      return url ? url.replace("square", "medium") : null;
    } catch {
      return null;
    }
  })();
  photoCache.set(scientificName, p);
  return p;
}
