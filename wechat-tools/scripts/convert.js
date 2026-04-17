#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { marked } = require('marked');
const juice = require('juice');

// Parse CLI arguments
function parseArgs() {
  const args = process.argv.slice(2);
  const options = {
    input: null,
    output: './output',
    images: 'embed',
    accent: '#e76f51'
  };

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--input' && args[i + 1]) {
      options.input = args[i + 1];
      i++;
    } else if (args[i] === '--output' && args[i + 1]) {
      options.output = args[i + 1];
      i++;
    } else if (args[i] === '--images' && args[i + 1]) {
      options.images = args[i + 1];
      i++;
    } else if (args[i] === '--accent' && args[i + 1]) {
      options.accent = args[i + 1];
      i++;
    }
  }

  if (!options.input) {
    console.error('Error: --input parameter is required');
    process.exit(1);
  }

  return options;
}

// Parse frontmatter from markdown
function parseFrontmatter(markdown) {
  const frontmatterRegex = /^---\n([\s\S]*?)\n---\n([\s\S]*)$/;
  const match = markdown.match(frontmatterRegex);

  if (!match) {
    return { frontmatter: {}, content: markdown };
  }

  const frontmatterText = match[1];
  const content = match[2];
  const frontmatter = {};

  frontmatterText.split('\n').forEach(line => {
    const colonIndex = line.indexOf(':');
    if (colonIndex > 0) {
      const key = line.substring(0, colonIndex).trim();
      const value = line.substring(colonIndex + 1).trim().replace(/^["']|["']$/g, '');
      frontmatter[key] = value;
    }
  });

  return { frontmatter, content };
}

// Pre-process ==text== highlight syntax → placeholders (before marked)
function parseHighlightSyntax(markdown) {
  return markdown.replace(/==(.+?)==/g, '%%HL_START%%$1%%HL_END%%');
}

// Custom block parser for :::highlight, :::question, :::insight
function parseCustomBlocks(markdown) {
  // Parse :::highlight blocks
  markdown = markdown.replace(/:::highlight\n([\s\S]*?)\n:::/g, (match, content) => {
    return `<CUSTOMBLOCK_HIGHLIGHT>${content.trim()}</CUSTOMBLOCK_HIGHLIGHT>`;
  });

  // Parse :::question blocks
  markdown = markdown.replace(/:::question\n([\s\S]*?)\n:::/g, (match, content) => {
    return `<CUSTOMBLOCK_QUESTION>${content.trim()}</CUSTOMBLOCK_QUESTION>`;
  });

  // Parse :::insight blocks
  markdown = markdown.replace(/:::insight\n([\s\S]*?)\n:::/g, (match, content) => {
    return `<CUSTOMBLOCK_INSIGHT>${content.trim()}</CUSTOMBLOCK_INSIGHT>`;
  });

  return markdown;
}

// Configure marked with custom renderer (marked v17 API)
function setupRenderer(inputDir) {
  const renderer = new marked.Renderer();
  let sectionCount = 0;

  // H2 → numbered magazine-style section header
  // H3 → teal-accented subtitle
  renderer.heading = function({ tokens, depth }) {
    const text = this.parser.parseInline(tokens);
    if (depth === 2) {
      sectionCount++;
      const num = String(sectionCount).padStart(2, '0');
      return `<section class="sh">` +
        `<section class="sh-num">${num}</section>` +
        `<section class="sh-part">PART</section>` +
        `<section class="sh-line"></section>` +
        `<section class="sh-title">${text}</section>` +
        `</section>\n`;
    } else if (depth === 3) {
      return `<section class="sub">${text}</section>\n`;
    }
    return `<h${depth}>${text}</h${depth}>\n`;
  };

  // Blockquote → section.qb
  renderer.blockquote = function({ tokens }) {
    const body = this.parser.parse(tokens);
    return `<section class="qb">${body}</section>\n`;
  };

  // Strong → span.b
  renderer.strong = function({ tokens }) {
    const text = this.parser.parseInline(tokens);
    return `<span class="b">${text}</span>`;
  };

  // Inline code → span.code
  renderer.codespan = function({ text }) {
    return `<span class="code">${text}</span>`;
  };

  // Image → section.iw wrapper
  renderer.image = function({ href, title, text }) {
    const caption = text || title || '';

    // For local images, silently drop broken image tags instead of shipping裂图到公众号。
    // Keep caption text as a lightweight fallback so the article flow stays intact.
    const isRemote = href.startsWith('http://') || href.startsWith('https://') || href.startsWith('data:');
    const fullPath = path.isAbsolute(href) ? href : path.join(inputDir, href);
    const exists = isRemote || fs.existsSync(fullPath);

    if (!exists) {
      return caption ? `<section class="iw"><p class="ic">${caption}</p></section>\n` : '';
    }

    return `<section class="iw"><img src="${href}" alt="${text || ''}" />${caption ? `<p class="ic">${caption}</p>` : ''}</section>\n`;
  };

  // List item → p.li
  renderer.listitem = function(item) {
    const text = this.parser.parse(item.tokens);
    return `<p class="li">- ${text}</p>\n`;
  };

  // List → just wrap items (no ol/ul tags)
  renderer.list = function(token) {
    let body = '';
    for (const item of token.items) {
      body += this.listitem(item);
    }
    return body;
  };

  // Hr → minimal line divider
  renderer.hr = function() {
    return `<section class="div"><section class="div-line"></section></section>\n`;
  };

  // Paragraph → p.p (with custom block handling)
  renderer.paragraph = function({ tokens }) {
    const text = this.parser.parseInline(tokens);
    // Check if it's a custom block placeholder
    if (text.startsWith('<CUSTOMBLOCK_HIGHLIGHT>')) {
      const content = text.replace(/<CUSTOMBLOCK_HIGHLIGHT>([\s\S]*?)<\/CUSTOMBLOCK_HIGHLIGHT>/, '$1');
      return `<section class="hbox">${content}</section>\n`;
    }
    if (text.startsWith('<CUSTOMBLOCK_QUESTION>')) {
      const content = text.replace(/<CUSTOMBLOCK_QUESTION>([\s\S]*?)<\/CUSTOMBLOCK_QUESTION>/, '$1');
      return `<section class="qbox">${content}</section>\n`;
    }
    if (text.startsWith('<CUSTOMBLOCK_INSIGHT>')) {
      const content = text.replace(/<CUSTOMBLOCK_INSIGHT>([\s\S]*?)<\/CUSTOMBLOCK_INSIGHT>/, '$1');
      return `<section class="hbox">${content}</section>\n`;
    }
    return `<p class="p">${text}</p>\n`;
  };

  return renderer;
}

// Convert image to base64
function imageToBase64(imagePath, inputDir) {
  try {
    const fullPath = path.isAbsolute(imagePath) ? imagePath : path.join(inputDir, imagePath);
    const imageBuffer = fs.readFileSync(fullPath);
    const ext = path.extname(imagePath).toLowerCase();
    const mimeTypes = {
      '.jpg': 'image/jpeg',
      '.jpeg': 'image/jpeg',
      '.png': 'image/png',
      '.gif': 'image/gif',
      '.webp': 'image/webp'
    };
    const mimeType = mimeTypes[ext] || 'image/png';
    return `data:${mimeType};base64,${imageBuffer.toString('base64')}`;
  } catch (error) {
    console.warn(`Warning: Could not read image ${imagePath}: ${error.message}`);
    return imagePath;
  }
}

// Process images in HTML
function processImages(html, inputDir, options) {
  const imageMap = [];
  let counter = 1;

  html = html.replace(/<img src="([^"]+)"/g, (match, src) => {
    // Skip URLs
    if (src.startsWith('http://') || src.startsWith('https://') || src.startsWith('data:')) {
      return match;
    }

    // Convert local file to base64
    const base64 = imageToBase64(src, inputDir);

    if (options.images === 'extract' || options.images === 'both') {
      const filename = `image_${counter}.${src.split('.').pop()}`;
      imageMap.push({ filename, base64, original: src });
      counter++;

      if (options.images === 'extract') {
        return `<img src="[IMAGE_PLACEHOLDER_${filename}]"`;
      }
    }

    return `<img src="${base64}"`;
  });

  return { html, imageMap };
}

