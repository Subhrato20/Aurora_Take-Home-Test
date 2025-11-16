import { useState } from 'react';
import { PromptInputBox } from '@/components/ui/ai-prompt-box';
import { askQuestion, type AskResponse } from '@/lib/api';
import { Loader2, Bot, User, AlertCircle } from 'lucide-react';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  error?: string;
}

export const QAChat = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const handleSend = async (message: string, _files?: File[]) => {
    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: message,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      // Extract the actual question (remove prefixes like [Search: ...])
      const question = message.replace(/^\[(?:Search|Think|Canvas):\s*(.+)\]$/, '$1').trim() || message;

      const response: AskResponse = await askQuestion(question);

      // Add assistant response
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.answer,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred';

      // Add error message
      const errorMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        error: errorMessage,
      };

      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen w-full bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Header */}
      <div className="border-b border-white/10 bg-black/20 backdrop-blur-sm p-4">
        <h1 className="text-2xl font-bold text-white">November Q&A Service</h1>
        <p className="text-sm text-white/70 mt-1">Ask questions about November messages</p>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-white/50">
              <Bot className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p className="text-lg">Start a conversation by asking a question</p>
              <p className="text-sm mt-2">Try: "When is Layla's next trip?" or "How many cars does Layla have?"</p>
            </div>
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex gap-3 ${
              message.role === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            {message.role === 'assistant' && (
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center">
                <Bot className="h-5 w-5 text-white" />
              </div>
            )}

            <div
              className={`max-w-[70%] rounded-2xl px-4 py-3 ${
                message.role === 'user'
                  ? 'bg-white text-black'
                  : message.error
                  ? 'bg-red-900/30 text-red-200 border border-red-500/50'
                  : 'bg-white/10 text-white backdrop-blur-sm'
              }`}
            >
              {message.error ? (
                <div className="flex items-center gap-2">
                  <AlertCircle className="h-4 w-4" />
                  <span>{message.error}</span>
                </div>
              ) : (
                <p className="whitespace-pre-wrap">{message.content}</p>
              )}
            </div>

            {message.role === 'user' && (
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center">
                <User className="h-5 w-5 text-white" />
              </div>
            )}
          </div>

        ))}

        {isLoading && (
          <div className="flex gap-3 justify-start">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center">
              <Bot className="h-5 w-5 text-white" />
            </div>
            <div className="bg-white/10 text-white backdrop-blur-sm rounded-2xl px-4 py-3">
              <div className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Thinking...</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="border-t border-white/10 bg-black/20 backdrop-blur-sm p-4">
        <PromptInputBox
          onSend={handleSend}
          isLoading={isLoading}
          placeholder="Ask a question about November messages..."
        />
      </div>
    </div>
  );
};

