/**
 * MessageSkeleton - Shimmer loading placeholder for message content
 */

export function MessageSkeleton() {
  return (
    <div className="space-y-3 animate-pulse">
      {/* First paragraph skeleton */}
      <div className="space-y-2">
        <div className="h-4 bg-[#e8e8e8] dark:bg-[#3a3a3a] rounded w-[90%]" />
        <div className="h-4 bg-[#e8e8e8] dark:bg-[#3a3a3a] rounded w-[75%]" />
        <div className="h-4 bg-[#e8e8e8] dark:bg-[#3a3a3a] rounded w-[85%]" />
      </div>

      {/* Second paragraph skeleton */}
      <div className="space-y-2 pt-2">
        <div className="h-4 bg-[#e8e8e8] dark:bg-[#3a3a3a] rounded w-[70%]" />
        <div className="h-4 bg-[#e8e8e8] dark:bg-[#3a3a3a] rounded w-[80%]" />
        <div className="h-4 bg-[#e8e8e8] dark:bg-[#3a3a3a] rounded w-[60%]" />
      </div>

      {/* Sources skeleton */}
      <div className="pt-3 flex gap-2">
        <div className="h-6 w-24 bg-[#e8e8e8] dark:bg-[#3a3a3a] rounded" />
        <div className="h-6 w-20 bg-[#e8e8e8] dark:bg-[#3a3a3a] rounded" />
        <div className="h-6 w-28 bg-[#e8e8e8] dark:bg-[#3a3a3a] rounded" />
      </div>
    </div>
  );
}
