document.addEventListener("DOMContentLoaded", () => {
    
    // -----------------------------------------------------------------
    // 1. THREE.JS 3D BACKGROUND SETUP
    // -----------------------------------------------------------------
    const canvas = document.querySelector('#bg-canvas');
    if (canvas && window.THREE) {
        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
        const renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
        
        renderer.setPixelRatio(window.devicePixelRatio);
        renderer.setSize(window.innerWidth, window.innerHeight);
        camera.position.z = 30;

        const geometry = new THREE.BufferGeometry();
        const particlesCount = 700;
        const posArray = new Float32Array(particlesCount * 3);

        for(let i = 0; i < particlesCount * 3; i++) {
            posArray[i] = (Math.random() - 0.5) * 100;
        }

        geometry.setAttribute('position', new THREE.BufferAttribute(posArray, 3));

        const material = new THREE.PointsMaterial({
            size: 0.15,
            color: 0x2ecc71, 
            transparent: true,
            opacity: 0.8,
            blending: THREE.AdditiveBlending
        });

        const particlesMesh = new THREE.Points(geometry, material);
        scene.add(particlesMesh);

        let mouseX = 0;
        let mouseY = 0;
        document.addEventListener('mousemove', (event) => {
            mouseX = event.clientX / window.innerWidth - 0.5;
            mouseY = event.clientY / window.innerHeight - 0.5;
        });

        const animate = () => {
            requestAnimationFrame(animate);
            
            particlesMesh.rotation.y += 0.001;
            particlesMesh.rotation.x += 0.0005;
            particlesMesh.rotation.y += mouseX * 0.01;
            particlesMesh.rotation.x += mouseY * 0.01;

            renderer.render(scene, camera);
        };
        
        animate();

        window.addEventListener('resize', () => {
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        });
    }

    // -----------------------------------------------------------------
    // 2. EXPIRY COUNTDOWN TIMER & DYNAMIC URGENCY
    // -----------------------------------------------------------------
    const expiryElements = document.querySelectorAll('.expiry-timer');
    
    if (expiryElements.length > 0) {
        setInterval(() => {
            const now = new Date().getTime();
            
            expiryElements.forEach(el => {
                const expiryTime = new Date(el.dataset.expires).getTime();
                const distance = expiryTime - now;
                const card = el.closest('.feature-card');
                
                if (distance < 0) {
                    el.innerHTML = "🔴 EXPIRED";
                    el.style.color = "#e74c3c";
                    if (card) card.classList.remove('urgent-card');
                    
                    const form = card ? card.querySelector('form') : null;
                    if(form) form.style.display = 'none';
                } else {
                    const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                    const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
                    const seconds = Math.floor((distance % (1000 * 60)) / 1000);
                    
                    let timeStr = "⏳ Expires in: ";
                    if (hours > 0) timeStr += `${hours}h `;
                    timeStr += `${minutes}m ${seconds}s`;
                    
                    el.innerHTML = timeStr;
                    
                    // Trigger glowing urgency state if under 15 minutes
                    if (hours === 0 && minutes < 15) {
                        el.style.color = "#e74c3c";
                        if (card && !card.classList.contains('urgent-card')) {
                            card.classList.add('urgent-card');
                        }
                    } else {
                        el.style.color = "";
                        if (card && card.classList.contains('urgent-card')) {
                            card.classList.remove('urgent-card');
                        }
                    }
                }
            });
        }, 1000);
    }

    // -----------------------------------------------------------------
    // 3. CUSTOM CURSOR TRACKING
    // -----------------------------------------------------------------
    const cursor = document.querySelector('.custom-cursor');
    
    if (cursor) {
        document.addEventListener('mousemove', (e) => {
            cursor.style.left = e.clientX + 'px';
            cursor.style.top = e.clientY + 'px';
        });

        const clickables = document.querySelectorAll('a, button, input, select, label');
        
        clickables.forEach(el => {
            el.addEventListener('mouseenter', () => cursor.classList.add('hovering'));
            el.addEventListener('mouseleave', () => cursor.classList.remove('hovering'));
        });
    }

    // -----------------------------------------------------------------
    // 4. BUTTON RIPPLE CLICK EFFECT
    // -----------------------------------------------------------------
    const buttons = document.querySelectorAll('.btn-primary, .btn-ghost, .nav-cta, button');
    
    buttons.forEach(btn => {
        btn.addEventListener('click', function (e) {
            // Calculate exact click coordinates relative to the button
            const rect = e.target.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            // Create the ripple span
            const ripple = document.createElement('span');
            ripple.classList.add('ripple');
            
            // Size it based on the button's largest dimension
            const size = Math.max(rect.width, rect.height);
            ripple.style.width = ripple.style.height = `${size}px`;
            
            // Center the ripple on the click point
            ripple.style.left = `${x - size / 2}px`;
            ripple.style.top = `${y - size / 2}px`;
            
            // Append and animate
            this.appendChild(ripple);
            
            // Remove the span from the DOM after the animation completes (600ms)
            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
    });

// -----------------------------------------------------------------
    // 5. LIVE SEARCH & DIETARY FILTERS
    // -----------------------------------------------------------------
    const searchInput = document.querySelector('#food-search');
    const filterChips = document.querySelectorAll('.filter-chip');
    const foodCards = document.querySelectorAll('.food-listing-card');

    if (searchInput && foodCards.length > 0) {
        let currentFilter = 'all';

        const filterCards = () => {
            const searchTerm = searchInput.value.toLowerCase();
            
            foodCards.forEach(card => {
                const nameAndLocation = card.dataset.name || '';
                const dietary = card.dataset.dietary || '';
                
                const matchesSearch = nameAndLocation.includes(searchTerm);
                const matchesDiet = currentFilter === 'all' || dietary.includes(currentFilter);
                
                // Show card if it matches BOTH the search bar and the selected chip
                if (matchesSearch && matchesDiet) {
                    card.style.display = 'block';
                } else {
                    card.style.display = 'none';
                }
            });
        };

        // Listen for typing in the search bar
        searchInput.addEventListener('input', filterCards);

        // Listen for clicks on the dietary filter buttons
        filterChips.forEach(chip => {
            chip.addEventListener('click', (e) => {
                // Remove the active styling from all chips
                filterChips.forEach(c => c.classList.remove('active'));
                
                // Add the active styling to the clicked chip
                e.target.classList.add('active');
                
                // Update the current filter and re-run the filtering function
                currentFilter = e.target.dataset.filter;
                filterCards();
            });
        });
    }});