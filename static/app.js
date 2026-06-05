// ── 날짜 표시 ──
const dateInput = document.getElementById('date-input');
const dateDisplayBtn = document.getElementById('date-display-btn');
const dateDisplay = document.getElementById('date-display');

const DAYS = ['일', '월', '화', '수', '목', '금', '토'];

function toKoreanDate(str) {
  const [y, m, d] = str.split('-');
  const day = new Date(str).getDay();
  return `${y}년 ${parseInt(m)}월 ${parseInt(d)}일 ${DAYS[day]}요일`;
}

function todayStr() {
  return new Date().toISOString().split('T')[0];
}

dateInput.value = todayStr();
dateDisplay.textContent = toKoreanDate(dateInput.value);

dateDisplayBtn.addEventListener('click', () => dateInput.showPicker?.() ?? dateInput.click());
dateInput.addEventListener('change', () => {
  dateDisplay.textContent = toKoreanDate(dateInput.value);
});

// ── 닉네임 (localStorage 기억) ──
const authorInput = document.getElementById('author-input');
authorInput.value = localStorage.getItem('journal_author') || '';
authorInput.addEventListener('change', () => {
  localStorage.setItem('journal_author', authorInput.value.trim());
});

// ── 미디어 선택 ──
const mediaDrop = document.getElementById('media-drop');
const mediaInput = document.getElementById('media-input');
const dropPlaceholder = document.getElementById('drop-placeholder');
const previewWrap = document.getElementById('preview-wrap');
const previewImg = document.getElementById('preview-img');
const previewVideo = document.getElementById('preview-video');
const removeMedia = document.getElementById('remove-media');

let selectedFile = null;

const cameraInput = document.getElementById('camera-input');
const fileBtn = document.getElementById('file-btn');
const cameraBtn = document.getElementById('camera-btn');

mediaDrop.addEventListener('click', (e) => {
  if (e.target.closest('#remove-media')) return;
  if (e.target.closest('#file-btn') || e.target.closest('#camera-btn')) return;
  mediaInput.click();
});

fileBtn.addEventListener('click', (e) => { e.stopPropagation(); mediaInput.click(); });
cameraBtn.addEventListener('click', (e) => { e.stopPropagation(); cameraInput.click(); });
cameraInput.addEventListener('change', () => {
  if (cameraInput.files[0]) setMedia(cameraInput.files[0]);
});

mediaInput.addEventListener('change', () => {
  if (mediaInput.files[0]) setMedia(mediaInput.files[0]);
});

mediaDrop.addEventListener('dragover', (e) => {
  e.preventDefault();
  mediaDrop.classList.add('drag-over');
});

mediaDrop.addEventListener('dragleave', () => mediaDrop.classList.remove('drag-over'));

mediaDrop.addEventListener('drop', (e) => {
  e.preventDefault();
  mediaDrop.classList.remove('drag-over');
  if (e.dataTransfer.files[0]) setMedia(e.dataTransfer.files[0]);
});

removeMedia.addEventListener('click', (e) => {
  e.stopPropagation();
  clearMedia();
});

function setMedia(file) {
  selectedFile = file;
  const url = URL.createObjectURL(file);
  const isVideo = file.type.startsWith('video/');

  dropPlaceholder.style.display = 'none';
  previewWrap.style.display = 'block';

  if (isVideo) {
    previewImg.style.display = 'none';
    previewVideo.style.display = 'block';
    previewVideo.src = url;
  } else {
    previewVideo.style.display = 'none';
    previewImg.style.display = 'block';
    previewImg.src = url;
  }
}

function clearMedia() {
  selectedFile = null;
  mediaInput.value = '';
  previewImg.src = '';
  previewVideo.src = '';
  previewWrap.style.display = 'none';
  dropPlaceholder.style.display = 'flex';
}

