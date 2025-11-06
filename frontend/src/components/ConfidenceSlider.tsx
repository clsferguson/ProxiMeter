/**
 * ConfidenceSlider Component
 * Slider for adjusting minimum confidence threshold (0.0-1.0)
 * Displays value as percentage (0-100%)
 */

import * as React from 'react';
import { Label } from '@/components/ui/label';

interface ConfidenceSliderProps {
  value: number; // 0.0 to 1.0
  onChange: (value: number) => void;
  className?: string;
}

export function ConfidenceSlider({ value, onChange, className }: ConfidenceSliderProps) {
  const percentageValue = Math.round(value * 100);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = parseInt(e.target.value) / 100;
    onChange(newValue);
  };

  return (
    <div className={className}>
      <div className="space-y-4">
        {/* Header with current value */}
        <div className="flex items-center justify-between">
          <Label htmlFor="confidence-slider" className="text-base font-medium">
            Minimum Confidence
          </Label>
          <span className="text-2xl font-bold tabular-nums">
            {percentageValue}%
          </span>
        </div>

        {/* Slider */}
        <input
          id="confidence-slider"
          type="range"
          min="0"
          max="100"
          step="1"
          value={percentageValue}
          onChange={handleChange}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700 accent-primary"
        />

        {/* Description */}
        <p className="text-sm text-muted-foreground">
          Lower values show more detections but may include false positives.
          Higher values show only high-confidence detections.
        </p>

        {/* Visual indicators */}
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>0% (All)</span>
          <span>50%</span>
          <span>100% (Very High)</span>
        </div>
      </div>
    </div>
  );
}
