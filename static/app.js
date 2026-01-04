// Handles simple client-side validations and username availability checks
document.addEventListener('DOMContentLoaded', function () {
    // Set active navigation link based on current page
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.glass-nav a');

    navLinks.forEach(link => {
        const linkPath = new URL(link.href).pathname;

        // Special handling for home/index page
        if (currentPath === '/' && (linkPath === '/' || linkPath === '/index')) {
            link.classList.add('active');
        }
        // For other pages, match the path
        else if (currentPath !== '/' && linkPath === currentPath) {
            link.classList.add('active');
        }
        // Also match base routes (e.g., /messages matches /messages/*)
        else if (currentPath.startsWith(linkPath) && linkPath !== '/') {
            link.classList.add('active');
        }
    });

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
                imagePreview.innerHTML = `<img src="${e.target.result}" style="max-width:100%;max-height:120px;border-radius:6px;margin-bottom:8px"><div style="font-size:12px;color:var(--muted)">${file.name} (${(file.size / 1024).toFixed(1)}KB)</div>`;
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
document.addEventListener('DOMContentLoaded', function () {
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
window.addEventListener('DOMContentLoaded', function () {
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

/* ===== ADVANCED ANIMATION ENHANCEMENTS ===== */

// Intersection Observer for Scroll Reveal Animations
document.addEventListener('DOMContentLoaded', function () {
    // Add scroll-reveal class to elements that should animate on scroll
    const scrollElements = document.querySelectorAll('.blog-post, .sidebar-card, .welcome-banner');

    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -100px 0px'
    };

    const scrollObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('revealed');
                // Stop observing once revealed
                scrollObserver.unobserve(entry.target);
            }
        });
    }, observerOptions);

    scrollElements.forEach(el => {
        if (!el.classList.contains('scroll-revealed')) {
            el.classList.add('scroll-reveal');
            scrollObserver.observe(el);
        }
    });
});

// Enhanced Smooth Scroll with Offset
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            const offset = 100; // Account for fixed header
            const targetPosition = target.offsetTop - offset;
            window.scrollTo({
                top: targetPosition,
                behavior: 'smooth'
            });
        }
    });
});

// Animated Counter for Stats
function animateCounter(element, start, end, duration) {
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);

        // Easing function for smooth animation
        const easeOutQuad = progress * (2 - progress);
        const current = Math.floor(start + (end - start) * easeOutQuad);

        element.textContent = current;

        if (progress < 1) {
            requestAnimationFrame(update);
        } else {
            element.textContent = end;
        }
    }

    requestAnimationFrame(update);
}

// Initialize counter animations for statistics
document.addEventListener('DOMContentLoaded', function () {
    const statsElements = document.querySelectorAll('[data-count]');
    const statsObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const element = entry.target;
                const endValue = parseInt(element.getAttribute('data-count'));
                animateCounter(element, 0, endValue, 1500);
                statsObserver.unobserve(element);
            }
        });
    }, { threshold: 0.5 });

    statsElements.forEach(el => statsObserver.observe(el));
});

// Particle Background Effect
class ParticleBackground {
    constructor(container) {
        this.container = container;
        this.particles = [];
        this.particleCount = 30;
        this.init();
    }

    init() {
        // Create canvas
        this.canvas = document.createElement('canvas');
        this.canvas.style.position = 'fixed';
        this.canvas.style.top = '0';
        this.canvas.style.left = '0';
        this.canvas.style.width = '100%';
        this.canvas.style.height = '100%';
        this.canvas.style.pointerEvents = 'none';
        this.canvas.style.zIndex = '0';
        this.canvas.style.opacity = '0.3';
        document.body.prepend(this.canvas);

        this.ctx = this.canvas.getContext('2d');
        this.resize();
        window.addEventListener('resize', () => this.resize());

        // Create particles
        for (let i = 0; i < this.particleCount; i++) {
            this.particles.push({
                x: Math.random() * this.canvas.width,
                y: Math.random() * this.canvas.height,
                vx: (Math.random() - 0.5) * 0.5,
                vy: (Math.random() - 0.5) * 0.5,
                radius: Math.random() * 2 + 1,
                color: Math.random() > 0.5 ? 'rgba(0,212,255,0.4)' : 'rgba(255,107,53,0.4)'
            });
        }

        this.animate();
    }

    resize() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
    }

    animate() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        // Update and draw particles
        this.particles.forEach(particle => {
            particle.x += particle.vx;
            particle.y += particle.vy;

            // Wrap around screen
            if (particle.x < 0) particle.x = this.canvas.width;
            if (particle.x > this.canvas.width) particle.x = 0;
            if (particle.y < 0) particle.y = this.canvas.height;
            if (particle.y > this.canvas.height) particle.y = 0;

            // Draw particle
            this.ctx.beginPath();
            this.ctx.arc(particle.x, particle.y, particle.radius, 0, Math.PI * 2);
            this.ctx.fillStyle = particle.color;
            this.ctx.fill();
        });

        // Draw connections
        this.particles.forEach((p1, i) => {
            this.particles.slice(i + 1).forEach(p2 => {
                const dx = p1.x - p2.x;
                const dy = p1.y - p2.y;
                const distance = Math.sqrt(dx * dx + dy * dy);

                if (distance < 150) {
                    this.ctx.beginPath();
                    this.ctx.moveTo(p1.x, p1.y);
                    this.ctx.lineTo(p2.x, p2.y);
                    this.ctx.strokeStyle = `rgba(0,212,255,${0.15 * (1 - distance / 150)})`;
                    this.ctx.lineWidth = 0.5;
                    this.ctx.stroke();
                }
            });
        });

        requestAnimationFrame(() => this.animate());
    }
}

