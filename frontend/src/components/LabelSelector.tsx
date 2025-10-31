/**
 * LabelSelector Component
 * Multi-select checkbox list for COCO class labels with search functionality
 */

import * as React from 'react';
import { Search } from 'lucide-react';
import { Checkbox } from '@/components/ui/checkbox';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { COCO_CLASSES } from '@/services/detection';

interface LabelSelectorProps {
  selectedLabels: string[];
  onChange: (labels: string[]) => void;
  className?: string;
}

export function LabelSelector({ selectedLabels, onChange, className }: LabelSelectorProps) {
  const [searchQuery, setSearchQuery] = React.useState('');

  // Filter classes based on search query
  const filteredClasses = React.useMemo(() => {
    if (!searchQuery.trim()) {
      return COCO_CLASSES;
    }
    const query = searchQuery.toLowerCase();
    return COCO_CLASSES.filter(cls => cls.toLowerCase().includes(query));
  }, [searchQuery]);

  const handleToggle = (label: string, checked: boolean) => {
    if (checked) {
      onChange([...selectedLabels, label]);
    } else {
      onChange(selectedLabels.filter(l => l !== label));
    }
  };

  const handleSelectAll = () => {
    onChange([...COCO_CLASSES]);
  };

  const handleClearAll = () => {
    onChange([]);
  };

  return (
    <div className={className}>
      <div className="space-y-4">
        {/* Header with counts and actions */}
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground">
            {selectedLabels.length} of {COCO_CLASSES.length} labels selected
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleSelectAll}
              className="text-xs text-primary hover:underline"
            >
              Select All
            </button>
            <span className="text-xs text-muted-foreground">|</span>
            <button
              type="button"
              onClick={handleClearAll}
              className="text-xs text-primary hover:underline"
            >
              Clear All
            </button>
          </div>
        </div>

        {/* Search input */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="text"
            placeholder="Search labels..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>

        {/* Scrollable checkbox list */}
        <ScrollArea className="h-[400px] rounded-md border p-4">
          <div className="space-y-3">
            {filteredClasses.length === 0 ? (
              <div className="text-center text-sm text-muted-foreground py-8">
                No labels found matching "{searchQuery}"
              </div>
            ) : (
              filteredClasses.map((label) => (
                <div key={label} className="flex items-center space-x-2">
                  <Checkbox
                    id={`label-${label}`}
                    checked={selectedLabels.includes(label)}
                    onCheckedChange={(checked) => handleToggle(label, checked as boolean)}
                  />
                  <Label
                    htmlFor={`label-${label}`}
                    className="text-sm font-normal cursor-pointer flex-1"
                  >
                    {label}
                  </Label>
                </div>
              ))
            )}
          </div>
        </ScrollArea>

        {/* Selected labels preview */}
        {selectedLabels.length > 0 && (
          <div className="rounded-md bg-muted p-3">
            <div className="text-xs font-medium mb-2">Selected labels:</div>
            <div className="flex flex-wrap gap-1">
              {selectedLabels.slice(0, 10).map((label) => (
                <span
                  key={label}
                  className="inline-flex items-center rounded-full bg-primary/10 px-2 py-1 text-xs font-medium text-primary"
                >
                  {label}
                </span>
              ))}
              {selectedLabels.length > 10 && (
                <span className="inline-flex items-center rounded-full bg-muted-foreground/10 px-2 py-1 text-xs font-medium text-muted-foreground">
                  +{selectedLabels.length - 10} more
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
