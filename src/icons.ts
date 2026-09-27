// Lucide icons (https://lucide.dev), inlined as SVG strings at build time.
import utensils from 'lucide-static/icons/utensils.svg?raw';
import martini from 'lucide-static/icons/martini.svg?raw';
import coffee from 'lucide-static/icons/coffee.svg?raw';
import bird from 'lucide-static/icons/bird.svg?raw';
import trees from 'lucide-static/icons/trees.svg?raw';
import landmark from 'lucide-static/icons/landmark.svg?raw';
import treePalm from 'lucide-static/icons/tree-palm.svg?raw';
import bed from 'lucide-static/icons/bed.svg?raw';
import library from 'lucide-static/icons/library.svg?raw';
import telescope from 'lucide-static/icons/telescope.svg?raw';
import car from 'lucide-static/icons/car.svg?raw';
import mountain from 'lucide-static/icons/mountain.svg?raw';
import shoppingBag from 'lucide-static/icons/shopping-bag.svg?raw';
import mapPin from 'lucide-static/icons/map-pin.svg?raw';
import map from 'lucide-static/icons/map.svg?raw';
import externalLink from 'lucide-static/icons/external-link.svg?raw';
import plane from 'lucide-static/icons/plane.svg?raw';
import arrowRight from 'lucide-static/icons/arrow-right.svg?raw';
import chevronDown from 'lucide-static/icons/chevron-down.svg?raw';
import play from 'lucide-static/icons/play.svg?raw';

/** Strip the license comment and size the icon to the surrounding text. */
const clean = (svg: string) =>
  svg.replace(/<!--.*?-->/s, '').replace(/\s+/g, ' ').trim()
    .replace(/width="24"/, 'width="1em"').replace(/height="24"/, 'height="1em"')
    .replace('<svg', '<svg aria-hidden="true"');

/** Icon per place kind (see Place.kind in trips.ts). */
export const KIND_ICONS: Record<string, string> = Object.fromEntries(Object.entries({
  food: utensils, drinks: martini, coffee, birding: bird, nature: trees, history: landmark,
  beach: treePalm, stay: bed, museum: library, stars: telescope, travel: car, adventure: mountain,
  shop: shoppingBag, town: mapPin,
}).map(([k, v]) => [k, clean(v)]));

export const ICONS = {
  map: clean(map), externalLink: clean(externalLink), plane: clean(plane),
  arrowRight: clean(arrowRight), chevronDown: clean(chevronDown), play: clean(play),
};
