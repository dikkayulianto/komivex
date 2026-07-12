// KomikID App Logic with Dynamic Jikan API (MyAnimeList) Integration

// 1. Local Fallback Manga Database (Used if API is rate-limited or offline)
const fallbackDatabase = [
    {
        id: "one-piece",
        title: "One Piece",
        type: "Manga",
        rating: 9.0,
        rank: 1,
        latestChapter: 1108,
        cover: "assets/manga_cover_1.jpg",
        author: "Eiichiro Oda",
        genres: ["Action", "Adventure", "Fantasy", "Comedy"],
        synopsis: "Gol D. Roger dikenal sebagai Raja Bajak Laut, bajak laut terkuat dan paling terkenal yang pernah berlayar di Grand Line. Sebelum eksekusinya, ia mengungkapkan keberadaan hartanya yang legendaris, One Piece. Monkey D. Luffy, seorang remaja berusia 17 tahun yang memakan Buah Iblis Gomu Gomu, berangkat dalam petualangan besar untuk menemukan One Piece dan menjadi Raja Bajak Laut yang baru.",
        updatedAt: "10 menit yang lalu"
    },
    {
        id: "martial-peak-2",
        title: "Martial Peak Part 2",
        type: "Manhua",
        rating: 7.5,
        rank: 2,
        latestChapter: 3882,
        cover: "assets/manga_cover_2.jpg",
        author: "Momo",
        genres: ["Action", "Fantasy", "Adventure"],
        synopsis: "Perjalanan ke puncak bela diri adalah jalan yang sepi, sunyi, dan panjang. Di hadapan kesulitan, kamu harus tetap tegar dan tak tergoyahkan. Hanya dengan begitu kamu dapat menerobos dan melanjutkan perjalananmu untuk menjadi yang terkuat.",
        updatedAt: "25 menit yang lalu"
    },
    {
        id: "rebirth-urban-cultivator",
        title: "Rebirth Of The Urban Immortal Cultivator",
        type: "Manhua",
        rating: 8.2,
        rank: 3,
        latestChapter: 1064,
        cover: "assets/manga_cover_3.jpg",
        author: "Tenisi",
        genres: ["Action", "Fantasy"],
        synopsis: "Chen Fan, seorang kultivator tertinggi yang jatuh saat menerobos kesengsaraan surgawi, bereinkarnasi kembali ke masa mudanya saat tinggal di bumi. Berbekal memori ribuan tahun kultivasi, ia memutuskan untuk melindungi orang-orang yang dicintainya dan menghancurkan musuh-musuh masa lalunya dengan kekuatan absolut.",
        updatedAt: "1 jam yang lalu"
    },
    {
        id: "new-career-every-week",
        title: "I Randomly Have A New Career Every Week",
        type: "Manhua",
        rating: 8.5,
        rank: 4,
        latestChapter: 890,
        cover: "assets/manga_cover_4.jpg",
        author: "Chao Shen",
        genres: ["Comedy", "Romance", "Action"],
        synopsis: "Lin Yi, seorang pemuda biasa, tiba-tiba mendapatkan sistem misterius yang memberikannya karir baru secara acak setiap minggu. Dari kurir makanan biasa, sopir taksi mewah, hingga agen rahasia dunia.",
        updatedAt: "2 jam yang lalu"
    },
    {
        id: "lookism",
        title: "Lookism",
        type: "Manhwa",
        rating: 9.0,
        rank: 10,
        latestChapter: 585,
        cover: "assets/manga_cover_2.jpg",
        author: "Park Tae-jun",
        genres: ["Action", "Comedy", "Drama"],
        synopsis: "Daniel Park adalah seorang siswa SMA penyendiri yang sering dirundung karena penampilannya yang gemuk dan tidak menarik. Suatu hari, ia terbangun dalam tubuh baru yang sangat tampan, atletis, dan sempurna.",
        updatedAt: "1 hari yang lalu"
    },
    {
        id: "solo-leveling",
        title: "Solo Leveling",
        type: "Manhwa",
        rating: 9.6,
        rank: 11,
        latestChapter: 180,
        cover: "assets/manga_cover_1.jpg",
        author: "Chugong",
        genres: ["Action", "Fantasy", "Adventure"],
        synopsis: "Di dunia di mana monster bermunculan dari portal dimensi (gate), orang-hari biasa dibekali kekuatan supranatural untuk memburu mereka, disebut Hunters. Sung Jin-Woo adalah Hunter terlemah kelas E yang berjuang bertahan hidup demi biaya rumah sakit ibunya.",
        updatedAt: "2 hari yang lalu"
    }
];

// 2. Global State Variables
let searchQuery = "";
let activeFilters = {
    type: "all",
    genre: "all",
    sort: "rating"
};
let isPopularExpanded = false;
let bookmarkedMangas = JSON.parse(localStorage.getItem("komikid_bookmarked_mangas")) || []; // Stores full manga objects
let readChapters = JSON.parse(localStorage.getItem("komikid_read_chapters")) || {}; // { mangaId: [chNums] }
let currentTab = "home";

// Authentication & User State
let registeredUsers = JSON.parse(localStorage.getItem("komivex_registered_users")) || [
    { username: "admin", email: "admin@komivex.com", password: "admin", role: "admin" }
];
let currentUser = JSON.parse(localStorage.getItem("komivex_current_user")) || null;
let readingHistory = [];
if (currentUser) {
    readingHistory = JSON.parse(localStorage.getItem(`komivex_history_${currentUser.email}`)) || [];
}

// Custom Ad Scripts Storage State
let customAdCodes = JSON.parse(localStorage.getItem("komivex_ad_codes")) || {
    head: "",
    body: "",
    header: "",
    sidebar_1: "",
    sidebar_2: "",
    footer: ""
};

if (customAdCodes && customAdCodes.sidebar && !customAdCodes.sidebar_1) {
    customAdCodes.sidebar_1 = customAdCodes.sidebar;
}

// Active API fetched lists to avoid duplicate requests & speed up clicks
let activeMangaList = []; 
let activeUpdatesList = [];
let mangaDetailsCache = {}; // { mangaId: FullJikanObject }

// Jikan Genre Mapping (MyAnimeList Genre IDs)
const genreMap = {
    "Action": 1,
    "Adventure": 2,
    "Comedy": 4,
    "Fantasy": 10,
    "Romance": 22,
    "Sports": 30
};

// 3. Document Element Selectors
const popularGrid = document.getElementById("popular-grid");
const updatesGrid = document.getElementById("updates-grid");
const libraryGrid = document.getElementById("library-grid");
const libraryEmptyMsg = document.getElementById("library-empty-msg");
const searchInput = document.getElementById("search-input");
const searchClearBtn = document.getElementById("search-clear");
const filterToggleBtn = document.getElementById("filter-toggle-btn");
const filterPanel = document.getElementById("filter-panel");
const themeToggleBtn = document.getElementById("theme-toggle-btn");
const togglePopularBtn = document.getElementById("toggle-popular-btn");
const toastContainer = document.getElementById("toast-container");

// Modals
const detailModal = document.getElementById("detail-modal");
const loginModal = document.getElementById("login-modal");

// 4. API Request Handlers

// Helper to delay executions (avoid hitting rate limits)
const delay = ms => new Promise(res => setTimeout(res, ms));

