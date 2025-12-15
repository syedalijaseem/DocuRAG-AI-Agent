/**
 * TypewriterMessage - Renders message content with typewriter animation
 */
import { useTypewriter } from "../hooks/useTypewriter";

interface TypewriterMessageProps {
  content: string;
  animate: boolean; // Only animate the most recent message
  speed?: number;
}

export function TypewriterMessage({
  content,
  animate,
  speed = 15,
}: TypewriterMessageProps) {
  const { displayedText, isTyping } = useTypewriter(
    animate ? content : "",
    speed
  );

  // If not animating, show full content immediately
  const textToShow = animate ? displayedText : content;

  return (
    <div className="whitespace-pre-wrap">
      {textToShow}
      {animate && isTyping && (
        <span className="inline-block w-2 h-4 ml-1 bg-[#14b8a6] animate-pulse" />
      )}
    </div>
  );
}
