import { useState, useRef, useEffect } from 'react';
import { Search, Sparkles, GraduationCap, X, Send, Loader2 } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { supabase } from '@/integrations/supabase/client';

interface SearchResult {
  type: 'experiment' | 'protocol' | 'order' | 'scholar';
  id: string;
  title: string;
  description?: string;
  url?: string;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export const AISearchBar = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [searchMode, setSearchMode] = useState<'lab' | 'scholar'>('lab');
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [summary, setSummary] = useState('');
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [followUpQuery, setFollowUpQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSearch = async () => {
    if (!query.trim()) return;
    
    setIsSearching(true);
    setIsOpen(true);
    setResults([]);
    setSummary('');
    setChatMessages([{ role: 'user', content: query }]);

    try {
      const { data, error } = await supabase.functions.invoke('ai-search', {
        body: { query, mode: searchMode }
      });

      if (error) throw error;

      setResults(data.results || []);
      setSummary(data.summary || '');
      setChatMessages(prev => [...prev, { role: 'assistant', content: data.summary || 'No results found.' }]);
    } catch (error) {
      console.error('Search error:', error);
      setSummary('An error occurred while searching. Please try again.');
      setChatMessages(prev => [...prev, { role: 'assistant', content: 'An error occurred while searching. Please try again.' }]);
    } finally {
      setIsSearching(false);
    }
  };

  const handleFollowUp = async () => {
    if (!followUpQuery.trim()) return;

    const newMessages = [...chatMessages, { role: 'user' as const, content: followUpQuery }];
    setChatMessages(newMessages);
    setFollowUpQuery('');
    setIsSearching(true);

    try {
      const { data, error } = await supabase.functions.invoke('ai-search', {
        body: { 
          query: followUpQuery, 
          mode: searchMode,
          context: newMessages,
          previousResults: results
        }
      });

      if (error) throw error;

      if (data.results) setResults(data.results);
      setChatMessages(prev => [...prev, { role: 'assistant', content: data.summary || 'I couldn\'t find more information.' }]);
    } catch (error) {
      console.error('Follow-up error:', error);
      setChatMessages(prev => [...prev, { role: 'assistant', content: 'An error occurred. Please try again.' }]);
    } finally {
      setIsSearching(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const clearSearch = () => {
    setQuery('');
    setResults([]);
    setSummary('');
    setChatMessages([]);
    setIsOpen(false);
  };

  return (
    <div className="relative w-full" ref={dropdownRef}>
      <div className="relative flex items-center">
        <Search className="absolute left-3 h-4 w-4 text-muted-foreground" />
        <Input
          ref={inputRef}
          type="text"
          placeholder={searchMode === 'lab' ? "Search experiments, protocols, orders..." : "Search Google Scholar..."}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => query && setIsOpen(true)}
          className="pl-9 pr-24"
        />
        <div className="absolute right-2 flex items-center gap-1">
          {query && (
            <Button variant="ghost" size="icon" className="h-6 w-6" onClick={clearSearch}>
              <X className="h-3 w-3" />
            </Button>
          )}
          <Button
            variant={searchMode === 'lab' ? 'default' : 'outline'}
            size="sm"
            className="h-6 px-2 text-xs"
            onClick={() => setSearchMode('lab')}
          >
            <Sparkles className="h-3 w-3 mr-1" />
            Lab
          </Button>
          <Button
            variant={searchMode === 'scholar' ? 'default' : 'outline'}
            size="sm"
            className="h-6 px-2 text-xs"
            onClick={() => setSearchMode('scholar')}
          >
            <GraduationCap className="h-3 w-3 mr-1" />
            Scholar
          </Button>
        </div>
      </div>

      {isOpen && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-popover border border-border rounded-lg shadow-lg z-50 max-h-[500px] overflow-hidden flex flex-col">
          <ScrollArea className="flex-1 max-h-[350px]">
            <div className="p-4 space-y-4">
              {isSearching && chatMessages.length <= 1 ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-primary" />
                  <span className="ml-2 text-muted-foreground">
                    {searchMode === 'scholar' ? 'Searching academic papers...' : 'Searching your lab data...'}
                  </span>
                </div>
              ) : chatMessages.length > 0 ? (
                <div className="space-y-3">
                  {chatMessages.map((msg, idx) => (
                    <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                      <div className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                        msg.role === 'user' 
                          ? 'bg-primary text-primary-foreground' 
                          : 'bg-muted text-foreground'
                      }`}>
                        {msg.content}
                      </div>
                    </div>
                  ))}
                  {isSearching && (
                    <div className="flex justify-start">
                      <div className="bg-muted rounded-lg px-3 py-2">
                        <Loader2 className="h-4 w-4 animate-spin" />
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-center text-muted-foreground py-4">
                  Type a query and press Enter to search
                </p>
              )}

              {results.length > 0 && (
                <div className="border-t border-border pt-3">
                  <p className="text-xs font-medium text-muted-foreground mb-2">
                    {searchMode === 'scholar' ? 'Related Papers' : 'Related Items'}
                  </p>
                  <div className="space-y-2">
                    {results.map((result, idx) => (
                      <div 
                        key={idx} 
                        className="p-2 rounded-md hover:bg-muted cursor-pointer transition-colors"
                        onClick={() => {
                          if (result.url) window.open(result.url, '_blank');
                        }}
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-xs px-1.5 py-0.5 rounded bg-secondary text-secondary-foreground capitalize">
                            {result.type}
                          </span>
                          <span className="text-sm font-medium truncate">{result.title}</span>
                        </div>
                        {result.description && (
                          <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                            {result.description}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </ScrollArea>

          {chatMessages.length > 0 && (
            <div className="border-t border-border p-3">
              <div className="flex items-center gap-2">
                <Input
                  placeholder="Ask a follow-up question..."
                  value={followUpQuery}
                  onChange={(e) => setFollowUpQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleFollowUp()}
                  className="flex-1"
                />
                <Button size="icon" onClick={handleFollowUp} disabled={isSearching}>
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
