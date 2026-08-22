/**
 * News Discover Frontend Application Logic
 * Supports 4 target categories: 경제, 글로벌, 비즈니스, IT/과학
 * Features: Multi-category support, History API modal, Custom calendar date selector, Responsive modern UI
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
      await loadNewsData('latest');
    } else {
      await loadNewsData(selectedDate);
    }
  }

  // Fetch Manifest of Available News Dates (No Cache)
  async function fetchAvailableDates() {
    try {
      const resp = await fetch(`data/available_dates.json?t=${Date.now()}`, { cache: 'no-store' });
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

    if (themeToggleBtn) {
      themeToggleBtn.addEventListener('click', () => {
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        setTheme(newTheme);
      });
    }
  }

  function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('news_discover_theme', theme);

    if (themeIcon) {
      if (theme === 'dark') {
        themeIcon.className = 'fa-solid fa-moon';
        if (themeToggleBtn) themeToggleBtn.title = '라이트 모드로 변경';
      } else {
        themeIcon.className = 'fa-solid fa-sun';
        if (themeToggleBtn) themeToggleBtn.title = '다크 모드로 변경';
      }
    }
  }

  // Custom Calendar Control Logic
  function setupCalendar() {
    if (selectedDateText) {
      selectedDateText.textContent = selectedDate;
    }

    if (datePickerTrigger && datePickerWrapper) {
      datePickerTrigger.addEventListener('click', (e) => {
        e.stopPropagation();
        datePickerWrapper.classList.toggle('active');
        renderCalendarGrid();
      });
    }

    if (calPrevMonthBtn) {
      calPrevMonthBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        viewMonth--;
        if (viewMonth < 0) {
          viewMonth = 11;
          viewYear--;
        }
        renderCalendarGrid();
      });
    }

    if (calNextMonthBtn) {
      calNextMonthBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        viewMonth++;
        if (viewMonth > 11) {
          viewMonth = 0;
          viewYear++;
        }
        renderCalendarGrid();
      });
    }

    document.addEventListener('click', (e) => {
      if (datePickerWrapper && !datePickerWrapper.contains(e.target)) {
        datePickerWrapper.classList.remove('active');
      }
    });

    renderCalendarGrid();
  }

  function renderCalendarGrid() {
    if (!calMonthTitle || !calendarDaysGrid) return;
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
    if (datePickerWrapper) {
      datePickerWrapper.classList.remove('active');
    }
    
    if (dateStr === todayStr) {
      loadNewsData('latest');
    } else {
      loadNewsData(dateStr);
    }
  }

  function setupEventListeners() {
    if (categoryBar) {
      categoryBar.addEventListener('click', (e) => {
        const targetBtn = e.target.closest('.category-chip');
        if (targetBtn) {
          document.querySelectorAll('.category-chip').forEach(chip => chip.classList.remove('active'));
          targetBtn.classList.add('active');
          activeCategory = targetBtn.dataset.category;
          renderNewsGrid();
        }
      });
    }

    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        searchQuery = e.target.value.toLowerCase().trim();
        renderNewsGrid();
      });
    }

    if (modalCloseBtn) {
      modalCloseBtn.addEventListener('click', () => {
        if (newsModal.classList.contains('active')) {
          history.back();
        }
      });
    }

    if (newsModal) {
      newsModal.addEventListener('click', (e) => {
        if (e.target === newsModal && newsModal.classList.contains('active')) {
          history.back();
        }
      });
    }

    window.addEventListener('popstate', () => {
      if (newsModal && newsModal.classList.contains('active')) {
        closeModalDOM();
      }
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && newsModal.classList.contains('active')) {
        history.back();
      }
    });
  }

  // Fetch Daily News Data (Bypassing Browser/CDN Cache)
  async function loadNewsData(targetDate) {
    showLoading();
    const fileName = targetDate === 'latest' ? 'latest.json' : `${targetDate}.json`;
    const dataUrl = `data/${fileName}?t=${Date.now()}`;

    try {
      const response = await fetch(dataUrl, { cache: 'no-store' });
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

      if (data.generated_at && updateTimeText) {
        const timeObj = new Date(data.generated_at);
        const formattedTime = timeObj.toLocaleString('ko-KR', {
          month: 'long',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit'
        });
        updateTimeText.textContent = `${data.date} (${formattedTime} 수집 완료)`;
      }

      if (mainHeroSubtitle) {
        mainHeroSubtitle.textContent = `경제, 글로벌, 비즈니스, IT/과학 4대 주요 분야의 뉴스 총 ${currentNewsData.length}개를 수집 및 심층 분석 하였습니다.`;
      }
      
      renderNewsGrid();
      return true;
    } catch (error) {
      console.warn('Failed to load JSON data:', error);
      if (targetDate !== 'latest') {
        try {
          const fbResp = await fetch(`data/latest.json?t=${Date.now()}`, { cache: 'no-store' });
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
            return true;
          }
        } catch (fbErr) {
          console.warn('Fallback failed:', fbErr);
        }
      }
      showEmptyState(`선택하신 날짜(${targetDate})의 뉴스 데이터가 존재하지 않거나 준비 중입니다.`);
      return false;
    }
  }

  // Check if article matches active category filter
  function matchCategoryFilter(item, category) {
    if (category === 'all') return true;
    
    // Check multiple categories array
    if (Array.isArray(item.categories) && item.categories.includes(category)) {
      return true;
    }
    // Check single category array or string
    if (Array.isArray(item.category) && item.category.includes(category)) {
      return true;
    }
    return item.category === category;
  }

  // Get normalized list of categories for an item
  function getItemCategories(item) {
    if (Array.isArray(item.categories) && item.categories.length > 0) {
      return item.categories;
    }
    if (Array.isArray(item.category) && item.category.length > 0) {
      return item.category;
    }
    if (item.category) {
      return [item.category];
    }
    return ['경제'];
  }

  // Render Grid Cards
  function renderNewsGrid() {
    if (!newsContainer) return;
    if (!currentNewsData || currentNewsData.length === 0) {
      showEmptyState('수집된 뉴스 데이터가 없습니다.');
      return;
    }

    const filteredNews = currentNewsData.filter(item => {
      const matchesCategory = matchCategoryFilter(item, activeCategory);
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
    const categories = getItemCategories(item);
    const categoryBadgesHTML = categories.map(cat => 
      `<span class="card-category-badge">${escapeHtml(cat)}</span>`
    ).join(' ');

    const publisherBadges = item.publishers.slice(0, 3).map(p => 
      `<span class="pub-chip">${escapeHtml(p.name)}</span>`
    ).join('');

    const extraPubCount = item.publishers.length > 3 ? `<span class="pub-chip">+${item.publishers.length - 3}</span>` : '';

    return `
      <article class="news-card" data-id="${item.id}">
        <div class="card-image-wrapper">
          <img src="${item.image_url}" alt="${escapeHtml(item.headline)}" class="card-image" loading="lazy" onerror="this.src='https://picsum.photos/seed/${item.id}/600/400'">
          <div class="card-badges-container">
            ${categoryBadgesHTML}
          </div>
        </div>
        <div class="card-body">
          <h2 class="card-headline">${escapeHtml(item.headline)}</h2>
          <p class="card-summary">${escapeHtml(item.summary ? (item.summary.overview || '') : '')}</p>
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
    const categories = getItemCategories(item);
    const categoryTagsHTML = categories.map(cat => 
      `<span class="modal-category-tag">${escapeHtml(cat)}</span>`
    ).join(' ');

    const publisherLinksHTML = item.publishers.map(pub => `
      <a href="${pub.url}" target="_blank" rel="noopener noreferrer" class="publisher-link-item">
        <span class="publisher-name-badge">${escapeHtml(pub.name)}</span>
        <span class="publisher-article-title">${escapeHtml(pub.title)}</span>
        <i class="fa-solid fa-arrow-up-right-from-square link-icon"></i>
      </a>
    `).join('');

    modalBody.innerHTML = `
      <div class="modal-categories-wrapper">
        ${categoryTagsHTML}
      </div>
      <h1 class="modal-headline">${escapeHtml(item.headline)}</h1>

      <!-- 1. 종합 요약 -->
      <div class="modal-section-title">
        <i class="fa-solid fa-wand-magic-sparkles"></i> 수집 기사 종합 요약
      </div>
      <div class="modal-overview-box">
        ${escapeHtml(item.summary ? (item.summary.overview || '') : '').replace(/\n/g, '<br>')}
      </div>

      <!-- 2. 언론사별 기사 원본 링크 -->
      <div class="modal-section-title">
        <i class="fa-solid fa-newspaper"></i> 언론사별 기사 원본 링크 (${item.publishers.length}개)
      </div>
      <div class="publisher-links-list">
        ${publisherLinksHTML}
      </div>
    `;

    history.pushState({ modalOpen: true, newsId: item.id }, '', `#news-${item.id}`);

    newsModal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function closeModalDOM() {
    if (newsModal) {
      newsModal.classList.remove('active');
      document.body.style.overflow = '';
    }
  }

  // Toast UI Notification Helper
  function showToast(message, type = 'info', duration = 3500) {
    if (!toastContainer) return;
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
    if (!newsContainer) return;
    newsContainer.innerHTML = `
      <div class="loading-state">
        <div class="spinner"></div>
        <p>주요 뉴스를 카테고리별로 불러오는 중입니다...</p>
      </div>
    `;
  }

  function showEmptyState(message) {
    if (!newsContainer) return;
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
