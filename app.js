/**
 * News Discover Frontend Application Logic
 * Supports 5 target categories: 정치, 경제, IT/과학, 세계, 사회
 * Sleek Dark Mode (default) with Theme Toggle
 */

document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const newsContainer = document.getElementById('newsContainer');
  const datePicker = document.getElementById('datePicker');
  const searchInput = document.getElementById('searchInput');
  const categoryBar = document.getElementById('categoryBar');
  const newsModal = document.getElementById('newsModal');
  const modalCloseBtn = document.getElementById('modalCloseBtn');
  const modalBody = document.getElementById('modalBody');
  const updateTimeText = document.getElementById('updateTimeText');
  const mainHeroSubtitle = document.getElementById('mainHeroSubtitle');
  const themeToggleBtn = document.getElementById('themeToggleBtn');
  const themeIcon = document.getElementById('themeIcon');

  // Application State
  let currentNewsData = [];
  let activeCategory = 'all';
  let searchQuery = '';

  // Set today's date in datePicker default
  const todayStr = new Date().toISOString().split('T')[0];
  datePicker.value = todayStr;
  datePicker.max = todayStr;

  // Initialize
  initApp();

  function initApp() {
    setupTheme();
    setupEventListeners();
    loadNewsData('latest');
  }

  // Theme Management (Default: Sleek Dark Mode)
  function setupTheme() {
    const savedTheme = localStorage.getItem('news_discover_theme') || 'dark';
    setTheme(savedTheme);

    themeToggleBtn.addEventListener('click', () => {
      const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      setTheme(newTheme);
    });
  }

  function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('news_discover_theme', theme);

    if (theme === 'dark') {
      themeIcon.className = 'fa-solid fa-moon';
      themeToggleBtn.title = '라이트 모드로 변경';
    } else {
      themeIcon.className = 'fa-solid fa-sun';
      themeToggleBtn.title = '다크 모드로 변경';
    }
  }

  function setupEventListeners() {
    // Date picker change
    datePicker.addEventListener('change', (e) => {
      const selectedDate = e.target.value;
      if (selectedDate === todayStr) {
        loadNewsData('latest');
      } else {
        loadNewsData(selectedDate);
      }
    });

    // Category Filter Chips (전체, 정치, 경제, IT/과학, 세계, 사회)
    categoryBar.addEventListener('click', (e) => {
      const targetBtn = e.target.closest('.category-chip');
      if (targetBtn) {
        document.querySelectorAll('.category-chip').forEach(chip => chip.classList.remove('active'));
        targetBtn.classList.add('active');
        activeCategory = targetBtn.dataset.category;
        renderNewsGrid();
      }
    });

    // Search input real-time filter
    searchInput.addEventListener('input', (e) => {
      searchQuery = e.target.value.toLowerCase().trim();
      renderNewsGrid();
    });

    // Modal Close Handlers
    modalCloseBtn.addEventListener('click', closeModal);
    newsModal.addEventListener('click', (e) => {
      if (e.target === newsModal) closeModal();
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && newsModal.classList.contains('active')) {
        closeModal();
      }
    });
  }

  // Fetch Daily News Data
  async function loadNewsData(targetDate) {
    showLoading();
    const fileName = targetDate === 'latest' ? 'latest.json' : `${targetDate}.json`;
    const dataUrl = `./data/${fileName}`;

    try {
      const response = await fetch(dataUrl);
      if (!response.ok) {
        throw new Error(`Data for ${targetDate} not found.`);
      }
      const data = await response.json();
      currentNewsData = data.news_items || [];
      
      if (data.generated_at) {
        const timeObj = new Date(data.generated_at);
        const formattedTime = timeObj.toLocaleString('ko-KR', {
          month: 'long',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit'
        });
        updateTimeText.textContent = `${data.date} (${formattedTime} 수집 완료)`;
      }

      mainHeroSubtitle.textContent = `경제, 세계, IT/과학 3대 주요 분야의 헤드라인 총 ${currentNewsData.length}개를 수집 및 심층 분석 하였습니다.`;
      
      renderNewsGrid();
    } catch (error) {
      console.warn('Failed to load JSON data:', error);
      showEmptyState(`선택하신 날짜(${targetDate})의 뉴스 데이터가 존재하지 않거나 준비 중입니다.`);
    }
  }

  // Render Grid Cards based on Category Filter & Search
  function renderNewsGrid() {
    if (!currentNewsData || currentNewsData.length === 0) {
      showEmptyState('수집된 뉴스 데이터가 없습니다.');
      return;
    }

    const filteredNews = currentNewsData.filter(item => {
      const matchesCategory = activeCategory === 'all' || item.category === activeCategory;
      const matchesSearch = !searchQuery || 
        item.headline.toLowerCase().includes(searchQuery) ||
        (item.summary && item.summary.overview && item.summary.overview.toLowerCase().includes(searchQuery)) ||
        (item.keywords && item.keywords.some(kw => kw.toLowerCase().includes(searchQuery)));
      
      return matchesCategory && matchesSearch;
    });

    if (filteredNews.length === 0) {
      showEmptyState(`[${activeCategory === 'all' ? '전체' : activeCategory}] 카테고리에 조건에 부합하는 뉴스가 없습니다.`);
      return;
    }

    newsContainer.innerHTML = filteredNews.map(item => createNewsCardHTML(item)).join('');

    // Attach Click Handler to Open Modal
    document.querySelectorAll('.news-card').forEach(card => {
      card.addEventListener('click', () => {
        const newsId = card.dataset.id;
        const selectedNews = currentNewsData.find(n => n.id === newsId);
        if (selectedNews) {
          openNewsModal(selectedNews);
        }
      });
    });
  }

  // Generate Card HTML
  function createNewsCardHTML(item) {
    const publisherBadges = item.publishers.slice(0, 3).map(p => 
      `<span class="pub-chip">${escapeHtml(p.name)}</span>`
    ).join('');

    const extraPubCount = item.publishers.length > 3 ? `<span class="pub-chip">+${item.publishers.length - 3}</span>` : '';

    return `
      <article class="news-card" data-id="${item.id}">
        <div class="card-image-wrapper">
          <img src="${item.image_url}" alt="${escapeHtml(item.headline)}" class="card-image" loading="lazy" onerror="this.src='https://picsum.photos/seed/${item.id}/600/400'">
          <span class="card-category-badge">${escapeHtml(item.category)}</span>
        </div>
        <div class="card-body">
          <h2 class="card-headline">${escapeHtml(item.headline)}</h2>
          <p class="card-summary">${escapeHtml(item.summary.overview || item.summary.details || '')}</p>
          <div class="publisher-bar">
            <div class="publisher-tags">
              ${publisherBadges}
              ${extraPubCount}
            </div>
            <span class="read-more-btn">
              기승전결 요약 <i class="fa-solid fa-arrow-right"></i>
            </span>
          </div>
        </div>
      </article>
    `;
  }

  // Open Detailed View Modal
  function openNewsModal(item) {
    // 1. Narrative Arc (기승전결) HTML
    let narrativeHTML = '';
    const n = item.summary.narrative;
    if (n && (n.intro || n.development || n.turn || n.conclusion)) {
      narrativeHTML = `
        <div class="modal-section-title">
          <i class="fa-solid fa-timeline"></i> 뉴스 사건 흐름 종합 (기승전결)
        </div>
        <div class="narrative-grid">
          ${n.intro ? `
            <div class="narrative-card">
              <div class="narrative-header">
                <span class="narrative-badge gi">기 [발단]</span>
              </div>
              <p class="narrative-text">${escapeHtml(n.intro)}</p>
            </div>
          ` : ''}
          ${n.development ? `
            <div class="narrative-card">
              <div class="narrative-header">
                <span class="narrative-badge seung">승 [전개]</span>
              </div>
              <p class="narrative-text">${escapeHtml(n.development)}</p>
            </div>
          ` : ''}
          ${n.turn ? `
            <div class="narrative-card">
              <div class="narrative-header">
                <span class="narrative-badge jeon">전 [쟁점]</span>
              </div>
              <p class="narrative-text">${escapeHtml(n.turn)}</p>
            </div>
          ` : ''}
          ${n.conclusion ? `
            <div class="narrative-card">
              <div class="narrative-header">
                <span class="narrative-badge gyeol">결 [결과]</span>
              </div>
              <p class="narrative-text">${escapeHtml(n.conclusion)}</p>
            </div>
          ` : ''}
        </div>
      `;
    }

    // 2. Impact & Outlook HTML
    let impactHTML = '';
    if (item.summary.impact) {
      impactHTML = `
        <div class="modal-section-title">
          <i class="fa-solid fa-chart-line-up"></i> 사회 · 경제적 파급 효과 & 향후 전망
        </div>
        <div class="impact-box">
          <div class="impact-content">
            <i class="fa-solid fa-bullseye impact-icon"></i>
            <p>${escapeHtml(item.summary.impact)}</p>
          </div>
        </div>
      `;
    }

    // 3. Publisher Differences HTML
    let differencesHTML = '';
    if (item.summary.differences && item.summary.differences.length > 0) {
      differencesHTML = `
        <div class="modal-section-title">
          <i class="fa-solid fa-scale-balanced"></i> 언론사별 보도 시각 & 강조점 비교
        </div>
        <div class="differences-grid">
          ${item.summary.differences.map(diff => `
            <div class="diff-card">
              <div class="diff-publisher">
                <i class="fa-solid fa-building-columns"></i> ${escapeHtml(diff.publisher)}
              </div>
              <div class="diff-point">${escapeHtml(diff.point)}</div>
            </div>
          `).join('')}
        </div>
      `;
    }

    // 4. Key Terms & Explanations HTML
    let keyTermsHTML = '';
    if (item.summary.key_terms && item.summary.key_terms.length > 0) {
      keyTermsHTML = `
        <div class="modal-section-title">
          <i class="fa-solid fa-book-open"></i> 쉬운 핵심 용어 & 개념 풀이
        </div>
        <div class="key-terms-grid">
          ${item.summary.key_terms.map(kt => `
            <div class="term-card">
              <div class="term-title">
                <i class="fa-solid fa-lightbulb"></i> ${escapeHtml(kt.term)}
              </div>
              <div class="term-desc">${escapeHtml(kt.explanation)}</div>
            </div>
          `).join('')}
        </div>
      `;
    }

    const publisherLinksHTML = item.publishers.map(pub => `
      <a href="${pub.url}" target="_blank" rel="noopener noreferrer" class="publisher-link-item">
        <span class="publisher-name-badge">${escapeHtml(pub.name)}</span>
        <span class="publisher-article-title">${escapeHtml(pub.title)}</span>
        <i class="fa-solid fa-arrow-up-right-from-square link-icon"></i>
      </a>
    `).join('');

    modalBody.innerHTML = `
      <span class="modal-category-tag">${escapeHtml(item.category)}</span>
      <h1 class="modal-headline">${escapeHtml(item.headline)}</h1>

      <div class="modal-section-title">
        <i class="fa-solid fa-wand-magic-sparkles"></i> AI 핵심 종합 요약
      </div>
      <div class="modal-overview-box">
        ${escapeHtml(item.summary.overview)}
      </div>

      ${narrativeHTML}

      ${impactHTML}

      ${differencesHTML}

      ${keyTermsHTML}

      <div class="modal-section-title">
        <i class="fa-solid fa-newspaper"></i> 언론사별 기사 원본 링크 (${item.publishers.length}개)
      </div>
      <div class="publisher-links-list">
        ${publisherLinksHTML}
      </div>
    `;

    newsModal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }


  function closeModal() {
    newsModal.classList.remove('active');
    document.body.style.overflow = '';
  }

  function showLoading() {
    newsContainer.innerHTML = `
      <div class="loading-state">
        <div class="spinner"></div>
        <p>주요 뉴스를 카테고리별로 불러오는 중입니다...</p>
      </div>
    `;
  }

  function showEmptyState(message) {
    newsContainer.innerHTML = `
      <div class="empty-state">
        <i class="fa-solid fa-folder-open" style="font-size: 48px; margin-bottom: 16px; opacity: 0.5;"></i>
        <p>${message}</p>
      </div>
    `;
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
});
