(function() {
  // Don't run twice
  if (document.querySelector('#comment-view-tabs')) return;

  const commentsLabel = document.querySelector('.comments_label');
  const commentsContainer = document.querySelector('ol.comments');

  if (!commentsLabel || !commentsContainer) {
    alert('This bookmarklet only works on Lobste.rs comment pages');
    return;
  }

  // Store original HTML
  const originalCommentsHTML = commentsContainer.innerHTML;

  // Helper to find author name
  function getAuthor(element) {
    const links = element.querySelectorAll('a[href^="/~"]');
    for (const link of links) {
      const text = link.textContent?.trim();
      if (text) return text;
    }
    return null;
  }

  // Extract all comments with their data
  function extractComments() {
    const comments = [];
    document.querySelectorAll('.comments_subtree').forEach(subtree => {
      const comment = subtree.querySelector(':scope > .comment[id^="c_"]');
      if (!comment) return;

      const timeEl = comment.querySelector('time');
      const parentSubtree = subtree.parentElement?.closest('.comments_subtree');
      const parentComment = parentSubtree?.querySelector(':scope > .comment[id^="c_"]');

      comments.push({
        id: comment.id,
        element: comment.cloneNode(true),
        author: getAuthor(comment),
        timestamp: parseInt(timeEl?.getAttribute('data-at-unix') || '0'),
        parentId: parentComment?.id || null,
        parentAuthor: parentComment ? getAuthor(parentComment) : null
      });
    });
    return comments;
  }

  // Create tabs
  const tabsContainer = document.createElement('div');
  tabsContainer.id = 'comment-view-tabs';
  tabsContainer.innerHTML = `
    <style>
      #comment-view-tabs { margin: 10px 0 }
      #comment-view-tabs .tab-buttons { display: flex; gap: 0 }
      #comment-view-tabs .tab-btn {
        padding: 8px 16px;
        border: 1px solid #ac0000;
        background: white;
        cursor: pointer;
        font-size: 14px;
        color: #ac0000;
      }
      #comment-view-tabs .tab-btn:first-child { border-radius: 4px 0 0 4px }
      #comment-view-tabs .tab-btn:nth-child(2) {
        border-radius: 0 4px 4px 0;
        border-left: none
      }
      #comment-view-tabs .tab-btn:last-child {
        border-radius: 4px;
        margin-left: auto
      }
      #comment-view-tabs .tab-btn.active { background: #ac0000; color: white }
      #comment-view-tabs .tab-btn:hover:not(.active) { background: #f0f0f0 }
      .flat-comment {
        margin: 0 0 15px 0 !important;
        padding: 10px !important;
        border-left: 3px solid #ddd !important;
      }
      .reply-to-link { font-size: 12px; color: #666; margin-left: 10px }
      .reply-to-link a { color: #ac0000; text-decoration: none }
      .reply-to-link a:hover { text-decoration: underline }
    </style>
    <div class="tab-buttons">
      <button class="tab-btn active" data-view="default">Default</button>
      <button class="tab-btn" data-view="latest">Latest</button>
      <button class="tab-btn" data-view="copy">Copy Thread</button>
    </div>
  `;

  // Insert tabs
  const byline = commentsLabel.closest('.byline');
  byline.parentNode.insertBefore(tabsContainer, byline.nextSibling);

  // Switch to default view and optionally scroll to a comment
  function switchToDefault(scrollToId) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelector('.tab-btn[data-view="default"]').classList.add('active');
    commentsContainer.innerHTML = originalCommentsHTML;

    if (scrollToId) {
      setTimeout(() => {
        const el = document.getElementById(scrollToId);
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'center' });
          el.style.transition = 'background 0.3s';
          el.style.background = '#ffffd0';
          setTimeout(() => el.style.background = '', 2000);
        }
      }, 100);
    }
  }

  // Build flat view
  function buildFlatView() {
    const comments = extractComments();
    comments.sort((a, b) => b.timestamp - a.timestamp);

    const flatContainer = document.createElement('div');

    comments.forEach(c => {
      const wrapper = document.createElement('div');
      wrapper.className = 'flat-comment-wrapper';

      const commentEl = c.element;
      commentEl.classList.add('flat-comment');
      commentEl.style.marginLeft = '0';

      // Add reply-to link
      if (c.parentId && c.parentAuthor) {
        const byline = commentEl.querySelector('.byline');
        if (byline) {
          const replySpan = document.createElement('span');
          replySpan.className = 'reply-to-link';
          replySpan.innerHTML = ` ↩ reply to <a href="#${c.parentId}">@${c.parentAuthor}</a>`;
          byline.appendChild(replySpan);
        }
      }

      // Add click handler for time link
      const timeLink = commentEl.querySelector('a[href^="/c/"]');
      if (timeLink) {
        const commentId = c.id;
        timeLink.addEventListener('click', function(e) {
          e.preventDefault();
          switchToDefault(commentId);
        });
      }

      wrapper.appendChild(commentEl);
      flatContainer.appendChild(wrapper);
    });

    return flatContainer;
  }

  // Format thread as plain text for clipboard export
  function formatThreadForExport() {
    const result = [];

    // Get story info for root entry
    const storyEl = document.querySelector('.story_liner');
    const storyTitle = storyEl?.querySelector('.u-url')?.textContent?.trim() || document.title;
    const storyAuthor = storyEl ? getAuthor(storyEl) : null;
    result.push(`[1] ${storyAuthor || 'Unknown'}: ${storyTitle}`);

    function processLevel(parentEl, pathPrefix) {
      const subtrees = parentEl.querySelectorAll(':scope > .comments_subtree');
      let counter = 0;
      subtrees.forEach(subtree => {
        const comment = subtree.querySelector(':scope > .comment[id^="c_"]');
        if (!comment) return;
        counter++;
        const path = `${pathPrefix}.${counter}`;
        const author = getAuthor(comment) || 'Anonymous';
        const textEl = comment.querySelector('.comment_text');
        const text = textEl ? textEl.textContent.trim().replace(/\s+/g, ' ') : '';
        result.push(`[${path}] ${author}: ${text}`);
        const nestedOl = subtree.querySelector(':scope > ol');
        if (nestedOl) {
          processLevel(nestedOl, path);
        }
      });
    }

    // The actual comment tree is inside #story_comments > ol.comments,
    // not the top-level ol.comments which also contains the comment form
    const actualComments = document.querySelector('#story_comments > ol.comments') || commentsContainer;
    processLevel(actualComments, '1');
    return result.join('\n\n');
  }

  let flatViewCache = null;

  // Tab switching
  const tabButtons = tabsContainer.querySelectorAll('.tab-btn');
  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const view = btn.dataset.view;

      if (view === 'copy') {
        const text = formatThreadForExport();
        navigator.clipboard.writeText(text).then(() => {
          btn.textContent = 'Copied!';
          setTimeout(() => btn.textContent = 'Copy Thread', 2000);
        }).catch(() => {
          const textarea = document.createElement('textarea');
          textarea.value = text;
          document.body.appendChild(textarea);
          textarea.select();
          document.execCommand('copy');
          document.body.removeChild(textarea);
          btn.textContent = 'Copied!';
          setTimeout(() => btn.textContent = 'Copy Thread', 2000);
        });
        return;
      }

      tabButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      if (view === 'default') {
        commentsContainer.innerHTML = originalCommentsHTML;
      } else if (view === 'latest') {
        if (!flatViewCache) {
          flatViewCache = buildFlatView();
        }
        commentsContainer.innerHTML = '';
        commentsContainer.appendChild(flatViewCache.cloneNode(true));

        // Re-attach click handlers after cloning
        commentsContainer.querySelectorAll('a[href^="/c/"]').forEach(link => {
          const wrapper = link.closest('.flat-comment-wrapper');
          const commentEl = wrapper?.querySelector('.comment');
          const commentId = commentEl?.id;
          if (commentId) {
            link.addEventListener('click', function(e) {
              e.preventDefault();
              switchToDefault(commentId);
            });
          }
        });
      }
    });
  });
})();
