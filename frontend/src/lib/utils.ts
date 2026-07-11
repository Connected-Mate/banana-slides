import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Merge Tailwind class names (clsx + tailwind-merge).
 * shadcn/ui convention. Mirrors `cn` in `@/utils` so both import paths work.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
