import ReactMarkdown from "react-markdown";

const INTENT_META = {
  check_balance: { emoji: "🏦", label: "Balance" },
  send_money: { emoji: "💸", label: "Transfer" },
  check_weather: { emoji: "🌤", label: "Weather" },
  currency_conversion: { emoji: "💱", label: "Exchange" },
  knowledge_base: { emoji: "📚", label: "Knowledge" },
  unknown: { emoji: "💬", label: "Chat" },
};

export default function ChatBubble({ message }) {
  const isUser = message.role === "user";

  return (
    <div className={`bubble-wrapper ${isUser ? "bubble-user" : "bubble-assistant"}`}>
      {!isUser && (
        <div className="avatar">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/></svg>
        </div>
      )}

      <div className={`bubble ${isUser ? "bubble-user-inner" : "bubble-assistant-inner"}`}>
        <div className="bubble-text">
          {isUser ? (
            <p>{message.content}</p>
          ) : (
            <>
              <ReactMarkdown>{message.content}</ReactMarkdown>
              {message.data && message.data.type === 'balance' && (
                <div className="structured-card">
                  <div className="balance-header">
                    <span className="balance-label">Available Balance</span>
                    <span className="balance-trend">{message.data.trend}</span>
                  </div>
                  <div className="balance-amount">{message.data.currency} {message.data.balance.toLocaleString('en-US', {minimumFractionDigits: 2})}</div>
                  <div className="balance-chart">
                    {message.data.history && message.data.history.map((val, idx) => (
                      <div key={idx} className={`chart-bar ${idx === message.data.history.length - 1 ? 'latest' : ''}`} style={{ height: `${(val / 50000) * 100}%` }}></div>
                    ))}
                  </div>
                  <div className="chart-label">Last 7 days performance</div>
                </div>
              )}
              {message.data && message.data.type === 'transaction' && (
                <div className="structured-card transaction-card">
                  <div className="tx-header">
                    <div className="tx-icon">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                    </div>
                    Transaction Successful
                  </div>
                  <div className="tx-row">
                    <span className="tx-label">Recipient</span>
                    <span className="tx-val">{message.data.recipient}</span>
                  </div>
                  <div className="tx-row">
                    <span className="tx-label">Amount</span>
                    <span className="tx-val amount">{message.data.currency} {message.data.amount.toLocaleString('en-US', {minimumFractionDigits: 2})}</span>
                  </div>
                  <div className="tx-row">
                    <span className="tx-label">Reference</span>
                    <span className="tx-val" style={{fontFamily: "monospace", fontSize: "11px", color: "var(--text-secondary)"}}>{message.data.reference}</span>
                  </div>
                  <button className="tx-btn" onClick={() => alert("Downloading receipt PDF...")}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="12" y1="18" x2="12" y2="12"></line><line x1="9" y1="15" x2="12" y2="18"></line><line x1="15" y1="15" x2="12" y2="18"></line></svg>
                    Download PDF Receipt
                  </button>
                </div>
              )}
            </>
          )}
        </div>

        <div className="bubble-time">
          {new Date(message.timestamp).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </div>
      </div>

      {isUser && (
        <div className="avatar avatar-user">
          <img src="https://i.pravatar.cc/150?u=a042581f4e29026704d" alt="User" />
        </div>
      )}
    </div>
  );
}
