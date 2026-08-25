// Shared number formatting for token counts.
//
// Token figures range from hundreds to tens of millions, so dashboards render
// them compactly ("234K", "23M") and keep the exact number for tooltips /
// title attributes via formatTokensFull.
const compactFmt = new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 });
const fullFmt = new Intl.NumberFormat('en');

export const formatTokens = (n: number | null | undefined): string =>
  n == null ? '0' : compactFmt.format(n);

export const formatTokensFull = (n: number | null | undefined): string =>
  n == null ? '0' : fullFmt.format(n);
