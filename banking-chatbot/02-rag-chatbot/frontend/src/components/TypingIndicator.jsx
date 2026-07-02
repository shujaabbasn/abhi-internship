/**
 * TypingIndicator — animated three-dot indicator shown while the backend responds.
 */
export default function TypingIndicator() {
  return (
    <div className="bubble-wrapper bubble-assistant">
      <div className="avatar">
        <span>A</span>
      </div>
      <div className="bubble bubble-assistant-inner typing-bubble">
        <span className="dot" />
        <span className="dot" />
        <span className="dot" />
      </div>
    </div>
  );
}
