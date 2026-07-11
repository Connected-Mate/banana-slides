import React from 'react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/utils';
import type { Page } from '@/types';
import { usePageStatus, type PageStatusContext } from '@/hooks/usePageStatus';
import { statusClassNames } from './StatusBadge';

interface ContextualStatusBadgeProps {
  page: Page;
  /** 上下文：description（描述页）、image（图片页）、full（完整状态） */
  context?: PageStatusContext;
  /** 是否显示详细描述（悬停提示） */
  showDescription?: boolean;
}

/**
 * 根据上下文智能显示状态的徽章 — adaptateur shadcn, rendu ui/badge.
 *
 * - 在描述编辑页面：只显示描述相关状态
 * - 在图片预览页面：显示图片生成状态
 * - 其他场景：显示完整页面状态
 */
export const ContextualStatusBadge: React.FC<ContextualStatusBadgeProps> = ({
  page,
  context = 'full',
  showDescription = true,
}) => {
  const { status, label, description } = usePageStatus(page, context);

  return (
    <Badge
      variant="secondary"
      className={cn(
        'rounded border-transparent shadow-none font-medium',
        statusClassNames[status as keyof typeof statusClassNames]
      )}
      title={showDescription ? description : undefined}
    >
      {label}
    </Badge>
  );
};
