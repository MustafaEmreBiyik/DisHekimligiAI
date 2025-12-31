"use client";

/**
 * Chat Message Component
 * ======================
 * Displays individual chat messages with different styles for roles.
 */

import React from "react";

interface ChatMessageProps {
  role: "student" | "patient" | "system";
  content: string;
  timestamp?: Date;
  isTyping?: boolean;
}

export default function ChatMessage({
  role,
  content,
  timestamp,
  isTyping,
}: ChatMessageProps) {
  // Typing indicator
  if (isTyping) {
    return (
      <div className="flex justify-start">
        <div className="bg-gray-100 rounded-2xl rounded-bl-md px-4 py-3 max-w-[80%]">
          <div className="flex items-center gap-1">
            <div
              className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
              style={{ animationDelay: "0ms" }}
            ></div>
            <div
              className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
              style={{ animationDelay: "150ms" }}
            ></div>
            <div
              className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
              style={{ animationDelay: "300ms" }}
            ></div>
          </div>
        </div>
      </div>
    );
  }

  // System message (info/announcements)
  if (role === "system") {
    return (
      <div className="flex justify-center">
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl px-4 py-3 max-w-[90%] text-center">
          <div
            className="text-sm text-gray-700 whitespace-pre-wrap"
            dangerouslySetInnerHTML={{
              __html: content
                .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
                .replace(/\n/g, "<br />"),
            }}
          />
        </div>
      </div>
    );
  }

  // Student message (right side, blue)
  if (role === "student") {
    return (
      <div className="flex justify-end">
        <div className="bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-2xl rounded-br-md px-4 py-3 max-w-[80%] shadow-md">
          <p className="text-sm whitespace-pre-wrap">{content}</p>
          {timestamp && (
            <p className="text-xs text-blue-200 mt-1 text-right">
              {timestamp.toLocaleTimeString("tr-TR", {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </p>
          )}
        </div>
      </div>
    );
  }

  // Patient message (left side, gray)
  return (
    <div className="flex justify-start">
      <div className="flex items-start gap-2">
        {/* Patient avatar */}
        <div className="w-8 h-8 bg-gradient-to-br from-gray-200 to-gray-300 rounded-full flex items-center justify-center flex-shrink-0">
          <span className="text-sm">🧑</span>
        </div>

        <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-md px-4 py-3 max-w-[80%] shadow-sm">
          <p className="text-xs text-gray-500 font-medium mb-1">Hasta</p>
          <p className="text-sm text-gray-800 whitespace-pre-wrap">{content}</p>
          {timestamp && (
            <p className="text-xs text-gray-400 mt-1">
              {timestamp.toLocaleTimeString("tr-TR", {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
