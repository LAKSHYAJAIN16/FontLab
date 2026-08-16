import type { AssignedVariant } from "./types";

export function applyVariant(variant: AssignedVariant): void {
  const element = document.querySelector<HTMLElement>(variant.selector);
  if (!element) return;

  for (const [property, value] of Object.entries(variant.patch)) {
    element.style.setProperty(property, value);
  }
}

export function applyVariants(variants: AssignedVariant[]): void {
  for (const variant of variants) applyVariant(variant);
}
