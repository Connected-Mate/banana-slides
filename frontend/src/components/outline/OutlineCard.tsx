import React, { useState, useEffect, useRef, useCallback } from 'react';
import { GripVertical, Edit2, Trash2, Check, X } from 'lucide-react';
import { useT } from '@/hooks/useT';
import { useImagePaste, buildMaterialsMarkdown } from '@/hooks/useImagePaste';
import { Card, Button, IconButton, useConfirm, Markdown, ShimmerOverlay, MaterialSelector } from '@/components/shared';
import { MarkdownTextarea, type MarkdownTextareaRef } from '@/components/shared/MarkdownTextarea';
import { Input } from '@/components/ui/input';
import type { Page, Material } from '@/types';

// OutlineCard 组件自包含翻译
const outlineCardI18n = {
  zh: {
    outlineCard: {
      page: "第 {{num}} 页", chapter: "章节", titleLabel: "标题",
      keyPointsPlaceholder: "要点（每行一个，支持粘贴图片）", confirmDeletePage: "确定要删除这一页吗？",
      confirmDeleteTitle: "确认删除",
      uploadingImage: "正在上传图片...",
      coverPage: "封面",
      coverPageTooltip: "第一页为封面页，通常包含标题和副标题"
    }
  },
  en: {
    outlineCard: {
      page: "Page {{num}}", chapter: "Chapter", titleLabel: "Title",
      keyPointsPlaceholder: "Key points (one per line, paste images supported)", confirmDeletePage: "Are you sure you want to delete this page?",
      confirmDeleteTitle: "Confirm Delete",
      uploadingImage: "Uploading image...",
      coverPage: "Cover",
      coverPageTooltip: "This is the cover page, usually containing the title and subtitle"
    }
  }
};

interface OutlineCardProps {
  page: Page;
  index: number;
  projectId?: string;
  showToast: (props: { message: string; type: 'success' | 'error' | 'info' | 'warning' }) => void;
  onUpdate: (data: Partial<Page>) => void;
  onDelete: () => void;
  onClick: () => void;
  isSelected: boolean;
  dragHandleProps?: React.HTMLAttributes<HTMLDivElement>;
  isAiRefining?: boolean;
}

