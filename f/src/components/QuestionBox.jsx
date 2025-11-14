import React, { useState, useEffect, useCallback, useRef, memo } from 'react';
import { SendHorizonal, Maximize2, X, Copy, Check } from 'lucide-react';
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";

const ChatInput = memo(({ prompt, setPrompt, isEnabled, isLoading, onSubmit }) => (
  <form onSubmit={onSubmit} className="flex items-center space-x-2 w-full text-gray-100">
    <input
      type="text"
      placeholder={isEnabled ? 'Ask a question...' : 'Upload CSV first.'}
      value={prompt}
      onChange={(e) => setPrompt(e.target.value)}
      disabled={!isEnabled || isLoading}
      className="grow px-3 py-2 border rounded-full text-gray-400"
    />

    <button
      type="submit"
      disabled={!isEnabled || isLoading || !prompt.trim()}
      className={`p-2 rounded-full transition ${
        !isEnabled || isLoading || !prompt.trim()
          ? "bg-gray-500 cursor-not-allowed opacity-50"
          : "bg-indigo-600 hover:bg-indigo-700 cursor-pointer"
      } text-white`}
    >
      {isLoading ? (
        <span className="animate-pulse px-2">Thinking...</span>
      ) : (
        <SendHorizonal />
      )}
    </button>
  </form>
));

/* ✅ Modern Copy Button Component */
const CopyButton = ({ text }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch (err) {
      console.error("Copy failed:", err);
    }
  };

  return (
    <button
      onClick={handleCopy}
      className={`absolute top-2 right-7 transition text-gray-400 hover:text-indigo-600 ${
        copied ? "text-green-500" : ""
      }`}
      title={copied ? "Copied!" : "Copy response"}
    >
      {copied ? (
        <Check className="w-4 h-4 animate-bounce" />
      ) : (
        <Copy className="w-4 h-4 text-gray-900" />
      )}
    </button>
  );
};

const QuestionBox = ({ isEnabled, chatHistory, setChatHistory, sessionId }) => {
  const [prompt, setPrompt] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const chatEndRef = useRef(null);

  const scrollToBottom = useCallback(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => scrollToBottom(), [chatHistory, scrollToBottom]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!isEnabled || isLoading || !prompt.trim()) return;

    const userMessage = prompt.trim();
    setPrompt('');
    setChatHistory((prev) => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    try {
      const formData = new FormData();
      formData.append('session_id', sessionId);
      formData.append('query', userMessage);

      const res = await fetch('https://chatcsv-production-c7d2.up.railway.app/chat', {
        method: 'POST',
        body: formData,
      });

      const contentType = res.headers.get('content-type') || '';

      if (contentType.includes('text/event-stream')) {
        // Handle streaming response (SSE)
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let done = false;

        // Placeholder for LLM response
        setChatHistory((prev) => [...prev, { role: 'ai', content: '' }]);

        while (!done) {
          const { value, done: readerDone } = await reader.read();
          done = readerDone;
          const chunk = decoder.decode(value);

          chunk.split('\n\n').forEach((line) => {
            if (line.startsWith('data:')) {
              try {
                const payload = JSON.parse(line.replace('data:', '').trim());
                if (payload.delta) {
                  setChatHistory((prev) => {
                    const updated = [...prev];
                    const last = updated[updated.length - 1];
                    const delta = payload.delta.trim();
                    // Avoid duplication
                    if (!last.content.endsWith(delta)) {
                      last.content += delta;
                    }
                    return updated;
                  });
                }
              } catch (err) {
                console.warn('Bad JSON chunk:', line);
              }
            }
          });
        }
      } else {
        // Normal (non-streaming) response
        const data = await res.json();

        // ✅ Clean and simplify LLM response
        const cleanResponse = (data.answer || '(No response)')
          .replace(/(\d+\.\d{4,})/g, (m) => Number(m).toFixed(2)) // Round decimals
          .replace(/(\n\s*){2,}/g, '\n') // Collapse blank lines
          .replace(/(\*\*?)([\w\s]+:)\1?/g, '**$2**') // Normalize bold labels
          .replace(/\b(The average .*?)(?=\1)/gi, '') // Remove repeated phrasing
          .trim();

        setChatHistory((prev) => [
          ...prev,
          { role: 'ai', content: cleanResponse },
        ]);
      }
    } catch (err) {
      console.error(err);
      setChatHistory((prev) => [
        ...prev,
        { role: 'ai', content: `⚠️ Error: ${err.message}` },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="p-6 bg-gray-800 dark:bg-gray-800 rounded-xl shadow-2xl flex flex-col h-full">
      <h2 className="text-2xl font-extrabold text-indigo-600 mb-4 flex items-center justify-between">
        <span>3. Ask Questions</span>
        <button className="cursor-pointer" onClick={() => setIsExpanded(true)}>
          <Maximize2 />
        </button>
      </h2>

      <div className="grow max-h-90 overflow-y-auto p-3 mb-4 border rounded bg-gray-800 space-y-4">
        {chatHistory.map((msg, i) => (
          <div key={i} className={`flex px-6 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`${msg.role === 'user'
                ? 'bg-indigo-500 text-white'
                : 'bg-gray-100 text-gray-800'} 
                p-3 rounded-xl max-w-3/4 m-4 relative`}
            >
              {msg.role === 'ai' && <CopyButton text={msg.content} />}

              <div className="max-h-60 overflow-y-auto pr-6 mr-7">
                <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
                  {msg.content}
                </ReactMarkdown>
              </div>
            </div>
          </div>
        ))}
        <div ref={chatEndRef} />
      </div>

      <ChatInput
        prompt={prompt}
        setPrompt={setPrompt}
        isEnabled={isEnabled}
        isLoading={isLoading}
        onSubmit={handleSubmit}
      />

      {!isEnabled && <p className="mt-2 text-red-500 text-xs italic">Upload a CSV to enable chat.</p>}

      {/* Expanded Modal */}
      {isExpanded && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl w-[95%] md:w-[80%] lg:w-[70%] h-[85%] flex flex-col relative">
            <div className="flex items-center justify-between p-4 border-b">
              <h3 className="text-lg font-bold text-indigo-600">Expanded Chat</h3>
              <button className="text-gray-200 cursor-pointer" onClick={() => setIsExpanded(false)}>
                <X />
              </button>
            </div>
            <div className="grow overflow-y-auto p-4">
              {chatHistory.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div
                    className={`${msg.role === 'user'
                      ? 'bg-indigo-500 text-white'
                      : 'bg-gray-100 text-gray-800'} 
                      p-3 rounded-xl max-w-3/4 m-4 relative`}
                  >
                    {msg.role === 'ai' && <CopyButton text={msg.content} />}
                    <div className="max-h-60 overflow-y-auto pr-6 mr-7">
                      <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
                        {msg.content}
                      </ReactMarkdown>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <div className="p-4 border-t">
              <ChatInput
                prompt={prompt}
                setPrompt={setPrompt}
                isEnabled={isEnabled}
                isLoading={isLoading}
                onSubmit={handleSubmit}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default QuestionBox;
