import React from 'react';
import { Shield, AlertTriangle, FileText, CheckCircle, Info } from 'lucide-react';
import clsx from 'clsx';

export const TagBadge = ({ tag, confidence, source, is_auto }) => {
  let color = 'badge-gray';
  let Icon = Info;

  if (tag.includes('Sensitive') || tag.includes('Confidential')) {
    color = 'badge-red';
    Icon = Shield;
  } else if (tag.includes('Contact') || tag.includes('Personal')) {
    color = 'badge-orange';
    Icon = AlertTriangle;
  } else {
    color = 'badge-blue';
    Icon = FileText;
  }

  const opacity = is_auto ? 'opacity-100' : 'opacity-70';
  const border = is_auto ? 'border-transparent' : 'border-dashed';

  return (
    <div className={clsx("badge gap-1", color, opacity, border)} title={`Source: ${source} (${Math.round(confidence * 100)}%)`}>
      <Icon size={12} />
      <span>{tag}</span>
      {is_auto && <CheckCircle size={10} className="ml-1" />}
    </div>
  );
};