// ── 폼 제출 ──
const form = document.getElementById('entry-form');
const textInput = document.getElementById('text-input');
const submitBtn = document.getElementById('submit-btn');

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const text = textInput.value.trim();
  if (!text) { textInput.focus(); return; }

  submitBtn.disabled = true;
  submitBtn.textContent = '저장 중…';

  const formData = new FormData();
  formData.append('date', dateInput.value);
  formData.append('author', authorInput.value.trim());
  formData.append('text', text);
  if (selectedFile) formData.append('media', selectedFile);

  try {
    const res = await fetch('/api/entries', { method: 'POST', body: formData });
    if (!res.ok) { const err = await res.json(); alert(err.error || '저장 실패'); return; }
    const entry = await res.json();
    textInput.value = '';
    clearMedia();
    prependEntry(entry);
  } catch {
    alert('서버 오류가 발생했습니다.');
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = '기록하기';
  }
});

// ── 목록 렌더 ──
const entriesList = document.getElementById('entries-list');

async function loadEntries() {
  entriesList.innerHTML = '<div class="loading">불러오는 중…</div>';
  try {
    const res = await fetch('/api/entries');
    const entries = await res.json();
    entriesList.innerHTML = '';
    if (!entries.length) { showEmpty(); return; }

    let lastDate = null;
    entries.forEach(entry => {
      if (entry.date !== lastDate) {
        appendDateLabel(entry.date);
        lastDate = entry.date;
      }
      entriesList.appendChild(buildCard(entry));
    });
  } catch {
    entriesList.innerHTML = '<div class="empty-state">불러오기 실패</div>';
  }
}

function appendDateLabel(dateStr) {
  const el = document.createElement('div');
  el.className = 'date-label' + (dateStr === todayStr() ? ' today' : '');
  el.dataset.date = dateStr;
  el.textContent = dateStr === todayStr() ? '✦ 오늘 · ' + toKoreanDate(dateStr) : toKoreanDate(dateStr);
  entriesList.appendChild(el);
}

function prependEntry(entry) {
  removeEmpty();

  // 같은 날짜 레이블이 맨 위에 있으면 재사용
  const firstLabel = entriesList.querySelector('.date-label');
  if (!firstLabel || firstLabel.dataset.date !== entry.date) {
    const label = document.createElement('div');
    label.className = 'date-label';
    label.dataset.date = entry.date;
    label.textContent = toKoreanDate(entry.date);
    entriesList.prepend(label);
  }

  const card = buildCard(entry);
  // 레이블 바로 뒤에 삽입
  const label = entriesList.querySelector('.date-label');
  label.insertAdjacentElement('afterend', card);
}

function buildCard(entry) {
  const card = document.createElement('div');
  card.className = 'entry-card';
  card.dataset.id = entry.id;

  const liked = getLiked(entry.id);
  const likeCount = entry.likes || 0;

  let leftHtml = '';
  if (entry.media_filename) {
    const src = `/uploads/${entry.media_filename}`;
    leftHtml = entry.media_type === 'video'
      ? `<div class="entry-thumb" onclick="openMedia(this)">
           <video src="${src}" muted preload="metadata" playsinline data-src="${src}"></video>
           <div class="play-badge"><svg width="20" height="20" viewBox="0 0 24 24" fill="white"><polygon points="5,3 19,12 5,21"/></svg></div>
         </div>`
      : `<div class="entry-thumb" onclick="openMedia(this)">
           <img src="${src}" alt="" loading="lazy" data-src="${src}">
         </div>`;
  } else {
    const [, m, d] = entry.date.split('-');
    leftHtml = `<div class="entry-date-badge">
      <span class="badge-day">${parseInt(d)}</span>
      <span class="badge-month">${parseInt(m)}월</span>
    </div>`;
  }

  const authorHtml = entry.author
    ? `<div class="entry-author">${escapeHtml(entry.author)}</div>` : '';

  card.innerHTML = `
    ${leftHtml}
    <div class="entry-right">
      ${authorHtml}
      <p class="entry-text">${escapeHtml(entry.text)}</p>
      <div class="entry-meta">
        <button class="like-btn ${liked ? 'liked' : ''}" data-id="${entry.id}">
          ${liked ? '♥' : '♡'} <span class="like-count">${likeCount > 0 ? likeCount : ''}</span>
        </button>
        <button class="del-btn" data-id="${entry.id}">삭제</button>
      </div>
    </div>
  `;

  card.querySelector('.del-btn').addEventListener('click', () => deleteEntry(entry.id, card));
  card.querySelector('.like-btn').addEventListener('click', () => toggleLike(entry.id, card));
  return card;
}

