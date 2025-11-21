import { type FC, memo } from "react";

interface StreamingIndicatorProps {
  statusMessage?: string;
}

const StreamingIndicator: FC<StreamingIndicatorProps> = ({ statusMessage }) => {
  const displayMessage = statusMessage || "AI is thinking...";
  
  return (
    <output
      className="flex items-center gap-2 text-gray-500 text-sm"
      aria-live="polite"
      aria-label={displayMessage}
    >
      <div className="flex space-x-1" aria-hidden="true">
        <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400 delay-0" />
        <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400 delay-150" />
        <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400 delay-300" />
      </div>
      <span>{displayMessage}</span>
    </output>
  );
};

export default memo(StreamingIndicator);
