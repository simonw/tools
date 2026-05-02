/**
 * <image-gallery> web component
 *
 * Lays out a list of <figure> children in justified rows: items in a row
 * share a common height, with widths proportional to each image's aspect
 * ratio. Handles mixed portrait / landscape mixes naturally.
 *
 * Clicking any image opens a full-screen lightbox with prev / next
 * navigation (arrow keys, swipe on touch devices, on-screen arrows). All
 * <image-gallery> elements on the page form a single navigation cycle and
 * the figure list is recomputed on every step, so galleries added or
 * removed after load are picked up automatically.
 *
 * Markup:
 *   <image-gallery>
 *     <figure>
 *       <a href="full.jpg"><img src="thumb.jpg" alt="..."></a>
 *       <figcaption>caption text</figcaption>
 *     </figure>
 *     ...
 *   </image-gallery>
 *
 * Attributes:
 *   show-counter   Display "n / total" position counter in the lightbox
 *                  while viewing a figure from this gallery.
 */

const STYLES = `
image-gallery:defined {
  --gap: 6px;
  --max-row-height: 240px;
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--gap);
  background: #f4f4f4;
  padding: var(--gap);
  border-radius: 4px;
}

image-gallery:defined > figure {
  margin: 0;
  position: relative;
  overflow: hidden;
  background: #ddd;
  border-radius: 2px;
  min-width: 0;
}

image-gallery:defined > figure > a {
  display: block;
  width: 100%;
  height: 100%;
  text-decoration: none;
  cursor: zoom-in;
}

image-gallery:defined img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

image-gallery:defined figcaption {
  position: absolute;
  bottom: 4px;
  left: 4px;
  right: 4px;
  margin: 0;
  padding: 2px 6px;
  font-size: 11px;
  color: white;
  background: rgba(0, 0, 0, 0.55);
  border-radius: 2px;
  pointer-events: none;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

image-gallery:defined figcaption a {
  pointer-events: auto;
  color: inherit;
  text-decoration: underline;
}

image-gallery:defined figcaption a:hover {
  color: #cfe8ff;
}

dialog.gallery-modal {
  border: none;
  padding: 0;
  margin: 0;
  width: 100vw;
  height: 100vh;
  max-width: 100vw;
  max-height: 100vh;
  background: #000;
  color: #fff;
  overflow: hidden;
}

dialog.gallery-modal::backdrop {
  background: rgba(0, 0, 0, 0.95);
}

.gallery-modal-stage {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  touch-action: pan-y;
}

.gallery-modal-img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  display: block;
  user-select: none;
  -webkit-user-drag: none;
  pointer-events: none;
}

.gallery-modal-btn {
  position: absolute;
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.55);
  cursor: pointer;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: color 0.15s ease, background 0.15s ease;
  z-index: 2;
  font-family: inherit;
}

.gallery-modal-btn:hover,
.gallery-modal-btn:focus-visible {
  color: #fff;
  background: rgba(255, 255, 255, 0.12);
  outline: none;
}

.gallery-modal-btn svg {
  width: 24px;
  height: 24px;
  display: block;
}

.gallery-modal-close {
  top: 12px;
  right: 12px;
  width: 44px;
  height: 44px;
}

.gallery-modal-prev,
.gallery-modal-next {
  top: 50%;
  transform: translateY(-50%);
  width: 56px;
  height: 56px;
}

.gallery-modal-prev {
  left: 8px;
}

.gallery-modal-next {
  right: 8px;
}

.gallery-modal-caption-wrap {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(0, 0, 0, 0.65);
  padding: 12px 72px;
  z-index: 1;
  pointer-events: none;
}

.gallery-modal-caption a {
  pointer-events: auto;
  color: #9cf;
  text-decoration: underline;
}

.gallery-modal-caption a:hover {
  color: #cfe8ff;
}

.gallery-modal-counter {
  display: block;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: rgba(255, 255, 255, 0.55);
  margin-bottom: 2px;
}

.gallery-modal-counter[hidden] {
  display: none;
}

.gallery-modal-caption {
  font-size: 14px;
  line-height: 1.4;
  color: #fff;
  word-wrap: break-word;
}

@media (max-width: 600px) {
  .gallery-modal-prev,
  .gallery-modal-next {
    width: 44px;
    height: 44px;
  }

  .gallery-modal-caption-wrap {
    padding: 10px 16px 14px;
  }
}
`;

function injectStyles() {
  if (document.getElementById('image-gallery-styles')) return;
  const style = document.createElement('style');
  style.id = 'image-gallery-styles';
  style.textContent = STYLES;
  document.head.appendChild(style);
}

class ImageGallery extends HTMLElement {
  static instances = new Set();
  static modal = null;
  static currentFigure = null;

