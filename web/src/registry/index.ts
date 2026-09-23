import registryData from './registry.json';

export interface StylePackEntry { riseDistance: number; transitionSpan: number; }

export interface PrimitiveEntry {
  type: string; category: 'layout' | 'content' | 'graphic'; children: readonly [number, number];
  props: readonly string[]; motions: readonly string[]; source: string; summary: string;
}

export const PRIMITIVES: Record<string, PrimitiveEntry> = Object.fromEntries(
  (registryData.primitives as unknown as PrimitiveEntry[]).map((entry) => [entry.type, entry]),
);
export function primitiveDefinition(type: string): PrimitiveEntry | undefined { return PRIMITIVES[type]; }
export function knownPrimitiveTypes(): string[] { return Object.keys(PRIMITIVES).sort(); }
export const STYLE_PACKS = registryData.stylePacks as Record<string, StylePackEntry>;
export function stylePackDefinition(name?: string): StylePackEntry { return STYLE_PACKS[name ?? 'editorial'] ?? STYLE_PACKS.editorial; }
