/**
 * LoadingStages - Show progress feedback during query processing
 */
import { useState, useEffect } from "react";
import { Search, FileText, Sparkles } from "lucide-react";

const stages = [
  { icon: Search, text: "Searching your documents...", delay: 0 },
  { icon: FileText, text: "Analyzing relevant passages...", delay: 2000 },
  { icon: Sparkles, text: "Generating response...", delay: 4000 },
];

export function LoadingStages() {
  const [currentStage, setCurrentStage] = useState(0);

  useEffect(() => {
    const timers = stages.map((stage, index) =>
      setTimeout(() => setCurrentStage(index), stage.delay)
    );
    return () => timers.forEach(clearTimeout);
  }, []);

  const { icon: Icon, text } = stages[currentStage];

  return (
    <div className="flex items-center gap-3 text-[#737373] dark:text-[#a0a0a0]">
      <Icon size={20} className="animate-pulse" />
      <span className="animate-pulse">{text}</span>
    </div>
  );
}

export function MessageSkeleton() {
  return (
    <div className="space-y-2 animate-pulse">
      <div className="h-4 bg-[#e8e8e8] dark:bg-[#3a3a3a] rounded w-3/4"></div>
      <div className="h-4 bg-[#e8e8e8] dark:bg-[#3a3a3a] rounded w-full"></div>
      <div className="h-4 bg-[#e8e8e8] dark:bg-[#3a3a3a] rounded w-5/6"></div>
      <div className="h-4 bg-[#e8e8e8] dark:bg-[#3a3a3a] rounded w-2/3"></div>
    </div>
  );
}
