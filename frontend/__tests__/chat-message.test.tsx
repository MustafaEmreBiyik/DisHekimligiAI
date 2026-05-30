import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ChatMessage from "@/components/ChatMessage";

describe("ChatMessage", () => {
  it("renders student message on the correct side with content", () => {
    render(<ChatMessage role="student" content="Hastanın alerjilerini kontrol ediyorum." />);
    expect(screen.getByText("Hastanın alerjilerini kontrol ediyorum.")).toBeInTheDocument();
  });

  it("renders patient message with 'Hasta' label", () => {
    render(<ChatMessage role="patient" content="Penisiline alerjim var." />);
    expect(screen.getByText("Hasta")).toBeInTheDocument();
    expect(screen.getByText("Penisiline alerjim var.")).toBeInTheDocument();
  });

  it("renders typing indicator without text content", () => {
    const { container } = render(<ChatMessage role="patient" content="" isTyping />);
    const dots = container.querySelectorAll(".animate-bounce");
    expect(dots.length).toBe(3);
    expect(screen.queryByText("Hasta")).not.toBeInTheDocument();
  });

  it("renders system message in centre with formatted content", () => {
    render(<ChatMessage role="system" content="Vaka başarıyla tamamlandı." />);
    expect(screen.getByText(/Vaka başarıyla tamamlandı/)).toBeInTheDocument();
  });

  it("does not render timestamp when prop is omitted", () => {
    const { container } = render(
      <ChatMessage role="student" content="Test" />
    );
    const timeElements = container.querySelectorAll("p.text-xs");
    expect(timeElements.length).toBe(0);
  });
});
