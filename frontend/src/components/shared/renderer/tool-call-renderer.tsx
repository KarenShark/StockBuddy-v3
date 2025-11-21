import { parse } from "best-effort-json-parser";
import { ChevronDown, Search, CheckCircle2, ExternalLink } from "lucide-react";
import { type FC, memo, useState, useEffect } from "react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";
import type { ToolCallRendererProps } from "@/types/renderer";
import MarkdownRenderer from "./markdown-renderer";

const ToolCallRenderer: FC<ToolCallRendererProps> = ({ content }) => {
  const [isOpen, setIsOpen] = useState(false);
  const { tool_name, tool_args, tool_result } = parse(content);
  const tool_result_array = parse(tool_result);
  
  // Auto-expand when result arrives (better transparency)
  useEffect(() => {
    if (tool_result && !isOpen) {
      setIsOpen(true);
    }
  }, [tool_result, isOpen]);
  
  // Parse tool_args if it's a string
  let parsedArgs = null;
  if (tool_args) {
    try {
      parsedArgs = typeof tool_args === 'string' ? JSON.parse(tool_args) : tool_args;
    } catch {
      parsedArgs = tool_args;
    }
  }

  // Generate result summary for preview
  const getResultSummary = () => {
    if (!tool_result_array) return null;
    if (Array.isArray(tool_result_array)) {
      const count = tool_result_array.length;
      return `Retrieved ${count} result${count !== 1 ? 's' : ''}`;
    }
    return "Result received";
  };

  const resultSummary = getResultSummary();
  const isCompleted = !!tool_result;
  const isRunning = !tool_result;

  return (
    <Collapsible
      open={isOpen}
      onOpenChange={setIsOpen}
      className={cn(
        "min-w-96 rounded-lg p-3 transition-all",
        isCompleted && "border border-green-200 bg-green-50/30",
        isRunning && "border border-blue-200 bg-blue-50/30 animate-pulse",
      )}
      data-active={isOpen}
    >
      <CollapsibleTrigger
        className={cn(
          "flex w-full items-center justify-between gap-2",
          tool_result && "cursor-pointer hover:bg-green-100/30 rounded transition-colors",
        )}
        disabled={!tool_result}
      >
        <div className="flex flex-col gap-1.5 flex-1 text-left">
          <div className="flex items-center gap-2">
            {isCompleted ? (
              <CheckCircle2 className="size-5 shrink-0 text-green-600" />
            ) : (
              <Spinner className="size-5 shrink-0 text-blue-600" />
            )}
            <div className="flex flex-col gap-0.5 flex-1">
              <p className={cn(
                "text-base leading-5 font-medium",
                isCompleted && "text-gray-900",
                isRunning && "text-blue-700",
              )}>
                {tool_name}
              </p>
              {isCompleted && resultSummary && (
                <p className="text-xs text-green-700 font-medium flex items-center gap-1">
                  <ExternalLink className="size-3" />
                  {resultSummary}
                </p>
              )}
              {isRunning && (
                <p className="text-xs text-blue-600">Searching...</p>
              )}
            </div>
          </div>
          {parsedArgs && (
            <div className="ml-7 text-sm text-gray-700 bg-white/50 rounded px-2 py-1 border border-gray-200">
              {typeof parsedArgs === 'object' ? (
                <div className="flex flex-wrap gap-x-3 gap-y-1">
                  {Object.entries(parsedArgs).map(([key, value]) => (
                    <span key={key} className="inline-flex items-center">
                      <span className="font-semibold text-gray-600">{key}:</span>
                      <span className="ml-1 text-gray-800">{String(value)}</span>
                    </span>
                  ))}
                </div>
              ) : (
                <span className="text-gray-800">{String(parsedArgs)}</span>
              )}
            </div>
          )}
        </div>
        {tool_result_array && (
          <ChevronDown
            className={cn(
              "h-5 w-5 transition-transform shrink-0",
              isCompleted && "text-green-700",
              isOpen && "rotate-180",
            )}
          />
        )}
      </CollapsibleTrigger>

      {/* Collapsible Content */}
      <CollapsibleContent>
        <div className="flex flex-col gap-4 pt-3 mt-2 border-t border-gray-200">
          <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide px-2">
            Search Results
          </div>
          {tool_result_array &&
            Array.isArray(tool_result_array) &&
            // TODO: temporarily use content as result type, need to improve later
            // biome-ignore lint/suspicious/noExplicitAny: temporarily use any as result type
            tool_result_array?.map((tool_result: any, index: number) => {
              return tool_result.content ? (
                <div key={tool_result.content} className="bg-white rounded-lg p-3 border border-gray-200 shadow-sm">
                  <div className="text-xs font-medium text-gray-500 mb-2">
                    Result #{index + 1}
                  </div>
                <MarkdownRenderer
                  content={tool_result.content}
                />
                </div>
              ) : (
                <div key={tool_result} className="bg-white rounded-lg p-3 border border-gray-200">
                  <p className="text-sm text-gray-700">{String(tool_result)}</p>
                </div>
              );
            })}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
};

export default memo(ToolCallRenderer);
