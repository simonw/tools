const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const html = fs.readFileSync(path.join(__dirname, '../blog-to-newsletter.html'), 'utf8');
const start = html.indexOf('async function fetchMonthlyNewsletterPreviews()');
const end = html.indexOf('function generateSponsorMessage()', start);
const source = html.slice(start, end);

for (const format of ['filenames', 'dated issues']) {
  test(`monthly preview links from ${format}`, async () => {
    const filenames = ['2026-05-may.md', '2026-06-june.md', '2026-07-july.md', '2026-08-august.md'];
    const index = format === 'filenames' ? filenames : filenames.map(filename => ({
      filename, sent_at: '2026-09-04T05:50:18Z'
    }));
    const context = vm.createContext({
      fetch: async url => {
        assert.equal(url, 'https://raw.githubusercontent.com/simonw/monthly-newsletter-archive/refs/heads/main/index.json');
        return { ok: true, json: async () => index };
      }
    });
    vm.runInContext(source, context);
    const result = JSON.parse(JSON.stringify(await context.fetchMonthlyNewsletterPreviews()));
    assert.deepEqual(result.map(item => item.label), ['June', 'July', 'August']);
    assert.deepEqual(result.map(item => item.url), filenames.slice(-3).map(filename =>
      `https://github.com/simonw/monthly-newsletter-archive/blob/main/${filename}`
    ));
  });
}
