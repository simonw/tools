/**
 * llm-lib.js - A unified JavaScript browser library for LLM providers
 * Supports OpenAI, Anthropic (Claude), and Google Gemini
 *
 * Usage:
 *   const llm = new LLM({ provider: 'openai', apiKey: 'sk-...', model: 'gpt-4o' });
 *
 *   // Non-streaming
 *   const response = await llm.prompt('Hello!');
 *
 *   // Streaming
 *   for await (const chunk of llm.stream('Hello!')) {
 *     console.log(chunk);
 *   }
 */

class LLM {
  /**
   * @param {Object} options
   * @param {string} options.provider - 'openai' | 'anthropic' | 'gemini'
   * @param {string} options.apiKey - API key for the provider
   * @param {string} [options.model] - Model to use (defaults per provider)
   * @param {string} [options.systemPrompt] - Optional system prompt
   */
  constructor(options) {
    this.provider = options.provider;
    this.apiKey = options.apiKey;
    this.systemPrompt = options.systemPrompt || null;

    // Set default models per provider
    const defaultModels = {
      openai: 'gpt-4o-mini',
      anthropic: 'claude-3-5-haiku-latest',
      gemini: 'gemini-2.0-flash'
    };
    this.model = options.model || defaultModels[this.provider];

    // Get the appropriate adapter
    this.adapter = LLM.adapters[this.provider];
    if (!this.adapter) {
      throw new Error(`Unknown provider: ${this.provider}. Supported: openai, anthropic, gemini`);
    }
  }

  /**
   * Send a prompt and get a complete response (non-streaming)
   * @param {string|Array} input - Either a string (user message) or array of messages
   * @returns {Promise<string>} The response text
   */
  async prompt(input) {
    const messages = this._normalizeInput(input);
    return this.adapter.prompt(this, messages);
  }

  /**
   * Send a prompt and stream the response
   * @param {string|Array} input - Either a string (user message) or array of messages
   * @yields {string} Text chunks as they arrive
   */
  async *stream(input) {
    const messages = this._normalizeInput(input);
    yield* this.adapter.stream(this, messages);
  }

  /**
   * Normalize input to message array format
   * @private
   */
  _normalizeInput(input) {
    if (typeof input === 'string') {
      return [{ role: 'user', content: input }];
    }
    return input;
  }
}