// Initialize particle background (only on dashboard pages)
document.addEventListener('DOMContentLoaded', function () {
    if (document.querySelector('.dashboard-body')) {
        // Only initialize if user prefers animations
        const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        if (!prefersReducedMotion) {
            new ParticleBackground(document.body);
        }
    }
});

// Enhanced Ripple Effect for Buttons
document.addEventListener('DOMContentLoaded', function () {
    const rippleButtons = document.querySelectorAll('.btn-primary, .btn-secondary, .btn-like, .post-action-btn');

    rippleButtons.forEach(button => {
        button.addEventListener('click', function (e) {
            // Create ripple element
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;

            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';
            ripple.classList.add('ripple-effect');

            this.appendChild(ripple);

            setTimeout(() => ripple.remove(), 600);
        });
    });
});

// Parallax Scroll Effect for Images
document.addEventListener('DOMContentLoaded', function () {
    const parallaxImages = document.querySelectorAll('.post-image img');

    window.addEventListener('scroll', () => {
        parallaxImages.forEach(img => {
            const rect = img.getBoundingClientRect();
            const windowHeight = window.innerHeight;

            if (rect.top < windowHeight && rect.bottom > 0) {
                const scrolled = (windowHeight - rect.top) / (windowHeight + rect.height);
                const translateY = (scrolled - 0.5) * 20; // Subtle parallax
                img.style.transform = `scale(1.1) translateY(${translateY}px)`;
            }
        });
    });
});

// Typed Effect for Welcome Message (Optional)
function typeWriter(element, text, speed = 50) {
    let i = 0;
    element.textContent = '';

    function type() {
        if (i < text.length) {
            element.textContent += text.charAt(i);
            i++;
            setTimeout(type, speed);
        }
    }

    type();
}

// Image Lazy Loading with Fade-in
document.addEventListener('DOMContentLoaded', function () {
    const images = document.querySelectorAll('img[data-src]');

    const imageObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.addEventListener('load', () => {
                    img.style.opacity = '1';
                });
                imageObserver.unobserve(img);
            }
        });
    });

    images.forEach(img => {
        img.style.opacity = '0';
        img.style.transition = 'opacity 0.6s ease';
        imageObserver.observe(img);
    });
});

// Add floating animation to avatars on hover
document.addEventListener('DOMContentLoaded', function () {
    const avatars = document.querySelectorAll('img[src*="gravatar"], img[src*="avatar"]');

    avatars.forEach(avatar => {
        avatar.addEventListener('mouseenter', function () {
            this.classList.add('floating-element');
        });

        avatar.addEventListener('mouseleave', function () {
            this.classList.remove('floating-element');
        });
    });
});

// Progress Bar for Page Scroll
document.addEventListener('DOMContentLoaded', function () {
    const progressBar = document.createElement('div');
    progressBar.style.position = 'fixed';
    progressBar.style.top = '0';
    progressBar.style.left = '0';
    progressBar.style.height = '3px';
    progressBar.style.background = 'linear-gradient(90deg, var(--primary), var(--accent-warm))';
    progressBar.style.zIndex = '3000'; // Above header (2000) but below modals
    progressBar.style.transition = 'width 0.1s ease';
    progressBar.style.width = '0%';
    document.body.appendChild(progressBar);

    window.addEventListener('scroll', () => {
        const windowHeight = window.innerHeight;
        const documentHeight = document.documentElement.scrollHeight;
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        const scrollPercent = (scrollTop / (documentHeight - windowHeight)) * 100;

        progressBar.style.width = scrollPercent + '%';
    });
});

// Enhanced Comment Form Animation
document.addEventListener('DOMContentLoaded', function () {
    const commentForms = document.querySelectorAll('.comment-form');

    commentForms.forEach(form => {
        const input = form.querySelector('input');
        if (input) {
            input.addEventListener('focus', function () {
                form.style.transform = 'scale(1.02)';
                form.style.transition = 'transform 0.3s ease';
            });

            input.addEventListener('blur', function () {
                form.style.transform = 'scale(1)';
            });
        }
    });
});

// Add shake animation for error states
function shakeElement(element) {
    element.classList.add('shake');
    setTimeout(() => element.classList.remove('shake'), 500);
}

// Add CSS for shake animation
document.addEventListener('DOMContentLoaded', function () {
    if (!document.querySelector('#shake-styles')) {
        const style = document.createElement('style');
        style.id = 'shake-styles';
        style.textContent = `
            @keyframes shake {
                0%, 100% { transform: translateX(0); }
                10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
                20%, 40%, 60%, 80% { transform: translateX(5px); }
            }
            .shake { animation: shake 0.5s; }
        `;
        document.head.appendChild(style);
    }
});

console.log('✨ Enhanced animations loaded successfully!');
