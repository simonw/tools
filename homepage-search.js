const scriptEl = document.querySelector('script[data-tool-search]');
const toolsJsonUrl = scriptEl ? new URL('tools.json', scriptEl.src).href : new URL('tools.json', window.location.href).href;

const ready = (callback) => {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', callback);
  } else {
    callback();
  }
};

const formatDate = (value) => {
  if (!value) {
    return '';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
};

ready(() => {
  const heading = Array.from(document.querySelectorAll('h1')).find((element) =>
    element.textContent?.trim().toLowerCase().includes('tools.simonwillison.net'),
  );

  if (!heading) {
    return;
  }

  const style = document.createElement('style');
  style.textContent = `
    .tool-search-container {
      margin: 1.5rem 0 2rem;
      padding: 1rem 1.25rem;
      border-radius: 0.85rem;
      border: 1px solid #e1e1e1;
      background: linear-gradient(180deg, #ffffff 0%, #f7f8ff 100%);
      box-shadow: 0 8px 24px rgba(23, 43, 99, 0.08);
    }
    .tool-search-container:focus-within {
      border-color: #5b6ef5;
      box-shadow: 0 12px 32px rgba(47, 64, 179, 0.15);
    }
    .tool-search-label {
      position: absolute;
      width: 1px;
      height: 1px;
      padding: 0;
      margin: -1px;
      overflow: hidden;
      clip: rect(0, 0, 0, 0);
      border: 0;
    }
    .tool-search-input-wrapper {
      position: relative;
    }
    #tool-search-input {
      width: 100%;
      box-sizing: border-box;
      border-radius: 0.75rem;
      border: 1px solid #cfd2ff;
      background-color: rgba(255, 255, 255, 0.9);
      padding: 0.75rem 1rem;
      font-size: 1rem;
      line-height: 1.5;
      transition: border-color 0.2s ease, box-shadow 0.2s ease;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    #tool-search-input:focus {
      outline: none;
      border-color: #4454f7;
      box-shadow: 0 0 0 3px rgba(68, 84, 247, 0.2);
      background-color: #fff;
    }
    #tool-search-input:disabled {
      color: #6b6f80;
      background-color: rgba(250, 250, 255, 0.8);
    }
    .tool-search-hint {
      margin: 0.5rem 0 0;
      font-size: 0.875rem;
      color: #4a4f67;
    }
    .tool-search-results {
      list-style: none;
      padding: 0;
      margin: 0.75rem 0 0;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }
    .tool-search-option {
      border-radius: 0.75rem;
      border: 1px solid #d8dcff;
      background: #ffffff;
      transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.1s ease;
    }
    .tool-search-option.active {
      border-color: #4454f7;
      box-shadow: 0 6px 18px rgba(68, 84, 247, 0.18);
      transform: translateY(-1px);
    }
    .tool-search-option-link {
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
      text-decoration: none;
      color: inherit;
      padding: 0.75rem 0.9rem 0.8rem;
    }
    .tool-search-option-title {
      font-weight: 600;
      font-size: 1rem;
      color: #242847;
    }
    .tool-search-option-description {
      font-size: 0.92rem;
      color: #3e4261;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .tool-search-option-meta {
      font-size: 0.82rem;
      color: #6b6f80;
    }
    .tool-search-empty {
      padding: 0.9rem 1rem;
      border-radius: 0.75rem;
      border: 1px dashed #c4c8ff;
      background: rgba(228, 232, 255, 0.5);
      font-size: 0.95rem;
      color: #3e4261;
    }
    .tool-search-status {
      position: absolute;
      width: 1px;
      height: 1px;
      padding: 0;
      margin: -1px;
      overflow: hidden;
      clip: rect(0, 0, 0, 0);
      border: 0;
    }
    @media (max-width: 640px) {
      .tool-search-container {
        margin: 1.25rem 0 1.75rem;
        padding: 0.85rem 0.75rem;
      }
      #tool-search-input {
        font-size: 1.05rem;
        padding: 0.8rem 0.9rem;
      }
      .tool-search-option-link {
        padding: 0.7rem 0.8rem 0.75rem;
      }
    }
  `;
  document.head.appendChild(style);

  const container = document.createElement('section');
  container.className = 'tool-search-container';
  container.setAttribute('role', 'search');

  const label = document.createElement('label');
  label.className = 'tool-search-label';
  label.setAttribute('for', 'tool-search-input');
  label.textContent = 'Search tools';

  const inputWrapper = document.createElement('div');
  inputWrapper.className = 'tool-search-input-wrapper';

  const input = document.createElement('input');
  input.type = 'search';
  input.id = 'tool-search-input';
  input.placeholder = 'Loading tools…';
  input.autocomplete = 'off';
  input.setAttribute('aria-autocomplete', 'list');
  input.setAttribute('aria-controls', 'tool-search-results');
  input.setAttribute('aria-expanded', 'false');
  input.setAttribute('aria-haspopup', 'listbox');
  input.setAttribute('role', 'combobox');
  input.disabled = true;

  const hint = document.createElement('p');
  hint.className = 'tool-search-hint';
  hint.textContent = 'Start typing to search all tools. Press “/” to focus the search.';

  const results = document.createElement('ul');
  results.id = 'tool-search-results';
  results.className = 'tool-search-results';
  results.setAttribute('role', 'listbox');
  results.setAttribute('aria-label', 'Tool suggestions');
  results.hidden = true;

  const status = document.createElement('div');
  status.className = 'tool-search-status';
  status.setAttribute('role', 'status');
  status.setAttribute('aria-live', 'polite');

  inputWrapper.appendChild(input);
  container.appendChild(label);
  container.appendChild(inputWrapper);
  container.appendChild(hint);
  container.appendChild(results);
  container.appendChild(status);

  heading.insertAdjacentElement('afterend', container);

  let tools = [];
  let currentMatches = [];
  let activeIndex = -1;

  const updateStatus = (message) => {
    status.textContent = message || '';
  };

  const clearResults = () => {
    results.innerHTML = '';
    results.hidden = true;
    input.setAttribute('aria-expanded', 'false');
    input.removeAttribute('aria-activedescendant');
    currentMatches = [];
    activeIndex = -1;
  };

  const highlightOption = (index) => {
    const options = results.querySelectorAll('.tool-search-option');
    options.forEach((option) => {
      option.classList.remove('active');
      option.setAttribute('aria-selected', 'false');
    });

    if (index < 0 || index >= options.length) {
      input.removeAttribute('aria-activedescendant');
      activeIndex = -1;
      return;
    }

    const option = options[index];
    option.classList.add('active');
    option.setAttribute('aria-selected', 'true');
    input.setAttribute('aria-activedescendant', option.id);
    option.scrollIntoView({ block: 'nearest' });
    activeIndex = index;
  };

  const navigateToTool = (tool, { newTab = false } = {}) => {
    if (!tool) {
      return;
    }
    const destination = tool.url || `${tool.slug}.html`;
    if (newTab) {
      window.open(destination, '_blank', 'noopener');
    } else {
      window.location.assign(destination);
    }
  };

  const renderMatches = (matches, query) => {
    results.innerHTML = '';
    currentMatches = matches.map((entry) => entry.tool);
    activeIndex = -1;

    if (!currentMatches.length) {
      const empty = document.createElement('li');
      empty.className = 'tool-search-empty';
      empty.textContent = `No tools match “${query}”.`;
      empty.setAttribute('role', 'option');
      empty.setAttribute('aria-selected', 'false');
      results.appendChild(empty);
      results.hidden = false;
      input.setAttribute('aria-expanded', 'true');
      updateStatus(`No tools match ${query}.`);
      return;
    }

    currentMatches.forEach((tool, index) => {
      const option = document.createElement('li');
      option.className = 'tool-search-option';
      option.id = `tool-search-option-${index}`;
      option.setAttribute('role', 'option');
      option.setAttribute('aria-selected', 'false');

      const link = document.createElement('a');
      link.className = 'tool-search-option-link';
      link.href = tool.url || `${tool.slug}.html`;
      link.tabIndex = -1;

      const title = document.createElement('span');
      title.className = 'tool-search-option-title';
      title.textContent = tool.title || tool.slug;

      link.appendChild(title);

      if (tool.description) {
        const description = document.createElement('span');
        description.className = 'tool-search-option-description';
        description.textContent = tool.description;
        link.appendChild(description);
      }

      const metaBits = [];
      if (tool.updated) {
        metaBits.push(`Updated ${formatDate(tool.updated)}`);
      } else if (tool.created) {
        metaBits.push(`Created ${formatDate(tool.created)}`);
      }

      if (metaBits.length) {
        const meta = document.createElement('span');
        meta.className = 'tool-search-option-meta';
        meta.textContent = metaBits.join(' • ');
        link.appendChild(meta);
      }

      link.addEventListener('mousedown', (event) => {
        event.preventDefault();
      });

      link.addEventListener('click', (event) => {
        event.preventDefault();
        navigateToTool(tool, { newTab: event.metaKey || event.ctrlKey });
      });

      option.appendChild(link);
      results.appendChild(option);
    });

    results.hidden = false;
    input.setAttribute('aria-expanded', 'true');
    updateStatus(`${currentMatches.length} result${currentMatches.length === 1 ? '' : 's'} available.`);
  };

  const performSearch = () => {
    const query = input.value.trim();
    if (!query) {
      clearResults();
      updateStatus('Search cleared.');
      return;
    }

    const lowered = query.toLowerCase();
    const terms = lowered.split(/\s+/).filter(Boolean);

    const ranked = tools
      .map((tool) => {
        const fields = [tool.title, tool.description, tool.slug]
          .filter(Boolean)
          .join(' ')
          .toLowerCase();

        if (!terms.every((term) => fields.includes(term))) {
          return null;
        }

        const title = (tool.title || '').toLowerCase();
        const slug = (tool.slug || '').toLowerCase();

        let score = 100;
        if (title.startsWith(lowered)) {
          score = 0;
        } else if (slug.startsWith(lowered)) {
          score = 10;
        } else if (title.includes(lowered)) {
          score = 20;
        } else if (slug.includes(lowered)) {
          score = 30;
        }

        const updated = tool.updated ? Date.parse(tool.updated) || 0 : 0;

        return { tool, score, updated };
      })
      .filter(Boolean)
      .sort((a, b) => {
        if (a.score !== b.score) {
          return a.score - b.score;
        }
        return b.updated - a.updated;
      })
      .slice(0, 12);

    renderMatches(ranked, query);
  };

  input.addEventListener('input', () => {
    if (!tools.length) {
      return;
    }
    performSearch();
  });

  input.addEventListener('keydown', (event) => {
    if (!currentMatches.length && !['Escape', 'Tab'].includes(event.key)) {
      return;
    }

    if (event.key === 'ArrowDown') {
      event.preventDefault();
      if (!results.hidden) {
        const nextIndex = (activeIndex + 1) % currentMatches.length;
        highlightOption(nextIndex);
      } else {
        performSearch();
      }
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      const nextIndex = activeIndex <= 0 ? currentMatches.length - 1 : activeIndex - 1;
      highlightOption(nextIndex);
    } else if (event.key === 'Enter') {
      if (!currentMatches.length) {
        return;
      }
      event.preventDefault();
      const chosen = activeIndex >= 0 ? currentMatches[activeIndex] : currentMatches[0];
      navigateToTool(chosen, { newTab: event.metaKey || event.ctrlKey });
    } else if (event.key === 'Escape') {
      clearResults();
      input.blur();
    }
  });

  input.addEventListener('focus', () => {
    if (input.value && currentMatches.length) {
      results.hidden = false;
      input.setAttribute('aria-expanded', 'true');
    }
  });

  input.addEventListener('blur', () => {
    window.setTimeout(() => {
      clearResults();
    }, 120);
  });

  document.addEventListener('click', (event) => {
    if (!container.contains(event.target)) {
      clearResults();
    }
  });

  document.addEventListener('keydown', (event) => {
    if (event.key !== '/' || event.altKey || event.ctrlKey || event.metaKey) {
      return;
    }

    const target = event.target;
    const tagName = target?.tagName?.toLowerCase();
    const isEditable = target?.isContentEditable;
    if (tagName === 'input' || tagName === 'textarea' || tagName === 'select' || isEditable) {
      return;
    }

    event.preventDefault();
    input.focus();
    input.select();
  });

  fetch(toolsJsonUrl, { cache: 'no-cache' })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`Failed to load tools.json: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      if (!Array.isArray(data)) {
        throw new Error('tools.json did not return an array');
      }
      tools = data;
      input.placeholder = 'Search tools…';
      input.disabled = false;
      updateStatus(`${tools.length} tools available to search.`);
      if (input === document.activeElement && input.value) {
        performSearch();
      }
    })
    .catch((error) => {
      console.error(error);
      input.placeholder = 'Search unavailable';
      input.disabled = true;
      updateStatus('Search unavailable.');
    });
});
