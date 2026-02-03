class TooltipManager {
    constructor() {
        this.enabled = localStorage.getItem('tooltipsEnabled') !== 'false'; // Default true
        this.tooltip = null;
        this.activeElement = null;
        this.init();
    }

    init() {
        this.createTooltipElement();
        this.setupGlobalListeners();
        this.updateToggleState();
        console.log('TooltipManager initialized');
    }

    createTooltipElement() {
        this.tooltip = document.createElement('div');
        this.tooltip.className = 'rich-tooltip';
        this.tooltip.style.display = 'none';
        document.body.appendChild(this.tooltip);
    }

    setupGlobalListeners() {
        document.addEventListener('mouseover', (e) => {
            if (!this.enabled) return;
            const target = e.target.closest('[data-tooltip]');
            if (target) {
                this.show(target);
            }
        });

        document.addEventListener('mouseout', (e) => {
            const target = e.target.closest('[data-tooltip]');
            if (target) {
                this.hide();
            }
        });

        document.addEventListener('mousemove', (e) => {
            if (this.tooltip.style.display === 'block') {
                this.move(e);
            }
        });

        // Toggle Button Listener (if exists)
        const toggleBtn = document.getElementById('toggleTooltipsBtn');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => this.toggle());
        }
    }

    show(element) {
        const content = element.getAttribute('data-tooltip');
        if (!content) return;

        this.tooltip.innerHTML = content;
        this.tooltip.style.display = 'block';
        this.tooltip.style.opacity = '1';
        this.activeElement = element;
    }

    hide() {
        this.tooltip.style.opacity = '0';
        this.activeElement = null;
        setTimeout(() => {
            if (!this.activeElement) {
                this.tooltip.style.display = 'none';
            }
        }, 200);
    }

    move(e) {
        const offset = 15;
        let left = e.pageX + offset;
        let top = e.pageY + offset;

        // Boundary checks
        if (left + this.tooltip.offsetWidth > window.innerWidth) {
            left = e.pageX - this.tooltip.offsetWidth - offset;
        }
        if (top + this.tooltip.offsetHeight > window.innerHeight) {
            top = e.pageY - this.tooltip.offsetHeight - offset;
        }

        this.tooltip.style.left = `${left}px`;
        this.tooltip.style.top = `${top}px`;
    }

    toggle() {
        this.enabled = !this.enabled;
        localStorage.setItem('tooltipsEnabled', this.enabled);
        this.updateToggleState();

        if (!this.enabled) this.hide();

        // Toast notification (if app exists)
        if (window.app && window.app.showToast) {
            window.app.showToast(`Tooltips ${this.enabled ? 'Enabled' : 'Disabled'}`);
        }
    }

    updateToggleState() {
        const btn = document.getElementById('toggleTooltipsBtn');
        if (btn) {
            btn.classList.toggle('active', this.enabled);
            btn.innerHTML = this.enabled ? '💬 On' : '💬 Off';
        }
    }
}

// Auto-initialize if script is loaded last
document.addEventListener('DOMContentLoaded', () => {
    window.tooltipManager = new TooltipManager();
});
