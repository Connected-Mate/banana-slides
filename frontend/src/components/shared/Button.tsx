import React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { Button as UiButton } from '@/components/ui/button';
import { cn } from '@/utils';

/**
 * Adaptateur shadcn — API historique préservée (variant primary/secondary/ghost,
 * size sm/md/lg, loading, icon). Rendu par ui/button, apparence banana via cva.
 */

const appButtonVariants = cva(
  'font-semibold rounded-lg transition-all duration-200 touch-manipulation',
  {
    variants: {
      variant: {
        primary:
          'bg-gradient-to-r from-banana-500 to-banana-600 text-black hover:shadow-yellow hover:-translate-y-0.5 active:translate-y-0 shadow-md',
        secondary:
          'bg-white dark:bg-background-secondary border border-banana-500 text-black dark:text-foreground-primary hover:bg-banana-50 dark:hover:bg-background-hover',
        ghost:
          'bg-transparent text-gray-700 dark:text-foreground-secondary hover:bg-gray-100 dark:hover:bg-background-secondary',
      },
      size: {
        sm: 'h-8 px-3 text-sm',
        md: 'h-10 px-6 text-base',
        lg: 'h-12 px-8 text-lg',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  }
);

interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof appButtonVariants> {
  loading?: boolean;
  icon?: React.ReactNode;
}

/** Mapping variantes app → variantes structurelles ui/button. */
const uiVariantMap = {
  primary: 'default',
  secondary: 'outline',
  ghost: 'ghost',
} as const;

const uiSizeMap = {
  sm: 'sm',
  md: 'default',
  lg: 'lg',
} as const;

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  loading = false,
  icon,
  className,
  disabled,
  ...props
}) => {
  return (
    <UiButton
      variant={uiVariantMap[variant ?? 'primary']}
      size={uiSizeMap[size ?? 'md']}
      className={cn(appButtonVariants({ variant, size }), className)}
      disabled={disabled || loading}
      {...props}
    >
      {loading && (
        <svg
          className="animate-spin -ml-1 mr-2 h-4 w-4"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      )}
      {!loading && icon && (
        <span className={children ? 'mr-2' : ''}>{icon}</span>
      )}
      {children}
    </UiButton>
  );
};
