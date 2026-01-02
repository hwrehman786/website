// Handles simple client-side validations and username availability checks
document.addEventListener('DOMContentLoaded', function () {
    const regUsername = document.getElementById('regUsername');
    const usernameHint = document.getElementById('usernameHint');
    const regPassword = document.getElementById('regPassword');
    const passwordHint = document.getElementById('passwordHint');
    const registerForm = document.getElementById('registerForm');

    if (regUsername) {
        let timeout;
        regUsername.addEventListener('input', function () {
            clearTimeout(timeout);
            usernameHint.textContent = '';
            timeout = setTimeout(async () => {
                const val = regUsername.value.trim();
                if (!val) return;
                try {
                    const res = await axios.get('/check_username', { params: { username: val } });
                    if (res.data.exists) {
                        usernameHint.textContent = 'Username is already taken.';
                        usernameHint.classList.add('hint-error');
                    } else {
                        usernameHint.textContent = 'Username is available.';
                        usernameHint.classList.remove('hint-error');
                        usernameHint.classList.add('hint-ok');
                    }
                } catch (e) {
                    console.warn('username check failed', e);
                }
            }, 400);
        });
    }

    if (regPassword && registerForm) {
        registerForm.addEventListener('submit', function (e) {
            const pw = regPassword.value || '';
            if (pw.length !== 8) {
                e.preventDefault();
                passwordHint.textContent = 'Password must be exactly 8 characters.';
                passwordHint.classList.add('hint-error');
            }
        });

        regPassword.addEventListener('input', function () {
            const pw = regPassword.value || '';
            if (pw.length !== 8) {
                passwordHint.classList.add('hint-error');
            } else {
                passwordHint.classList.remove('hint-error');
                passwordHint.classList.add('hint-ok');
            }
        });
    }

    // Markdown live preview (uses marked.js included on create/edit post pages)
    const mdEditor = document.getElementById('contentEditor');
    const mdPreview = document.getElementById('mdPreview');
    if (mdEditor && mdPreview && typeof marked !== 'undefined') {
        function renderPreview() {
            try {
                const raw = mdEditor.value || '';
                mdPreview.innerHTML = marked.parse(raw);
            } catch (e) {
                mdPreview.textContent = mdEditor.value || '';
            }
        }
        mdEditor.addEventListener('input', renderPreview);
        // initial render
        renderPreview();
    }

    // Drag and drop image upload for post creation/editing
    const dropZone = document.getElementById('dropZone');
    const imageInput = document.getElementById('image');
    const imagePreview = document.getElementById('imagePreview');
    
    if (dropZone && imageInput) {
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.style.background = 'rgba(0,212,255,0.08)';
            dropZone.style.borderColor = 'rgba(0,212,255,0.3)';
        });
        
        dropZone.addEventListener('dragleave', () => {
            dropZone.style.background = '';
            dropZone.style.borderColor = 'rgba(255,255,255,0.2)';
        });
        
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.style.background = '';
            dropZone.style.borderColor = 'rgba(255,255,255,0.2)';
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                imageInput.files = files;
                showImagePreview(files[0]);
            }
        });

        dropZone.addEventListener('click', () => imageInput.click());

        imageInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                showImagePreview(e.target.files[0]);
            }
        });
    }

    function showImagePreview(file) {
        if (!imagePreview) return;
        if (file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = (e) => {
                imagePreview.innerHTML = `<img src="${e.target.result}" style="max-width:100%;max-height:120px;border-radius:6px;margin-bottom:8px"><div style="font-size:12px;color:var(--muted)">${file.name} (${(file.size/1024).toFixed(1)}KB)</div>`;
            };
            reader.readAsDataURL(file);
        }
    }

    // Tag cloud fetch and render
    const tagCloud = document.getElementById('tagCloud');
    if (tagCloud) {
        axios.get('/api/tags').then(res => {
            if (res.data.tags && res.data.tags.length > 0) {
                const maxCount = Math.max(...res.data.tags.map(t => t.count));
                const html = res.data.tags.map(tag => {
                    const size = 12 + ((tag.count / maxCount) * 14); // 12px to 26px
                    const opacity = 0.6 + ((tag.count / maxCount) * 0.4); // 0.6 to 1.0
                    return `<a href="/tag/${encodeURIComponent(tag.name)}" style="font-size:${size}px;opacity:${opacity};color:var(--primary);text-decoration:none;transition:0.2s" onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=${opacity}">#${tag.name}</a>`;
                }).join('');
                tagCloud.innerHTML = html;
            }
        }).catch(() => {
            tagCloud.innerHTML = '<div style="color:var(--muted);font-size:12px">Could not load tags</div>';
        });
    }

    // Theme toggle (light/dark) using localStorage
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        const currentTheme = localStorage.getItem('theme') || 'dark';
        applyTheme(currentTheme);
        
        themeToggle.addEventListener('click', () => {
            const newTheme = localStorage.getItem('theme') === 'dark' ? 'light' : 'dark';
            localStorage.setItem('theme', newTheme);
            applyTheme(newTheme);
        });
    }

    function applyTheme(theme) {
        const isDark = theme === 'dark';
        document.documentElement.setAttribute('data-theme', theme);
        const toggle = document.getElementById('themeToggle');
        if (toggle) {
            toggle.innerHTML = isDark ? '<i class="fas fa-sun"></i>' : '<i class="fas fa-moon"></i>';
        }
        // Update CSS variables for theme
        const root = document.documentElement;
        if (isDark) {
            root.style.setProperty('--bg-0', '#0b2230');
            root.style.setProperty('--bg-1', '#071726');
            root.style.setProperty('--panel', 'rgba(255,255,255,0.94)');
            root.style.setProperty('--text', '#08303a');
        } else {
            root.style.setProperty('--bg-0', '#f8f9fa');
            root.style.setProperty('--bg-1', '#e8ecf0');
            root.style.setProperty('--panel', 'rgba(255,255,255,0.98)');
            root.style.setProperty('--text', '#1a1a1a');
        }
    }