  connectedCallback() {
    this.figures = [...this.querySelectorAll(':scope > figure')];
    if (!this.figures.length) return;
    this.dataset.count = this.figures.length;

    ImageGallery.instances.add(this);

    // Wire up clicks on each figure's anchor: open the lightbox instead
    this.figures.forEach(figure => {
      const a = figure.querySelector('a');
      if (a && !a.dataset.galleryWired) {
        a.dataset.galleryWired = '1';
        a.addEventListener('click', e => {
          e.preventDefault();
          ImageGallery.openFor(figure);
        });
      }
    });

    // Layout once images have natural dimensions available, then keep
    // it in sync with container width changes
    const imgs = this.figures.map(f => f.querySelector('img')).filter(Boolean);
    Promise.all(imgs.map(img => {
      if (img.complete && img.naturalWidth > 0) return Promise.resolve();
      return new Promise(res => {
        img.addEventListener('load', res, { once: true });
        img.addEventListener('error', res, { once: true });
      });
    })).then(() => {
      this.applyLayout();
      this._lastWidth = this.clientWidth;
      this._ro = new ResizeObserver(entries => {
        const w = entries[0].contentRect.width;
        if (Math.abs(w - this._lastWidth) > 0.5) {
          this._lastWidth = w;
          this.applyLayout();
        }
      });
      this._ro.observe(this);
    });
  }

  disconnectedCallback() {
    this._ro?.disconnect();
    ImageGallery.instances.delete(this);
  }

  ratioOf(figure) {
    const img = figure.querySelector('img');
    if (!img) return 1;
    const r = img.naturalWidth / img.naturalHeight;
    return isFinite(r) && r > 0 ? r : 1;
  }

  applyLayout() {
    const ratios = this.figures.map(f => this.ratioOf(f));
    const count = this.figures.length;

    this.figures.forEach(f => {
      f.style.width = '';
      f.style.height = '';
      f.style.aspectRatio = '';
      f.style.maxHeight = '';
    });

    const cs = getComputedStyle(this);
    const padL = parseFloat(cs.paddingLeft) || 0;
    const padR = parseFloat(cs.paddingRight) || 0;
    const gap = parseFloat(cs.gap) || 0;
    const containerW = this.clientWidth - padL - padR;
    const maxH = parseFloat(cs.getPropertyValue('--max-row-height')) || 240;

    if (containerW <= 0) return;

    if (count === 1) {
      const f = this.figures[0];
      const r = ratios[0];
      this.dataset.orientation = r >= 1 ? 'landscape' : 'portrait';
      let h = maxH;
      let w = h * r;
      if (w > containerW) {
        w = containerW;
        h = w / r;
      }
      f.style.width = w + 'px';
      f.style.height = h + 'px';
      return;
    }

    const splits = this.getRowSplits(count);
    let idx = 0;
    splits.forEach(rowCount => {
      const rowFigs = this.figures.slice(idx, idx + rowCount);
      const rowRatios = ratios.slice(idx, idx + rowCount);
      const sum = rowRatios.reduce((a, b) => a + b, 0);
      const rowAvailW = Math.max(0, containerW - (rowCount - 1) * gap);
      const naturalH = sum > 0 ? rowAvailW / sum : maxH;
      const rowH = Math.min(naturalH, maxH);
      rowFigs.forEach((f, i) => {
        f.style.width = (rowH * rowRatios[i]) + 'px';
        f.style.height = rowH + 'px';
      });
      idx += rowCount;
    });
  }

  getRowSplits(n) {
    if (n <= 3) return [n];
    // Cap rows at 3 wide. Use rows of 3 plus rows of 2 to make up the
    // remainder; smaller rows lead so the bottom row is the widest.
    const splits = [];
    const rem = n % 3;
    let twos, threes;
    if (rem === 0) {
      twos = 0;
      threes = n / 3;
    } else if (rem === 1) {
      twos = 2;
      threes = (n - 4) / 3;
    } else {
      twos = 1;
      threes = (n - 2) / 3;
    }
    for (let i = 0; i < twos; i++) splits.push(2);
    for (let i = 0; i < threes; i++) splits.push(3);
    return splits;
  }

  // ----- Cross-gallery flat list (in document order) -----

  static getAllFigures() {
    const sorted = [...ImageGallery.instances].sort((a, b) => {
      if (a === b) return 0;
      const pos = a.compareDocumentPosition(b);
      if (pos & Node.DOCUMENT_POSITION_FOLLOWING) return -1;
      if (pos & Node.DOCUMENT_POSITION_PRECEDING) return 1;
      return 0;
    });
    const all = [];
    sorted.forEach(g => {
      [...g.querySelectorAll(':scope > figure')].forEach(f => all.push(f));
    });
    return all;
  }