async function fetchFromJikan(url) {
    try {
        const response = await fetch(url);
        
        if (response.status === 429) {
            console.warn("Jikan API rate limit (429) hit, retrying or falling back...");
            showToast("Batas akses API tercapai. Mencoba memuat komik cadangan...", "info");
            throw new Error("429 Rate Limited");
        }
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (err) {
        console.error("Fetch failed: ", err);
        return null;
    }
}

// Convert Jikan Manga Object to our internal UI format
function mapJikanManga(manga) {
    return {
        id: manga.mal_id.toString(),
        title: manga.title_english || manga.title,
        type: manga.type || "Manga",
        rating: manga.score || 0.0,
        rank: manga.rank || 99,
        latestChapter: manga.chapters || 120, // default if chapters is null (ongoing)
        cover: manga.images.jpg.image_url,
        author: manga.authors && manga.authors.length > 0 ? manga.authors[0].name : "Unknown",
        genres: manga.genres ? manga.genres.map(g => g.name) : ["Fantasy"],
        synopsis: manga.synopsis || "Sinopsis tidak tersedia untuk judul ini.",
        updatedAt: "Terbaru"
    };
}

async function getPopularMangaList() {
    try {
        // 1. If searching, query our backend search suggestion relay
        if (searchQuery.trim() !== "") {
            const res = await fetch(`/api/search?q=${encodeURIComponent(searchQuery)}`);
            if (res.ok) {
                let list = await res.json();
                if (activeFilters.type !== "all") list = list.filter(m => m.type === activeFilters.type);
                if (activeFilters.genre !== "all") list = list.filter(m => m.genres.includes(activeFilters.genre));
                return list;
            }
        }

        // 2. Fetch popular list from local backend scraper
        const res = await fetch('/api/popular');
        if (res.ok) {
            let list = await res.json();
            
            // Apply filters client-side on scraped popular list
            if (activeFilters.type !== "all") {
                list = list.filter(m => m.type === activeFilters.type);
            }
            if (activeFilters.genre !== "all") {
                list = list.filter(m => m.genres.includes(activeFilters.genre));
            }

            // Apply sorting client-side
            if (activeFilters.sort === "rating") {
                list.sort((a, b) => b.rating - a.rating);
            } else if (activeFilters.sort === "rank") {
                list.sort((a, b) => a.rank - b.rank);
            } else if (activeFilters.sort === "alphabet") {
                list.sort((a, b) => a.title.localeCompare(b.title));
            }
            return list;
        }
        throw new Error("Express backend scraper returned error status");
    } catch (err) {
        console.warn("Backend API failed, falling back to Jikan MAL API...", err);
        return await getMALFallbackList();
    }
}

async function getLatestUpdatesList() {
    try {
        const res = await fetch('/api/updates');
        if (res.ok) {
            return await res.json();
        }
        throw new Error("Express backend updates scraper failed");
    } catch (err) {
        console.warn("Backend updates failed, falling back to Jikan...", err);
        return await getMALUpdatesFallback();
    }
}

// --- JIKAN MAL API SECONDARY FALLBACKS ---
async function getMALFallbackList() {
    if (searchQuery.trim() !== "" || activeFilters.type !== "all" || activeFilters.genre !== "all") {
        let url = `https://api.jikan.moe/v4/manga?limit=24`;
        if (searchQuery.trim() !== "") {
            url += `&q=${encodeURIComponent(searchQuery)}`;
        }
        if (activeFilters.type !== "all") {
            url += `&type=${activeFilters.type.toLowerCase()}`;
        }
        if (activeFilters.genre !== "all") {
            const genreId = genreMap[activeFilters.genre];
            if (genreId) url += `&genres=${genreId}`;
        }
        if (activeFilters.sort === "rating") {
            url += `&order_by=score&sort=desc`;
        } else if (activeFilters.sort === "rank") {
            url += `&order_by=rank&sort=asc`;
        } else if (activeFilters.sort === "alphabet") {
            url += `&order_by=title&sort=asc`;
        }

        const response = await fetchFromJikan(url);
        if (response && response.data) {
            return response.data.map(mapJikanManga);
        }
    } else {
        const response = await fetchFromJikan(`https://api.jikan.moe/v4/top/manga?limit=24`);
        if (response && response.data) {
            return response.data.map(mapJikanManga);
        }
    }
    return getLocalFilteredManga();
}

async function getMALUpdatesFallback() {
    const response = await fetchFromJikan(`https://api.jikan.moe/v4/top/manga?filter=publishing&limit=9`);
    if (response && response.data) {
        return response.data.map(m => {
            const mapped = mapJikanManga(m);
            const times = ["5 menit lalu", "12 menit lalu", "45 menit lalu", "2 jam lalu", "4 jam lalu"];
            mapped.updatedAt = times[Math.floor(Math.random() * times.length)];
            return mapped;
        });
    }
    return fallbackDatabase.slice(0, 9);
}


// Local fallback filter implementation
function getLocalFilteredManga() {
    let result = [...fallbackDatabase];

    if (searchQuery.trim() !== "") {
        const query = searchQuery.toLowerCase();
        result = result.filter(m => m.title.toLowerCase().includes(query));
    }
    if (activeFilters.type !== "all") {
        result = result.filter(m => m.type === activeFilters.type);
    }
    if (activeFilters.genre !== "all") {
        result = result.filter(m => m.genres.includes(activeFilters.genre));
    }
    if (activeFilters.sort === "rating") {
        result.sort((a, b) => b.rating - a.rating);
    } else if (activeFilters.sort === "rank") {
        result.sort((a, b) => a.rank - b.rank);
    }

    return result;
}

// 5. Grid Loaders & Renderers
function renderSkeletons(parent, count = 6) {
    parent.innerHTML = "";
    for (let i = 0; i < count; i++) {
        const skeleton = document.createElement("div");
        skeleton.className = "skeleton-card";
        parent.appendChild(skeleton);
    }
}

function renderSpinner(parent) {
    parent.innerHTML = `
        <div class="grid-loader-container">
            <div class="spinner"></div>
        </div>
    `;
}

async function renderPopularGrid() {
    // Render skeleton loadings
    renderSkeletons(popularGrid, 12);
    togglePopularBtn.style.display = "none";

    const list = await getPopularMangaList();
    activeMangaList = list; // cache list
    
    // Cache inside detail lookup cache
    list.forEach(manga => {
        mangaDetailsCache[manga.id] = manga;
    });

    popularGrid.innerHTML = "";

    // If searching, always show as expanded grid
    const isSearching = searchQuery.trim() !== "";
    const wrapper = document.getElementById("popular-carousel-wrapper");

    if (list.length === 0) {
        // Show empty state
        if (isSearching) {
            popularGrid.classList.add("grid-view");
            if (wrapper) wrapper.classList.add("expanded");
        }
        popularGrid.innerHTML = `
            <div class="grid-empty-message" style="grid-column: 1 / -1; text-align: center; padding: 60px 0; color: var(--text-secondary);">
                <div style="font-size: 48px; margin-bottom: 16px;">🔍</div>
                <h3 style="font-size: 18px; margin-bottom: 8px;">Tidak ada komik ditemukan untuk "<span style="color: var(--accent);">${searchQuery}</span>"</h3>
                <p style="font-size: 14px;">Coba kata kunci lain atau periksa ejaan.</p>
            </div>
        `;
        return;
    }

    if (isSearching) {
        // In search mode: always show full grid, add search context header 
        popularGrid.classList.add("grid-view");
        if (wrapper) wrapper.classList.add("expanded");
        togglePopularBtn.style.display = "none";

        // Insert a search result header above the cards
        const header = document.createElement("div");
        header.className = "search-result-header";
        header.style.cssText = "grid-column: 1 / -1; padding: 0 0 16px; display: flex; align-items: center; gap: 12px;";
        header.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:20px;height:20px;color:var(--accent);flex-shrink:0;">
                <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            <span style="color: var(--text-secondary); font-size: 14px;">
                Hasil pencarian untuk <strong style="color: var(--text-primary);">"${searchQuery}"</strong>
                — <span style="color: var(--accent);">${list.length} komik ditemukan</span>
            </span>
        `;
        popularGrid.appendChild(header);
    } else {
        // Normal mode: carousel or grid based on expand state
        if (list.length > 6) {
            togglePopularBtn.style.display = "flex";
            togglePopularBtn.querySelector("span").textContent = isPopularExpanded ? "Tampilkan Lebih Sedikit" : "Lihat Semua Manga";
            if (isPopularExpanded) {
                togglePopularBtn.querySelector(".arrow-icon").style.transform = "rotate(-90deg)";
                popularGrid.classList.add("grid-view");
                if (wrapper) wrapper.classList.add("expanded");
            } else {
                togglePopularBtn.querySelector(".arrow-icon").style.transform = "rotate(0deg)";
                popularGrid.classList.remove("grid-view");
                if (wrapper) wrapper.classList.remove("expanded");
            }
        } else {
            togglePopularBtn.style.display = "none";
            popularGrid.classList.add("grid-view");
            if (wrapper) wrapper.classList.add("expanded");
        }
    }

    list.forEach(manga => {
        const card = document.createElement("div");
        card.className = "manga-card";
        card.setAttribute("data-id", manga.id);
        const ratingVal = parseFloat(manga.rating) || 0;
        
        card.innerHTML = `
            <div class="manga-card-badges">
                <span class="type-tag ${manga.type.toLowerCase()}">${manga.type}</span>
                <span class="rank-badge">${manga.rank}</span>
            </div>
            <img src="${manga.cover}" alt="${manga.title}" class="manga-card-image" loading="lazy" onerror="this.src='assets/manga_cover_1.jpg'">
            <div class="manga-card-overlay">
                <h3 class="manga-card-title">${manga.title}</h3>
                <div class="manga-card-meta">
                    <span class="manga-card-ch">Ch. ${manga.latestChapter}</span>
                    <span class="manga-card-rating">⭐ ${ratingVal.toFixed(1)}</span>
                </div>
            </div>
        `;

        card.addEventListener("click", () => openMangaDetail(manga.id));
        popularGrid.appendChild(card);
    });
}

async function renderUpdatesGrid() {
    renderSpinner(updatesGrid);
    const updates = await getLatestUpdatesList();
    activeUpdatesList = updates;

    // Cache inside detail lookup cache
    updates.forEach(manga => {
        mangaDetailsCache[manga.id] = manga;
    });

    updatesGrid.innerHTML = "";

    updates.forEach(manga => {
        const card = document.createElement("div");
        card.className = "update-card";
        card.setAttribute("data-id", manga.id);

        card.innerHTML = `
            <div class="update-thumb">
                <img src="${manga.cover}" alt="${manga.title}" loading="lazy" onerror="this.src='assets/manga_cover_1.jpg'">
            </div>
            <div class="update-info">
                <h3 class="update-title">${manga.title}</h3>
                <div class="update-chapter-row">
                    <span class="update-ch">Ch. ${manga.latestChapter}</span>
                    <span class="update-time">${manga.updatedAt}</span>
                </div>
                <div class="update-chapter-row">
                    <span class="update-ch">Ch. ${Math.max(1, manga.latestChapter - 1)}</span>
                    <span class="update-time">1 hari lalu</span>
                </div>
                <span class="update-status-tag">${manga.type}</span>
            </div>
        `;

        card.addEventListener("click", () => openMangaDetail(manga.id));
        updatesGrid.appendChild(card);
    });
}

function renderLibraryGrid() {
    libraryGrid.innerHTML = "";
    
    if (bookmarkedMangas.length === 0) {
        libraryGrid.style.display = "none";
        libraryEmptyMsg.style.display = "flex";
        return;
    }

    libraryGrid.style.display = "grid";
    libraryEmptyMsg.style.display = "none";

    bookmarkedMangas.forEach(manga => {
        const card = document.createElement("div");
        card.className = "manga-card";
        card.setAttribute("data-id", manga.id);
        const ratingVal = parseFloat(manga.rating) || 0;

        card.innerHTML = `
            <div class="manga-card-badges">
                <span class="type-tag ${manga.type.toLowerCase()}">${manga.type}</span>
                <span class="rank-badge">${manga.rank}</span>
            </div>
            <img src="${manga.cover}" alt="${manga.title}" class="manga-card-image" loading="lazy" onerror="this.src='assets/manga_cover_1.jpg'">
            <div class="manga-card-overlay">
                <h3 class="manga-card-title">${manga.title}</h3>
                <div class="manga-card-meta">
                    <span class="manga-card-ch">Ch. ${manga.latestChapter}</span>
                    <span class="manga-card-rating">⭐ ${ratingVal.toFixed(1)}</span>
                </div>
            </div>
        `;

        card.addEventListener("click", () => openMangaDetail(manga.id));
        libraryGrid.appendChild(card);
    });
}

let mangaDirectoryCurrentPage = 1;
let mangaDirectoryLastPage = 1;

async function renderMangaDirectory(page = 1) {
    mangaDirectoryCurrentPage = page;
    const directoryGrid = document.getElementById("directory-grid");
    const paginationContainer = document.getElementById("directory-pagination");
    
    if (!directoryGrid) return;
    
    // Render skeleton loadings
    renderSkeletons(directoryGrid, 12);
    if (paginationContainer) paginationContainer.innerHTML = "";

    try {
        let url = `/api/mangas?page=${page}`;
        if (activeFilters.type && activeFilters.type !== "all") {
            url += `&type=${encodeURIComponent(activeFilters.type)}`;
        }
        if (activeFilters.genre && activeFilters.genre !== "all") {
            url += `&genre=${encodeURIComponent(activeFilters.genre)}`;
        }
        if (activeFilters.sort) {
            url += `&sort=${encodeURIComponent(activeFilters.sort)}`;
        }

        const response = await fetch(url);
        if (!response.ok) throw new Error("Scraper failed to fetch page data");
        
        const payload = await response.json();
        const list = payload.data || [];
        mangaDirectoryLastPage = payload.last_page || 1;
        
        // Cache items inside details lookup cache
        list.forEach(manga => {
            mangaDetailsCache[manga.id] = manga;
        });

        directoryGrid.innerHTML = "";
        
        if (list.length === 0) {
            directoryGrid.innerHTML = `
                <div class="grid-empty-message" style="grid-column: 1 / -1; text-align: center; padding: 40px 0; color: var(--text-secondary);">
                    <h3>Daftar komik kosong.</h3>
                </div>
            `;
            return;
        }

        list.forEach(manga => {
            const card = document.createElement("div");
            card.className = "manga-card";
            card.setAttribute("data-id", manga.id);
            
            card.innerHTML = `
                <div class="manga-card-badges">
                    <span class="type-tag ${manga.type.toLowerCase()}">${manga.type}</span>
                    <span class="rank-badge">${manga.rank}</span>
                </div>
                <img src="${manga.cover}" alt="${manga.title}" class="manga-card-image" loading="lazy" onerror="this.src='assets/manga_cover_1.jpg'">
                <div class="manga-card-overlay">
                    <h3 class="manga-card-title">${manga.title}</h3>
                    <div class="manga-card-meta">
                        <span class="manga-card-ch">Ch. ${manga.latestChapter}</span>
                        <span class="manga-card-rating">⭐ ${manga.rating.toFixed(1)}</span>
                    </div>
                </div>
            `;

            card.addEventListener("click", () => openMangaDetail(manga.id));
            directoryGrid.appendChild(card);
        });

        // Render pagination controls
        renderPaginationControls(paginationContainer);

    } catch (err) {
        console.error("Failed to load manga directory: ", err);
        directoryGrid.innerHTML = `
            <div class="grid-empty-message" style="grid-column: 1 / -1; text-align: center; padding: 40px 0; color: var(--text-secondary);">
                <h3>Gagal memuat data dari server. Silakan coba lagi.</h3>
            </div>
        `;
    }
}

function renderPaginationControls(container) {
    if (!container) return;
    container.innerHTML = "";

    const currentPage = mangaDirectoryCurrentPage;
    const lastPage = mangaDirectoryLastPage;

    // Previous Button
    const prevBtn = document.createElement("button");
    prevBtn.className = `page-btn ${currentPage === 1 ? 'disabled' : ''}`;
    prevBtn.textContent = "Sebelumnya";
    prevBtn.onclick = () => {
        if (currentPage > 1) {
            renderMangaDirectory(currentPage - 1);
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    };
    container.appendChild(prevBtn);

    // Determine range of page buttons (show first, last, and surrounding pages)
    const delta = 2; // number of pages to show before and after current
    const range = [];
    const rangeWithDots = [];
    let l;

    for (let i = 1; i <= lastPage; i++) {
        if (i === 1 || i === lastPage || (i >= currentPage - delta && i <= currentPage + delta)) {
            range.push(i);
        }
    }

    for (let i of range) {
        if (l) {
            if (i - l === 2) {
                rangeWithDots.push(l + 1);
            } else if (i - l > 2) {
                rangeWithDots.push('...');
            }
        }
        rangeWithDots.push(i);
        l = i;
    }

    // Render Page Numbers
    rangeWithDots.forEach(page => {
        if (page === '...') {
            const dots = document.createElement("span");
            dots.className = "page-dots";
            dots.textContent = "...";
            container.appendChild(dots);
        } else {
            const pageBtn = document.createElement("button");
            pageBtn.className = `page-btn ${page === currentPage ? 'active' : ''}`;
            pageBtn.textContent = page;
            pageBtn.onclick = () => {
                if (page !== currentPage) {
                    renderMangaDirectory(page);
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                }
            };
            container.appendChild(pageBtn);
        }
    });

    // Next Button
    const nextBtn = document.createElement("button");
    nextBtn.className = `page-btn ${currentPage === lastPage ? 'disabled' : ''}`;
    nextBtn.textContent = "Berikutnya";
    nextBtn.onclick = () => {
        if (currentPage < lastPage) {
            renderMangaDirectory(currentPage + 1);
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    };
    container.appendChild(nextBtn);
}


// 6. Search Debouncer implementation
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

const triggerDebouncedSearch = debounce(async () => {
    const q = searchQuery.trim();
    if (q !== "") {
        if (currentTab !== "home") {
            switchTab("home");
        }
        // Fetch suggestions for dropdown
        await renderSearchDropdown(q);
    } else {
        hideSearchDropdown();
    }
    renderPopularGrid();
}, 400); // Wait 400ms before querying API

// ── Search Dropdown Autocomplete ──────────────────────────────────────────────
const searchDropdown = document.getElementById("search-dropdown");

async function renderSearchDropdown(query) {
    if (!searchDropdown) return;
    try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
        if (!res.ok) { hideSearchDropdown(); return; }
        const list = await res.json();

        // Filter: only manga/manhwa/manhua (skip anime)
        const mangaOnly = list.filter(m => ["Manga","Manhwa","Manhua"].includes(m.type));

        if (mangaOnly.length === 0) {
            searchDropdown.innerHTML = `<div class="search-dropdown-empty">🔍 Tidak ada hasil untuk "<strong>${query}</strong>"</div>`;
            searchDropdown.style.display = "block";
            return;
        }

        searchDropdown.innerHTML = "";
        const show = mangaOnly.slice(0, 5);

        show.forEach(item => {
            const el = document.createElement("div");
            el.className = "search-dropdown-item";
            el.innerHTML = `
                <img class="search-dropdown-thumb" src="${item.cover}" alt="${item.title}" onerror="this.src='assets/manga_cover_1.jpg'">
                <div class="search-dropdown-info">
                    <div class="search-dropdown-title">${item.title}</div>
                    <div class="search-dropdown-meta">Ch. ${item.latestChapter}</div>
                </div>
                <span class="search-dropdown-badge ${item.type.toLowerCase()}">${item.type}</span>
            `;
            el.addEventListener("click", () => {
                // Cache the item so the detail modal can open it
                mangaDetailsCache[item.id] = item;
                hideSearchDropdown();
                openMangaDetail(item.id);
            });
            searchDropdown.appendChild(el);
        });

        if (mangaOnly.length > 5) {
            const more = document.createElement("div");
            more.className = "search-dropdown-more";
            more.textContent = `Lihat ${mangaOnly.length - 5} hasil lainnya →`;
            more.addEventListener("click", () => {
                hideSearchDropdown();
                renderPopularGrid();
            });
            searchDropdown.appendChild(more);
        }

        searchDropdown.style.display = "block";
    } catch(e) {
        hideSearchDropdown();
    }
}

function hideSearchDropdown() {
    if (searchDropdown) searchDropdown.style.display = "none";
}

// Close dropdown when clicking outside
document.addEventListener("click", (e) => {
    const wrapper = document.getElementById("search-box-wrapper");
    if (wrapper && !wrapper.contains(e.target)) {
        hideSearchDropdown();
    }
});



// 7. Modals Logic
async function openMangaDetail(mangaId) {
    // Find manga from details lookup cache, or fallback database, or library bookmarks
    let manga = mangaDetailsCache[mangaId];
    if (!manga) {
        manga = bookmarkedMangas.find(m => m.id === mangaId);
    }
    if (!manga) {
        manga = fallbackDatabase.find(m => m.id === mangaId);
    }

    // Populate initial (possibly partial) data and show modal
    if (manga) {
        renderModalData(manga);
    } else {
        // Show loading template inside modal
        document.getElementById("detail-title").textContent = "Memuat...";
        document.getElementById("detail-author").textContent = "";
        document.getElementById("detail-synopsis").textContent = "Sedang mengambil data terbaru dari server...";
        document.getElementById("detail-rating").textContent = "0.0";
        document.getElementById("detail-rank").textContent = "99";
        document.getElementById("detail-genres").innerHTML = "";
        document.getElementById("detail-chapters-list").innerHTML = "";
    }

    detailModal.classList.add("open");
    document.body.style.overflow = "hidden";

    // Dynamically fetch full real-time details from bacakomik.my
    try {
        const res = await fetch(`/api/manga?id=${encodeURIComponent(mangaId)}`);
        if (res.ok) {
            const fullManga = await res.json();
            if (fullManga && !fullManga.error) {
                mangaDetailsCache[mangaId] = fullManga;
                renderModalData(fullManga);
            }
        }
    } catch (err) {
        console.error("Gagal mengambil detail manga:", err);
    }
}

function renderModalData(manga) {
    const detailCover = document.getElementById("detail-cover");
    detailCover.src = manga.cover;
    detailCover.alt = manga.title;

    const detailBanner = document.getElementById("detail-banner");
    detailBanner.style.background = `linear-gradient(rgba(0, 0, 0, 0.4), rgba(0, 0, 0, 0.8)), url(${manga.cover})`;
    detailBanner.style.backgroundSize = "cover";
    detailBanner.style.backgroundPosition = "center";

    document.getElementById("detail-title").textContent = manga.title;
    document.getElementById("detail-author").textContent = manga.author ? `Oleh ${manga.author}` : "Oleh Unknown";
    document.getElementById("detail-synopsis").textContent = manga.synopsis || "Sinopsis tidak tersedia.";
    document.getElementById("detail-rating").textContent = (parseFloat(manga.rating) || 0).toFixed(1);
    document.getElementById("detail-rank").textContent = manga.rank || 99;

    const typeBadge = document.getElementById("detail-type");
    typeBadge.textContent = manga.type;
    typeBadge.className = `manga-type-badge ${manga.type.toLowerCase()}`;
    if (manga.type === "Manga") typeBadge.style.backgroundColor = "var(--tag-manga)";
    else if (manga.type === "Manhua") typeBadge.style.backgroundColor = "var(--tag-manhua)";
    else if (manga.type === "Manhwa") typeBadge.style.backgroundColor = "var(--tag-manhwa)";

    const genresContainer = document.getElementById("detail-genres");
    genresContainer.innerHTML = "";
    if (manga.genres) {
        manga.genres.forEach(genre => {
            const tag = document.createElement("span");
            tag.className = "genre-tag";
            tag.textContent = genre;
            genresContainer.appendChild(tag);
        });
    }

    updateBookmarkBtnUI(manga.id, manga);
    renderChaptersList(manga);
}

function closeMangaDetail() {
    detailModal.classList.remove("open");
    document.body.style.overflow = "";
}

function renderChaptersList(manga) {
    const chaptersContainer = document.getElementById("detail-chapters-list");
    chaptersContainer.innerHTML = "";

    const userReadList = readChapters[manga.id] || [];

    if (manga.chapters && manga.chapters.length > 0) {
        document.getElementById("detail-chapters-count").textContent = `${manga.chapters.length} Chapter`;
        
        // Show first 20 chapters for performance
        const displayList = manga.chapters.slice(0, 20);
        displayList.forEach(ch => {
            const item = document.createElement("div");
            item.className = `chapter-item ${userReadList.includes(ch.chapter_number) ? 'read' : ''}`;
            item.innerHTML = `
                <span class="chapter-name">${ch.title}</span>
                <span class="chapter-date">Terbaru</span>
            `;
            item.addEventListener("click", () => {
                closeMangaDetail();
                openChapterReader(manga.id, ch.chapter_number);
            });
            chaptersContainer.appendChild(item);
        });
    } else {
        const latestNum = parseInt(manga.latestChapter) || 0;
        const displayCount = Math.min(20, latestNum);
        document.getElementById("detail-chapters-count").textContent = `${latestNum} Chapter`;

        if (displayCount === 0) {
            chaptersContainer.innerHTML = `<p style="color:var(--text-secondary);padding:16px;font-size:13px;">Daftar chapter tidak tersedia.</p>`;
            return;
        }

        for (let i = 0; i < displayCount; i++) {
            const chNum = latestNum - i;
            if (chNum <= 0) break;

            const item = document.createElement("div");
            item.className = `chapter-item ${userReadList.includes(chNum) ? 'read' : ''}`;
            item.innerHTML = `
                <span class="chapter-name">Chapter ${chNum}</span>
                <span class="chapter-date">${i === 0 ? 'Terbaru' : (i * 2) + ' hari lalu'}</span>
            `;

            item.addEventListener("click", () => {
                closeMangaDetail();
                openChapterReader(manga.id, chNum);
            });

            chaptersContainer.appendChild(item);
        }
    }
}

function toggleChapterRead(mangaId, chNum, element) {
    if (!readChapters[mangaId]) {
        readChapters[mangaId] = [];
    }

    const idx = readChapters[mangaId].indexOf(chNum);
    if (idx === -1) {
        readChapters[mangaId].push(chNum);
        element.classList.add("read");
        showToast(`Membaca Chapter ${chNum}`, "success");
    } else {
        readChapters[mangaId].splice(idx, 1);
        element.classList.remove("read");
    }

    localStorage.setItem("komikid_read_chapters", JSON.stringify(readChapters));
}

let currentMangaIdForReader = null;
let currentChapterNumberForReader = null;

async function openChapterReader(mangaId, chapterNumber) {
    currentMangaIdForReader = mangaId;
    currentChapterNumberForReader = parseInt(chapterNumber);
    
    // Switch active tab to reader-view
    currentTab = "reader";
    const mainLayout = document.querySelector(".main-layout-wrapper");
    if (mainLayout) mainLayout.style.display = "none";
    const footer = document.querySelector(".footer");
    if (footer) footer.style.display = "";
    const mobileNav = document.getElementById("mobile-bottom-nav");
    if (mobileNav) mobileNav.style.display = "none";

    document.querySelectorAll(".nav-menu .nav-item").forEach(item => {
        item.classList.remove("active");
    });
    document.querySelectorAll(".tab-content").forEach(content => {
        content.classList.remove("active");
    });
    
    const readerView = document.getElementById("reader-view");
    if (readerView) readerView.classList.add("active");
    window.scrollTo({ top: 0 });
    
    const imagesContainer = document.getElementById("reader-images-container");
    if (imagesContainer) {
        imagesContainer.innerHTML = `
            <div class="grid-loader-container" style="padding: 100px 0;">
                <div class="spinner"></div>
                <h3 style="margin-top: 20px; color: var(--text-secondary);">Memuat halaman komik...</h3>
            </div>
        `;
    }

    // Mark chapter as read
    if (!readChapters[mangaId]) {
        readChapters[mangaId] = [];
    }
    if (!readChapters[mangaId].includes(currentChapterNumberForReader)) {
        readChapters[mangaId].push(currentChapterNumberForReader);
        localStorage.setItem("komikid_read_chapters", JSON.stringify(readChapters));
    }

    try {
        const response = await fetch(`/api/read?manga=${encodeURIComponent(mangaId)}&chapter=${currentChapterNumberForReader}`);
        if (!response.ok) throw new Error("Gagal mengambil data chapter");
        
        const data = await response.json();
        
        // Track reading history for logged in user
        if (currentUser && currentUser.role === "user") {
            const existingIdx = readingHistory.findIndex(h => h.mangaId === mangaId);
            const historyEntry = {
                mangaId: mangaId,
                mangaTitle: data.manga_title || mangaId.replace('-', ' ').toUpperCase(),
                cover: data.images && data.images[0] ? data.images[0] : (mangaDetailsCache[mangaId]?.cover || "/assets/manga_cover_1.jpg"),
                chapterNumber: currentChapterNumberForReader,
                timestamp: new Date().toLocaleString('id-ID', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' })
            };

            if (existingIdx !== -1) {
                readingHistory.splice(existingIdx, 1);
            }
            readingHistory.unshift(historyEntry);
            localStorage.setItem(`komivex_history_${currentUser.email}`, JSON.stringify(readingHistory));
        }
        
        if (data.error) throw new Error(data.error);

        // Update headers texts
        const rMangaTitle = document.getElementById("reader-manga-title");
        const rChTitle = document.getElementById("reader-chapter-title");
        if (rMangaTitle) rMangaTitle.textContent = data.manga_title;
        if (rChTitle) rChTitle.textContent = data.chapter_title;
        
        // Populate chapter selection dropdown
        const select = document.getElementById("reader-chapter-select");
        if (select) {
            select.innerHTML = "";
            const sortedChs = (data.chapters || []).sort((a, b) => b.chapter_number - a.chapter_number);
            sortedChs.forEach(c => {
                const opt = document.createElement("option");
                opt.value = c.chapter_number;
                opt.textContent = c.title;
                if (parseInt(c.chapter_number) === currentChapterNumberForReader) {
                    opt.selected = true;
                }
                select.appendChild(opt);
            });
            
            select.onchange = (e) => {
                openChapterReader(mangaId, e.target.value);
            };
        }

        // Render images
        if (imagesContainer) {
            imagesContainer.innerHTML = "";
            const images = data.images || [];
            
            if (images.length === 0) {
                imagesContainer.innerHTML = `
                    <div style="text-align: center; padding: 100px 20px; color: var(--text-secondary);">
                        <h3>Halaman komik tidak ditemukan atau belum dirilis untuk chapter ini.</h3>
                    </div>
                `;
            } else {
                images.forEach((imgUrl, index) => {
                    const img = document.createElement("img");
                    img.className = "reader-img";
                    if (imgUrl.startsWith("/api/proxy-img")) {
                        img.src = imgUrl;
                    } else {
                        img.src = `/api/proxy-img?url=${encodeURIComponent(imgUrl)}`;
                    }
                    img.alt = `Halaman ${index + 1}`;
                    img.loading = "lazy";
                    img.onerror = () => {
                        img.src = "assets/manga_cover_1.jpg";
                    };
                    imagesContainer.appendChild(img);
                });
            }
        }

        // Configure Prev/Next buttons
        const prevBtn = document.getElementById("reader-prev-chapter-btn");
        const nextBtn = document.getElementById("reader-next-chapter-btn");
        
        if (prevBtn) {
            if (data.prev_chapter) {
                prevBtn.className = "page-btn";
                prevBtn.onclick = () => openChapterReader(mangaId, data.prev_chapter);
            } else {
                prevBtn.className = "page-btn disabled";
                prevBtn.onclick = null;
            }
        }
        
        if (nextBtn) {
            if (data.next_chapter) {
                nextBtn.className = "page-btn";
                nextBtn.onclick = () => openChapterReader(mangaId, data.next_chapter);
            } else {
                nextBtn.className = "page-btn disabled";
                nextBtn.onclick = null;
            }
        }

    } catch (err) {
        console.error(err);
        if (imagesContainer) {
            imagesContainer.innerHTML = `
                <div style="text-align: center; padding: 100px 20px; color: var(--text-secondary);">
                    <h3 style="color: var(--accent);">Gagal memuat chapter pembaca</h3>
                    <p style="margin-top: 10px;">${err.message || "Eror tidak diketahui"}</p>
                    <button class="btn-primary" style="margin-top: 20px;" onclick="openChapterReader('${mangaId}', ${chapterNumber})">Coba Lagi</button>
                </div>
            `;
        }
    }
}

const goBackFromReader = () => {
    // Show main layout wrapper
    const mainLayout = document.querySelector(".main-layout-wrapper");
    if (mainLayout) mainLayout.style.display = "flex";
    
    // Show footer and mobile bottom nav on normal tabs
    const footer = document.querySelector(".footer");
    if (footer) footer.style.display = "";
    const mobileNav = document.getElementById("mobile-bottom-nav");
    if (mobileNav) mobileNav.style.display = "";

    // Switch back to details view or home
    if (currentMangaIdForReader) {
        // Switch tab to home/manga (depending on where they were, or default manga tab)
        currentTab = "manga";
        document.querySelectorAll(".tab-content").forEach(content => {
            content.classList.remove("active");
        });
        document.getElementById("manga-view").classList.add("active");
        openMangaDetail(currentMangaIdForReader);
    } else {
        switchTab("home");
    }
};

// Bookmarking updates (stores full manga object structure in localStorage)
function toggleBookmark(mangaId, mangaObj) {
    const idx = bookmarkedMangas.findIndex(m => m.id === mangaId);
    
    if (idx === -1) {
        bookmarkedMangas.push(mangaObj);
        showToast(`Berhasil menyimpan "${mangaObj.title}" ke Library!`, "success");
    } else {
        bookmarkedMangas.splice(idx, 1);
        showToast(`Menghapus "${mangaObj.title}" dari Library`, "info");
    }

    localStorage.setItem("komikid_bookmarked_mangas", JSON.stringify(bookmarkedMangas));
    updateBookmarkBtnUI(mangaId, mangaObj);
    renderLibraryGrid();
}

function updateBookmarkBtnUI(mangaId, mangaObj) {
    const bookmarkBtn = document.getElementById("bookmark-btn");
    const bookmarkText = document.getElementById("bookmark-text");
    const isBookmarked = bookmarkedMangas.some(m => m.id === mangaId);

    if (isBookmarked) {
        bookmarkBtn.className = "bookmark-toggle-btn saved";
        bookmarkText.textContent = "Disimpan di Library";
    } else {
        bookmarkBtn.className = "bookmark-toggle-btn";
        bookmarkText.textContent = "Simpan ke Library";
    }

    bookmarkBtn.onclick = () => toggleBookmark(mangaId, mangaObj);
}

// Toast Alert System
function showToast(message, type = "success") {
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    
    let icon = "🔔";
    if (type === "success") icon = "✅";
    if (type === "info") icon = "ℹ️";
    
    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
    toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 3000);
}

// Tab Switching
function switchTab(tabName) {
    currentTab = tabName;
    
    // Show main layout wrapper
    const mainLayout = document.querySelector(".main-layout-wrapper");
    if (mainLayout) mainLayout.style.display = "flex";
    
    // Show footer and mobile bottom nav on normal tabs
    const footer = document.querySelector(".footer");
    if (footer) footer.style.display = "";
    const mobileNav = document.getElementById("mobile-bottom-nav");
    if (mobileNav) mobileNav.style.display = "";
    
    document.querySelectorAll(".nav-menu .nav-item").forEach(item => {
        if (item.getAttribute("data-tab") === tabName) {
            item.classList.add("active");
        } else {
            item.classList.remove("active");
        }
    });

    document.querySelectorAll(".mobile-bottom-nav .mobile-nav-item[data-tab]").forEach(item => {
        if (item.getAttribute("data-tab") === tabName) {
            item.classList.add("active");
        } else {
            item.classList.remove("active");
        }
    });

    document.querySelectorAll(".tab-content").forEach(content => {
        content.classList.remove("active");
    });

    if (tabName === "home") {
        document.getElementById("home-view").classList.add("active");
    } else if (tabName === "library") {
        renderLibraryGrid();
        document.getElementById("library-view").classList.add("active");
    } else if (tabName === "manga") {
        renderMangaDirectory(1);
        document.getElementById("manga-view").classList.add("active");
        showToast("Membuka Daftar Manga", "info");
    } else if (tabName === "admin") {
        // Simulate stats
        const viewStat = document.getElementById("admin-stat-views");
        const scrapeStat = document.getElementById("admin-stat-scrapes");
        if (viewStat) viewStat.textContent = (15000 + Math.floor(Math.random() * 800)).toLocaleString('id-ID');
        if (scrapeStat) scrapeStat.textContent = (120 + Math.floor(Math.random() * 20)).toString();
        
        // Populate textareas with saved ad scripts
        const inputHead = document.getElementById("ad-code-head");
        const inputBody = document.getElementById("ad-code-body");
        const inputHeader = document.getElementById("ad-code-header");
        const inputSidebar1 = document.getElementById("ad-code-sidebar-1");
        const inputSidebar2 = document.getElementById("ad-code-sidebar-2");
        const inputFooter = document.getElementById("ad-code-footer");
        
        if (inputHead) inputHead.value = customAdCodes.head || "";
        if (inputBody) inputBody.value = customAdCodes.body || "";
        if (inputHeader) inputHeader.value = customAdCodes.header || "";
        if (inputSidebar1) inputSidebar1.value = customAdCodes.sidebar_1 || "";
        if (inputSidebar2) inputSidebar2.value = customAdCodes.sidebar_2 || "";
        if (inputFooter) inputFooter.value = customAdCodes.footer || "";

        document.getElementById("admin-view").classList.add("active");
        showToast("Membuka Admin Panel", "info");
    } else if (tabName === "user-dashboard") {
        renderUserDashboard();
        document.getElementById("user-dashboard-view").classList.add("active");
        showToast("Membuka Dashboard User", "info");
    }
}

function renderUserDashboard() {
    const historyListContainer = document.getElementById("dashboard-history-list");
    const updatesListContainer = document.getElementById("dashboard-updates-list");
    
    if (!historyListContainer || !updatesListContainer) return;
    
    // 1. Render reading history
    historyListContainer.innerHTML = "";
    if (readingHistory.length === 0) {
        historyListContainer.innerHTML = `<p style="color: var(--text-muted); padding: 12px; font-size: 13px; text-align: center; width: 100%;">Belum ada riwayat membaca.</p>`;
    } else {
        readingHistory.forEach(item => {
            const el = document.createElement("div");
            el.className = "history-item";
            el.innerHTML = `
                <img src="${item.cover}" alt="${item.mangaTitle}" class="history-cover" onerror="this.src='/assets/manga_cover_1.jpg'">
                <div class="history-info">
                    <h4 class="history-title">${item.mangaTitle}</h4>
                    <span class="history-ch">Terakhir dibaca: Ch. ${item.chapterNumber}</span>
                </div>
                <span class="history-time">${item.timestamp}</span>
            `;
            el.onclick = () => {
                openMangaDetail(item.mangaId);
            };
            historyListContainer.appendChild(el);
        });
    }

    // 2. Render bookmarked manga updates
    updatesListContainer.innerHTML = "";
    if (bookmarkedMangas.length === 0) {
        updatesListContainer.innerHTML = `<p style="color: var(--text-muted); padding: 12px; font-size: 13px; text-align: center; width: 100%;">Library kamu kosong. Simpan manga ke library untuk melihat update di sini.</p>`;
    } else {
        bookmarkedMangas.forEach(manga => {
            const el = document.createElement("div");
            el.className = "update-item-row";
            el.innerHTML = `
                <img src="${manga.cover}" alt="${manga.title}" class="update-item-cover" onerror="this.src='/assets/manga_cover_1.jpg'">
                <div class="update-item-info">
                    <h4 class="update-item-title">${manga.title}</h4>
                    <span class="update-item-meta">Terbaru: Ch. ${manga.latestChapter} · ${manga.type}</span>
                </div>
            `;
            el.onclick = () => {
                openMangaDetail(manga.id);
            };
            updatesListContainer.appendChild(el);
        });
    }
}

function updateFilterActiveUI(groupName, value) {
    const parent = document.getElementById(`filter-${groupName}`);
    if (!parent) return;
    parent.querySelectorAll(".filter-opt").forEach(btn => {
        if (btn.getAttribute("data-value") === value) {
            btn.classList.add("active");
        } else {
            btn.classList.remove("active");
        }
    });
}

// Dark/Light Theme Switching
function toggleTheme() {
    const isDark = document.body.classList.contains("dark-theme");
    const sunIcon = document.querySelector(".sun-icon");
    const moonIcon = document.querySelector(".moon-icon");

    if (isDark) {
        document.body.classList.remove("dark-theme");
        document.body.classList.add("light-theme");
        sunIcon.style.display = "none";
        moonIcon.style.display = "block";
        localStorage.setItem("komikid_theme", "light");
        showToast("Mode Terang Aktif", "info");
    } else {
        document.body.classList.add("dark-theme");
        document.body.classList.remove("light-theme");
        sunIcon.style.display = "block";
        moonIcon.style.display = "none";
        localStorage.setItem("komikid_theme", "dark");
        showToast("Mode Gelap Aktif", "info");
    }
}

function updateAuthUI() {
    const loginModalBtn = document.getElementById("login-modal-btn");
    const navAdminBtn = document.getElementById("nav-admin");
    const navUserDashboardBtn = document.getElementById("nav-user-dashboard");
    
    // Mobile bottom nav buttons
    const mobNavTheme = document.getElementById("mob-nav-theme");
    const mobNavDashboard = document.getElementById("mob-nav-dashboard");
    const mobNavAdmin = document.getElementById("mob-nav-admin");

    if (currentUser) {
        const name = currentUser.username;
        loginModalBtn.textContent = name.charAt(0).toUpperCase() + name.slice(1, 7) + " (Keluar)";
        loginModalBtn.style.background = "linear-gradient(135deg, #ef4444 0%, #dc2626 100%)";
        loginModalBtn.style.boxShadow = "0 4px 14px rgba(239, 68, 68, 0.3)";
        
        if (currentUser.role === "admin") {
            if (navAdminBtn) navAdminBtn.style.display = "flex";
            if (navUserDashboardBtn) navUserDashboardBtn.style.display = "none";
            
            if (mobNavTheme) mobNavTheme.style.display = "none";
            if (mobNavDashboard) mobNavDashboard.style.display = "none";
            if (mobNavAdmin) mobNavAdmin.style.display = "flex";
        } else {
            if (navAdminBtn) navAdminBtn.style.display = "none";
            if (navUserDashboardBtn) navUserDashboardBtn.style.display = "flex";
            
            if (mobNavTheme) mobNavTheme.style.display = "none";
            if (mobNavDashboard) mobNavDashboard.style.display = "flex";
            if (mobNavAdmin) mobNavAdmin.style.display = "none";
        }
    } else {
        loginModalBtn.textContent = "Masuk";
        loginModalBtn.style.background = "linear-gradient(135deg, #a855f7 0%, #ec4899 100%)";
        loginModalBtn.style.boxShadow = "none";
        if (navAdminBtn) navAdminBtn.style.display = "none";
        if (navUserDashboardBtn) navUserDashboardBtn.style.display = "none";
        
        if (mobNavTheme) mobNavTheme.style.display = "flex";
        if (mobNavDashboard) mobNavDashboard.style.display = "none";
        if (mobNavAdmin) mobNavAdmin.style.display = "none";
    }
}

// 8. Event Wiring
function setupEventListeners() {
    themeToggleBtn.addEventListener("click", toggleTheme);

    // Dynamic search inputs with debounce mapping
    searchInput.addEventListener("input", (e) => {
        searchQuery = e.target.value;
        if (searchQuery.trim() !== "") {
            searchClearBtn.style.display = "block";
        } else {
            searchClearBtn.style.display = "none";
        }
        triggerDebouncedSearch();
    });

    searchClearBtn.addEventListener("click", () => {
        searchInput.value = "";
        searchQuery = "";
        searchClearBtn.style.display = "none";
        hideSearchDropdown();
        renderPopularGrid();
        searchInput.focus();
    });

    filterToggleBtn.addEventListener("click", () => {
        filterPanel.classList.toggle("open");
        filterToggleBtn.classList.toggle("active");
    });

    togglePopularBtn.addEventListener("click", () => {
        switchTab("manga");
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    const viewAllUpdatesBtn = document.getElementById("view-all-updates");
    if (viewAllUpdatesBtn) {
        viewAllUpdatesBtn.addEventListener("click", (e) => {
            e.preventDefault();
            switchTab("manga");
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }

    // Carousel navigation button clicks
    const prevBtn = document.getElementById("popular-prev-btn");
    const nextBtn = document.getElementById("popular-next-btn");
    if (prevBtn && nextBtn) {
        prevBtn.addEventListener("click", () => {
            popularGrid.scrollBy({ left: -popularGrid.clientWidth * 0.75, behavior: 'smooth' });
        });
        nextBtn.addEventListener("click", () => {
            popularGrid.scrollBy({ left: popularGrid.clientWidth * 0.75, behavior: 'smooth' });
        });
    }

    document.querySelectorAll(".nav-menu .nav-item").forEach(btn => {
        btn.addEventListener("click", () => {
            const tab = btn.getAttribute("data-tab");
            switchTab(tab);
        });
    });

    // Footer linkages
    document.querySelectorAll(".footer-nav-link").forEach(link => {
        link.addEventListener("click", (e) => {
            e.preventDefault();
            const tab = link.getAttribute("data-tab");
            switchTab(tab);
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    });

    document.querySelectorAll(".footer-filter-link").forEach(link => {
        link.addEventListener("click", (e) => {
            e.preventDefault();
            const type = link.getAttribute("data-type");
            activeFilters.type = type;
            updateFilterActiveUI("type", type);
            switchTab("home");
            renderPopularGrid();
            popularGrid.scrollIntoView({ behavior: 'smooth', block: 'center' });
            showToast(`Filter tipe: ${type} aktif`, "info");
        });
    });

    const libBackHome = document.getElementById("library-back-home");
    if (libBackHome) {
        libBackHome.addEventListener("click", () => {
            switchTab("home");
        });
    }

    const otherTabBack = document.getElementById("other-tab-back");
    if (otherTabBack) {
        otherTabBack.addEventListener("click", () => {
            switchTab("home");
        });
    }

    document.getElementById("logo-btn").addEventListener("click", (e) => {
        e.preventDefault();
        switchTab("home");
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    // Filters action wiring
    function handleFilterChange() {
        if (currentTab === "manga") {
            renderMangaDirectory(1);
        } else {
            renderPopularGrid();
        }
    }

    document.querySelectorAll("#filter-type .filter-opt").forEach(btn => {
        btn.addEventListener("click", () => {
            activeFilters.type = btn.getAttribute("data-value");
            updateFilterActiveUI("type", activeFilters.type);
            handleFilterChange();
        });
    });

    document.querySelectorAll("#filter-genre .filter-opt").forEach(btn => {
        btn.addEventListener("click", () => {
            activeFilters.genre = btn.getAttribute("data-value");
            updateFilterActiveUI("genre", activeFilters.genre);
            handleFilterChange();
        });
    });

    document.querySelectorAll("#filter-sort .filter-opt").forEach(btn => {
        btn.addEventListener("click", () => {
            activeFilters.sort = btn.getAttribute("data-value");
            updateFilterActiveUI("sort", activeFilters.sort);
            handleFilterChange();
        });
    });

    document.getElementById("filter-reset-btn").addEventListener("click", () => {
        activeFilters = {
            type: "all",
            genre: "all",
            sort: "rating"
        };
        updateFilterActiveUI("type", "all");
        updateFilterActiveUI("genre", "all");
        updateFilterActiveUI("sort", "rating");
        handleFilterChange();
        showToast("Filter disetel ulang", "info");
    });

    // Close Modals
    document.getElementById("detail-close-btn").addEventListener("click", closeMangaDetail);
    detailModal.addEventListener("click", (e) => {
        if (e.target === detailModal) {
            closeMangaDetail();
        }
    });

    // Login modal handling
    const loginModalBtn = document.getElementById("login-modal-btn");
    const loginCloseBtn = document.getElementById("login-close-btn");
    const loginForm = document.getElementById("login-form");

    loginModalBtn.addEventListener("click", () => {
        if (currentUser) {
            showToast(`Sampai jumpa kembali, ${currentUser.username}!`, "info");
            currentUser = null;
            localStorage.removeItem("komivex_current_user");
            readingHistory = [];
            updateAuthUI();
            switchTab("home");
        } else {
            loginModal.classList.add("open");
            document.body.style.overflow = "hidden";
        }
    });

    function closeLoginModal() {
        loginModal.classList.remove("open");
        document.body.style.overflow = "";
    }

    loginCloseBtn.addEventListener("click", closeLoginModal);
    loginModal.addEventListener("click", (e) => {
        if (e.target === loginModal) {
            closeLoginModal();
        }
    });

    // Login/Register Form Switching
    const tabLoginBtn = document.getElementById("tab-login-btn");
    const tabRegisterBtn = document.getElementById("tab-register-btn");
    const loginFormContainer = document.getElementById("login-form-container");
    const registerFormContainer = document.getElementById("register-form-container");

    if (tabLoginBtn && tabRegisterBtn) {
        tabLoginBtn.addEventListener("click", () => {
            tabLoginBtn.classList.add("active");
            tabRegisterBtn.classList.remove("active");
            loginFormContainer.style.display = "block";
            registerFormContainer.style.display = "none";
        });

        tabRegisterBtn.addEventListener("click", () => {
            tabRegisterBtn.classList.add("active");
            tabLoginBtn.classList.remove("active");
            registerFormContainer.style.display = "block";
            loginFormContainer.style.display = "none";
        });
    }

    // Submit register form
    const registerForm = document.getElementById("register-form");
    if (registerForm) {
        registerForm.addEventListener("submit", (e) => {
            e.preventDefault();
            const username = document.getElementById("register-username").value.trim();
            const email = document.getElementById("register-email").value.trim();
            const password = document.getElementById("register-password").value;

            const exists = registeredUsers.some(u => u.email === email);
            if (exists) {
                showToast("Email sudah terdaftar!", "info");
                return;
            }

            registeredUsers.push({ username, email, password, role: "user" });
            localStorage.setItem("komivex_registered_users", JSON.stringify(registeredUsers));

            showToast("Pendaftaran sukses! Silakan login.", "success");
            registerForm.reset();
            tabLoginBtn.click();
        });
    }

    // Submit login form
    loginForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const email = document.getElementById("login-email").value.trim();
        const password = document.getElementById("login-password").value;

        const user = registeredUsers.find(u => u.email === email && u.password === password);

        if (user) {
            currentUser = { username: user.username, email: user.email, role: user.role };
            localStorage.setItem("komivex_current_user", JSON.stringify(currentUser));
            
            readingHistory = JSON.parse(localStorage.getItem(`komivex_history_${currentUser.email}`)) || [];
            
            updateAuthUI();
            closeLoginModal();
            loginForm.reset();
            
            showToast(`Selamat datang kembali, ${currentUser.username}!`, "success");
            
            if (currentUser.role === "admin") {
                switchTab("admin");
            } else {
                switchTab("user-dashboard");
            }
        } else {
            showToast("Email atau password salah!", "info");
        }
    });

    // Admin toggles for Ads
    const toggleHeaderAds = document.getElementById("toggle-header-ads");
    const toggleSidebarAds = document.getElementById("toggle-sidebar-ads");
    const toggleFooterAds = document.getElementById("toggle-footer-ads");

    const headerAds = document.getElementById("header-ads");
    const sidebarAds = document.getElementById("sidebar-ads");
    const footerAds = document.getElementById("footer-ads");

    if (toggleHeaderAds) {
        toggleHeaderAds.addEventListener("change", (e) => {
            if (headerAds) headerAds.style.display = e.target.checked ? "block" : "none";
            showToast(`Iklan Header ${e.target.checked ? 'Diaktifkan' : 'Dinonaktifkan'}`, "info");
        });
    }

    if (toggleSidebarAds) {
        toggleSidebarAds.addEventListener("change", (e) => {
            if (sidebarAds) sidebarAds.style.display = e.target.checked ? "block" : "none";
            showToast(`Iklan Sidebar ${e.target.checked ? 'Diaktifkan' : 'Dinonaktifkan'}`, "info");
        });
    }

    if (toggleFooterAds) {
        toggleFooterAds.addEventListener("change", (e) => {
            if (footerAds) footerAds.style.display = e.target.checked ? "block" : "none";
            showToast(`Iklan Footer ${e.target.checked ? 'Diaktifkan' : 'Dinonaktifkan'}`, "info");
        });
    }

    // Save Custom Ad Codes
    const saveAdCodesBtn = document.getElementById("save-ad-codes-btn");
    if (saveAdCodesBtn) {
        saveAdCodesBtn.addEventListener("click", async () => {
            const headCode = document.getElementById("ad-code-head").value;
            const bodyCode = document.getElementById("ad-code-body").value;
            const headerCode = document.getElementById("ad-code-header").value;
            const sidebar1Code = document.getElementById("ad-code-sidebar-1").value;
            const sidebar2Code = document.getElementById("ad-code-sidebar-2").value;
            const footerCode = document.getElementById("ad-code-footer").value;

            customAdCodes = {
                head: headCode,
                body: bodyCode,
                header: headerCode,
                sidebar_1: sidebar1Code,
                sidebar_2: sidebar2Code,
                footer: footerCode
            };

            localStorage.setItem("komivex_ad_codes", JSON.stringify(customAdCodes));

            try {
                const response = await fetch('/api/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        custom_ad_codes: customAdCodes
                    })
                });

                if (response.ok) {
                    showToast("Script iklan berhasil disimpan dan diterapkan!", "success");
                    loadAndApplySiteConfig();
                } else {
                    showToast("Gagal menyimpan script iklan ke server", "info");
                    applyAllAdCodes();
                }
            } catch (err) {
                console.error(err);
                showToast("Eror koneksi ke server", "error");
                applyAllAdCodes();
            }
        });
    }

    window.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            closeMangaDetail();
            closeLoginModal();
            // Go back from reader on escape key as well if active
            if (currentTab === "reader") goBackFromReader();
        }
    });

    // Save Custom SEO Settings
    const saveSeoSettingsBtn = document.getElementById("save-seo-settings-btn");
    if (saveSeoSettingsBtn) {
        saveSeoSettingsBtn.addEventListener("click", async () => {
            const metaTitle = document.getElementById("seo-meta-title").value;
            const metaDesc = document.getElementById("seo-meta-desc").value;
            const verifCode = document.getElementById("seo-search-console").value;
            
            try {
                const response = await fetch('/api/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        meta_title: metaTitle,
                        meta_description: metaDesc,
                        verification_code: verifCode
                    })
                });
                
                if (response.ok) {
                    showToast("Setelan SEO berhasil disimpan!", "success");
                    loadAndApplySiteConfig();
                } else {
                    showToast("Gagal menyimpan setelan SEO", "info");
                }
            } catch (err) {
                console.error(err);
                showToast("Eror koneksi ke server", "error");
            }
        });
    }

    // File upload change listeners
    const logoFileInput = document.getElementById("brand-logo-file");
    if (logoFileInput) {
        logoFileInput.addEventListener("change", async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            
            document.getElementById("logo-file-name").textContent = file.name;
            
            showToast("Mengunggah gambar logo...", "info");
            try {
                const response = await fetch('/api/upload', {
                    method: 'POST',
                    headers: {
                        'X-File-Type': 'logo',
                        'Content-Type': file.type
                    },
                    body: file
                });
                const res = await response.json();
                if (response.ok && res.status === "success") {
                    showToast("Logo berhasil diunggah!", "success");
                    loadAndApplySiteConfig();
                } else {
                    showToast("Gagal mengunggah logo", "error");
                }
            } catch (err) {
                console.error(err);
                showToast("Eror koneksi ke server saat mengunggah", "error");
            }
        });
    }

    const faviconFileInput = document.getElementById("brand-favicon-file");
    if (faviconFileInput) {
        faviconFileInput.addEventListener("change", async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            
            document.getElementById("favicon-file-name").textContent = file.name;
            
            showToast("Mengunggah gambar favicon...", "info");
            try {
                const response = await fetch('/api/upload', {
                    method: 'POST',
                    headers: {
                        'X-File-Type': 'favicon',
                        'Content-Type': file.type
                    },
                    body: file
                });
                const res = await response.json();
                if (response.ok && res.status === "success") {
                    showToast("Favicon berhasil diunggah!", "success");
                    loadAndApplySiteConfig();
                } else {
                    showToast("Gagal mengunggah favicon", "error");
                }
            } catch (err) {
                console.error(err);
                showToast("Eror koneksi ke server saat mengunggah", "error");
            }
        });
    }

    // Save Custom Branding & Analytics Settings
    const saveBrandingBtn = document.getElementById("save-branding-btn");
    if (saveBrandingBtn) {
        saveBrandingBtn.addEventListener("click", async () => {
            const logoUrl = document.getElementById("brand-logo-url").value;
            const faviconUrl = document.getElementById("brand-favicon-url").value;
            const scraperDomain = document.getElementById("scraper-target-domain").value.trim();
            const analyticsId = document.getElementById("brand-analytics-id").value;
            
            try {
                const response = await fetch('/api/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        logo_url: logoUrl,
                        favicon_url: faviconUrl,
                        scraper_target_domain: scraperDomain,
                        analytics_id: analyticsId
                    })
                });
                
                if (response.ok) {
                    showToast("Setelan Branding berhasil disimpan!", "success");
                    loadAndApplySiteConfig();
                } else {
                    showToast("Gagal menyimpan setelan Branding", "info");
                }
            } catch (err) {
                console.error(err);
                showToast("Eror koneksi ke server", "error");
            }
        });
    }

    // Generate sitemap.xml Action
    const generateSitemapBtn = document.getElementById("admin-generate-sitemap-btn");
    if (generateSitemapBtn) {
        generateSitemapBtn.addEventListener("click", async () => {
            showToast("Sedang men-generate sitemap...", "info");
            try {
                const response = await fetch('/api/generate-sitemap', { method: 'POST' });
                const resData = await response.json();
                if (response.ok && resData.status === "success") {
                    showToast(resData.message || "Sitemap.xml berhasil di-generate!", "success");
                } else {
                    showToast("Gagal men-generate sitemap.xml", "info");
                }
            } catch (err) {
                console.error(err);
                showToast("Eror koneksi ke server", "error");
            }
        });
    }

    // Clear Thumbnail Cache Action
    const clearCacheBtn = document.getElementById("admin-clear-cache-btn");
    if (clearCacheBtn) {
        clearCacheBtn.addEventListener("click", async () => {
            showToast("Sedang membersihkan cache...", "info");
            try {
                const response = await fetch('/api/clear-cache', { method: 'POST' });
                const resData = await response.json();
                if (response.ok && resData.status === "success") {
                    showToast(resData.message || "Cache berhasil dibersihkan!", "success");
                } else {
                    showToast("Gagal membersihkan cache", "info");
                }
            } catch (err) {
                console.error(err);
                showToast("Eror koneksi ke server", "error");
            }
        });
    }

    const rBackBtn = document.getElementById("reader-back-btn");
    const rBottomBackBtn = document.getElementById("reader-bottom-back-btn");
    if (rBackBtn) rBackBtn.addEventListener("click", goBackFromReader);
    if (rBottomBackBtn) rBottomBackBtn.addEventListener("click", goBackFromReader);
}

// ═══════════════════════════════════════════════════════════
// AUTO UPDATE FEATURE — Powered by MyAnimeList (Jikan API)
// Checks every 5 minutes if bookmarked manga has new chapters
// ═══════════════════════════════════════════════════════════
async function checkMangaUpdates() {
    if (!bookmarkedMangas || bookmarkedMangas.length === 0) return;

    let hasNewUpdates = false;
    const updatedTitles = [];

    for (const bookmarked of bookmarkedMangas) {
        try {
            // Search manga by title on Jikan (MyAnimeList public API — no key needed)
            const res = await fetch(
                `https://api.jikan.moe/v4/manga?q=${encodeURIComponent(bookmarked.title)}&limit=1&order_by=popularity&sort=asc`
            );

            if (!res.ok) {
                // Rate limited or offline — skip silently
                await new Promise(r => setTimeout(r, 2000));
                continue;
            }

            const data = await res.json();
            if (!data.data || data.data.length === 0) {
                await new Promise(r => setTimeout(r, 1200));
                continue;
            }

            const malManga = data.data[0];
            // MAL `chapters` is null for ongoing manga; use `publishing` status check
            const newChapterCount = malManga.chapters || 0;
            const currentChapterCount = parseFloat(bookmarked.latestChapter) || 0;

            if (newChapterCount > 0 && newChapterCount > currentChapterCount) {
                showToast(
                    `📖 Chapter baru! "${bookmarked.title}" — Ch. ${newChapterCount} sudah tersedia di MyAnimeList!`,
                    "success"
                );
                // Update saved chapter count
                const idx = bookmarkedMangas.indexOf(bookmarked);
                if (idx !== -1) {
                    bookmarkedMangas[idx].latestChapter = newChapterCount;
                    // Also update MAL score if available
                    if (malManga.score) {
                        bookmarkedMangas[idx].rating = malManga.score;
                    }
                    // Update cover to MAL's image if it's a local placeholder
                    if (malManga.images && malManga.images.jpg && malManga.images.jpg.image_url) {
                        if (!bookmarked.cover || bookmarked.cover.startsWith('/assets/')) {
                            bookmarkedMangas[idx].cover = malManga.images.jpg.image_url;
                        }
                    }
                }
                updatedTitles.push(bookmarked.title);
                hasNewUpdates = true;
            }

            // Jikan rate limit: 1 request/second — wait 1.3s between each
            await new Promise(r => setTimeout(r, 1300));

        } catch (e) {
            console.warn(`[Auto Update] Gagal cek update untuk "${bookmarked.title}":`, e);
            await new Promise(r => setTimeout(r, 1500));
        }
    }

    if (hasNewUpdates) {
        localStorage.setItem("komikid_bookmarked_mangas", JSON.stringify(bookmarkedMangas));

        if (currentTab === "library") {
            renderLibraryGrid();
        }

        // Refresh open detail modal if it matches one of the updated manga
        if (detailModal && detailModal.classList.contains("open")) {
            const openTitle = document.getElementById("detail-title").textContent;
            if (updatedTitles.includes(openTitle)) {
                // Re-render the chapter count in the open modal
                const updatedManga = bookmarkedMangas.find(m => m.title === openTitle);
                if (updatedManga) renderChaptersList(updatedManga);
            }
        }
    }

    // Always refresh the home updates grid
    if (currentTab === "home") {
        renderUpdatesGrid();
    }
}

