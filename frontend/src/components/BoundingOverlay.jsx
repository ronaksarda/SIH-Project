import React from 'react';

const BoundingOverlay = ({ boxes }) => {
  if (!boxes || boxes.length === 0) return null;

  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden">
      {boxes.map((box, i) => (
        <div
          key={i}
          className="absolute border-2 border-indigo-500 bg-indigo-500/10"
          style={{ left: `${box.x}%`, top: `${box.y}%`, width: `${box.width}%`, height: `${box.height}%` }}
        >
          <span className="absolute -top-5 left-0 bg-indigo-500 text-white text-[10px] font-semibold px-1.5 py-0.5 rounded-sm whitespace-nowrap">
            {box.label}
          </span>
        </div>
      ))}
    </div>
  );
};

export default BoundingOverlay;