export const OutlineCard: React.FC<OutlineCardProps> = ({
  page,
  index,
  projectId,
  showToast,
  onUpdate,
  onDelete,
  onClick,
  isSelected,
  dragHandleProps,
  isAiRefining = false,
}) => {
  const t = useT(outlineCardI18n);
  const { confirm, ConfirmDialog } = useConfirm();
  const outlineRaw = page.outline_content ?? { title: '', points: [] as string[] };
  const outline = { ...outlineRaw, points: outlineRaw.points ?? [] };
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(outline.title);
  const [editPoints, setEditPoints] = useState(outline.points.join('\n'));
  const [editPart, setEditPart] = useState(page.part || '');
  const [isMaterialSelectorOpen, setIsMaterialSelectorOpen] = useState(false);
  const textareaRef = useRef<MarkdownTextareaRef>(null);

  // Callback to insert at cursor position in the textarea
  const insertAtCursor = useCallback((markdown: string) => {
    textareaRef.current?.insertAtCursor(markdown);
  }, []);

  const { handlePaste, handleFiles, isUploading } = useImagePaste({
    projectId,
    setContent: setEditPoints,
    showToast: showToast,
    insertAtCursor,
  });

  const handleMaterialSelect = useCallback((materials: Material[]) => {
    const markdown = buildMaterialsMarkdown(materials, setEditPoints);
    textareaRef.current?.insertAtCursor(markdown + '\n');
  }, []);

  // 当 page prop 变化时，同步更新本地编辑状态（如果不在编辑模式）
  useEffect(() => {
    if (!isEditing) {
      setEditTitle(outline.title);
      setEditPoints(outline.points.join('\n'));
      setEditPart(page.part || '');
    }
  }, [outline.title, outline.points, page.part, isEditing]);

  const handleSave = () => {
    onUpdate({
      outline_content: {
        title: editTitle,
        points: editPoints.split('\n').filter((p) => p.trim()),
      },
      part: editPart.trim() || undefined,
    });
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditTitle(outline.title);
    setEditPoints(outline.points.join('\n'));
    setEditPart(page.part || '');
    setIsEditing(false);
  };

  return (
    <Card
      className={`p-4 relative ${
        isSelected ? 'border-2 border-banana-500 shadow-yellow' : ''
      }`}
      onClick={!isEditing ? onClick : undefined}
    >
      <ShimmerOverlay show={isAiRefining} />

      <div className="flex items-start gap-3 relative z-10">
        {/* 拖拽手柄 */}
        <div
          {...dragHandleProps}
          className="flex-shrink-0 cursor-move text-gray-400 hover:text-gray-600 pt-1"
        >
          <GripVertical size={20} />
        </div>

        {/* 内容区 */}
        <div className="flex-1 min-w-0">
          {/* 页码和章节 */}
          <div className="flex items-center gap-2 mb-2">
            <span className="text-sm font-semibold text-gray-900 dark:text-foreground-primary">
              {t('outlineCard.page', { num: index + 1 })}
            </span>
            {index === 0 && !isEditing && (
              <span
                className="text-xs px-1.5 py-0.5 bg-banana-100 dark:bg-banana-900/30 text-banana-700 dark:text-banana-400 rounded"
                title={t('outlineCard.coverPageTooltip')}
              >
                {t('outlineCard.coverPage')}
              </span>
            )}
            {isEditing ? (
              <Input
                type="text"
                value={editPart}
                onChange={(e) => setEditPart(e.target.value)}
                onClick={(e) => e.stopPropagation()}
                className="h-6 w-24 rounded px-2 py-0.5 text-xs border-blue-300 dark:border-blue-700 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 focus-visible:ring-1 focus-visible:ring-blue-500"
                placeholder={t('outlineCard.chapter')}
              />
            ) : (
              page.part && (
                <span className="text-xs px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded">
                  {page.part}
                </span>
              )
            )}
          </div>

          {isEditing ? (
            /* 编辑模式 */
            <div className="space-y-3" onClick={(e) => e.stopPropagation()}>
              <Input
                type="text"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                className="rounded-lg bg-white dark:bg-background-secondary text-gray-900 dark:text-foreground-primary focus-visible:ring-banana-500"
                placeholder={t('outlineCard.titleLabel')}
              />
              <div>
                <MarkdownTextarea
                  ref={textareaRef}
                  value={editPoints}
                  onChange={setEditPoints}
                  onPaste={handlePaste}
                  onFiles={handleFiles}
                  onSelectFromLibrary={() => setIsMaterialSelectorOpen(true)}
                  rows={5}
                  placeholder={t('outlineCard.keyPointsPlaceholder')}
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="ghost" size="sm" icon={<X size={16} />} onClick={handleCancel}>
                  {t('common.cancel')}
                </Button>
                <Button variant="primary" size="sm" icon={<Check size={16} />} onClick={handleSave} disabled={isUploading}>
                  {t('common.save')}
                </Button>
              </div>
            </div>
          ) : (
            /* 查看模式 */
            <div>
              <h4 className="font-semibold text-gray-900 dark:text-foreground-primary mb-2">
                {outline.title}
              </h4>
              <div className="text-gray-600 dark:text-foreground-tertiary">
                <Markdown>{outline.points.join('\n')}</Markdown>
              </div>
            </div>
          )}
        </div>

        {/* 操作按钮 */}
        {!isEditing && (
          <div className="flex-shrink-0 flex gap-2">
            <IconButton
              icon={<Edit2 size={16} />}
              label={t('common.edit')}
              variant="primary"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                setIsEditing(true);
              }}
            />
            <IconButton
              icon={<Trash2 size={16} />}
              label={t('common.delete')}
              variant="danger"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                confirm(
                  t('outlineCard.confirmDeletePage'),
                  onDelete,
                  { title: t('outlineCard.confirmDeleteTitle'), variant: 'danger' }
                );
              }}
            />
          </div>
        )}
      </div>
      {ConfirmDialog}
      <MaterialSelector
        projectId={projectId}
        isOpen={isMaterialSelectorOpen}
        onClose={() => setIsMaterialSelectorOpen(false)}
        onSelect={handleMaterialSelect}
        multiple
      />
    </Card>
  );
};