function startAutoUpdate() {
    // First check after 10 seconds (give app time to load)
    // Then every 5 minutes (300000ms) — respects Jikan rate limits
    setTimeout(() => {
        checkMangaUpdates();
        setInterval(checkMangaUpdates, 300000);
    }, 10000);
}

function executeScripts(container) {
    const scripts = container.querySelectorAll("script");
    scripts.forEach(oldScript => {
        // Skip already executed scripts to avoid infinite loops
        if (oldScript.type === "text/executed-script") return;

        const newScript = document.createElement("script");
        Array.from(oldScript.attributes).forEach(attr => {
            newScript.setAttribute(attr.name, attr.value);
        });
        
        if (oldScript.src) {
            newScript.src = oldScript.src;
            oldScript.parentNode.replaceChild(newScript, oldScript);
        } else {
            const originalWrite = document.write;
            let writtenHtml = "";
            document.write = function(html) {
                writtenHtml += html;
            };
            
            try {
                window.eval(oldScript.textContent);
            } catch (e) {
                console.error("Error executing inline ad script:", e);
            }
            
            document.write = originalWrite;
            
            if (writtenHtml && writtenHtml.trim() !== "") {
                const tempDiv = document.createElement("div");
                tempDiv.innerHTML = writtenHtml;
                
                Array.from(tempDiv.childNodes).forEach(child => {
                    if (child.tagName !== "SCRIPT") {
                        container.appendChild(child);
                    }
                });
                
                const writtenScripts = tempDiv.querySelectorAll("script");
                writtenScripts.forEach(ws => {
                    const dynamicScript = document.createElement("script");
                    Array.from(ws.attributes).forEach(attr => {
                        dynamicScript.setAttribute(attr.name, attr.value);
                    });
                    if (ws.src) {
                        dynamicScript.src = ws.src;
                    } else {
                        dynamicScript.textContent = ws.textContent;
                    }
                    container.appendChild(dynamicScript);
                });
            }
            
            oldScript.type = "text/executed-script";
        }
    });
}

