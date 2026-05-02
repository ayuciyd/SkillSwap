// Dismiss flash messages automatically after 5 seconds
document.addEventListener('DOMContentLoaded', () => {
    const flashes = document.querySelectorAll('.flash-msg');
    
    flashes.forEach(flash => {
        setTimeout(() => {
            flash.style.animation = 'slideIn 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275) reverse';
            setTimeout(() => flash.remove(), 280);
        }, 5000);
    });
});

function dismissFlash(btn) {
    const msg = btn.closest('.flash-msg');
    msg.style.display = 'none';
}

// Any tooltips or interactive JS can go here.

function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    if (sidebar) {
        sidebar.classList.toggle('active');
    }
}
