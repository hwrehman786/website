// Handles simple client-side validations and username availability checks
document.addEventListener('DOMContentLoaded', function () {
    const regUsername = document.getElementById('regUsername');
    const usernameHint = document.getElementById('usernameHint');
    const regPassword = document.getElementById('regPassword');
    const passwordHint = document.getElementById('passwordHint');
    const registerForm = document.getElementById('registerForm');

    // Reset all like buttons to 0 on page load
    const likeButtons = document.querySelectorAll('.btn-like');
    likeButtons.forEach(btn => {
        btn.classList.remove('liked');
        btn.querySelector('span:nth-child(2)').textContent = 'Like';
        btn.querySelector('span:last-child').textContent = '(0)';
    });

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

});

/* ===== NEW INTERACTIVE FEATURES ===== */

// Toggle Like Button with persistent storage
function toggleLike(button, postId) {
    const isLiked = button.classList.contains('liked');
    const endpoint = isLiked ? `/api/unlike/${postId}` : `/api/like/${postId}`;
    
    fetch(endpoint, { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                button.classList.toggle('liked');
                const countSpan = button.querySelector('.like-count');
                countSpan.textContent = `(${data.like_count})`;
                
                if (button.classList.contains('liked')) {
                    button.querySelector('span:nth-child(2)').textContent = 'Liked';
                } else {
                    button.querySelector('span:nth-child(2)').textContent = 'Like';
                }
            }
        })
        .catch(err => console.error('Like error:', err));
}

// Load like state on page load
document.addEventListener('DOMContentLoaded', function() {
    const likeButtons = document.querySelectorAll('[data-post-id]');
    likeButtons.forEach(button => {
        const postId = button.getAttribute('data-post-id');
        fetch(`/api/is_liked/${postId}`)
            .then(res => res.json())
            .then(data => {
                if (data.liked) {
                    button.classList.add('liked');
                    button.querySelector('span:nth-child(2)').textContent = 'Liked';
                }
                const countSpan = button.querySelector('.like-count');
                countSpan.textContent = `(${data.like_count})`;
            })
            .catch(err => console.error('Error loading like state:', err));
    });
});

// Copy Post Link to Clipboard
function copyPostLink(url) {
    navigator.clipboard.writeText(window.location.origin + url).then(() => {
        alert('Post link copied to clipboard!');
    }).catch(() => {
        alert('Could not copy link');
    });
}

// Smooth scroll to comments
function scrollToComments(postId) {
    const commentsSection = document.querySelector(`[data-post-id="${postId}"] .comments-section`);
    if (commentsSection) {
        commentsSection.scrollIntoView({ behavior: 'smooth' });
        commentsSection.querySelector('input')?.focus();
    }
}

// Toggle Follow Button
function toggleFollow(button, userId) {
    const isFollowing = button.classList.contains('following');
    const endpoint = isFollowing ? `/unfollow/${userId}` : `/follow/${userId}`;
    
    fetch(endpoint, { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                button.classList.toggle('following');
                if (button.classList.contains('following')) {
                    button.querySelector('span').textContent = 'Following';
                    button.querySelector('i').className = 'fas fa-check';
                } else {
                    button.querySelector('span').textContent = 'Follow';
                    button.querySelector('i').className = 'fas fa-user-plus';
                }
            }
        })
        .catch(err => console.error('Follow error:', err));
}

// Toggle Bookmark
function toggleBookmark(button, postId) {
    const isBookmarked = button.classList.contains('bookmarked');
    const endpoint = isBookmarked ? `/api/unbookmark/${postId}` : `/api/bookmark/${postId}`;
    
    fetch(endpoint, { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                button.classList.toggle('bookmarked');
                if (button.classList.contains('bookmarked')) {
                    button.querySelector('i').className = 'fas fa-bookmark';
                    button.style.background = 'rgba(255,107,53,0.15)';
                    button.style.borderColor = 'rgba(255,107,53,0.3)';
                } else {
                    button.querySelector('i').className = 'fas fa-bookmark';
                    button.style.background = 'rgba(0,212,255,0.05)';
                    button.style.borderColor = 'rgba(0,212,255,0.1)';
                }
            }
        })
        .catch(err => console.error('Bookmark error:', err));
}

// Dark mode toggle
function toggleDarkMode() {
    const isDarkMode = document.body.classList.toggle('dark-mode');
    localStorage.setItem('darkMode', isDarkMode);
    
    // Update button icon
    const btn = document.getElementById('darkModeToggle');
    if (isDarkMode) {
        btn.innerHTML = '<i class="fas fa-sun"></i>';
        btn.title = 'Toggle light mode';
    } else {
        btn.innerHTML = '<i class="fas fa-moon"></i>';
        btn.title = 'Toggle dark mode';
    }
    
    // Sync with backend if user is logged in
    if (document.querySelector('.user-info span').textContent !== 'Guest') {
        fetch('/api/toggle_dark_mode', { method: 'POST' })
            .catch(err => console.warn('Could not sync dark mode preference:', err));
    }
}

// Initialize dark mode from localStorage
window.addEventListener('DOMContentLoaded', function() {
    const isDarkMode = localStorage.getItem('darkMode') === 'true';
    if (isDarkMode) {
        document.body.classList.add('dark-mode');
        const btn = document.getElementById('darkModeToggle');
        if (btn) {
            btn.innerHTML = '<i class="fas fa-sun"></i>';
            btn.title = 'Toggle light mode';
        }
    }
});