function updateAdContent(zoneId, adHtml, defaultHtml) {
    const zone = document.getElementById(zoneId);
    if (!zone) return;

    if (adHtml && adHtml.trim() !== "") {
        zone.innerHTML = adHtml;
        executeScripts(zone);
    } else {
        zone.innerHTML = defaultHtml;
    }
}

// Default HTML backups to restore if custom code is cleared
const defaultAdContents = {
    header: `
        <a href="#" class="ads-link">
            <div class="ads-banner-mock">Beli Kopi Komivex Premium - Diskon 50% untuk Pembaca Setia! ☕</div>
        </a>
    `,
    sidebar_1: `
        <div class="ads-banner-mock vertical-ad-1">
            <h4>Komivex Shop</h4>
            <p>Dapatkan merchandise eksklusif manga favoritmu sekarang juga!</p>
            <button class="btn-primary btn-sm">Beli Sekarang</button>
        </div>
    `,
    sidebar_2: `
        <div class="ads-banner-mock vertical-ad-2">
            <h4>Gaming Zone</h4>
            <p>Mainkan game MMORPG anime terbaik 2026 gratis di browser!</p>
            <button class="btn-secondary btn-sm">Main Gratis</button>
        </div>
    `,
    footer: `
        <div class="ads-banner-mock">Join Komivex Discord & Dapatkan Info Update Manga Tercepat! 👾</div>
    `
};

