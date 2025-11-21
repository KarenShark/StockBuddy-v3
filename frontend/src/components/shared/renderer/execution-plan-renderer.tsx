import { type FC, memo, useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { useCurrentConversation } from "@/store/agent-store";

interface TaskItem {
  id: string;
  agentName: string;
  title: string;
  query: string;
  status: "pending" | "running" | "completed" | "failed";
  dependsOn: string[];
}

interface ExecutionPlanData {
  tasks: TaskItem[];
  totalCount: number;
  parallelCount: number;
  sequentialCount: number;
}

interface ExecutionPlanRendererProps {
  content: string;
}

const ExecutionPlanRenderer: FC<ExecutionPlanRendererProps> = ({ content }) => {
  const [planData, setPlanData] = useState<ExecutionPlanData | null>(null);
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  
  // Subscribe to conversation store for task status updates
  const { curConversation } = useCurrentConversation();
  const conversationMetadata = curConversation?.metadata;

  useEffect(() => {
    // Parse execution plan from JSON content
    try {
      const parsed = JSON.parse(content) as ExecutionPlanData;
      setPlanData(parsed);
      setTasks(parsed.tasks);
    } catch (e) {
      console.error("Failed to parse execution plan:", e);
    }
  }, [content]);

  // Update task status based on current task execution and completed tasks
  useEffect(() => {
    const currentTaskId = conversationMetadata?.currentTaskStatus?.taskId;
    const completedTaskIds = conversationMetadata?.completedTaskIds;
    
    setTasks(prevTasks => {
      if (prevTasks.length === 0) return prevTasks;
      
      return prevTasks.map(task => {
        // Check if task is completed
        if (completedTaskIds?.has(task.id)) {
          return { ...task, status: "completed" as const };
        }
        
        // Check if task is currently running
        if (currentTaskId === task.id) {
          return { ...task, status: "running" as const };
        }
        
        // Otherwise keep as pending
        return task.status === "completed" ? task : { ...task, status: "pending" as const };
      });
    });
  }, [conversationMetadata?.currentTaskStatus, conversationMetadata?.completedTaskIds]);

  if (!planData || tasks.length === 0) {
    return null;
  }

  // Calculate progress
  const completedCount = tasks.filter(t => t.status === "completed").length;
  const runningTask = tasks.find(t => t.status === "running");
  const allCompleted = completedCount === tasks.length;

  // Group tasks by execution type
  const parallelTasks = tasks.filter(t => t.dependsOn.length === 0);
  const sequentialTasks = tasks.filter(t => t.dependsOn.length > 0);

  return (
    <div className="overflow-hidden rounded-lg border border-gray-100 bg-neutral-100 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between bg-white p-4">
        <div className="flex items-center gap-2">
          <span className="text-lg">📋</span>
          <h3 className="font-semibold text-gray-900">Execution Plan</h3>
        </div>
        <div className="text-sm text-gray-600">
          {completedCount} / {planData.totalCount} completed
        </div>
      </div>

      {/* Content area */}
      <div className="space-y-3 p-4">
      {/* Execution structure info */}
      {planData.parallelCount > 1 && (
          <div className="flex items-start gap-2 rounded-lg border border-gray-200 bg-gray-50 p-3 text-sm">
          <span>⚡</span>
          <div>
              <span className="font-medium text-gray-900">Parallel Execution: </span>
              <span className="text-gray-700">{planData.parallelCount} tasks will run simultaneously</span>
          </div>
        </div>
      )}

      {/* Task list */}
      <div className="space-y-2">
        {tasks.map((task, index) => (
          <TaskRow
            key={task.id}
            task={task}
            index={index}
          />
        ))}
      </div>

        {/* Dynamic Footer - shows current status */}
        <div className="flex items-center gap-2 border-t border-gray-200 pt-3 text-sm">
          {allCompleted ? (
            <>
              <span>✅</span>
              <span className="font-medium text-green-600">All tasks completed</span>
            </>
          ) : runningTask ? (
            <>
        <span>🚀</span>
              <div className="flex-1">
                <span className="font-medium text-blue-600">Currently executing: </span>
                <span className="text-gray-700">{runningTask.agentName}</span>
              </div>
            </>
          ) : (
            <>
              <span>⏳</span>
              <span className="font-medium text-gray-600">Preparing next task...</span>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

interface TaskRowProps {
  task: TaskItem;
  index: number;
}

const TaskRow: FC<TaskRowProps> = ({ task, index }) => {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // Staggered animation for initial render
    const timer = setTimeout(() => {
      setIsVisible(true);
    }, index * 100);
    return () => clearTimeout(timer);
  }, [index]);

  const getStatusIcon = (status: TaskItem["status"]) => {
    switch (status) {
      case "pending":
        return <div className="h-4 w-4 rounded-full border-2 border-gray-300" />;
      case "running":
        return (
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
        );
      case "completed":
        return (
          <div className="flex h-4 w-4 items-center justify-center rounded-full bg-green-500">
            <svg
              className="h-2.5 w-2.5 text-white"
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path d="M5 13l4 4L19 7" />
            </svg>
          </div>
        );
      case "failed":
        return (
          <div className="flex h-4 w-4 items-center justify-center rounded-full bg-red-500">
            <svg
              className="h-2.5 w-2.5 text-white"
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
        );
    }
  };

  const getStatusColor = (status: TaskItem["status"]) => {
    switch (status) {
      case "pending":
        return "text-gray-600";
      case "running":
        return "text-blue-600 font-medium";
      case "completed":
        return "text-green-600";
      case "failed":
        return "text-red-600";
    }
  };

  return (
    <div
      className={cn(
        "flex items-start gap-2.5 rounded-lg border border-gray-200 bg-white p-3 transition-all duration-300",
        isVisible ? "translate-x-0 opacity-100" : "-translate-x-4 opacity-0"
      )}
    >
      {/* Status icon */}
      <div className="mt-0.5 flex-shrink-0">{getStatusIcon(task.status)}</div>

      {/* Task info */}
      <div className="flex-1 space-y-1">
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">
            {task.agentName}
          </span>
          {task.status === "running" && (
            <span className="text-xs text-blue-600">Running</span>
          )}
          {task.status === "completed" && (
            <span className="text-xs text-green-600">✓ Completed</span>
          )}
        </div>
        <p className={cn("text-sm", getStatusColor(task.status))}>
          {task.title}
        </p>
      </div>
    </div>
  );
};

export default memo(ExecutionPlanRenderer);

