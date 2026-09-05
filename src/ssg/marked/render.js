'use strict';

// 注意：这三行必须在文件最顶部，且不能放进任何 if / try / 函数里。
// 一旦被挪走或删掉，下面 emit() 里就会报 "ReferenceError: fs is not defined"。
const fs = require('fs');
const path = require('path');
const marked = require(path.join(__dirname, './official/marked-18.0.5.js'));
const hljs = require(path.join(__dirname, './official/highlight.min.js')); // 路径按你实际放的位置调整
const katex = require(path.join(__dirname, './official/katex-0.18.5.min.js'));


const DEFAULT_OPTIONS = {
    gfm: true,          // 表格、删除线、自动链接等 GitHub 扩展语法
    breaks: false,      // true = 单个换行变 <br>（中文博客常用，按需开）
    pedantic: false,
};

// ---------------------------------------------------------------------------
// 3. TOC 逻辑 —— 严格对齐 Python 版 _slugify + heading + _anchor_counts
// ---------------------------------------------------------------------------
function slugify(text) {
    text = String(text == null ? '' : text).toLowerCase().trim();
    // Python 的 html_escape 只处理 & " < > ；空格/下划线保留，由下一步处理
    text = text
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    // Python 版实际跑起来时，中文标题能进锚点（如 #背景），
    // 说明它的 \w 覆盖了中文（re.ASCII=False / re.LOCALE 的效果）。
    // JS 里没有"Unicode 字面的 \w"，所以手动补上中文区间。
    // 注意 JS 正则的字符类里 - 必须放在末尾或开头，否则被当作范围。
    text = text.replace(/[^-\w\s一-鿿]/g, '');
    // Python: re.sub(r'[\s_]+', '-', text)    空格和下划线 → 连字符
    text = text.replace(/[\s_]+/g, '-');
    // Python: re.sub(r'-+', '-', text).strip('-')
    text = text.replace(/-+/g, '-').replace(/^-|-$/g, '');
    return text || 'heading';
}


function renderOne(content, options) {
    const renderer = {};

    const anchorCounts = Object.create(null);
    let tocItems = [];

    renderer.heading = function (token) {
        const level = token.depth;

        if (options.toc !== false) {
            const baseAnchor = slugify(token.text);
            const count = anchorCounts[baseAnchor] || 0;
            const anchor = count > 0 ? `${baseAnchor}-${count}` : baseAnchor;
            anchorCounts[baseAnchor] = count + 1;

            tocItems.push({ level: level, text: token.text, anchor: anchor });
            return `<h${level} id="${anchor}">${token.text}</h${level}>\n`;
        }
        return `<h${level}>${token.text}</h${level}>\n`;
    }

    renderer.blockquote = function (token) {
        let body = this.parser.parse(token.tokens);
        // 只替换 <p>...</p> 内部的换行；标签之间的换行保持不动，否则块之间会多空行
        body = body.replace(/<p>([\s\S]*?)<\/p>/g,
            (mm, inner) => '<p>' + inner.replace(/\n/g, '<br>\n') + '</p>');
        return `<blockquote>\n${body}</blockquote>\n`;
    };

    // 👇 新增：代码块高亮
    let usedCode = false;   // 👈 追踪是否遇到代码块
    renderer.code = function (token) {
        usedCode = true;   // 标记：这篇用到了代码

        const lang = (token.lang || '').trim();
        const code = token.text || '';

        let highlighted = code;
        if (lang && hljs.getLanguage && hljs.getLanguage(lang)) {
            try {
                highlighted = hljs.highlight(code, { language: lang }).value;
            } catch (_) { /* 高亮失败，降级用原始代码 */ }
        } else if (hljs.highlightAuto) {
            try {
                highlighted = hljs.highlightAuto(code).value;
            } catch (_) { /* 降级 */ }
        }

        const langClass = lang ? ` language-${lang}` : '';
        return `<pre><code class="hljs${langClass}">${highlighted}</code></pre>\n`;
    };

    // ============ KaTeX 扩展 ============
    let usedMath = false;   // 👈 追踪是否遇到公式
    const escapeAttr = (s) => {
        return String(s)
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    };
    const inlineMathExtension = {
        name: 'inlineMath',
        level: 'inline',
        start(src) { return src.indexOf('$'); },
        tokenizer(src) {
            // 匹配 $...$，允许 LaTeX 命令（\command），排除转义的 \$ 和首尾空格
            const match = src.match(/^\$(?!\s)((?:\\.|[^$\n])+?)(?<!\s)\$/);
            if (match) {
                return {
                    type: 'inlineMath',
                    raw: match[0],
                    text: match[1].replace(/\\\$/g, '$'), // 把转义的 \$ 还原为 $
                };
            }
        },
        renderer(token) {
            usedMath = true;
            try {
                return katex.renderToString(token.text, {
                    displayMode: false,
                    throwOnError: false,
                });
            } catch (e) {
                return `<code class="math-error">${escapeAttr(token.text)}</code>`;
            }
        }
    };
    const blockMathExtension = {
        name: 'blockMath',
        level: 'block',
        start(src) { return src.indexOf('$$'); },
        tokenizer(src) {
            // 匹配 $$...$$，支持多行
            const match = src.match(/^\$\$([\s\S]+?)\$\$/);
            if (match) {
                return {
                    type: 'blockMath',
                    raw: match[0],
                    text: match[1].trim(),
                };
            }
        },
        renderer(token) {
            usedMath = true;
            try {
                return '<p>' + katex.renderToString(token.text, {
                    displayMode: true,
                    throwOnError: false,
                }) + '</p>\n';
            } catch (e) {
                return `<pre class="math-error">${escapeAttr(token.text)}</pre>\n`;
            }
        }
    };

    const instance = new marked.Marked({
        gfm: DEFAULT_OPTIONS.gfm,
        breaks: DEFAULT_OPTIONS.breaks,
        pedantic: DEFAULT_OPTIONS.pedantic,
        renderer,
    });
    instance.use({ extensions: [inlineMathExtension, blockMathExtension] }); // 👇 挂载扩展

    const html = instance.parse(String(content == null ? '' : content));
    return {
        ok: true,
        html: html == null ? '' : html,
        toc: tocItems,
        usedCode: usedCode,
        usedMath: usedMath,
    };
}

