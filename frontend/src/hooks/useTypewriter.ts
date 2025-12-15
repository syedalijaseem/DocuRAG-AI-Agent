/**
 * useTypewriter - Animate text word-by-word for a typewriter effect
 */
import { useState, useEffect } from "react";

export function useTypewriter(text: string, speed: number = 20) {
  const [displayedText, setDisplayedText] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    if (!text) {
      setDisplayedText("");
      setIsComplete(true);
      return;
    }

    setIsTyping(true);
    setIsComplete(false);
    setDisplayedText("");

    const words = text.split(" ");
    let currentIndex = 0;

    const interval = setInterval(() => {
      if (currentIndex < words.length) {
        setDisplayedText(
          (prev) => prev + (prev ? " " : "") + words[currentIndex]
        );
        currentIndex++;
      } else {
        setIsTyping(false);
        setIsComplete(true);
        clearInterval(interval);
      }
    }, speed);

    return () => clearInterval(interval);
  }, [text, speed]);

  return { displayedText, isTyping, isComplete };
}
