import japan from '../content/japan.json';
import seattle from '../content/seattle.json';
import southwest from '../content/southwest.json';
import london from '../content/london.json';

export interface Img { id: string; file: string; w: number; h: number }
export interface Block { type: 'grid' | 'carousel'; images: Img[] }
export interface Section { heading: string; subtitle: string | null; text: string[]; blocks: Block[] }
export interface Trip {
  slug: string; title: string; subtitle: string | null; year: number;
  hero: Block[]; sections: Section[]; source: string;
}

const raw = { southwest, london, japan, seattle };

export const trips: Trip[] = Object.entries(raw).map(([slug, t]) => ({
  slug,
  year: Number(((t.title + ' ' + (t.subtitle ?? '')).match(/\d{4}/) ?? [0])[0]),
  ...t,
})).sort((a, b) => b.year - a.year);

export const bySlug = (slug: string) => trips.find((t) => t.slug === slug)!;