function readStdin() {
    return new Promise((resolve, reject) => {
        const chunks = [];
        // stdin 显式按 utf-8 拼接，绕开 Windows 控制台代码页（GBK）导致的中文乱码
        process.stdin.setEncoding('utf8');
        process.stdin.on('data', (c) => chunks.push(c));
        process.stdin.on('end', () => resolve(chunks.join('')));
        process.stdin.on('error', reject);
    });
}

function emit(obj, exitCode) {
    const json = JSON.stringify(obj);
    const buf = Buffer.from(json, 'utf8');

    // 必须同步写 fd 1。
    // 千万不能写成 process.stdout.write(buf) 再配 process.exit(code)：
    // stdout 通向管道时是异步的，process.exit 会立刻掐断，实测 1.8MB 输出只剩 65536 字节。
    if (typeof fs !== 'undefined' && fs.writeSync) {
        // 循环写：管道缓冲区满时 writeSync 可能只写入一部分
        let off = 0;
        while (off < buf.length) {
            try {
                off += fs.writeSync(1, buf, off, buf.length - off);
            } catch (e) {
                if (e.code === 'EAGAIN') continue;   // 非阻塞 stdout，稍后重试
                if (e.code === 'EPIPE') break;       // 调用方已关闭管道，放弃
                throw e;
            }
        }
    } else {
        // 兜底：fs 不可用时绝不配 process.exit，只设 exitCode，让 Node 自然冲刷后退出
        process.stdout.write(buf);
    }
    process.exitCode = exitCode || 0;
}

async function main() {
    let raw = '';
    try {
        raw = (await readStdin()).trim();
        if (!raw) throw new Error('stdin 为空');
        const input = JSON.parse(raw);
        emit(renderOne(input.content, input.options));
    } catch (e) {
        emit(
            {
                ok: false,
                error: String(e && e.message ? e.message : e),
                stdin_head: raw.slice(0, 200),
            },
            1
        );
    }
}

main().catch((e) => emit({ ok: false, error: String(e && e.stack ? e.stack : e) }, 1));