  static openFor(figure) {
    if (!figure) return;
    if (!ImageGallery.modal) ImageGallery.buildModal();
    ImageGallery.currentFigure = figure;
    ImageGallery.renderModal();
    if (!ImageGallery.modal.open) ImageGallery.modal.showModal();
  }

  static step(direction) {
    // Recompute the list every step so newly-added galleries are picked up
    const all = ImageGallery.getAllFigures();
    if (!all.length) return;
    const n = all.length;
    let idx = all.indexOf(ImageGallery.currentFigure);
    if (idx < 0) idx = 0; // current figure was removed; restart at 0
    else idx = (idx + direction + n) % n;
    ImageGallery.openFor(all[idx]);
  }

  static next() { ImageGallery.step(1); }
  static prev() { ImageGallery.step(-1); }

  static renderModal() {
    const figure = ImageGallery.currentFigure;
    if (!figure) return;
    const a = figure.querySelector('a');
    const thumb = figure.querySelector('img');
    const caption = figure.querySelector('figcaption');
    const fullSrc = a ? a.href : (thumb ? thumb.src : '');

    const img = ImageGallery.modal.querySelector('.gallery-modal-img');
    img.src = fullSrc;
    img.alt = thumb ? thumb.alt : '';

    const cap = ImageGallery.modal.querySelector('.gallery-modal-caption');
    cap.replaceChildren();
    if (caption) {
      for (const node of caption.childNodes) {
        cap.appendChild(node.cloneNode(true));
      }
    }

    // Counter is opt-in via show-counter on the figure's parent gallery
    const parent = figure.closest('image-gallery');
    const showCounter = parent && parent.hasAttribute('show-counter');
    const counter = ImageGallery.modal.querySelector('.gallery-modal-counter');
    counter.hidden = !showCounter;
    if (showCounter) {
      const all = ImageGallery.getAllFigures();
      const idx = all.indexOf(figure);
      counter.textContent = `${idx + 1} / ${all.length}`;
    } else {
      counter.textContent = '';
    }
  }

  static buildModal() {
    const dialog = document.createElement('dialog');
    dialog.className = 'gallery-modal';
    dialog.innerHTML = `
      <div class="gallery-modal-stage">
        <img class="gallery-modal-img" alt="">
      </div>
      <button type="button" class="gallery-modal-btn gallery-modal-prev" aria-label="Previous image">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 6 9 12 15 18"/></svg>
      </button>
      <button type="button" class="gallery-modal-btn gallery-modal-next" aria-label="Next image">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 6 15 12 9 18"/></svg>
      </button>
      <button type="button" class="gallery-modal-btn gallery-modal-close" aria-label="Close">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><line x1="6" y1="6" x2="18" y2="18"/><line x1="6" y1="18" x2="18" y2="6"/></svg>
      </button>
      <div class="gallery-modal-caption-wrap">
        <span class="gallery-modal-counter" hidden></span>
        <div class="gallery-modal-caption"></div>
      </div>
    `;

    dialog.querySelector('.gallery-modal-close').addEventListener('click', () => dialog.close());
    dialog.querySelector('.gallery-modal-prev').addEventListener('click', () => ImageGallery.prev());
    dialog.querySelector('.gallery-modal-next').addEventListener('click', () => ImageGallery.next());

    // Tap on stage background (not the image, not buttons) closes the modal
    const stage = dialog.querySelector('.gallery-modal-stage');
    stage.addEventListener('click', e => {
      if (e.target === stage) dialog.close();
    });

    // Keyboard navigation while open
    dialog.addEventListener('keydown', e => {
      if (e.key === 'ArrowLeft') { e.preventDefault(); ImageGallery.prev(); }
      else if (e.key === 'ArrowRight') { e.preventDefault(); ImageGallery.next(); }
    });

    // Single-finger horizontal swipe
    let sx = null, sy = null, st = 0;
    dialog.addEventListener('touchstart', e => {
      if (e.touches.length === 1) {
        sx = e.touches[0].clientX;
        sy = e.touches[0].clientY;
        st = Date.now();
      } else {
        sx = null;
      }
    }, { passive: true });

    dialog.addEventListener('touchend', e => {
      if (sx === null || e.changedTouches.length !== 1) { sx = null; return; }
      const dx = e.changedTouches[0].clientX - sx;
      const dy = e.changedTouches[0].clientY - sy;
      const dt = Date.now() - st;
      sx = null;
      if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.5 && dt < 600) {
        if (dx < 0) ImageGallery.next();
        else ImageGallery.prev();
      }
    }, { passive: true });

    document.body.appendChild(dialog);
    ImageGallery.modal = dialog;
  }
}

injectStyles();

if (!customElements.get('image-gallery')) {
  customElements.define('image-gallery', ImageGallery);
}
