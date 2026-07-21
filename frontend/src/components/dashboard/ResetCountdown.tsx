import React, { useState, useEffect } from 'react';
import { Clock } from 'lucide-react';

interface ResetCountdownProps {
  targetDateStr: string | null;
  label: string;
}

export const ResetCountdown: React.FC<ResetCountdownProps> = ({ targetDateStr, label }) => {
  const [timeLeft, setTimeLeft] = useState<string>('--:--:--');

  useEffect(() => {
    if (!targetDateStr) {
      setTimeLeft('--:--:--');
      return;
    }

    const target = new Date(targetDateStr).getTime();

    const interval = setInterval(() => {
      const now = new Date().getTime();
      const distance = target - now;

      if (distance < 0) {
        setTimeLeft('Resetting...');
        return;
      }

      const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((distance % (1000 * 60)) / 1000);

      setTimeLeft(`${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`);
    }, 1000);

    return () => clearInterval(interval);
  }, [targetDateStr]);

  return (
    <div className="flex items-center space-x-2 text-slate-300">
      <Clock size={16} className="text-slate-500" />
      <span className="text-sm font-medium">{label}:</span>
      <span className="text-sm font-mono text-emerald-400">{timeLeft}</span>
    </div>
  );
};