function applyAllAdCodes() {
    updateAdContent("header-ads-zone", customAdCodes.header, defaultAdContents.header);
    updateAdContent("sidebar-ads-zone", customAdCodes.sidebar_1, defaultAdContents.sidebar_1);
    updateAdContent("sidebar-ads-zone-2", customAdCodes.sidebar_2, defaultAdContents.sidebar_2);
    updateAdContent("footer-ads-zone", customAdCodes.footer, defaultAdContents.footer);
}

let siteConfig = {};

async function loadAndApplySiteConfig() {
    try {
        const response = await fetch('/api/config');
        if (!response.ok) throw new Error("Gagal mengambil konfigurasi");
        siteConfig = await response.json();
        
        // Apply meta title and description
        if (siteConfig.meta_title) {
            document.title = siteConfig.meta_title;
        }
        
        // Meta description
        let metaDescTag = document.querySelector('meta[name="description"]');
        if (!metaDescTag) {
            metaDescTag = document.createElement('meta');
            metaDescTag.name = "description";
            document.head.appendChild(metaDescTag);
        }
        if (siteConfig.meta_description) {
            metaDescTag.content = siteConfig.meta_description;
        }
        
        // Search Console Verification Code
        if (siteConfig.verification_code) {
            let verifTag = document.querySelector('meta[name="google-site-verification"]');
            if (!verifTag) {
                verifTag = document.createElement('meta');
                verifTag.name = "google-site-verification";
                document.head.appendChild(verifTag);
            }
            verifTag.content = siteConfig.verification_code;
        }
        
        // Apply Logo URL
        if (siteConfig.logo_url) {
            document.querySelectorAll('.logo-link img').forEach(img => {
                img.src = siteConfig.logo_url;
            });
        }
        
        // Apply Favicon URL
        if (siteConfig.favicon_url) {
            let faviconLink = document.querySelector('link[rel="icon"]');
            if (!faviconLink) {
                faviconLink = document.createElement('link');
                faviconLink.rel = "icon";
                document.head.appendChild(faviconLink);
            }
            faviconLink.href = siteConfig.favicon_url;
        }
        
        // Apply Google Analytics Tracking Code
        if (siteConfig.analytics_id) {
            const gaId = siteConfig.analytics_id;
            if (!document.getElementById('google-analytics-script')) {
                const gaScript = document.createElement('script');
                gaScript.id = 'google-analytics-script';
                gaScript.async = true;
                gaScript.src = `https://www.googletagmanager.com/gtag/js?id=${gaId}`;
                document.head.appendChild(gaScript);
                
                const gaInit = document.createElement('script');
                gaInit.innerHTML = `
                    window.dataLayer = window.dataLayer || [];
                    function gtag(){dataLayer.push(arguments);}
                    gtag('js', new Date());
                    gtag('config', '${gaId}');
                `;
                document.head.appendChild(gaInit);
            }
        }
        
        // Populate inputs in Admin Panel if visible
        const inputMetaTitle = document.getElementById("seo-meta-title");
        const inputMetaDesc = document.getElementById("seo-meta-desc");
        const inputVerifCode = document.getElementById("seo-search-console");
        const inputLogoUrl = document.getElementById("brand-logo-url");
        const inputFaviconUrl = document.getElementById("brand-favicon-url");
        const inputScraperDomain = document.getElementById("scraper-target-domain");
        const inputAnalyticsId = document.getElementById("brand-analytics-id");
        
        if (inputMetaTitle) inputMetaTitle.value = siteConfig.meta_title || "";
        if (inputMetaDesc) inputMetaDesc.value = siteConfig.meta_description || "";
        if (inputVerifCode) inputVerifCode.value = siteConfig.verification_code || "";
        if (inputLogoUrl) inputLogoUrl.value = siteConfig.logo_url || "";
        if (inputFaviconUrl) inputFaviconUrl.value = siteConfig.favicon_url || "";
        if (inputScraperDomain) inputScraperDomain.value = siteConfig.scraper_target_domain || "https://bacakomik.my";
        if (inputAnalyticsId) inputAnalyticsId.value = siteConfig.analytics_id || "";
        
        // Show status of custom logo/favicon files
        const logoFileName = document.getElementById("logo-file-name");
        if (logoFileName) {
            if (siteConfig.logo_url && siteConfig.logo_url.includes('logo_uploaded')) {
                logoFileName.textContent = "Logo kustom terunggah (OK)";
                logoFileName.style.color = "var(--accent-color)";
            } else {
                logoFileName.textContent = "Menggunakan logo bawaan";
                logoFileName.style.color = "var(--text-secondary)";
            }
        }
        const faviconFileName = document.getElementById("favicon-file-name");
        if (faviconFileName) {
            if (siteConfig.favicon_url && siteConfig.favicon_url.includes('favicon_uploaded')) {
                faviconFileName.textContent = "Favicon kustom terunggah (OK)";
                faviconFileName.style.color = "var(--accent-color)";
            } else {
                faviconFileName.textContent = "Menggunakan favicon bawaan";
                faviconFileName.style.color = "var(--text-secondary)";
            }
        }
        
        // Apply custom ads if present in siteConfig
        if (siteConfig.custom_ad_codes) {
            customAdCodes = siteConfig.custom_ad_codes;
            
            // Backwards compatibility migration
            if (customAdCodes.sidebar && !customAdCodes.sidebar_1) {
                customAdCodes.sidebar_1 = customAdCodes.sidebar;
            }
            
            applyAllAdCodes();
            
            // Populate all textareas in Admin panel
            const inputHeadCode = document.getElementById("ad-code-head");
            const inputBodyCode = document.getElementById("ad-code-body");
            const inputHeader = document.getElementById("ad-code-header");
            const inputSidebar1 = document.getElementById("ad-code-sidebar-1");
            const inputSidebar2 = document.getElementById("ad-code-sidebar-2");
            const inputFooter = document.getElementById("ad-code-footer");
            
            if (inputHeadCode) inputHeadCode.value = customAdCodes.head || "";
            if (inputBodyCode) inputBodyCode.value = customAdCodes.body || "";
            if (inputHeader) inputHeader.value = customAdCodes.header || "";
            if (inputSidebar1) inputSidebar1.value = customAdCodes.sidebar_1 || "";
            if (inputSidebar2) inputSidebar2.value = customAdCodes.sidebar_2 || "";
            if (inputFooter) inputFooter.value = customAdCodes.footer || "";
            
            // Inject custom head scripts dynamically to document head
            if (customAdCodes.head && customAdCodes.head.trim() !== "") {
                let headAdsContainer = document.getElementById("custom-head-scripts");
                if (!headAdsContainer) {
                    headAdsContainer = document.createElement("div");
                    headAdsContainer.id = "custom-head-scripts";
                    headAdsContainer.style.display = "none";
                    document.head.appendChild(headAdsContainer);
                }
                headAdsContainer.innerHTML = customAdCodes.head;
                executeScripts(headAdsContainer);
            }
            
            // Inject custom body scripts dynamically to document body
            if (customAdCodes.body && customAdCodes.body.trim() !== "") {
                let bodyAdsContainer = document.getElementById("custom-body-scripts");
                if (!bodyAdsContainer) {
                    bodyAdsContainer = document.createElement("div");
                    bodyAdsContainer.id = "custom-body-scripts";
                    bodyAdsContainer.style.display = "none";
                    document.body.appendChild(bodyAdsContainer);
                }
                bodyAdsContainer.innerHTML = customAdCodes.body;
                executeScripts(bodyAdsContainer);
            }
        }
        
    } catch (e) {
        console.error("Error applying site configuration:", e);
    }
}

