/**
 * CSS Grid Lanes Polyfill
 * 
 * Polyfills the new `display: grid-lanes` CSS feature for browsers
 * that don't support it natively. Based on the WebKit implementation
 * described at: https://webkit.org/blog/17660/introducing-css-grid-lanes/
 * 
 * Features supported:
 * - display: grid-lanes
 * - grid-template-columns / grid-template-rows for lane definition
 * - gap, column-gap, row-gap
 * - item-tolerance for placement sensitivity
 * - Spanning items (grid-column: span N)
 * - Explicit placement (grid-column: N / M)
 * - Responsive auto-fill/auto-fit with minmax()
 * - Both waterfall (columns) and brick (rows) layouts
 * 
 * @version 1.0.0
 * @license MIT
 */

(function(global) {
  'use strict';

  const POLYFILL_NAME = 'GridLanesPolyfill';
  const POLYFILL_ATTR = 'data-grid-lanes-polyfilled';
  const DEFAULT_TOLERANCE = 16; // ~1em in pixels

  // Store parsed CSS rules for grid-lanes containers
  const parsedGridLanesRules = new Map();

  /**
   * Check if the browser natively supports display: grid-lanes
   */
  function supportsGridLanes() {
    if (typeof CSS === 'undefined' || !CSS.supports) {
      return false;
    }
    return CSS.supports('display', 'grid-lanes');
  }

  /**
   * Parse a CSS length value to pixels
   */
  function parseLengthToPixels(value, containerSize, fontSize = 16, rootFontSize = 16) {
    if (!value || value === 'auto' || value === 'none') return null;
    
    const num = parseFloat(value);
    if (isNaN(num)) return null;

    if (value.endsWith('px')) return num;
    if (value.endsWith('rem')) return num * rootFontSize;
    if (value.endsWith('em')) return num * fontSize;
    if (value.endsWith('ch')) return num * fontSize * 0.5; // Approximate
    if (value.endsWith('lh')) return num * fontSize * 1.2; // Approximate line-height
    if (value.endsWith('%')) return (num / 100) * containerSize;
    if (value.endsWith('vw')) return (num / 100) * window.innerWidth;
    if (value.endsWith('vh')) return (num / 100) * window.innerHeight;
    if (value.endsWith('vmin')) return (num / 100) * Math.min(window.innerWidth, window.innerHeight);
    if (value.endsWith('vmax')) return (num / 100) * Math.max(window.innerWidth, window.innerHeight);
    if (value.endsWith('fr')) return null; // Handled separately
    
    // Unitless number treated as pixels
    if (!isNaN(num) && value === String(num)) return num;
    
    return null;
  }

  /**
   * Parse minmax() function
   */
  function parseMinMax(value) {
    const match = value.match(/minmax\(\s*([^,]+)\s*,\s*([^)]+)\s*\)/);
    if (!match) return null;
    return {
      min: match[1].trim(),
      max: match[2].trim()
    };
  }

  /**
   * Parse repeat() function
   */
  function parseRepeat(value) {
    const match = value.match(/repeat\(\s*([^,]+)\s*,\s*(.+)\s*\)/);
    if (!match) return null;
    return {
      count: match[1].trim(),
      pattern: match[2].trim()
    };
  }

  /**
   * Calculate lane sizes from grid-template-columns/rows
   */
  function calculateLaneSizes(template, containerSize, gap, fontSize, rootFontSize) {
    if (!template || template === 'none' || template === 'auto') {
      return null;
    }

    const availableSpace = containerSize;
    let lanes = [];
    let totalFr = 0;
    let fixedSpace = 0;

    // Parse the template
    const tokens = tokenizeTemplate(template);
    
    for (const token of tokens) {
      // Handle repeat()
      const repeatInfo = parseRepeat(token);
      if (repeatInfo) {
        const { count, pattern } = repeatInfo;
        const patternTokens = tokenizeTemplate(pattern);
        
        if (count === 'auto-fill' || count === 'auto-fit') {
          // Calculate how many repetitions fit
          let minSize = 0;
          let hasFlexible = false;
          
          for (const pt of patternTokens) {
            const minmax = parseMinMax(pt);
            if (minmax) {
              const minVal = parseLengthToPixels(minmax.min, containerSize, fontSize, rootFontSize);
              if (minmax.min === 'max-content' || minmax.min === 'min-content') {
                minSize += 100; // Fallback estimate
              } else if (minVal !== null) {
                minSize += minVal;
              }
              if (minmax.max.endsWith('fr')) {
                hasFlexible = true;
              }
            } else {
              const size = parseLengthToPixels(pt, containerSize, fontSize, rootFontSize);
              if (size !== null) {
                minSize += size;
              } else if (pt.endsWith('fr')) {
                hasFlexible = true;
                minSize += 100; // Minimum fallback for fr units
              }
            }
          }
          
          // Calculate repetitions
          const patternCount = patternTokens.length;
          const gapCount = patternCount - 1;
          const minPatternSize = minSize + (gapCount * gap);
          
          let reps = Math.max(1, Math.floor((availableSpace + gap) / (minPatternSize + gap)));
          
          // Expand pattern
          for (let i = 0; i < reps; i++) {
            for (const pt of patternTokens) {
              const minmax = parseMinMax(pt);
              if (minmax) {
                const minVal = parseLengthToPixels(minmax.min, containerSize, fontSize, rootFontSize);
                const maxVal = minmax.max.endsWith('fr') 
                  ? { fr: parseFloat(minmax.max) }
                  : parseLengthToPixels(minmax.max, containerSize, fontSize, rootFontSize);
                
                lanes.push({
                  min: minVal || 0,
                  max: maxVal,
                  size: 0
                });
                
                if (typeof maxVal === 'object' && maxVal.fr) {
                  totalFr += maxVal.fr;
                }
                fixedSpace += minVal || 0;
              } else if (pt.endsWith('fr')) {
                const fr = parseFloat(pt);
                lanes.push({ min: 0, max: { fr }, size: 0 });
                totalFr += fr;
              } else {
                const size = parseLengthToPixels(pt, containerSize, fontSize, rootFontSize) || 0;
                lanes.push({ min: size, max: size, size });
                fixedSpace += size;
              }
            }
          }
        } else {
          // Fixed repeat count
          const reps = parseInt(count, 10);
          for (let i = 0; i < reps; i++) {
            for (const pt of patternTokens) {
              const size = parseLengthToPixels(pt, containerSize, fontSize, rootFontSize);
              if (pt.endsWith('fr')) {
                const fr = parseFloat(pt);
                lanes.push({ min: 0, max: { fr }, size: 0 });
                totalFr += fr;
              } else if (size !== null) {
                lanes.push({ min: size, max: size, size });
                fixedSpace += size;
              }
            }
          }
        }
        continue;
      }

      // Handle minmax()
      const minmax = parseMinMax(token);
      if (minmax) {
        const minVal = parseLengthToPixels(minmax.min, containerSize, fontSize, rootFontSize);
        const maxVal = minmax.max.endsWith('fr')
          ? { fr: parseFloat(minmax.max) }
          : parseLengthToPixels(minmax.max, containerSize, fontSize, rootFontSize);
        
        lanes.push({ min: minVal || 0, max: maxVal, size: 0 });
        if (typeof maxVal === 'object' && maxVal.fr) {
          totalFr += maxVal.fr;
        }
        fixedSpace += minVal || 0;
        continue;
      }

      // Handle fr units
      if (token.endsWith('fr')) {
        const fr = parseFloat(token);
        lanes.push({ min: 0, max: { fr }, size: 0 });
        totalFr += fr;
        continue;
      }

      // Handle fixed sizes
      const size = parseLengthToPixels(token, containerSize, fontSize, rootFontSize);
      if (size !== null) {
        lanes.push({ min: size, max: size, size });
        fixedSpace += size;
      }
    }

    // Calculate final sizes
    const totalGaps = Math.max(0, lanes.length - 1) * gap;
    const flexSpace = Math.max(0, availableSpace - fixedSpace - totalGaps);
    const frUnit = totalFr > 0 ? flexSpace / totalFr : 0;

    for (const lane of lanes) {
      if (typeof lane.max === 'object' && lane.max.fr) {
        lane.size = Math.max(lane.min, frUnit * lane.max.fr);
      } else if (typeof lane.max === 'number') {
        lane.size = Math.min(lane.max, Math.max(lane.min, lane.min));
      } else {
        lane.size = lane.min;
      }
    }

    return lanes.map(l => l.size);
  }

  /**
   * Tokenize a grid template string
   */
  function tokenizeTemplate(template) {
    const tokens = [];
    let current = '';
    let parenDepth = 0;

    for (let i = 0; i < template.length; i++) {
      const char = template[i];
      
      if (char === '(') {
        parenDepth++;
        current += char;
      } else if (char === ')') {
        parenDepth--;
        current += char;
      } else if (char === ' ' && parenDepth === 0) {
        if (current.trim()) {
          tokens.push(current.trim());
        }
        current = '';
      } else {
        current += char;
      }
    }

    if (current.trim()) {
      tokens.push(current.trim());
    }

    return tokens;
  }

  /**
   * Get computed styles for grid-lanes properties
   */
  function getGridLanesStyles(element) {
    const computed = window.getComputedStyle(element);
    const fontSize = parseFloat(computed.fontSize) || 16;
    const rootFontSize = parseFloat(window.getComputedStyle(document.documentElement).fontSize) || 16;

    // Get parsed CSS rules for this element (from raw CSS parsing)
    const parsedRules = parsedGridLanesRules.get(element) || {};

    // Get gap values - prefer parsed rules, fall back to computed
    let gap = parsedRules['gap'] || computed.gap || computed.gridGap || '0px';
    let columnGap = parsedRules['column-gap'] || computed.columnGap || computed.gridColumnGap || gap;
    let rowGap = parsedRules['row-gap'] || computed.rowGap || computed.gridRowGap || gap;

    // Handle combined gap values like "24px 16px"
    if (gap.includes(' ')) {
      const [rg, cg] = gap.split(/\s+/);
      if (!parsedRules['row-gap']) rowGap = rg;
      if (!parsedRules['column-gap']) columnGap = cg;
    }

    // Parse item-tolerance (custom property or default)
    let tolerance = DEFAULT_TOLERANCE;
    const toleranceValue = parsedRules['--item-tolerance'] ||
                          computed.getPropertyValue('--item-tolerance').trim() ||
                          computed.getPropertyValue('item-tolerance').trim();
    if (toleranceValue) {
      const parsed = parseLengthToPixels(toleranceValue, 0, fontSize, rootFontSize);
      if (parsed !== null) tolerance = parsed;
    }

    // Get grid template - prefer parsed rules since computed styles won't work for non-grid elements
    const gridTemplateColumns = parsedRules['grid-template-columns'] || computed.gridTemplateColumns;
    const gridTemplateRows = parsedRules['grid-template-rows'] || computed.gridTemplateRows;

    return {
      gridTemplateColumns,
      gridTemplateRows,
      columnGap: parseLengthToPixels(String(columnGap).split(' ')[0], 0, fontSize, rootFontSize) || 0,
      rowGap: parseLengthToPixels(String(rowGap).split(' ')[0], 0, fontSize, rootFontSize) || 0,
      fontSize,
      rootFontSize,
      tolerance
    };
  }

  /**
   * Get item placement properties
   */
  function getItemStyles(element) {
    const computed = window.getComputedStyle(element);
    const gridColumn = computed.gridColumn || computed.gridColumnStart;
    const gridRow = computed.gridRow || computed.gridRowStart;

    let columnSpan = 1;
    let columnStart = null;
    let columnEnd = null;
    let rowSpan = 1;
    let rowStart = null;
    let rowEnd = null;

    // Parse grid-column
    if (gridColumn && gridColumn !== 'auto') {
      const spanMatch = gridColumn.match(/span\s+(\d+)/);
      if (spanMatch) {
        columnSpan = parseInt(spanMatch[1], 10);
      } else if (gridColumn.includes('/')) {
        const [start, end] = gridColumn.split('/').map(s => s.trim());
        columnStart = parseInt(start, 10);
        columnEnd = parseInt(end, 10);
        if (!isNaN(columnStart) && !isNaN(columnEnd)) {
          columnSpan = Math.abs(columnEnd - columnStart);
        }
      } else {
        const num = parseInt(gridColumn, 10);
        if (!isNaN(num)) {
          columnStart = num;
        }
      }
    }

    // Parse grid-row
    if (gridRow && gridRow !== 'auto') {
      const spanMatch = gridRow.match(/span\s+(\d+)/);
      if (spanMatch) {
        rowSpan = parseInt(spanMatch[1], 10);
      } else if (gridRow.includes('/')) {
        const [start, end] = gridRow.split('/').map(s => s.trim());
        rowStart = parseInt(start, 10);
        rowEnd = parseInt(end, 10);
        if (!isNaN(rowStart) && !isNaN(rowEnd)) {
          rowSpan = Math.abs(rowEnd - rowStart);
        }
      } else {
        const num = parseInt(gridRow, 10);
        if (!isNaN(num)) {
          rowStart = num;
        }
      }
    }

    return {
      columnSpan,
      columnStart,
      columnEnd,
      rowSpan,
      rowStart,
      rowEnd
    };
  }

  /**
   * Main Grid Lanes layout class
   */
  class GridLanesLayout {
    constructor(container, options = {}) {
      this.container = container;
      this.options = options;
      this.isVertical = true; // true = waterfall (columns), false = brick (rows)
      this.lanes = [];
      this.laneHeights = [];
      this.resizeObserver = null;
      this.mutationObserver = null;
      
      this.init();
    }

    init() {
      // Mark as polyfilled
      this.container.setAttribute(POLYFILL_ATTR, 'true');
      
      // Set up container styles
      this.container.style.position = 'relative';
      this.container.style.display = 'block';
      
      // Initial layout
      this.layout();
      
      // Set up observers
      this.setupObservers();
    }

    setupObservers() {
      // Debounce layout calls to avoid excessive recalculations
      let layoutTimeout = null;
      const debouncedLayout = () => {
        if (layoutTimeout) clearTimeout(layoutTimeout);
        layoutTimeout = setTimeout(() => this.layout(), 16);
      };

      // Resize observer for responsive layouts AND child size changes
      this.resizeObserver = new ResizeObserver((entries) => {
        // Check if it's the container or a child that resized
        for (const entry of entries) {
          if (entry.target === this.container || entry.target.parentElement === this.container) {
            debouncedLayout();
            break;
          }
        }
      });
      this.resizeObserver.observe(this.container);

      // Observe all direct children for size changes
      for (const child of this.container.children) {
        if (child.nodeType === Node.ELEMENT_NODE) {
          this.resizeObserver.observe(child);
        }
      }

      // Mutation observer for dynamic content
      this.mutationObserver = new MutationObserver((mutations) => {
        let shouldRelayout = false;
        for (const mutation of mutations) {
          if (mutation.type === 'childList') {
            // Observe new children
            for (const node of mutation.addedNodes) {
              if (node.nodeType === Node.ELEMENT_NODE) {
                this.resizeObserver.observe(node);
                // Also watch for images in new nodes
                this.observeImages(node);
              }
            }
            shouldRelayout = true;
          } else if (mutation.type === 'attributes' && mutation.attributeName === 'style') {
            shouldRelayout = true;
          }
        }
        if (shouldRelayout) {
          debouncedLayout();
        }
      });
      this.mutationObserver.observe(this.container, {
        childList: true,
        subtree: false,
        attributes: true,
        attributeFilter: ['style', 'class']
      });

      // Observe all images for load events
      this.observeImages(this.container);
    }

    observeImages(root) {
      const images = root.querySelectorAll('img');
      for (const img of images) {
        if (!img.complete) {
          img.addEventListener('load', () => this.layout(), { once: true });
          img.addEventListener('error', () => this.layout(), { once: true });
        }
      }
    }

    layout() {
      const styles = getGridLanesStyles(this.container);
      const containerRect = this.container.getBoundingClientRect();
      
      // Determine direction based on which template is defined
      const hasColumns = styles.gridTemplateColumns && 
                        styles.gridTemplateColumns !== 'none' &&
                        !styles.gridTemplateColumns.startsWith('auto');
      const hasRows = styles.gridTemplateRows && 
                     styles.gridTemplateRows !== 'none' &&
                     !styles.gridTemplateRows.startsWith('auto');
      
      this.isVertical = hasColumns || !hasRows;
      
      // Calculate lane sizes
      if (this.isVertical) {
        this.lanes = calculateLaneSizes(
          styles.gridTemplateColumns,
          containerRect.width,
          styles.columnGap,
          styles.fontSize,
          styles.rootFontSize
        ) || [containerRect.width];
      } else {
        this.lanes = calculateLaneSizes(
          styles.gridTemplateRows,
          containerRect.height,
          styles.rowGap,
          styles.fontSize,
          styles.rootFontSize
        ) || [containerRect.height];
      }

      // Initialize lane positions (heights for vertical, widths for horizontal)
      this.laneHeights = new Array(this.lanes.length).fill(0);
      
      // Get all direct children
      const items = Array.from(this.container.children).filter(
        el => el.nodeType === Node.ELEMENT_NODE && 
             window.getComputedStyle(el).display !== 'none'
      );

      // Separate explicitly placed items from auto-placed items
      const explicitItems = [];
      const autoItems = [];
      
      for (const item of items) {
        const itemStyles = getItemStyles(item);
        if (this.isVertical && itemStyles.columnStart !== null) {
          explicitItems.push({ element: item, styles: itemStyles });
        } else if (!this.isVertical && itemStyles.rowStart !== null) {
          explicitItems.push({ element: item, styles: itemStyles });
        } else {
          autoItems.push({ element: item, styles: itemStyles });
        }
      }

      // Place explicitly positioned items first
      for (const { element, styles: itemStyles } of explicitItems) {
        this.placeExplicitItem(element, itemStyles, styles);
      }

      // Place auto-positioned items
      for (const { element, styles: itemStyles } of autoItems) {
        this.placeAutoItem(element, itemStyles, styles);
      }

      // Set container height
      const containerHeight = Math.max(...this.laneHeights);
      this.container.style.minHeight = `${containerHeight}px`;
    }

    placeExplicitItem(element, itemStyles, containerStyles) {
      const gap = this.isVertical ? containerStyles.columnGap : containerStyles.rowGap;
      const crossGap = this.isVertical ? containerStyles.rowGap : containerStyles.columnGap;
      
      let laneIndex;
      let span;
      
      if (this.isVertical) {
        // Handle negative indices
        laneIndex = itemStyles.columnStart;
        if (laneIndex < 0) {
          laneIndex = this.lanes.length + laneIndex + 1;
        }
        laneIndex = Math.max(0, Math.min(laneIndex - 1, this.lanes.length - 1));
        span = itemStyles.columnSpan;
      } else {
        laneIndex = itemStyles.rowStart;
        if (laneIndex < 0) {
          laneIndex = this.lanes.length + laneIndex + 1;
        }
        laneIndex = Math.max(0, Math.min(laneIndex - 1, this.lanes.length - 1));
        span = itemStyles.rowSpan;
      }

      // Calculate position
      let position = 0;
      for (let i = 0; i < laneIndex; i++) {
        position += this.lanes[i] + gap;
      }

      // Calculate width (for spanning)
      let size = 0;
      const endLane = Math.min(laneIndex + span, this.lanes.length);
      for (let i = laneIndex; i < endLane; i++) {
        size += this.lanes[i];
        if (i < endLane - 1) size += gap;
      }

      // Get the tallest lane in the span
      let maxHeight = 0;
      for (let i = laneIndex; i < endLane; i++) {
        maxHeight = Math.max(maxHeight, this.laneHeights[i]);
      }

      // Position the element
      element.style.position = 'absolute';
      
      if (this.isVertical) {
        element.style.left = `${position}px`;
        element.style.top = `${maxHeight > 0 ? maxHeight + crossGap : 0}px`;
        element.style.width = `${size}px`;
        element.style.height = '';
      } else {
        element.style.top = `${position}px`;
        element.style.left = `${maxHeight > 0 ? maxHeight + crossGap : 0}px`;
        element.style.height = `${size}px`;
        element.style.width = '';
      }

      // Update lane heights
      const itemRect = element.getBoundingClientRect();
      const itemSize = this.isVertical ? itemRect.height : itemRect.width;
      const newHeight = maxHeight + (maxHeight > 0 ? crossGap : 0) + itemSize;
      
      for (let i = laneIndex; i < endLane; i++) {
        this.laneHeights[i] = newHeight;
      }
    }

    placeAutoItem(element, itemStyles, containerStyles) {
      const gap = this.isVertical ? containerStyles.columnGap : containerStyles.rowGap;
      const crossGap = this.isVertical ? containerStyles.rowGap : containerStyles.columnGap;
      const tolerance = containerStyles.tolerance;
      const span = this.isVertical ? itemStyles.columnSpan : itemStyles.rowSpan;

      // Find the best lane(s) considering tolerance
      let bestLane = 0;
      let bestHeight = Infinity;

      for (let i = 0; i <= this.lanes.length - span; i++) {
        // Get the max height across the span
        let maxHeight = 0;
        for (let j = i; j < i + span; j++) {
          maxHeight = Math.max(maxHeight, this.laneHeights[j]);
        }

        // Use tolerance to determine if this is meaningfully better
        if (bestHeight - maxHeight > tolerance) {
          bestHeight = maxHeight;
          bestLane = i;
        } else if (Math.abs(maxHeight - bestHeight) <= tolerance && i < bestLane) {
          // Within tolerance, prefer earlier lane for reading order
          bestHeight = maxHeight;
          bestLane = i;
        }
      }

      // Calculate position
      let position = 0;
      for (let i = 0; i < bestLane; i++) {
        position += this.lanes[i] + gap;
      }

      // Calculate size (for spanning)
      let size = 0;
      const endLane = Math.min(bestLane + span, this.lanes.length);
      for (let i = bestLane; i < endLane; i++) {
        size += this.lanes[i];
        if (i < endLane - 1) size += gap;
      }

      // Position the element
      element.style.position = 'absolute';
      
      if (this.isVertical) {
        element.style.left = `${position}px`;
        element.style.top = `${bestHeight > 0 ? bestHeight + crossGap : 0}px`;
        element.style.width = `${size}px`;
        element.style.height = '';
      } else {
        element.style.top = `${position}px`;
        element.style.left = `${bestHeight > 0 ? bestHeight + crossGap : 0}px`;
        element.style.height = `${size}px`;
        element.style.width = '';
      }

      // Update lane heights
      const itemRect = element.getBoundingClientRect();
      const itemSize = this.isVertical ? itemRect.height : itemRect.width;
      const newHeight = bestHeight + (bestHeight > 0 ? crossGap : 0) + itemSize;
      
      for (let i = bestLane; i < endLane; i++) {
        this.laneHeights[i] = newHeight;
      }
    }

    destroy() {
      if (this.resizeObserver) {
        this.resizeObserver.disconnect();
      }
      if (this.mutationObserver) {
        this.mutationObserver.disconnect();
      }
      
      this.container.removeAttribute(POLYFILL_ATTR);
      this.container.style.position = '';
      this.container.style.display = '';
      this.container.style.minHeight = '';
      
      // Reset item styles
      for (const item of this.container.children) {
        if (item.nodeType === Node.ELEMENT_NODE) {
          item.style.position = '';
          item.style.left = '';
          item.style.top = '';
          item.style.width = '';
          item.style.height = '';
        }
      }
    }

    refresh() {
      this.layout();
    }
  }

  /**
   * Parse CSS properties from a CSS block text
   */
  function parseCSSProperties(cssBlock) {
    const props = {};
    // Extract property: value pairs
    const propRegex = /([\w-]+)\s*:\s*([^;]+);?/g;
    let match;
    while ((match = propRegex.exec(cssBlock)) !== null) {
      props[match[1].trim()] = match[2].trim();
    }
    return props;
  }

  /**
   * Find and process all grid-lanes containers
   */
  function processStyleSheets() {
    const containers = new Set();
    const gridLanesSelectors = new Set();

    // Check inline styles (look at the raw style attribute)
    const allElements = document.querySelectorAll('[style*="grid-lanes"]');
    for (const el of allElements) {
      const styleAttr = el.getAttribute('style') || '';
      if (/display\s*:\s*grid-lanes/i.test(styleAttr)) {
        containers.add(el);
        // Parse and store inline style properties
        const props = parseCSSProperties(styleAttr);
        if (!parsedGridLanesRules.has(el)) {
          parsedGridLanesRules.set(el, props);
        }
      }
    }

    // Check style elements directly and parse raw CSS
    const styleElements = document.querySelectorAll('style');
    for (const styleEl of styleElements) {
      const cssText = styleEl.textContent || '';
      // Match selectors with display: grid-lanes and capture the full block
      const regex = /([^{}]+)\{([^}]*display\s*:\s*grid-lanes[^}]*)\}/gi;
      let match;
      while ((match = regex.exec(cssText)) !== null) {
        const selectorText = match[1].trim();
        const cssBlock = match[2];

        // Handle comma-separated selectors
        const selectors = selectorText.split(',').map(s => s.trim());

        for (const selector of selectors) {
          if (!selector) continue;
          gridLanesSelectors.add(selector);

          // Parse properties from the CSS block
          const props = parseCSSProperties(cssBlock);

          try {
            const elements = document.querySelectorAll(selector);
            for (const el of elements) {
              containers.add(el);
              // Store parsed rules for this element (merge if exists)
              if (parsedGridLanesRules.has(el)) {
                Object.assign(parsedGridLanesRules.get(el), props);
              } else {
                parsedGridLanesRules.set(el, { ...props });
              }
            }
          } catch (e) {
            // Invalid selector, skip
          }
        }
      }
    }

    // Also check stylesheet rules (may work for some browsers)
    for (const sheet of document.styleSheets) {
      try {
        const rules = sheet.cssRules || sheet.rules;
        if (!rules) continue;

        for (const rule of rules) {
          if (rule.cssText && /display\s*:\s*grid-lanes/i.test(rule.cssText)) {
            if (rule.selectorText && !gridLanesSelectors.has(rule.selectorText)) {
              gridLanesSelectors.add(rule.selectorText);
              const props = parseCSSProperties(rule.cssText);
              try {
                const elements = document.querySelectorAll(rule.selectorText);
                for (const el of elements) {
                  containers.add(el);
                  if (!parsedGridLanesRules.has(el)) {
                    parsedGridLanesRules.set(el, props);
                  }
                }
              } catch (e) {
                // Invalid selector, skip
              }
            }
          }
        }
      } catch (e) {
        // Cross-origin stylesheets will throw
        console.warn(`${POLYFILL_NAME}: Could not access stylesheet:`, e);
      }
    }

    return containers;
  }

  /**
   * Initialize the polyfill
   */
  function init(options = {}) {
    // Check if native support exists
    if (supportsGridLanes() && !options.force) {
      console.log(`${POLYFILL_NAME}: Native support detected, polyfill not needed.`);
      return { supported: true, instances: [] };
    }

    const instances = new Map();

    // Process existing containers
    const containers = processStyleSheets();
    for (const container of containers) {
      if (!container.hasAttribute(POLYFILL_ATTR)) {
        instances.set(container, new GridLanesLayout(container, options));
      }
    }

    // Watch for new stylesheets and elements
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        // Check for new style elements
        if (mutation.type === 'childList') {
          for (const node of mutation.addedNodes) {
            if (node.nodeType === Node.ELEMENT_NODE) {
              // Check if the added element is a grid-lanes container
              const style = window.getComputedStyle(node);
              if (node.style.display === 'grid-lanes' || 
                  style.getPropertyValue('display') === 'grid-lanes') {
                if (!instances.has(node)) {
                  instances.set(node, new GridLanesLayout(node, options));
                }
              }
              
              // Check descendants
              const descendants = node.querySelectorAll('*');
              for (const desc of descendants) {
                const descStyle = window.getComputedStyle(desc);
                if (desc.style.display === 'grid-lanes' ||
                    descStyle.getPropertyValue('display') === 'grid-lanes') {
                  if (!instances.has(desc)) {
                    instances.set(desc, new GridLanesLayout(desc, options));
                  }
                }
              }
            }
          }
        }
      }

      // Re-scan stylesheets for new rules
      const newContainers = processStyleSheets();
      for (const container of newContainers) {
        if (!instances.has(container)) {
          instances.set(container, new GridLanesLayout(container, options));
        }
      }
    });

    observer.observe(document.documentElement, {
      childList: true,
      subtree: true
    });

    console.log(`${POLYFILL_NAME}: Initialized, ${instances.size} container(s) found.`);

    return {
      supported: false,
      instances,
      observer,
      refresh() {
        for (const instance of instances.values()) {
          instance.refresh();
        }
      },
      destroy() {
        observer.disconnect();
        for (const instance of instances.values()) {
          instance.destroy();
        }
        instances.clear();
      }
    };
  }

  /**
   * Apply to a specific element
   */
  function apply(element, options = {}) {
    if (supportsGridLanes() && !options.force) {
      return null;
    }
    return new GridLanesLayout(element, options);
  }

  // Export
  const GridLanesPolyfill = {
    supportsGridLanes,
    init,
    apply,
    GridLanesLayout,
    version: '1.0.0'
  };

  // AMD
  if (typeof define === 'function' && define.amd) {
    define([], function() { return GridLanesPolyfill; });
  }
  // CommonJS
  else if (typeof module === 'object' && module.exports) {
    module.exports = GridLanesPolyfill;
  }
  // Global
  else {
    global.GridLanesPolyfill = GridLanesPolyfill;
  }

})(typeof globalThis !== 'undefined' ? globalThis : 
   typeof window !== 'undefined' ? window : 
   typeof global !== 'undefined' ? global : this);