// Clean HTML for WeChat
function wechatCleanup(html) {
  // Replace all div with section
  html = html.replace(/<div/g, '<section').replace(/<\/div>/g, '</section>');

  // Remove linear-gradient
  html = html.replace(/linear-gradient\([^)]*\)/g, 'transparent');

  // Remove box-shadow
  html = html.replace(/box-shadow:[^;]+;/g, '');

  return html;
}

// Main conversion function
function convert() {
  console.log('Starting conversion...');

  const options = parseArgs();

  // Read input file
  console.log(`Reading input file: ${options.input}`);
  if (!fs.existsSync(options.input)) {
    console.error(`Error: Input file not found: ${options.input}`);
    process.exit(1);
  }

  const markdown = fs.readFileSync(options.input, 'utf8');
  const inputDir = path.dirname(options.input);
  const inputBasename = path.basename(options.input, '.md');

  // Parse frontmatter
  const { frontmatter, content } = parseFrontmatter(markdown);
  const title = frontmatter.title || '';
  const subtitle = frontmatter.subtitle || '';
  const accentColor = frontmatter.accent_color || options.accent;

  console.log(`Title: ${title || '(none)'}`);
  console.log(`Accent color: ${accentColor}`);

  // Pre-process ==text== highlight syntax
  let processedContent = parseHighlightSyntax(content);

  // Parse custom blocks
  processedContent = parseCustomBlocks(processedContent);

  // Convert markdown to HTML
  const renderer = setupRenderer(inputDir);
  marked.setOptions({ renderer });
  let bodyHtml = marked.parse(processedContent);

  // Fix: marked fails to parse **bold** when closing ** is preceded by CJK
  // punctuation and immediately followed by CJK text (no space).
  // e.g. "数据：**55%的企业后悔。**预测" leaves raw ** in output.
  // Catch any remaining **...** patterns and convert them to <span class="b">.
  bodyHtml = bodyHtml.replace(/\*\*([^*]+?)\*\*/g, '<span class="b">$1</span>');

  // Convert ==highlight== placeholders to .hl spans
  bodyHtml = bodyHtml.replace(/%%HL_START%%(.*?)%%HL_END%%/g, '<span class="hl">$1</span>');

  // Build hero section (with accent stripe)
  let heroHtml = '';
  if (title) {
    heroHtml = `
    <section class="hero">
      <section class="hero-accent"></section>
      <section class="hero-title">${title}</section>
      ${subtitle ? `<section class="hero-sub">${subtitle}</section>` : ''}
    </section>`;
  }

  // Build content section
  const contentHtml = `
    <section class="content">
      ${bodyHtml}
    </section>`;

  // Load theme CSS
  const themePath = path.join(__dirname, '../assets/theme-default.css');
  console.log(`Loading theme: ${themePath}`);

  if (!fs.existsSync(themePath)) {
    console.error(`Error: Theme file not found: ${themePath}`);
    process.exit(1);
  }

  let themeCSS = fs.readFileSync(themePath, 'utf8');

  // Replace accent color placeholders
  themeCSS = themeCSS.replace(/#e76f51/g, accentColor);

  // Assemble HTML
  let html = `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${title || 'WeChat Article'}</title>
  <style>
${themeCSS}
  </style>
</head>
<body>
${heroHtml}
${contentHtml}
</body>
</html>`;

  // Inline CSS
  console.log('Inlining CSS...');
  html = juice(html, { removeStyleTags: true });

  // Process images
  console.log(`Processing images (mode: ${options.images})...`);
  const { html: processedHtml, imageMap } = processImages(html, inputDir, options);
  html = processedHtml;

  // WeChat cleanup
  console.log('Applying WeChat compatibility cleanup...');
  html = wechatCleanup(html);

  // Create output directory
  if (!fs.existsSync(options.output)) {
    fs.mkdirSync(options.output, { recursive: true });
  }

  // Write output HTML
  const outputHtmlPath = path.join(options.output, `${inputBasename}.html`);
  fs.writeFileSync(outputHtmlPath, html, 'utf8');
  console.log(`✓ HTML output: ${outputHtmlPath}`);

  // Save extracted images if needed
  if ((options.images === 'extract' || options.images === 'both') && imageMap.length > 0) {
    const imagesDir = path.join(options.output, 'images');
    if (!fs.existsSync(imagesDir)) {
      fs.mkdirSync(imagesDir, { recursive: true });
    }

    imageMap.forEach(({ filename, base64 }) => {
      const base64Data = base64.replace(/^data:image\/\w+;base64,/, '');
      const imagePath = path.join(imagesDir, filename);
      fs.writeFileSync(imagePath, Buffer.from(base64Data, 'base64'));
      console.log(`✓ Extracted image: ${imagePath}`);
    });
  }

  console.log('\nConversion complete!');
}

// Run
try {
  convert();
} catch (error) {
  console.error(`Error: ${error.message}`);
  console.error(error.stack);
  process.exit(1);
}