// 9. Initial Build Fire
function init() {
    const savedTheme = localStorage.getItem("komikid_theme") || "dark";
    if (savedTheme === "light") {
        document.body.classList.remove("dark-theme");
        document.body.classList.add("light-theme");
        document.querySelector(".sun-icon").style.display = "none";
        document.querySelector(".moon-icon").style.display = "block";
    } else {
        document.body.classList.add("dark-theme");
        document.body.classList.remove("light-theme");
        document.querySelector(".sun-icon").style.display = "block";
        document.querySelector(".moon-icon").style.display = "none";
    }

    updateAuthUI();
    loadAndApplySiteConfig();
    applyAllAdCodes();
    renderPopularGrid();
    renderUpdatesGrid();
    renderLibraryGrid();
    setupEventListeners();
    startAutoUpdate();
}

document.addEventListener("DOMContentLoaded", init);

// ══════════════════════════════════════════════════════════════
// 10. MOBILE NAVIGATION & SEARCH OVERLAY
// ══════════════════════════════════════════════════════════════

(function setupMobileNav() {
    // ── Bottom Nav Tab Switching ──
    const mobileNavItems = document.querySelectorAll(".mobile-bottom-nav .mobile-nav-item[data-tab]");
    mobileNavItems.forEach(btn => {
        btn.addEventListener("click", () => {
            const tab = btn.getAttribute("data-tab");
            switchTab(tab);
            // Update active state on mobile nav
            mobileNavItems.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
        });
    });

    // ── Mobile Theme Toggle ──
    const mobThemeBtn = document.getElementById("mob-nav-theme");
    if (mobThemeBtn) {
        mobThemeBtn.addEventListener("click", () => {
            toggleTheme(); // Use the existing toggleTheme function
            // Sync icon inside mobile nav
            const sunIcons = mobThemeBtn.querySelectorAll(".sun-icon");
            const moonIcons = mobThemeBtn.querySelectorAll(".moon-icon");
            const isLight = document.body.classList.contains("light-theme");
            sunIcons.forEach(el => el.style.display = isLight ? "none" : "block");
            moonIcons.forEach(el => el.style.display = isLight ? "block" : "none");
        });
    }

    // ── Mobile Search Overlay ──
    const mobSearchBtn   = document.getElementById("mob-nav-search");
    const overlay        = document.getElementById("mobile-search-overlay");
    const mobCloseBtn    = document.getElementById("mobile-search-close");
    const mobInput       = document.getElementById("mobile-search-input");
    const mobResults     = document.getElementById("mobile-search-results");

    function openMobileSearch() {
        if (!overlay) return;
        overlay.classList.add("open");
        document.body.style.overflow = "hidden";
        setTimeout(() => mobInput && mobInput.focus(), 200);
    }

    function closeMobileSearch() {
        if (!overlay) return;
        overlay.classList.remove("open");
        document.body.style.overflow = "";
        if (mobInput) mobInput.value = "";
        if (mobResults) mobResults.innerHTML = `
            <div class="mobile-search-hint">
                <div style="font-size:40px;margin-bottom:12px;">🔍</div>
                <p>Ketik untuk mencari manga favoritmu</p>
            </div>
        `;
    }

    if (mobSearchBtn) mobSearchBtn.addEventListener("click", openMobileSearch);
    if (mobCloseBtn)  mobCloseBtn.addEventListener("click", closeMobileSearch);

    // Debounced search for mobile overlay
    const debouncedMobileSearch = debounce(async (query) => {
        if (!query.trim()) {
            if (mobResults) mobResults.innerHTML = `
                <div class="mobile-search-hint">
                    <div style="font-size:40px;margin-bottom:12px;">🔍</div>
                    <p>Ketik untuk mencari manga favoritmu</p>
                </div>`;
            return;
        }

        if (mobResults) {
            mobResults.innerHTML = `<div class="mobile-search-hint"><div style="font-size:28px;">⏳</div><p>Mencari...</p></div>`;
        }

        try {
            const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
            if (!res.ok) throw new Error("Search failed");
            const list = await res.json();

            if (!mobResults) return;

            if (list.length === 0) {
                mobResults.innerHTML = `
                    <div class="mobile-search-hint">
                        <div style="font-size:40px;margin-bottom:12px;">😕</div>
                        <p>Tidak ada hasil untuk "<strong>${query}</strong>"</p>
                    </div>`;
                return;
            }

            mobResults.innerHTML = "";
            list.forEach(item => {
                const el = document.createElement("div");
                el.className = "mob-result-item";
                el.innerHTML = `
                    <img class="mob-result-thumb" src="${item.cover}" alt="${item.title}" onerror="this.src='assets/manga_cover_1.jpg'">
                    <div class="mob-result-info">
                        <div class="mob-result-title">${item.title}</div>
                        <div class="mob-result-meta">Ch. ${item.latestChapter} · ${item.updatedAt || ""}</div>
                    </div>
                    <span class="mob-result-badge ${item.type.toLowerCase()}">${item.type}</span>
                `;
                el.addEventListener("click", () => {
                    mangaDetailsCache[item.id] = item;
                    closeMobileSearch();
                    openMangaDetail(item.id);
                });
                mobResults.appendChild(el);
            });
        } catch(e) {
            if (mobResults) {
                mobResults.innerHTML = `<div class="mobile-search-hint"><p>⚠️ Gagal memuat hasil. Coba lagi.</p></div>`;
            }
        }
    }, 400);

    if (mobInput) {
        mobInput.addEventListener("input", (e) => {
            debouncedMobileSearch(e.target.value);
        });
    }

    // Keep mobile bottom nav active state in sync with tab switching
    const origSwitchTab = window.switchTab;
    if (typeof switchTab === "function") {
        // Patch switchTab to sync mobile bottom nav
        const _oldSwitch = switchTab;
        window.switchTab = function(tab) {
            _oldSwitch(tab);
            document.querySelectorAll(".mobile-bottom-nav .mobile-nav-item[data-tab]").forEach(b => {
                b.classList.toggle("active", b.getAttribute("data-tab") === tab);
            });
        };
    }
})();