// Provider adapters
LLM.adapters = {
  /**
   * OpenAI adapter (Chat Completions API)
   */
  openai: {
    async prompt(llm, messages) {
      const body = {
        model: llm.model,
        messages: llm.systemPrompt
          ? [{ role: 'system', content: llm.systemPrompt }, ...messages]
          : messages
      };

      const response = await fetch('https://api.openai.com/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${llm.apiKey}`
        },
        body: JSON.stringify(body)
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(`OpenAI API error: ${error.error?.message || response.statusText}`);
      }

      const data = await response.json();
      return data.choices[0].message.content;
    },

    async *stream(llm, messages) {
      const body = {
        model: llm.model,
        messages: llm.systemPrompt
          ? [{ role: 'system', content: llm.systemPrompt }, ...messages]
          : messages,
        stream: true
      };

      const response = await fetch('https://api.openai.com/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${llm.apiKey}`
        },
        body: JSON.stringify(body)
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(`OpenAI API error: ${error.error?.message || response.statusText}`);
      }

      yield* parseSSE(response, (data) => {
        if (data === '[DONE]') return null;
        const parsed = JSON.parse(data);
        return parsed.choices[0]?.delta?.content || '';
      });
    }
  },

  /**
   * Anthropic (Claude) adapter
   */
  anthropic: {
    async prompt(llm, messages) {
      const body = {
        model: llm.model,
        max_tokens: 4096,
        messages: messages.map(m => ({
          role: m.role === 'system' ? 'user' : m.role,
          content: m.content
        }))
      };

      if (llm.systemPrompt) {
        body.system = llm.systemPrompt;
      }

      const response = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': llm.apiKey,
          'anthropic-version': '2023-06-01',
          'anthropic-dangerous-direct-browser-access': 'true'
        },
        body: JSON.stringify(body)
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(`Anthropic API error: ${error.error?.message || response.statusText}`);
      }

      const data = await response.json();
      return data.content[0].text;
    },

    async *stream(llm, messages) {
      const body = {
        model: llm.model,
        max_tokens: 4096,
        stream: true,
        messages: messages.map(m => ({
          role: m.role === 'system' ? 'user' : m.role,
          content: m.content
        }))
      };

      if (llm.systemPrompt) {
        body.system = llm.systemPrompt;
      }

      const response = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': llm.apiKey,
          'anthropic-version': '2023-06-01',
          'anthropic-dangerous-direct-browser-access': 'true'
        },
        body: JSON.stringify(body)
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(`Anthropic API error: ${error.error?.message || response.statusText}`);
      }

      yield* parseSSE(response, (data) => {
        const parsed = JSON.parse(data);
        if (parsed.type === 'content_block_delta') {
          return parsed.delta?.text || '';
        }
        return '';
      });
    }
  },

  /**
   * Google Gemini adapter
   */
  gemini: {
    async prompt(llm, messages) {
      // Convert messages to Gemini format
      const contents = messages.map(m => ({
        role: m.role === 'assistant' ? 'model' : 'user',
        parts: [{ text: m.content }]
      }));

      // If there's a system prompt, prepend it as a user message
      if (llm.systemPrompt) {
        contents.unshift({
          role: 'user',
          parts: [{ text: llm.systemPrompt }]
        });
        // Add a model acknowledgment to maintain alternating pattern
        contents.splice(1, 0, {
          role: 'model',
          parts: [{ text: 'Understood.' }]
        });
      }

      const url = `https://generativelanguage.googleapis.com/v1beta/models/${llm.model}:generateContent`;

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-goog-api-key': llm.apiKey
        },
        body: JSON.stringify({ contents })
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(`Gemini API error: ${error.error?.message || response.statusText}`);
      }

      const data = await response.json();
      return data.candidates[0].content.parts[0].text;
    },

    async *stream(llm, messages) {
      // Convert messages to Gemini format
      const contents = messages.map(m => ({
        role: m.role === 'assistant' ? 'model' : 'user',
        parts: [{ text: m.content }]
      }));

      // If there's a system prompt, prepend it
      if (llm.systemPrompt) {
        contents.unshift({
          role: 'user',
          parts: [{ text: llm.systemPrompt }]
        });
        contents.splice(1, 0, {
          role: 'model',
          parts: [{ text: 'Understood.' }]
        });
      }

      const url = `https://generativelanguage.googleapis.com/v1beta/models/${llm.model}:streamGenerateContent?alt=sse`;

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-goog-api-key': llm.apiKey
        },
        body: JSON.stringify({ contents })
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(`Gemini API error: ${error.error?.message || response.statusText}`);
      }

      yield* parseSSE(response, (data) => {
        const parsed = JSON.parse(data);
        return parsed.candidates?.[0]?.content?.parts?.[0]?.text || '';
      });
    }
  }
};

/**
 * Parse Server-Sent Events from a fetch response
 * @param {Response} response - Fetch response with SSE body
 * @param {Function} extractor - Function to extract text from each data line
 * @yields {string} Extracted text chunks
 */
async function* parseSSE(response, extractor) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop(); // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data.trim()) {
            try {
              const text = extractor(data);
              if (text) yield text;
            } catch (e) {
              // Skip malformed data
            }
          }
        }
      }
    }

    // Process any remaining buffer
    if (buffer.startsWith('data: ')) {
      const data = buffer.slice(6);
      if (data.trim()) {
        try {
          const text = extractor(data);
          if (text) yield text;
        } catch (e) {
          // Skip malformed data
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

// Export for ES modules
export { LLM };
