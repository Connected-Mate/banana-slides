import React from 'react';
import { Button as UiButton } from '@/components/ui/button';
import { cn } from '@/utils';

/**
 * Adaptateur shadcn — API historique préservée (icon, label, variant, size,
 * active, loading, tooltipSide). Bouton rendu par ui/button (variant ghost,
 * size icon) ; tooltip hover conservé en CSS pur (pas de provider Radix requis).
 */

interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** Icon node (e.g. a lucide icon). */
  icon: React.ReactNode;
  /** Accessible name + hover tooltip text. */
  label: string;
  variant?: 'default' | 'primary' | 'danger';
  size?: 'sm' | 'md';
  active?: boolean;
  loading?: boolean;
  /** Tooltip placement relative to the button. */
  tooltipSide?: 'top' | 'bottom';
}

const sizeClass: Record<NonNullable<IconButtonProps['size']>, string> = {
  sm: 'h-7 w-7',
  md: 'h-8 w-8',
};

const variantClass: Record<NonNullable<IconButtonProps['variant']>, string> = {
  default:
    'text-gray-500 hover:text-gray-800 hover:bg-gray-100 dark:text-foreground-tertiary dark:hover:text-foreground-primary dark:hover:bg-background-hover',
  primary:
    'text-banana-600 hover:text-banana-700 hover:bg-banana-50 dark:text-banana-400 dark:hover:bg-banana-900/30',
  danger:
    'text-gray-400 hover:text-red-600 hover:bg-red-50 dark:text-foreground-tertiary dark:hover:text-red-400 dark:hover:bg-red-900/30',
};

export const IconButton = React.forwardRef<HTMLButtonElement, IconButtonProps>(({
  icon,
  label,
  variant = 'default',
  size = 'md',
  active = false,
  loading = false,
  tooltipSide = 'top',
  className,
  disabled,
  ...props
}, ref) => (
  <span className={cn('group relative inline-flex', className)}>
    <UiButton
      ref={ref}
      type="button"
      variant="ghost"
      size="icon"
      aria-label={label}
      disabled={disabled || loading}
      className={cn(
        'rounded-lg transition-colors duration-150 disabled:opacity-40',
        sizeClass[size],
        variantClass[variant],
        active && 'bg-gray-100 text-gray-800 dark:bg-background-hover dark:text-foreground-primary'
      )}
      {...props}
    >
      {loading ? (
        <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
      ) : (
        icon
      )}
    </UiButton>
    <span
      role="tooltip"
      className={cn(
        'pointer-events-none absolute left-1/2 z-30 -translate-x-1/2 whitespace-nowrap rounded-md bg-gray-900 px-2 py-1 text-[11px] font-medium text-white opacity-0 shadow-lg transition-opacity duration-150 group-hover:opacity-100 dark:bg-background-elevated dark:text-foreground-primary',
        tooltipSide === 'top' ? 'bottom-full mb-1.5' : 'top-full mt-1.5'
      )}
    >
      {label}
    </span>
  </span>
));

IconButton.displayName = 'IconButton';
