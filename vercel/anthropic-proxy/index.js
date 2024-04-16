const express = require('express');
const cors = require('cors');
const { createProxyMiddleware } = require('http-proxy-middleware');

const app = express();

app.use(cors({origin: 'https://tools.simonwillison.net'}));

// Proxy middleware
const apiProxy = createProxyMiddleware({
  target: 'https://api.anthropic.com',
  changeOrigin: true,
  pathRewrite: {
    '^/v1': '/v1',
  },
});

// Use the proxy middleware for /v1/* routes
app.use('/v1', apiProxy);

module.exports = app;
