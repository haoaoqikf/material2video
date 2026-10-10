export const MIN_STANDARD_CHARS = 130;
export const MAX_STANDARD_CHARS = 170;

/** Remove only the first non-empty Markdown H1; plain text's first line is body text. */
export function extractArticleBody(text: string): string {
  const lines = text.split(/\r\n|\n|\r/);
  const index = lines.findIndex((line) => line.trim().length > 0);
  if (index >= 0 && /^# .+\S.*$/.test(lines[index]!)) return lines.slice(index + 1).join('\n');
  return text;
}

/** Count Unicode code points except General_Category=P and Unicode White_Space. */
export function countArticleCharacters(text: string): number {
  let count = 0;
  for (const char of text) {
    if (!/[\p{P}\p{White_Space}]/u.test(char)) count += 1;
  }
  return count;
}

export function standardLengthResult(text: string): { count: number; pass: boolean } {
  const count = countArticleCharacters(text);
  return { count, pass: count >= MIN_STANDARD_CHARS && count <= MAX_STANDARD_CHARS };
}