// ── 좋아요 ──
function getLiked(id) {
  return JSON.parse(localStorage.getItem('liked') || '[]').includes(id);
}

function setLiked(id, val) {
  const arr = JSON.parse(localStorage.getItem('liked') || '[]');
  const idx = arr.indexOf(id);
  if (val && idx === -1) arr.push(id);
  if (!val && idx !== -1) arr.splice(idx, 1);
  localStorage.setItem('liked', JSON.stringify(arr));
}

async function toggleLike(id, card) {
  const btn = card.querySelector('.like-btn');
  if (btn.dataset.loading) return;
  btn.dataset.loading = '1';

  btn.style.transform = 'scale(1.4)';
  setTimeout(() => { btn.style.transform = ''; delete btn.dataset.loading; }, 200);

  try {
    const res = await fetch(`/api/entries/${id}/like`, { method: 'POST' });
    const data = await res.json();
    const newLiked = !getLiked(id);
    setLiked(id, newLiked);
    btn.classList.toggle('liked', newLiked);
    btn.childNodes[0].textContent = newLiked ? '♥ ' : '♡ ';
    btn.querySelector('.like-count').textContent = data.likes > 0 ? data.likes : '';
  } catch {
    console.error('like failed');
  }
}

async function deleteEntry(id, card) {
  if (!confirm('이 기록을 삭제할까요?')) return;
  try {
    await fetch(`/api/entries/${id}`, { method: 'DELETE' });
    card.style.transition = 'opacity 0.2s, transform 0.2s';
    card.style.opacity = '0';
    card.style.transform = 'scale(0.97)';
    setTimeout(() => {
      card.remove();
      if (!entriesList.querySelector('.entry-card')) showEmpty();
    }, 200);
  } catch {
    alert('삭제에 실패했습니다.');
  }
}

function showEmpty() {
  entriesList.innerHTML = `<div class="empty-state">아직 기록이 없어요.<br>오늘 나를 기쁘게 한 것을 적어보세요 ✦</div>`;
}

function removeEmpty() {
  entriesList.querySelector('.empty-state')?.remove();
}

function escapeHtml(str) {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── 라이트박스 ──
function openMedia(thumbEl) {
  const img = thumbEl.querySelector('img');
  const video = thumbEl.querySelector('video');
  const src = img ? img.dataset.src : video.dataset.src;
  const isVideo = !!video;

  const overlay = document.createElement('div');
  overlay.style.cssText = `
    position:fixed;inset:0;background:rgba(0,0,0,0.88);
    display:flex;align-items:center;justify-content:center;
    z-index:1000;cursor:zoom-out;padding:24px;
  `;

  const media = isVideo
    ? Object.assign(document.createElement('video'), { src, controls: true, autoplay: true })
    : Object.assign(document.createElement('img'), { src, alt: '' });

  media.style.cssText = `
    max-width:100%;max-height:90vh;border-radius:12px;
    object-fit:contain;cursor:default;
  `;
  media.addEventListener('click', e => e.stopPropagation());

  overlay.appendChild(media);
  overlay.addEventListener('click', () => overlay.remove());
  document.addEventListener('keydown', function esc(e) {
    if (e.key === 'Escape') { overlay.remove(); document.removeEventListener('keydown', esc); }
  });
  document.body.appendChild(overlay);
}

loadEntries();
