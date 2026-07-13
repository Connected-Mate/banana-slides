import React, { useState, useCallback, useRef, useEffect } from 'react';
import { Plus, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useT } from '@/hooks/useT';
import { cn } from '@/utils';
import { Modal } from '@/components/shared/Modal';
import { Button } from '@/components/shared/Button';
import { Textarea } from '@/components/shared/Textarea';
import { badgeVariants } from '@/components/ui/badge';

// ─── i18n ────────────────────────────────────────────────────────────────────
const presetI18n = {
  zh: {
    preset: {
      addCustom: '自定义',
      modalTitle: '添加自定义预设',
      nameLabel: '预设名称',
      namePlaceholder: '例如：学术风格',
      contentLabel: '提示词内容',
      contentPlaceholder: '例如：使用学术论文的严谨表述，引用数据时标注来源',
      add: '添加',
      cancel: '取消',
    },
  },
  en: {
    preset: {
      addCustom: 'Custom',
      modalTitle: 'Add Custom Preset',
      nameLabel: 'Preset Name',
      namePlaceholder: 'e.g., Academic style',
      contentLabel: 'Prompt Content',
      contentPlaceholder: 'e.g., Use rigorous academic language, cite data sources',
      add: 'Add',
      cancel: 'Cancel',
    },
  },
};

// ─── Types ───────────────────────────────────────────────────────────────────
export interface Preset {
  name: string;
  content: string;
}

export type PresetType = 'outline' | 'description';

// ─── System presets ──────────────────────────────────────────────────────────
const SYSTEM_PRESETS: Record<PresetType, Record<'zh' | 'en', Preset[]>> = {
  outline: {
    zh: [],
    en: [],
  },
  description: {
    zh: [],
    en: [],
  },
};

const STORAGE_KEY_PREFIX = 'presetCapsules_';

