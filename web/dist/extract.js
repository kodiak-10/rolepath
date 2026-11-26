/* 简历文件浏览器端解析:txt/md 直读,docx 解包 word/document.xml,pdf 走 pdf.js;原文不落地 */
async function extractResumeFile(file) {
  const name = (file.name || '').toLowerCase();
  if (file.size > 5 * 1024 * 1024) throw new Error('简历文件超过 5MB。');
  if (name.endsWith('.txt') || name.endsWith('.md')) {
    return resumeCheckLen(await file.text());
  }
  if (name.endsWith('.docx')) return resumeCheckLen(await docxText(file));
  if (name.endsWith('.pdf')) return resumeCheckLen(await pdfText(file));
  throw new Error('简历支持 PDF、DOCX、TXT 或 Markdown 文件。');
}

function resumeCheckLen(text) {
  const t = String(text || '').replace(/\s+$/g, '');
  if (!t.trim()) throw new Error('简历为空或无法提取文字。');
  if (t.length > 20000) throw new Error('简历文字超过 20000 字,请精简后重新上传。');
  return t;
}

function resumeInflateRaw(data) {
  const stream = new Blob([data]).stream().pipeThrough(new DecompressionStream('deflate-raw'));
  return new Response(stream).arrayBuffer().then((buf) => new Uint8Array(buf));
}

function zipEntry(buf, want) {
  const dv = new DataView(buf.buffer, buf.byteOffset, buf.byteLength);
  let eocd = -1;
  for (let i = buf.length - 22; i >= 0; i--) {
    if (dv.getUint32(i, true) === 0x06054b50) { eocd = i; break; }
  }
  if (eocd < 0) return null;
  let off = dv.getUint32(eocd + 16, true);
  const count = dv.getUint16(eocd + 10, true);
  for (let n = 0; n < count; n++) {
    if (dv.getUint32(off, true) !== 0x02014b50) return null;
    const method = dv.getUint16(off + 10, true);
    const csize = dv.getUint32(off + 20, true);
    const nlen = dv.getUint16(off + 28, true);
    const elen = dv.getUint16(off + 30, true);
    const clen = dv.getUint16(off + 32, true);
    const loff = dv.getUint32(off + 42, true);
    const name = new TextDecoder().decode(buf.subarray(off + 46, off + 46 + nlen));
    if (name === want) {
      const lnlen = dv.getUint16(loff + 26, true);
      const lelen = dv.getUint16(loff + 28, true);
      const start = loff + 30 + lnlen + lelen;
      return { method, data: buf.subarray(start, start + csize) };
    }
    off += 46 + nlen + elen + clen;
  }
  return null;
}

async function docxText(file) {
  const buf = new Uint8Array(await file.arrayBuffer());
  const entry = zipEntry(buf, 'word/document.xml');
  if (!entry) throw new Error('无法读取 DOCX 简历,请检查文件是否损坏。');
  const bytes = entry.method === 0 ? entry.data : await resumeInflateRaw(entry.data);
  const xml = new TextDecoder().decode(bytes);
  return xml
    .replace(/<\/w:p>/g, '\n')
    .replace(/<[^>]+>/g, '')
    .replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'")
    .replace(/\n{3,}/g, '\n\n');
}

async function pdfText(file) {
  if (!window.pdfjsLib) throw new Error('PDF 解析组件未加载,请刷新后重试。');
  window.pdfjsLib.GlobalWorkerOptions.workerSrc = 'vendor/pdf.worker.min.js';
  const doc = await window.pdfjsLib.getDocument({ data: new Uint8Array(await file.arrayBuffer()) }).promise;
  if (doc.numPages > 10) {
    const pages = doc.numPages;
    await doc.destroy();
    throw new Error('简历 PDF 最多 10 页,当前 ' + pages + ' 页。');
  }
  const parts = [];
  for (let i = 1; i <= doc.numPages; i++) {
    const page = await doc.getPage(i);
    const tc = await page.getTextContent();
    parts.push(tc.items.map((it) => it.str + (it.hasEOL ? '\n' : '')).join(''));
  }
  await doc.destroy();
  return parts.join('\n');
}
