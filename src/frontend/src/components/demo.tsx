import { useState } from "react";
import { PromptInputBox } from "@/components/ui/ai-prompt-box";
import { askQuestion, type AskResponse } from "@/lib/api";
import { motion, AnimatePresence } from "framer-motion";
import { X, Bot, Code2, Copy, Check } from "lucide-react";

const DemoOne = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [response, setResponse] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleSend = async (message: string, files?: File[]) => {
    console.log('Message:', message);
    console.log('Files:', files);
    
    setIsLoading(true);
    setResponse(null);
    setError(null);
    
    try {
      // Extract the actual question (remove prefixes like [Search: ...])
      const question = message.replace(/^\[(?:Search|Think|Canvas):\s*(.+)\]$/, '$1').trim() || message;
      const apiResponse = await askQuestion(question);
      setResponse(apiResponse);
      console.log('Answer:', apiResponse.answer);
      console.log('Message:', apiResponse.message);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get answer from server';
      setError(errorMessage);
      console.error('Error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const clearResponse = () => {
    setResponse(null);
    setError(null);
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const jsonPayload = response ? JSON.stringify(response, null, 2) : null;

  return (
    <div className="flex w-full h-screen justify-center items-center bg-[radial-gradient(125%_125%_at_50%_101%,rgba(245,87,2,1)_10.5%,rgba(245,120,2,1)_16%,rgba(245,140,2,1)_17.5%,rgba(245,170,100,1)_25%,rgba(238,174,202,1)_40%,rgba(202,179,214,1)_65%,rgba(148,201,233,1)_100%)]">
      <div className="p-4 w-[500px] flex flex-col gap-4 max-h-[90vh] overflow-y-auto [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
        <PromptInputBox 
          onSend={handleSend} 
          isLoading={isLoading}
        />
        
        <AnimatePresence>
          {(response || error) && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="flex flex-col gap-3"
            >
              {/* Answer Card */}
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className={`relative rounded-2xl p-4 backdrop-blur-sm border ${
                  error
                    ? 'bg-red-900/30 border-red-500/50 text-red-100'
                    : 'bg-white/10 border-white/20 text-white'
                } shadow-xl`}
              >
                <button
                  onClick={clearResponse}
                  className="absolute top-3 right-3 p-1.5 rounded-full hover:bg-white/10 transition-colors z-10"
                >
                  <X className="h-4 w-4" />
                </button>
                <div className="flex items-start gap-3 pr-8">
                  <Bot className="h-5 w-5 mt-0.5 flex-shrink-0" />
                  <div className="flex-1">
                    <p className="text-sm font-medium mb-2">
                      {error ? 'Error' : 'Answer'}
                    </p>
                    <p className="text-sm whitespace-pre-wrap leading-relaxed">
                      {error || response?.answer}
                    </p>
                  </div>
                </div>
              </motion.div>

              {/* JSON Payload Card */}
              {response && jsonPayload && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.1 }}
                  className="relative rounded-2xl p-4 bg-black/40 border border-white/10 text-white shadow-xl backdrop-blur-sm"
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <Code2 className="h-4 w-4 text-purple-300" />
                      <p className="text-xs font-medium text-gray-300 uppercase tracking-wider">
                        JSON Response
                      </p>
                    </div>
                    <button
                      onClick={() => copyToClipboard(jsonPayload)}
                      className="p-1.5 rounded-lg hover:bg-white/10 transition-colors group"
                      title="Copy JSON"
                    >
                      {copied ? (
                        <Check className="h-4 w-4 text-green-400" />
                      ) : (
                        <Copy className="h-4 w-4 text-gray-400 group-hover:text-white" />
                      )}
                    </button>
                  </div>
                  <pre className="text-xs font-mono text-gray-300 overflow-x-auto [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
                    <code>{jsonPayload}</code>
                  </pre>
                </motion.div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export { DemoOne };