function loadUserPresets(type: PresetType): Preset[] {
  try {
    const raw = localStorage.getItem(`${STORAGE_KEY_PREFIX}${type}`);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveUserPresets(type: PresetType, presets: Preset[]) {
  localStorage.setItem(`${STORAGE_KEY_PREFIX}${type}`, JSON.stringify(presets));
}

// ─── Component ───────────────────────────────────────────────────────────────
interface PresetCapsulesProps {
  type: PresetType;
  onAppend: (text: string) => void;
}

export default function PresetCapsules({ type, onAppend }: PresetCapsulesProps) {
  const t = useT(presetI18n);
  const [userPresets, setUserPresets] = useState<Preset[]>(() => loadUserPresets(type));
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newName, setNewName] = useState('');
  const [newContent, setNewContent] = useState('');
  const nameInputRef = useRef<HTMLInputElement>(null);

  const { i18n } = useTranslation();
  const currentLang = i18n.language?.startsWith('zh') ? 'zh' : 'en';
  const systemPresets = SYSTEM_PRESETS[type][currentLang];

  useEffect(() => {
    if (isModalOpen && nameInputRef.current) {
      // Delay focus slightly to allow modal animation
      const timer = setTimeout(() => nameInputRef.current?.focus(), 100);
      return () => clearTimeout(timer);
    }
  }, [isModalOpen]);

  const handleCloseModal = useCallback(() => {
    setIsModalOpen(false);
    setNewName('');
    setNewContent('');
  }, []);

  const handleAddPreset = useCallback(() => {
    const trimmedName = newName.trim();
    const trimmedContent = newContent.trim();
    if (!trimmedName || !trimmedContent) return;

    const updated = [...userPresets, { name: trimmedName, content: trimmedContent }];
    setUserPresets(updated);
    saveUserPresets(type, updated);
    handleCloseModal();
  }, [newName, newContent, userPresets, type, handleCloseModal]);

  const handleDeletePreset = useCallback((index: number) => {
    const updated = userPresets.filter((_, i) => i !== index);
    setUserPresets(updated);
    saveUserPresets(type, updated);
  }, [userPresets, type]);

  const capsuleBase = cn(badgeVariants({ variant: 'outline' }), 'gap-1 rounded-full py-1 cursor-pointer max-w-[200px] truncate');
  const systemCapsule = cn(capsuleBase, 'border-gray-200 bg-gray-100 text-gray-600 hover:bg-banana-50 hover:text-banana-700 dark:border-border-primary dark:bg-background-primary dark:text-foreground-secondary dark:hover:bg-banana-900/20 dark:hover:text-banana-400');
  const userCapsule = cn(capsuleBase, 'border-banana-200 bg-banana-50 text-banana-700 hover:bg-banana-100 dark:border-banana-700/40 dark:bg-banana-900/20 dark:text-banana-400 dark:hover:bg-banana-900/30');

  return (
    <>
      <div className="flex flex-wrap items-center gap-1.5 mt-2" data-testid={`${type}-presets`}>
        {/* System presets */}
        {systemPresets.map((preset, i) => (
          <button
            key={`sys-${i}`}
            type="button"
            data-testid={`${type}-system-preset-${i}`}
            className={systemCapsule}
            title={preset.content}
            onClick={() => onAppend(preset.content)}
          >
            {preset.name}
          </button>
        ))}

        {/* User presets */}
        {userPresets.map((preset, i) => (
          <span
            key={`usr-${i}`}
            className={userCapsule}
            title={preset.content}
            data-testid={`${type}-user-preset-${i}`}
          >
            <button
              type="button"
              className="truncate"
              onClick={() => onAppend(preset.content)}
            >
              {preset.name}
            </button>
            <button
              type="button"
              data-testid={`${type}-delete-preset-${i}`}
              aria-label="Delete preset"
              className="ml-0.5 p-0.5 rounded-full hover:bg-banana-200 dark:hover:bg-banana-800/40 transition-colors"
              onClick={(e) => { e.stopPropagation(); handleDeletePreset(i); }}
            >
              <X size={10} />
            </button>
          </span>
        ))}

        {/* Add button */}
        <Button
          type="button"
          variant="ghost"
          data-testid={`${type}-add-preset`}
          onClick={() => setIsModalOpen(true)}
          className={cn(capsuleBase, 'h-auto border-dashed border-gray-300 bg-white text-gray-400 hover:border-banana-300 hover:bg-white hover:text-banana-600 dark:border-border-primary dark:bg-background-primary dark:text-foreground-tertiary dark:hover:border-banana-600/40 dark:hover:bg-background-primary dark:hover:text-banana-400')}
        >
          <Plus size={10} />
          {t('preset.addCustom')}
        </Button>
      </div>

      {/* Add preset modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={handleCloseModal}
        title={t('preset.modalTitle')}
        size="sm"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-foreground-secondary mb-1.5">
              {t('preset.nameLabel')}
            </label>
            <input
              ref={nameInputRef}
              data-testid={`${type}-preset-name-input`}
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder={t('preset.namePlaceholder')}
              className="w-full px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-border-primary bg-gray-50 dark:bg-background-primary text-gray-700 dark:text-foreground-secondary placeholder-gray-400 dark:placeholder-foreground-tertiary/50 focus:outline-none focus:border-banana-300 dark:focus:border-banana-500/40 transition-colors"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-foreground-secondary mb-1.5">
              {t('preset.contentLabel')}
            </label>
            <Textarea
              data-testid={`${type}-preset-content-input`}
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
              placeholder={t('preset.contentPlaceholder')}
              rows={3}
              className="min-h-0 rounded-lg bg-gray-50 px-3 py-2 focus-visible:ring-banana-400 dark:bg-background-primary"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              data-testid={`${type}-preset-cancel`}
              onClick={handleCloseModal}
            >
              {t('preset.cancel')}
            </Button>
            <Button
              type="button"
              size="sm"
              data-testid={`${type}-preset-confirm`}
              onClick={handleAddPreset}
              disabled={!newName.trim() || !newContent.trim()}
            >
              {t('preset.add')}
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
}
