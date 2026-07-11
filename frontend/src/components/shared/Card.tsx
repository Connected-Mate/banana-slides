import React from 'react';
import { Card as UiCard } from '@/components/ui/card';
import { cn } from '@/utils';

/** Adaptateur shadcn — API historique préservée (hoverable). Rendu par ui/card. */

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  hoverable?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  hoverable = false,
  className,
  ...props
}) => {
  return (
    <UiCard
      className={cn(
        'bg-white dark:bg-background-secondary rounded-card shadow-md border border-gray-100 dark:border-border-primary',
        hoverable && 'hover:shadow-lg hover:-translate-y-1 hover:border-banana-500 transition-all duration-200 cursor-pointer',
        className
      )}
      {...props}
    >
      {children}
    </UiCard>
  );
};
