import { Brain, ChevronDown } from "lucide-react";
import { type FC, memo, useState } from "react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";
import type { ReasoningRendererProps } from "@/types/renderer";
import MarkdownRenderer from "./markdown-renderer";

const ReasoningRenderer: FC<ReasoningRendererProps> = ({ content }) => {
  const [isOpen, setIsOpen] = useState(true); // Default open to show thinking

  // Parse content - could be string or object with reasoning text
  let reasoningText = content;
  if (typeof content === "string") {
    try {
      const parsed = JSON.parse(content);
      reasoningText = parsed.reasoning || parsed.content || parsed;
    } catch {
      reasoningText = content;
    }
  }

  return (
    <Collapsible
      open={isOpen}
      onOpenChange={setIsOpen}
      className={cn(
        "min-w-96 rounded-lg border border-blue-300 bg-blue-50 p-3 shadow-sm",
      )}
      data-active={isOpen}
    >
      <CollapsibleTrigger
        className={cn(
          "flex w-full items-center justify-between",
          "cursor-pointer hover:bg-blue-100 rounded px-2 py-1 transition-colors",
        )}
      >
        <div className="flex items-center gap-2.5 text-blue-800">
          <Brain className="size-5 animate-pulse" />
          <div className="flex flex-col">
            <p className="text-sm font-semibold">AI Reasoning</p>
            <p className="text-xs text-blue-600">Analyzing strategy...</p>
          </div>
        </div>
        <ChevronDown
          className={cn(
            "h-5 w-5 text-blue-700 transition-transform",
            isOpen && "rotate-180",
          )}
        />
      </CollapsibleTrigger>

      {/* Collapsible Content */}
      <CollapsibleContent>
        <div className="pt-3 border-t border-blue-200 mt-2">
          <div className="bg-white rounded-lg p-3 border border-blue-100">
            <div className="text-sm text-gray-800 leading-relaxed">
              {typeof reasoningText === "string" ? (
                <MarkdownRenderer content={reasoningText} />
              ) : (
                <pre className="whitespace-pre-wrap text-xs text-gray-700">
                  {JSON.stringify(reasoningText, null, 2)}
                </pre>
              )}
            </div>
          </div>
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
};

export default memo(ReasoningRenderer);

