/**
 * News Discover Frontend Application Logic
 * Supports 2 target categories: 경제, 글로벌
 * Features: History API Back-Button Modal Close, Secure Refresh without GitHub Tokens, Local Feedback Storage
 */

document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const newsContainer = document.getElementById('newsContainer');
  const searchInput = document.getElementById('searchInput');
  const categoryBar = document.getElementById('categoryBar');
  const newsModal = document.getElementById('newsModal');
  const modalCloseBtn = document.getElementById('modalCloseBtn');
  const modalBody = document.getElementById('modalBody');
  const updateTimeText = document.getElementById('updateTimeText');
  const mainHeroSubtitle = document.getElementById('mainHeroSubtitle');
  const themeToggleBtn = document.getElementById('themeToggleBtn');
  const themeIcon = document.getElementById('themeIcon');

  // Control Buttons
  const updateNewsBtn = document.getElementById('updateNewsBtn');
  const toastContainer = document.getElementById('toastContainer');

  // Custom Calendar DOM Elements
  const datePickerWrapper = document.querySelector('.date-selector-wrapper');
  const datePickerTrigger = document.getElementById('datePickerTrigger');
  const selectedDateText = document.getElementById('selectedDateText');
  const calendarPopover = document.getElementById('calendarPopover');
  const calMonthTitle = document.getElementById('calMonthTitle');
  const calPrevMonthBtn = document.getElementById('calPrevMonthBtn');
  const calNextMonthBtn = document.getElementById('calNextMonthBtn');
  const calendarDaysGrid = document.getElementById('calendarDaysGrid');

  // Application State
  let currentNewsData = [];
  let activeCategory = 'all';
  let searchQuery = '';
  let availableDates = [];
  
  const todayObj = new Date();
  const todayStr = todayObj.toISOString().split('T')[0];
  let selectedDate = todayStr;
  
  let viewYear = todayObj.getFullYear();
  let viewMonth = todayObj.getMonth();

  // Initialize App
  initApp();

  async function initApp() {
    setupTheme();
    await fetchAvailableDates();
    
    if (availableDates.length > 0) {
      if (availableDates.includes(todayStr)) {
        selectedDate = todayStr;
      } else {
        selectedDate = availableDates[0];
      }
    } else {
      selectedDate = todayStr;
    }

    const [sYear, sMonth] = selectedDate.split('-').map(Number);
    if (sYear && sMonth) {
      viewYear = sYear;
      viewMonth = sMonth - 1;
    }

    if (selectedDateText) {
      selectedDateText.textContent = selectedDate;
    }

    setupEventListeners();
    setupCalendar();
    
    if (selectedDate === todayStr) {
      loadNewsData('latest');
    } else {
      loadNewsData(selectedDate);
    }
  }

  // Fetch Manifest of Available News Dates
  async function fetchAvailableDates() {
    try {
      const resp = await fetch(`data/available_dates.json?t=${Date.now()}`);
      if (resp.ok) {
        const data = await resp.json();
        availableDates = data.available_dates || [];
      }
    } catch (e) {
      console.warn('Failed to load available_dates.json:', e);
      availableDates = [todayStr];
    }
    
    if (availableDates.length === 0) {
      availableDates = [todayStr];
    }
  }

  // Theme Management
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

  // Custom Calendar Control Logic
  function setupCalendar() {
    if (selectedDateText) {
      selectedDateText.textContent = selectedDate;
    }

    datePickerTrigger.addEventListener('click', (e) => {
      e.stopPropagation();
      datePickerWrapper.classList.toggle('active');
      renderCalendarGrid();
    });

    calPrevMonthBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      viewMonth--;
      if (viewMonth < 0) {
        viewMonth = 11;
        viewYear--;
      }
      renderCalendarGrid();
    });

    calNextMonthBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      viewMonth++;
      if (viewMonth > 11) {
        viewMonth = 0;
        viewYear++;
      }
      renderCalendarGrid();
    });

    document.addEventListener('click', (e) => {
      if (datePickerWrapper && !datePickerWrapper.contains(e.target)) {
        datePickerWrapper.classList.remove('active');
      }
    });

    renderCalendarGrid();
  }

  function renderCalendarGrid() {
    calMonthTitle.textContent = `${viewYear}년 ${viewMonth + 1}월`;

    const firstDay = new Date(viewYear, viewMonth, 1).getDay();
    const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();

    let gridHTML = '';

    for (let i = 0; i < firstDay; i++) {
      gridHTML += `<div class="cal-day-cell empty"></div>`;
    }

    for (let day = 1; day <= daysInMonth; day++) {
      const monthStr = String(viewMonth + 1).padStart(2, '0');
      const dayStr = String(day).padStart(2, '0');
      const dateKey = `${viewYear}-${monthStr}-${dayStr}`;

      const hasData = availableDates.includes(dateKey);
      const isSelected = dateKey === selectedDate;

      let cellClasses = ['cal-day-cell'];
      if (hasData) cellClasses.push('has-data');
      else cellClasses.push('disabled');

      if (isSelected) cellClasses.push('active-date');

      gridHTML += `
        <div class="${cellClasses.join(' ')}" data-date="${dateKey}">
          ${day}
        </div>
      `;
    }

    calendarDaysGrid.innerHTML = gridHTML;

    calendarDaysGrid.querySelectorAll('.cal-day-cell.has-data').forEach(cell => {
      cell.addEventListener('click', (e) => {
        e.stopPropagation();
        const targetDate = cell.dataset.date;
        selectDate(targetDate);
      });
    });
  }

  function selectDate(dateStr) {
    selectedDate = dateStr;
    if (selectedDateText) {
      selectedDateText.textContent = dateStr;
    }
    datePickerWrapper.classList.remove('active');
    
    if (dateStr === todayStr) {
      loadNewsData('latest');
    } else {
      loadNewsData(dateStr);
    }
  }

  function setupEventListeners() {
    categoryBar.addEventListener('click', (e) => {
      const targetBtn = e.target.closest('.category-chip');
      if (targetBtn) {
        document.querySelectorAll('.category-chip').forEach(chip => chip.classList.remove('active'));
        targetBtn.classList.add('active');
        activeCategory = targetBtn.dataset.category;
        renderNewsGrid();
      }
    });

    searchInput.addEventListener('input', (e) => {
      searchQuery = e.target.value.toLowerCase().trim();
      renderNewsGrid();
    });

    modalCloseBtn.addEventListener('click', () => {
      if (newsModal.classList.contains('active')) {
        history.back();
      }
    });

    newsModal.addEventListener('click', (e) => {
      if (e.target === newsModal && newsModal.classList.contains('active')) {
        history.back();
      }
    });

    // History API popstate event for Back-button closing support
    window.addEventListener('popstate', () => {
      if (newsModal.classList.contains('active')) {
        closeModalDOM();
      }
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && newsModal.classList.contains('active')) {
        history.back();
      }
    });

    // Secure Refresh Button Handler (No GitHub PAT Required!)
    if (updateNewsBtn) {
      updateNewsBtn.addEventListener('click', async () => {
        showToast('🔄 최신 뉴스 데이터를 불러오는 중입니다...', 'info', 2000);
        await fetchAvailableDates();
        await loadNewsData(selectedDate === todayStr ? 'latest' : selectedDate);
        showToast('✅ 뉴스가 최신 상태로 새로고침 되었습니다.', 'success');
      });
    }
  }

  // Fetch Daily News Data
  async function loadNewsData(targetDate) {
    showLoading();
    const fileName = targetDate === 'latest' ? 'latest.json' : `${targetDate}.json`;
    const dataUrl = `data/${fileName}?t=${Date.now()}`;

    try {
      const response = await fetch(dataUrl);
      if (!response.ok) {
        throw new Error(`Data for ${targetDate} not found.`);
      }
      const data = await response.json();
      currentNewsData = data.news_items || [];
      
      if (data.date) {
        selectedDate = data.date;
        if (selectedDateText) {
          selectedDateText.textContent = selectedDate;
        }
      }

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

      mainHeroSubtitle.textContent = `경제 및 글로벌 2대 주요 분야의 뉴스 총 ${currentNewsData.length}개를 수집 및 심층 분석 하였습니다.`;
      
      renderNewsGrid();
    } catch (error) {
      console.warn('Failed to load JSON data:', error);
      if (targetDate !== 'latest') {
        try {
          const fbResp = await fetch(`data/latest.json?t=${Date.now()}`);
          if (fbResp.ok) {
            const fbData = await fbResp.json();
            currentNewsData = fbData.news_items || [];
            if (fbData.date) {
              selectedDate = fbData.date;
              if (selectedDateText) {
                selectedDateText.textContent = selectedDate;
              }
            }
            renderNewsGrid();
            return;
          }
        } catch (fbErr) {
          console.warn('Fallback failed:', fbErr);
        }
      }
      showEmptyState(`선택하신 날짜(${targetDate})의 뉴스 데이터가 존재하지 않거나 준비 중입니다.`);
    }
  }

  // Render Grid Cards
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

  function createNewsCardHTML(item) {
    const publisherBadges = item.publishers.slice(0, 3).map(p => 
      `<span class="pub-chip">${escapeHtml(p.name)}</span>`
    ).join('');

    const extraPubCount = item.publishers.length > 3 ? `<span class="pub-chip">+${item.publishers.length - 3}</span>` : '';
    const hasFB = hasFeedback(item.id);

    return `
      <article class="news-card ${hasFB ? 'has-feedback-card' : ''}" data-id="${item.id}">
        <div class="card-image-wrapper">
          <img src="${item.image_url}" alt="${escapeHtml(item.headline)}" class="card-image" loading="lazy" onerror="this.src='https://picsum.photos/seed/${item.id}/600/400'">
          <span class="card-category-badge">${escapeHtml(item.category)}</span>
          ${hasFB ? '<span class="feedback-indicator-tag"><i class="fa-solid fa-comment"></i> 피드백 저장됨</span>' : ''}
        </div>
        <div class="card-body">
          <h2 class="card-headline">${escapeHtml(item.headline)}</h2>
          <p class="card-summary">${escapeHtml(item.summary.overview || '')}</p>
          <div class="publisher-bar">
            <div class="publisher-tags">
              ${publisherBadges}
              ${extraPubCount}
            </div>
            <span class="read-more-btn">
              뉴스 리포트 보기 <i class="fa-solid fa-arrow-right"></i>
            </span>
          </div>
        </div>
      </article>
    `;
  }

  // Open Detailed View Modal with History API Push State
  function openNewsModal(item) {
    let featuredArticleHTML = '';
    const fa = item.summary.featured_article;
    if (fa) {
      featuredArticleHTML = `
        <div class="modal-section-title">
          <i class="fa-solid fa-file-lines"></i> [랜덤 선택] ${escapeHtml(fa.publisher)} 기사 본문 전체
        </div>
        <div class="featured-article-card">
          <div class="featured-article-header">
            <span class="featured-pub-badge">${escapeHtml(fa.publisher)}</span>
            <h3 class="featured-article-title">${escapeHtml(fa.title)}</h3>
          </div>
          <div class="featured-article-body">
            <p>${escapeHtml(fa.full_content || '본문 내용을 불러올 수 없습니다.')}</p>
          </div>
          ${fa.url ? `
            <a href="${fa.url}" target="_blank" rel="noopener noreferrer" class="featured-article-link">
              해당 기사 원본으로 이동 <i class="fa-solid fa-arrow-up-right-from-square"></i>
            </a>
          ` : ''}
        </div>
      `;
    }

    let differencesHTML = '';
    if (item.summary.differences && item.summary.differences.length > 0) {
      differencesHTML = `
        <div class="modal-section-title">
          <i class="fa-solid fa-scale-balanced"></i> 언론사별 보도 시작 & 강조점 비교
        </div>
        <div class="differences-grid">
          ${item.summary.differences.map(diff => `
            <div class="diff-card">
              <div class="diff-publisher">
                <i class="fa-solid fa-building-columns"></i> ${escapeHtml(diff.publisher)}
              </div>
              <div class="diff-section">
                <div class="diff-label start-label">
                  <i class="fa-solid fa-play"></i> 보도 시작 (도입부)
                </div>
                <div class="diff-content">${escapeHtml(diff.start_point || '-')}</div>
              </div>
              <div class="diff-section">
                <div class="diff-label emphasis-label">
                  <i class="fa-solid fa-bullseye"></i> 핵심 강조점 (시각)
                </div>
                <div class="diff-content">${escapeHtml(diff.emphasis_point || '-')}</div>
              </div>
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

    const savedFB = getFeedback(item.id);

    modalBody.innerHTML = `
      <span class="modal-category-tag">${escapeHtml(item.category)}</span>
      <h1 class="modal-headline">${escapeHtml(item.headline)}</h1>

      <!-- 1. 종합 요약 -->
      <div class="modal-section-title">
        <i class="fa-solid fa-wand-magic-sparkles"></i> 수집 기사 종합 요약
      </div>
      <div class="modal-overview-box">
        ${escapeHtml(item.summary.overview)}
      </div>

      <!-- 2. 랜덤 선택 기사 본문 전체 -->
      ${featuredArticleHTML}

      <!-- 3. 언론사별 보도 시작과 강조점 비교 -->
      ${differencesHTML}

      <!-- 4. 언론사별 기사 원본 링크 -->
      <div class="modal-section-title">
        <i class="fa-solid fa-newspaper"></i> 언론사별 기사 원본 링크 (${item.publishers.length}개)
      </div>
      <div class="publisher-links-list">
        ${publisherLinksHTML}
      </div>

      <!-- 5. 기사 피드백 입력란 -->
      <div class="modal-section-title feedback-title">
        <i class="fa-solid fa-comment-dots"></i> 기사 품질 피드백 (개발 메모)
      </div>
      <div class="feedback-input-container">
        <p class="feedback-desc">요약 결과, 관점 비교, 분류 등 개선사항 메모를 작성하여 저장해둘 수 있습니다.</p>
        <textarea id="modalFeedbackText" class="feedback-textarea" placeholder="예: 특정 파생 영향을 추가 요약에 포함하면 좋겠습니다.">${escapeHtml(savedFB)}</textarea>
        <div class="feedback-actions">
          <button id="saveFeedbackBtn" class="btn btn-secondary">
            <i class="fa-solid fa-floppy-disk"></i> 메모 저장
          </button>
          ${savedFB ? `
            <button id="deleteFeedbackBtn" class="btn btn-danger-outline">
              <i class="fa-solid fa-trash"></i> 삭제
            </button>
          ` : ''}
        </div>
      </div>
    `;

    history.pushState({ modalOpen: true, newsId: item.id }, '', `#news-${item.id}`);

    newsModal.classList.add('active');
    document.body.style.overflow = 'hidden';

    const saveFBtn = document.getElementById('saveFeedbackBtn');
    const deleteFBtn = document.getElementById('deleteFeedbackBtn');
    const fbText = document.getElementById('modalFeedbackText');

    if (saveFBtn) {
      saveFBtn.addEventListener('click', () => {
        const val = fbText.value.trim();
        if (val) {
          saveFeedback(item.id, item.headline, item.category, val);
          showToast('💾 피드백 메모가 브라우저에 저장되었습니다.');
        } else {
          removeFeedback(item.id);
          showToast('피드백이 삭제되었습니다.');
        }
        openNewsModal(item);
      });
    }

    if (deleteFBtn) {
      deleteFBtn.addEventListener('click', () => {
        removeFeedback(item.id);
        showToast('피드백이 삭제되었습니다.');
        openNewsModal(item);
      });
    }
  }

  function closeModalDOM() {
    newsModal.classList.remove('active');
    document.body.style.overflow = '';
  }

  // Feedback Store in localStorage
  function getFeedbacksMap() {
    try {
      return JSON.parse(localStorage.getItem('news_discover_feedbacks') || '{}');
    } catch (e) {
      return {};
    }
  }

  function saveFeedback(id, headline, category, text) {
    const map = getFeedbacksMap();
    map[id] = { headline, category, text, updated_at: new Date().toISOString() };
    localStorage.setItem('news_discover_feedbacks', JSON.stringify(map));
    renderNewsGrid();
  }

  function removeFeedback(id) {
    const map = getFeedbacksMap();
    delete map[id];
    localStorage.setItem('news_discover_feedbacks', JSON.stringify(map));
    renderNewsGrid();
  }

  function getFeedback(id) {
    const map = getFeedbacksMap();
    return map[id]?.text || '';
  }

  function hasFeedback(id) {
    const map = getFeedbacksMap();
    return !!map[id];
  }

  // Toast UI Notification Helper
  function showToast(message, type = 'info', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = `toast-item toast-${type}`;
    
    let iconClass = 'fa-info-circle';
    if (type === 'success') iconClass = 'fa-check-circle';
    if (type === 'warning') iconClass = 'fa-exclamation-triangle';
    if (type === 'error') iconClass = 'fa-times-circle';

    toast.innerHTML = `<i class="fa-solid ${iconClass}"></i> <span>${escapeHtml(message)}</span>`;
    toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.classList.add('fade-out');
      setTimeout(() => toast.remove(), 400);
    }, duration);
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
