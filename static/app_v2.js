/**
 * Multi-Agent Orchestrator - Main Application
 * Integrates VisualCanvas, NodeEditor, and WebSocket communication
 */

class OrchestratorApp {
    constructor() {
        this.ws = null;
        this.isConnected = false;
        this.isRunning = false;
        this.projectWorkflowsPath = ''; // Dynamic path from server
        this.systemInfoPromise = null; // Promise tracker for path fetching

        // God Mode Stats
        this.totalTokens = 0;
        this.totalCost = 0.00;
        this.tooltipsEnabled = true;
        this.expertMode = false;
        this.hudInterval = null;


        // Initialize components
        this.canvas = new VisualCanvas('canvasContainer');
        this.nodeEditor = new NodeEditor('nodeEditorContainer');
        this.nodeEditor.init(); // <--- Initialize the editor
        this.providerManager = new ProviderManager(this);

        // Bind component events
        this.bindComponentEvents();
        this.bindUIEvents();

        // Connect WebSocket
        this.connectWebSocket();

        // Fetch system info
        this.fetchSystemInfo();

        // Add default nodes for demo
        this.addDefaultNodes();
    }

    async fetchSystemInfo() {
        if (this.systemInfoPromise) return this.systemInfoPromise;

        this.systemInfoPromise = (async () => {
            console.log('Orchestrator: Fetching system info...');
            const pathEl = document.getElementById('guidancePath');

            try {
                const response = await fetch('/api/system/info');
                if (!response.ok) {
                    const errorText = await response.text();
                    throw new Error(`HTTP ${response.status}: ${errorText || 'Not Found'}`);
                }

                const data = await response.json();
                if (!data.workflows_path) {
                    throw new Error('Server returned empty path');
                }

                this.projectWorkflowsPath = data.workflows_path;

                if (pathEl) {
                    pathEl.value = this.projectWorkflowsPath;
                    pathEl.style.color = "#fff";
                    console.log('Orchestrator: Project path updated ->', this.projectWorkflowsPath);
                }
                return { success: true };
            } catch (e) {
                console.error('Orchestrator: Failed to fetch system info:', e);
                const errorMsg = `⚠️ Error: ${e.message}`;
                if (pathEl) {
                    pathEl.value = errorMsg;
                    pathEl.style.color = "#ff4d4d";
                }
                // Clear promise so we can retry later
                this.systemInfoPromise = null;
                return { success: false, error: errorMsg };
            }
        })();

        return this.systemInfoPromise;
    }

    // ============ WebSocket Connection ============

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        console.log(`Connecting to WebSocket: ${wsUrl}`);
        const statusDot = document.querySelector('.status-dot');
        const statusText = document.querySelector('.status-text');

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket Connected');
            this.isConnected = true;
            if (statusDot) {
                statusDot.style.background = '#10b981'; // Green
                statusDot.classList.add('pulse');
            }
            if (statusText) statusText.textContent = 'Active';

            // Re-auth or sync state if needed
            this.ws.send(JSON.stringify({ type: 'get_state' }));
        };

        this.ws.onmessage = (event) => {
            this.handleMessage(event);
        };

        this.ws.onclose = () => {
            console.log('WebSocket Disconnected. Reconnecting...');
            this.isConnected = false;

            if (statusDot) {
                statusDot.style.background = '#ef4444'; // Red
                statusDot.classList.remove('pulse');
            }
            if (statusText) statusText.textContent = 'Connecting...';

            setTimeout(() => this.connectWebSocket(), 3000);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket Error:', error);
        };
    }

    handleMessage(event) {
        try {
            const msg = JSON.parse(event.data);
            const { type, data } = msg;

            switch (type) {
                case 'connected':
                    this.addLogEntry({ speaker: 'System', message: 'Connected to Orchestrator' });
                    break;

                case 'node_update':
                    if (data.id) {
                        this.canvas.updateNode(data.id, data.updates);
                        if (data.updates.status === 'running') {
                            this.setActiveNode(data.name, data.id);
                        } else if (data.updates.status === 'completed' || data.updates.status === 'failed') {
                            // Only clear if it's the active one
                            if (document.getElementById('activeNodeName').textContent === data.name) {
                                this.setActiveNode(null);
                            }
                        }
                    }
                    break;

                case 'thought':
                    this.appendLiveThought(data);
                    break;

                case 'log':
                    this.addLogEntry(data);
                    break;

                case 'token_usage':
                    this.updateHUD(data);
                    break;

                case 'trace':
                    this.addTraceEntry(data.node, data.action, data.data);
                    break;

                case 'workflow_started':
                    this.showExecutionPanel();
                    this.addLogEntry({ speaker: 'System', message: 'Workflow Started 🚀' });
                    break;

                case 'workflow_complete':
                    this.addLogEntry({ speaker: 'System', message: 'Workflow Complete ✨' });
                    this.setActiveNode(null);
                    break;

                case 'providers_update':
                    if (this.providerManager) this.providerManager.providers = data;
                    break;

                case 'error':
                    this.showToast(data.message || 'Unknown Error', 'error');
                    break;

                case 'ui_component':
                    this.appendUIComponent(data);
                    break;

                default:
                    // transform-layer updates etc
                    break;
            }
        } catch (e) {
            console.error('Error handling message:', e);
        }
    }

    addLogEntry({ speaker, message, timestamp }) {
        const logsContainer = document.getElementById('logsContainer');
        if (!logsContainer) return;

        const entry = document.createElement('div');
        entry.className = 'log-entry';
        const time = timestamp ? new Date(timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();

        entry.innerHTML = `
            <span class="log-time">[${time}]</span>
            <span class="log-speaker ${speaker ? speaker.toLowerCase() : 'system'}">${speaker || 'System'}:</span>
            <span class="log-message">${message}</span>
        `;

        logsContainer.appendChild(entry);
        logsContainer.scrollTop = logsContainer.scrollHeight;
    }

    showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer') || this.createToastContainer();
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container';
        document.body.appendChild(container);
        return container;
    }

    // ============ Component Events ============

    bindComponentEvents() {
        // Canvas node selection
        this.canvas.on('nodeSelected', (node) => {
            this.nodeEditor.open(node);
        });

        this.canvas.on('nodeDeselected', () => {
            this.nodeEditor.close();
        });

        this.canvas.on('openEditor', (node) => {
            this.nodeEditor.open(node);
        });

        // Node editor events
        this.nodeEditor.on('saveNode', ({ id, updates }) => {
            this.canvas.updateNode(id, updates);
        });

        this.nodeEditor.on('deleteNode', (nodeId) => {
            this.canvas.removeNode(nodeId);
        });

        // Keyboard action events
        this.canvas.on('saveRequested', () => {
            // Background autosave to localStorage is handled by canvas_v2
            // We can also trigger a background sync here if desired
            this._backgroundSync();
        });
        this.canvas.on('runRequested', () => this.openMissionModal());

        // Context Menu Events
        this.canvas.on('attachWorkflowRequested', (node) => {
            this.handleAttachWorkflow(node);
        });

        this.canvas.on('mergeWorkflowRequested', (node) => {
            this.handleMergeWorkflow(node);
        });

        this.canvas.on('node:update', () => {
            if (this.debouncedSave) this.debouncedSave();
        });

        this.canvas.on('searchAddRequested', (item) => {
            this.addNodeFromPalette(item.type, item.canvasX, item.canvasY, { name: item.name });
        });

        this.canvas.on('edgeSelected', (edge) => {
            this.openEdgeModal(edge);
        });
    }

    // ============ UI Events ============

    bindUIEvents() {
        const bind = (id, event, handler) => {
            const el = document.getElementById(id);
            if (el) {
                el.addEventListener(event, handler);
            } else {
                console.warn(`Orchestrator: Element '${id}' not found for binding '${event}'`);
            }
        };

        // Toolbar buttons
        bind('runWorkflowBtn', 'click', () => this.openMissionModal());
        bind('factoryResetBtn', 'click', () => {
            if (confirm('FACTORY RESET: This will clear your local autosave and reload the page. Are you sure?')) {
                localStorage.removeItem('orchestrator_autosave');
                window.location.reload();
            }
        });

        // Sidebar Collapse & Resize
        this.initSidebarToggles();
        this.initResizableSidebars();
        this.initBottomDrawer();

        // Agent Palette Accordion
        document.querySelectorAll('.palette-group-title').forEach(title => {
            title.addEventListener('click', () => {
                title.parentElement.classList.toggle('collapsed');
            });
        });

        if (toggleSidebarsBtn) {
            toggleSidebarsBtn.addEventListener('click', () => {
                const sLeft = document.getElementById('sidebarLeft');
                const sRight = document.getElementById('sidebarRight');
                if (sLeft) sLeft.classList.toggle('collapsed');
                if (sRight) sRight.classList.toggle('collapsed');
                setTimeout(() => this.canvas.fitToContainer(), 300);
            });
        }

        bind('tidyBtn', 'click', () => this.canvas.tidyLayout());
        bind('fitViewBtn', 'click', () => this.canvas.fitView());

        bind('clearCanvasBtn', 'click', async () => {
            if (confirm('FULL SYSTEM RESET: Clear all nodes, logs, and backend state?')) {
                try {
                    await fetch('/api/workflow/reset', { method: 'POST' });
                    this.canvas.clear();
                    this.clearLogs();
                    const ts = document.getElementById('thoughtStreamContent');
                    if (ts) ts.innerHTML = '<div class="empty-state"><p>Waiting for AI reasoning...</p></div>';
                    this.addLogEntry({ speaker: 'System', message: 'System reset complete' });
                } catch (e) {
                    console.error('Reset failed:', e);
                    alert('Backend reset failed: ' + e.message);
                }
            }
        });

        bind('saveWorkflowBtn', 'click', () => this.saveWorkflow());
        bind('loadWorkflowBtn', 'click', () => this.loadWorkflow());
        bind('clearLogsBtn', 'click', () => this.clearLogs());

        const clearResultsBtn = document.getElementById('clearResultsBtn');
        if (clearResultsBtn) {
            clearResultsBtn.addEventListener('click', () => this.clearResults());
        }

        bind('clearBlackboardBtn', 'click', () => {
            if (confirm('Clear entire Blackboard state?')) {
                if (this.ws) this.ws.send(JSON.stringify({ type: 'clear_blackboard' }));
            }
        });

        bind('clearTraceBtn', 'click', () => {
            const container = document.getElementById('traceTreeContent');
            if (container) container.innerHTML = '<div class="empty-state">Trace cleared</div>';
        });

        bind('helpBtn', 'click', () => {
            const helpModal = document.getElementById('helpModal');
            if (helpModal) {
                helpModal.classList.remove('hidden');
                helpModal.style.display = 'flex';
            }
        });

        bind('closeHelpBtn', 'click', () => {
            const helpModal = document.getElementById('helpModal');
            if (helpModal) helpModal.style.display = 'none';
        });
        bind('closeHelpModal', 'click', () => {
            const helpModal = document.getElementById('helpModal');
            if (helpModal) helpModal.style.display = 'none';
        });

        // Generative AI Events
        bind('magicAutoBtn', 'click', () => {
            const genModal = document.getElementById('generationModal');
            const promptInput = document.getElementById('genPrompt');
            if (genModal) {
                genModal.classList.remove('hidden');
                genModal.style.display = 'flex';
                if (promptInput) {
                    promptInput.focus();
                    this.loadTemplates();
                    const selected = this.canvas.selectedNode;
                    if (selected) {
                        promptInput.placeholder = `Attach new nodes to '${selected.name}'...`;
                    } else {
                        promptInput.placeholder = 'Describe a new workflow...';
                    }
                }
            }
        });

        bind('smartConnectBtn', 'click', () => this.handleSmartConnect());

        bind('closeGenModal', 'click', () => document.getElementById('generationModal').classList.add('hidden'));
        bind('cancelGenBtn', 'click', () => document.getElementById('generationModal').classList.add('hidden'));

        bind('startGenBtn', 'click', async () => {
            const promptInput = document.getElementById('genPrompt');
            const genSpinner = document.getElementById('genSpinner');
            const startBtn = document.getElementById('startGenBtn');

            const prompt = promptInput ? promptInput.value.trim() : '';
            if (!prompt) return;

            if (genSpinner) genSpinner.style.display = 'block';
            if (startBtn) startBtn.disabled = true;

            try {
                const selected = this.canvas.selectedNode;
                const parentId = selected ? selected.id : null;
                await this.handleGeneration(prompt, parentId);
                document.getElementById('generationModal').classList.add('hidden');
                if (promptInput) promptInput.value = '';
                this.addLogEntry({ speaker: 'System', message: 'Workflow generated successfully.' });
            } catch (e) {
                alert('Generation failed: ' + e.message);
            } finally {
                if (genSpinner) genSpinner.style.display = 'none';
                if (startBtn) startBtn.disabled = false;
            }
        });

        bind('exportWorkflowBtn', 'click', () => this.handleExportWorkflow());
        bind('deployWorkflowBtn', 'click', () => this.handleDeployWorkflow());

        bind('closeExportModal', 'click', () => document.getElementById('exportModal').classList.add('hidden'));
        bind('cancelExportModal', 'click', () => document.getElementById('exportModal').classList.add('hidden'));
        // Note: ID in HTML might be cancelExportBtn
        bind('cancelExportBtn', 'click', () => document.getElementById('exportModal').classList.add('hidden'));


        document.querySelectorAll('[data-export-tab]').forEach(btn => {
            btn.addEventListener('click', () => this.switchExportTab(btn.dataset.exportTab));
        });

        bind('copyExportCodeBtn', 'click', () => {
            const codeArea = document.getElementById('exportCodeArea');
            if (codeArea) {
                navigator.clipboard.writeText(codeArea.textContent);
                const copyBtn = document.getElementById('copyExportCodeBtn');
                if (copyBtn) {
                    const originalText = copyBtn.innerHTML;
                    copyBtn.innerHTML = '✅ Copied!';
                    setTimeout(() => copyBtn.innerHTML = originalText, 2000);
                }
            }
        });

        bind('tidyBtn', 'click', () => this.canvas.autoLayout());
        bind('fitViewBtn', 'click', () => this.canvas.fitView());

        // Edge Modal Events
        bind('saveEdgeBtn', 'click', () => {
            if (this.currentEdge) {
                const labelEl = document.getElementById('edgeLabel');
                const typeEl = document.getElementById('edgeType');
                const condEl = document.getElementById('edgeCondition');
                const regexEl = document.getElementById('edgeRegex');

                const label = labelEl ? labelEl.value : '';
                const type = typeEl ? typeEl.value : 'default';
                const condition = condEl ? condEl.value : '';
                const regex = regexEl ? regexEl.value : '';

                this.canvas.updateEdge(this.currentEdge.id, {
                    label,
                    feedback: type === 'feedback',
                    condition,
                    value: condition === 'custom' ? regex : this.currentEdge.value
                });
                document.getElementById('edgeModal').classList.add('hidden');
                this.debouncedSave();
            }
        });

        bind('deleteEdgeBtn', 'click', () => {
            if (this.currentEdge && confirm('Are you sure?')) {
                this.canvas.removeEdge(this.currentEdge.id);
                document.getElementById('edgeModal').classList.add('hidden');
                this.debouncedSave();
            }
        });

        bind('closeEdgeModal', 'click', () => document.getElementById('edgeModal').classList.add('hidden'));
        bind('cancelEdgeBtn', 'click', () => document.getElementById('edgeModal').classList.add('hidden'));

        // Condition toggle
        const condEl = document.getElementById('edgeCondition');
        if (condEl) {
            condEl.addEventListener('change', (e) => {
                const grp = document.getElementById('customConditionGroup');
                if (grp) grp.style.display = e.target.value === 'custom' ? 'block' : 'none';
            });
        }

        // Guidance Modal
        bind('closeGuidanceModal', 'click', () => document.getElementById('guidanceModal').classList.add('hidden'));
        bind('cancelGuidance', 'click', () => document.getElementById('guidanceModal').classList.add('hidden'));
        bind('copyPathBtn', 'click', () => this.copyPathToClipboard());
        bind('startNativePickerBtn', 'click', () => this.startNativeAction());

        // Mission Modal
        bind('closeMissionModal', 'click', () => this.closeMissionModal());
        bind('cancelMission', 'click', () => this.closeMissionModal());
        bind('startMission', 'click', () => this.startMission());

        // Result Banner
        bind('closeResult', 'click', () => this.hideResultBanner());

        // Palette drag/drop & search
        this.setupPaletteDragDrop();
        this.setupPaletteSearch();

        // Responsive
        this.setupMobileToggle();

        // Execution controls
        this.setupExecutionControls();

        // Tabs
        this.setupTabs();

        // Tooltips Toggle
        bind('toggleTooltipsBtn', 'click', () => this.toggleTooltips());

        // Expert Mode Toggle
        bind('expertModeBtn', 'click', () => this.toggleExpertMode());
    }

    setupPaletteSearch() {
        const searchInput = document.getElementById('paletteSearch');
        if (!searchInput) return;

        searchInput.addEventListener('input', (e) => {
            const term = e.target.value.toLowerCase().trim();
            const groups = document.querySelectorAll('.palette-group');

            groups.forEach(group => {
                const items = group.querySelectorAll('.palette-item');
                let hasVisible = false;

                items.forEach(item => {
                    const label = item.querySelector('.palette-label')?.textContent.toLowerCase() || '';
                    const persona = item.dataset.persona?.toLowerCase() || '';
                    const type = item.dataset.type?.toLowerCase() || '';

                    if (!term || label.includes(term) || persona.includes(term) || type.includes(term)) {
                        item.style.display = 'flex';
                        hasVisible = true;
                    } else {
                        item.style.display = 'none';
                    }
                });

                // Hide empty groups
                group.style.display = hasVisible ? 'block' : 'none';
            });
        });
    }

    setupMobileToggle() {
        const toggleBtn = document.getElementById('toggleSidebarsBtn');
        const overlay = document.getElementById('sidebarOverlay');
        const leftSidebar = document.querySelector('.sidebar-left');
        const rightSidebar = document.querySelector('.sidebar-right');

        if (!toggleBtn) return;

        const toggle = () => {
            const isOpen = leftSidebar.classList.contains('open');
            if (isOpen) {
                leftSidebar.classList.remove('open');
                rightSidebar.classList.remove('open');
                overlay.classList.remove('active');
            } else {
                leftSidebar.classList.add('open');
                rightSidebar.classList.add('open');
                overlay.classList.add('active');
            }
        };

        toggleBtn.addEventListener('click', toggle);
        overlay.addEventListener('click', toggle);

        // Close on escape
        window.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && leftSidebar.classList.contains('open')) {
                toggle();
            }
        });
    }

    toggleTooltips() {
        this.tooltipsEnabled = !this.tooltipsEnabled;
        const btn = document.getElementById('toggleTooltipsBtn');
        if (btn) {
            btn.textContent = this.tooltipsEnabled ? '💬 On' : '💬 Off';
            btn.classList.toggle('active', this.tooltipsEnabled);
        }
        this.showToast(`Tooltips ${this.tooltipsEnabled ? 'Enabled' : 'Disabled'}`);
    }

    toggleExpertMode() {
        this.expertMode = !this.expertMode;
        const btn = document.getElementById('expertModeBtn');
        const hud = document.getElementById('usageHud');

        // Toggle visual mode on body
        document.body.classList.toggle('expert-mode', this.expertMode);

        if (btn) {
            btn.textContent = this.expertMode ? '🚀 Expert: On' : '🚀 Expert';
            btn.classList.toggle('active', this.expertMode);
        }

        if (hud) {
            hud.classList.toggle('hidden', !this.expertMode);
        }

        if (this.expertMode) {
            this.startHudUpdates();
            this.showToast('Expert Mode Enabled - HUD Active');
        } else {
            this.stopHudUpdates();
            this.showToast('Expert Mode Disabled');
        }
    }

    startHudUpdates() {
        if (this.hudInterval) clearInterval(this.hudInterval);
        this.updateUsageHud(); // Initial update
        this.hudInterval = setInterval(() => this.updateUsageHud(), 2000);
    }

    stopHudUpdates() {
        if (this.hudInterval) {
            clearInterval(this.hudInterval);
            this.hudInterval = null;
        }
    }

    updateUsageHud() {
        const memEl = document.getElementById('hudMemory');
        const cpuEl = document.getElementById('hudCpu');
        const agentsEl = document.getElementById('hudAgents');

        if (memEl) {
            const mem = (Math.random() * 50 + 150).toFixed(1);
            memEl.textContent = `${mem} MB`;
        }
        if (cpuEl) {
            const cpu = (Math.random() * 15 + 5).toFixed(1);
            cpuEl.textContent = `${cpu}%`;
        }
        if (agentsEl) {
            agentsEl.textContent = this.canvas ? (this.canvas.nodes || []).length || (this.canvas.allNodes ? this.canvas.allNodes.size : 0) : 0;
        }
    }

    setupTabs() {
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const targetTab = e.target.dataset.tab;
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                document.querySelectorAll('.tab-content').forEach(content => {
                    content.classList.toggle('ui-hidden', content.id !== `${targetTab}Tab`);
                });
                if (targetTab === 'blackboard') {
                    this.refreshBlackboard();
                }
            });
        });
    }

    updateHUD(stats) {
        if (this.expertMode) {
            this.updateUsageHud();
        }
    }

    addTraceEntry(nodeName, action, data) {
        const container = document.getElementById('traceTreeContent');
        if (container.querySelector('.empty-state')) container.innerHTML = '';

        const entry = document.createElement('div');
        entry.className = 'trace-entry';
        entry.innerHTML = `
            <div class="trace-header">
                <span class="trace-node">${nodeName}</span>
                <span class="trace-action">${action}</span>
            </div>
            ${data ? `<pre class="trace-data">${JSON.stringify(data, null, 2)}</pre>` : ''}
        `;
        container.appendChild(entry);
        container.scrollTop = container.scrollHeight;
    }

    async refreshBlackboard() {
        try {
            const response = await fetch('/api/blackboard/state');
            const data = await response.json();
            const body = document.getElementById('blackboardBody');
            body.innerHTML = '';

            for (const [key, value] of Object.entries(data)) {
                const row = document.createElement('tr');
                row.innerHTML = `<td>${key}</td><td>${typeof value === 'object' ? JSON.stringify(value) : value}</td>`;
                body.appendChild(row);
            }
        } catch (e) {
            console.error('Failed to sync blackboard:', e);
        }
    }

    setupExecutionControls() {
        document.getElementById('pauseWorkflowBtn').addEventListener('click', () => {
            this.pauseWorkflow();
        });

        document.getElementById('stopWorkflowBtn').addEventListener('click', () => {
            this.stopWorkflow();
        });

        document.getElementById('interveneBtn').addEventListener('click', () => {
            this.interveneWorkflow();
        });

        document.getElementById('replayBtn')?.addEventListener('click', () => {
            this.triggerReplay();
        });

        // Thought Stream controls
        document.getElementById('minimizeThoughtsBtn')?.addEventListener('click', () => {
            this.hideThoughtPanel();
        });

        // Load last session if exists
        this.loadFromLocalStorage();

        // Auto-save on changes (debounced)
        this.debouncedSave = this.debounce(() => this.saveToLocalStorage(), 1000);
        this.canvas.on('node:move', () => this.debouncedSave());
        this.canvas.on('link:connect', () => this.debouncedSave());
        this.canvas.on('node:add', () => {
            this.debouncedSave();
            this.updateHUD({ nodes: this.canvas.nodes.size });
        });
        this.canvas.on('node:delete', () => {
            this.debouncedSave();
            this.updateHUD({ nodes: this.canvas.nodes.size });
        });
    }

    debounce(func, wait) {
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

    saveToLocalStorage() {
        const data = this.canvas.toJSON();
        localStorage.setItem('orchestrator_autosave', JSON.stringify(data));
        console.log('Autosaved to localStorage');
        // We don't necessarily want a banner for every auto-save to avoid spam
    }

    loadFromLocalStorage() {
        const saved = localStorage.getItem('orchestrator_autosave');
        if (saved) {
            try {
                const data = JSON.parse(saved);

                // CRITICAL: Sanitize status to prevent frozen states
                if (data.nodes) {
                    Object.values(data.nodes).forEach(node => {
                        node.status = 'idle';
                    });
                }

                this.canvas.fromJSON(data);
                console.log('Restored from localStorage (Sanitized)');
            } catch (e) {
                console.error('Failed to restore autosave', e);
            }
        }
    }

    showExecutionPanel() {
        document.getElementById('executionPanel').style.display = 'block';
        document.getElementById('liveOutput').textContent = '';
        document.getElementById('activeNodeName').textContent = '—';
        document.getElementById('activeNodeName').classList.remove('processing');
        document.getElementById('executionProgress').style.width = '0%';
    }

    hideExecutionPanel() {
        document.getElementById('executionPanel').style.display = 'none';
    }

    updateExecutionProgress(current, total) {
        const progressBar = document.getElementById('executionProgressBar');
        if (progressBar) {
            const percentage = Math.round((current / total) * 100);
            progressBar.style.width = `${percentage}%`;
        }
    }

    setActiveNode(nodeName, nodeId) {
        const nameEl = document.getElementById('activeNodeName');
        const labelEl = document.getElementById('outputNodeLabel');
        nameEl.textContent = nodeName || '—';
        nameEl.classList.add('processing');
        labelEl.textContent = nodeName || '—';

        // Update node illumination
        this.clearNodeIllumination();
        if (nodeId) {
            const nodeEl = document.getElementById(`node-${nodeId}`);
            if (nodeEl) {
                nodeEl.classList.add('node-processing');
            }
        }
    }

    appendLiveOutput(text) {
        const output = document.getElementById('liveOutput');
        output.textContent += text;
        output.scrollTop = output.scrollHeight;
    }

    appendLiveThought({ node_name, thought }) {
        const container = document.getElementById('thoughtStreamContent');
        const emptyState = container.querySelector('.empty-state');
        if (emptyState) emptyState.style.display = 'none';

        // Ensure marked is available
        if (typeof marked === 'undefined') {
            console.warn('Marked.js not loaded, falling back to text');
            // Fallback mock
            window.marked = { parse: (t) => t };
        }

        // Find the last thought message to see if it's from the same node
        const messageNodes = container.querySelectorAll('.thought-message');
        const lastMsg = messageNodes[messageNodes.length - 1];

        if (lastMsg && lastMsg.dataset.nodeName === node_name) {
            const bubble = lastMsg.querySelector('.thought-bubble');

            // Accumulate raw text
            let currentText = lastMsg.dataset.rawText || '';
            currentText += thought;
            lastMsg.dataset.rawText = currentText;

            // Render Markdown
            bubble.innerHTML = marked.parse(currentText);

            // Scroll only if near bottom or forced? Standard behavior is stick to bottom.
            container.scrollTop = container.scrollHeight;
            return;
        }

        const div = document.createElement('div');
        div.className = 'thought-message';
        div.dataset.nodeName = node_name;
        div.dataset.rawText = thought; // Initialize raw text

        div.innerHTML = `
            <div class="thought-header">
                <span class="thought-node-name">${this.escapeHtml(node_name)}</span>
                <span class="thought-typing">thinking...</span>
            </div>
            <div class="thought-bubble">${marked.parse(thought)}</div>
        `;
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    }

    appendUIComponent({ node_id, node_name, schema }) {
        const container = document.getElementById('thoughtStreamContent');
        const emptyState = container.querySelector('.empty-state');
        if (emptyState) emptyState.style.display = 'none';

        const div = document.createElement('div');
        div.className = 'thought-message a2ui-container';
        div.dataset.nodeName = node_name;

        let componentHtml = '';
        const { type, title, content, payload, fields, actions } = schema;

        if (type === 'form') {
            componentHtml = `
                <form class="a2ui-form" onsubmit="event.preventDefault(); window.app.handleFormSubmit('${node_id}', this)">
                    ${(fields || []).map(f => `
                        <div class="form-group" style="margin-bottom: 10px;">
                            <label style="display: block; font-size: 0.8rem; margin-bottom: 4px;">${this.escapeHtml(f.label || f.name)}</label>
                            <input type="${f.type || 'text'}" name="${f.name}" class="form-control" style="width: 100%; box-sizing: border-box;" placeholder="${this.escapeHtml(f.placeholder || '')}" ${f.required ? 'required' : ''}>
                        </div>
                    `).join('')}
                    <button type="submit" class="btn btn-primary" style="width: 100%; margin-top: 10px; background: var(--accent-primary); border: none; padding: 10px; border-radius: 4px; color: white; cursor: pointer;">Submit Action</button>
                </form>
            `;
        } else if (type === 'buttons') {
            componentHtml = `
                <div class="a2ui-buttons" style="display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px;">
                    ${(actions || []).map(a => `
                        <button class="btn btn-secondary" style="padding: 6px 12px; font-size: 0.8rem; border-radius: 4px;" onclick="window.app.handleButtonClick('${node_id}', '${a.value || a.label}')">${this.escapeHtml(a.label)}</button>
                    `).join('')}
                </div>
            `;
        } else if (type === 'chart') {
            componentHtml = `
                <div class="a2ui-chart" style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 4px; border: 1px solid var(--border-color);">
                    <p style="font-size: 0.8rem; color: var(--accent-primary); text-align: center; margin-bottom: 5px; font-weight: bold;">[Chart: ${this.escapeHtml(schema.chart_type || 'bar')}]</p>
                    <pre style="font-size: 0.7rem; margin: 0; white-space: pre-wrap; color: var(--text-secondary);">${JSON.stringify(schema.chart_data, null, 2)}</pre>
                </div>
            `;
        } else {
            // Default Card
            componentHtml = `
                <div class="a2ui-card">
                    <p>${marked.parse(content || '')}</p>
                    ${payload && payload.image_url ? `<img src="${payload.image_url}" style="width: 100%; border-radius: 4px; margin-top: 8px; border: 1px solid var(--border-color);">` : ''}
                </div>
            `;
        }

        div.innerHTML = `
            <div class="thought-header">
                <span class="thought-node-name" style="color: var(--accent-secondary);">${this.escapeHtml(node_name)}</span>
                <span class="thought-typing">🎨 Generated UI</span>
            </div>
            <div class="thought-bubble a2ui-content" style="border-left: 3px solid var(--accent-primary); background: var(--bg-card); backdrop-filter: var(--glass-blur); -webkit-backdrop-filter: var(--glass-blur);">
                <h5 style="margin: 0 0 10px 0; color: var(--accent-primary); border-bottom: 1px solid var(--border-light); padding-bottom: 5px; font-size: 0.9rem; letter-spacing: 0.5px;">${this.escapeHtml(title || 'Action Required')}</h5>
                ${componentHtml}
            </div>
        `;
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    }

    handleFormSubmit(nodeId, form) {
        const formData = new FormData(form);
        const data = {};
        formData.forEach((value, key) => data[key] = value);

        this.addLogEntry({ speaker: 'User', message: `Submitted form for node ${nodeId}` });

        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'workflow_resume',
                data: { node_id: nodeId, action: 'form_submit', payload: data }
            }));
        }
        form.closest('.thought-message').style.opacity = '0.7';
        form.style.pointerEvents = 'none';
        const submitBtn = form.querySelector('button');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span>✅ Submitted</span>';
        }
    }

    handleButtonClick(nodeId, value) {
        this.addLogEntry({ speaker: 'User', message: `Clicked ${this.escapeHtml(value)} on node ${nodeId}` });

        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'workflow_resume',
                data: { node_id: nodeId, action: 'button_click', payload: { value } }
            }));
        }
        // Visual feedback
        const btn = event.target;
        const group = btn.closest('.a2ui-buttons');
        if (group) {
            group.style.opacity = '0.7';
            group.style.pointerEvents = 'none';
            group.querySelectorAll('button').forEach(b => b.disabled = true);
        }
        btn.style.boxShadow = '0 0 15px var(--accent-primary)';
        btn.style.borderColor = 'var(--accent-primary)';
    }

    escapeHtml(text) {
        if (!text) return '';
        if (typeof text !== 'string') text = String(text);
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showThoughtPanel() {
        document.getElementById('nodeEditorContainer').style.display = 'none';
        document.getElementById('thoughtStreamPanel').style.display = 'flex';
    }

    hideThoughtPanel() {
        document.getElementById('thoughtStreamPanel').style.display = 'none';
        document.getElementById('nodeEditorContainer').style.display = 'block';
    }

    clearNodeIllumination() {
        document.querySelectorAll('.visual-node').forEach(node => {
            node.classList.remove('node-active', 'node-processing', 'node-complete', 'node-error', 'node-paused');
        });
    }

    illuminateNode(nodeId, state) {
        const nodeEl = document.getElementById(`node-${nodeId}`);
        if (nodeEl) {
            nodeEl.classList.remove('node-active', 'node-processing', 'node-complete', 'node-error', 'node-paused');
            if (state) {
                nodeEl.classList.add(`node-${state}`);
            }
        }
    }

    async pauseWorkflow() {
        if (!this.isRunning) return;
        this.isPaused = !this.isPaused;
        const btn = document.getElementById('pauseWorkflowBtn');
        btn.textContent = this.isPaused ? '▶️' : '⏸️';
        btn.title = this.isPaused ? 'Resume' : 'Pause';

        // Send pause signal to backend
        try {
            await fetch('/api/workflow/pause', { method: 'POST' });
        } catch (e) {
            console.error('Pause failed:', e);
        }

        this.addLogEntry({
            speaker: 'System',
            message: this.isPaused ? 'Workflow paused' : 'Workflow resumed',
            timestamp: new Date().toISOString()
        });
    }

    async stopWorkflow() {
        if (!this.isRunning) return;

        if (confirm('Stop the current workflow execution?')) {
            try {
                await fetch('/api/workflow/stop', { method: 'POST' });
            } catch (e) {
                console.error('Stop failed:', e);
            }

            this.isRunning = false;
            this.isPaused = false;
            this.clearNodeIllumination();
            this.hideExecutionPanel();
            this.hideThoughtPanel();

            this.addLogEntry({
                speaker: 'System',
                message: 'Workflow stopped by user',
                timestamp: new Date().toISOString()
            });
        }
    }

    interveneWorkflow() {
        const decision = prompt('Enter intervention decision (e.g., "ROUTE:node_sarah" or "APPROVE" or "REJECT"):');
        if (decision) {
            try {
                fetch('/api/workflow/intervene', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ decision })
                });
            } catch (e) {
                console.error('Intervention failed:', e);
            }

            this.addLogEntry({
                speaker: 'User',
                message: `Intervention: ${decision}`,
                timestamp: new Date().toISOString()
            });
        }
    }

    setupPaletteDragDrop() {
        const paletteItems = document.querySelectorAll('.palette-item');
        const canvasContainer = document.getElementById('canvasContainer');

        paletteItems.forEach(item => {
            item.addEventListener('dragstart', (e) => {
                e.dataTransfer.setData('nodeType', item.dataset.type);
                if (item.dataset.name) e.dataTransfer.setData('nodeName', item.dataset.name);
                if (item.dataset.persona) e.dataTransfer.setData('nodePersona', item.dataset.persona);
                if (item.dataset.icon) e.dataTransfer.setData('nodeIcon', item.dataset.icon); // Future use
            });
        });

        canvasContainer.addEventListener('dragover', (e) => {
            e.preventDefault();
        });

        canvasContainer.addEventListener('drop', (e) => {
            e.preventDefault();
            const nodeType = e.dataTransfer.getData('nodeType');
            const nodeName = e.dataTransfer.getData('nodeName');
            const nodePersona = e.dataTransfer.getData('nodePersona');

            if (nodeType) {
                const rect = canvasContainer.getBoundingClientRect();
                // Convert screen coordinates to canvas space coordinates
                const x = (e.clientX - rect.left - this.canvas.offset.x) / this.canvas.scale - 100;
                const y = (e.clientY - rect.top - this.canvas.offset.y) / this.canvas.scale - 40;

                this.addNodeFromPalette(nodeType, x, y, { name: nodeName, persona: nodePersona });
            }
        });
    }

    addNodeFromPalette(type, x, y, overrides = {}) {
        const defaults = {
            agent: { name: 'New Agent', persona: 'You are a helpful AI assistant.' },
            auditor: { name: 'Auditor', persona: 'You are an impartial auditor. Review the input and provide a verdict.' },
            router: { name: 'Router', persona: 'Analyze the input and route to the best handler.', provider: 'opencode' },
            character: { name: 'New Character', persona: 'Define the character\'s role and goals...', backstory: 'Character history here.' },
            director: { name: 'Director', persona: 'You are the Director. Oversee the narrative flow and approve content.', requires_approval: true },
            optimizer: { name: 'Workflow Optimizer', persona: 'Analyze the current execution state, identify errors, and suggest/perform model reconfigurations.', tier: 'paid' },
            script: { name: 'Python Processor', script_code: '# Python logic\n# Access current blackboard with blackboard["key"]\n# Tools: cli.execute("ls"), git.status(), hf.search_models("gpt2")\noutput = "Done"\n' },
            memory: { name: 'Long-Term Memory', provider: 'google_ai', model: 'embedding-004', provider_config: { action: 'retrieve' } },
            github: { name: 'Git Manager', provider: 'system', provider_config: { action: 'status' } },
            huggingface: { name: 'HF Hub', provider: 'system', provider_config: { action: 'search' } },
            input: { name: 'User Input', persona: '' },
            output: { name: 'File Output', persona: '' },
            reroute: { name: 'Reroute', persona: '' }
        };

        if (type === 'group') {
            this.canvas.addGroup({
                name: 'New Group',
                x,
                y,
                width: 400,
                height: 300
            });
            return;
        }

        const nodeData = {
            type,
            x,
            y,
            ...(defaults[type] || {}), // Base defaults
            ...overrides,              // Specific palette overrides (e.g., Medical Critic)
            provider: 'ollama',
            model: 'deepseek-r1'
        };

        // Clean up undefined overrides
        if (!nodeData.name) nodeData.name = defaults[type]?.name || 'Node';
        if (!nodeData.persona) nodeData.persona = defaults[type]?.persona || '';

        this.canvas.addNode(nodeData);
    }

    addDefaultNodes() {
        // Add a sample workflow
        const architectId = this.canvas.addNode({
            name: 'The Architect',
            type: 'agent',
            x: 100,
            y: 150,
            persona: 'You are The Architect. Propose creative, well-structured solutions with citations.',
            provider: 'mock',
            model: 'default'
        });

        const criticId = this.canvas.addNode({
            name: 'The Critic',
            type: 'agent',
            x: 400,
            y: 100,
            persona: 'You are The Critic. Cross-examine proposals for flaws, security risks, and logical fallacies.',
            provider: 'mock',
            model: 'default'
        });

        const auditorId = this.canvas.addNode({
            name: 'The Auditor',
            type: 'auditor',
            x: 700,
            y: 150,
            persona: 'You are The Auditor. Review the debate and provide a final verdict: APPROVED or REJECTED.',
            provider: 'mock',
            model: 'default'
        });

        // Connect nodes
        this.canvas.addEdge(architectId, criticId);
        this.canvas.addEdge(criticId, auditorId);
    }
    // ============ Intervention Logic ============

    showInterventionBanner(nodeId, data) {
        const panel = document.getElementById('resultsPanel');
        const banner = document.createElement('div');
        banner.className = 'intervention-banner';
        banner.id = `intervention-${nodeId}`;
        const cmdTxt = data.data ? (data.data.pending_command || 'Action') : 'Action';
        banner.innerHTML = `
            <span>✋ Approval Required: <code>${cmdTxt}</code></span>
            <div class="intervention-controls">
                <button class="btn-approve" onclick="window.app.approveAction('${nodeId}')">APPROVE</button>
                <button class="btn-reject" onclick="window.app.rejectAction('${nodeId}')">REJECT</button>
            </div>
        `;
        panel.prepend(banner);
        this.selectTab('results');
    }

    approveAction(nodeId) {
        this.addLogEntry({ speaker: 'System', message: `✅ Command approved for node ${nodeId}` });
        const banner = document.getElementById(`intervention-${nodeId}`);
        if (banner) banner.remove();

        // Resume workflow via WebSocket
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'workflow_resume',
                data: { node_id: nodeId, action: 'approve' }
            }));
        }
    }

    rejectAction(nodeId) {
        this.addLogEntry({ speaker: 'System', message: `❌ Command rejected for node ${nodeId}` });
        const banner = document.getElementById(`intervention-${nodeId}`);
        if (banner) banner.remove();

        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'workflow_resume',
                data: { node_id: nodeId, action: 'reject' }
            }));
        }
    }

    selectTab(tabName) {
        const btn = document.querySelector(`.tab-btn[data-tab="${tabName}"]`);
        if (btn) btn.click();
    }

    // ============ WebSocket ============

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            this.setConnectionStatus(true);
            // Debug: Prove UI works
            this.appendLiveThought({
                node_name: 'System',
                thought: 'Connected to Thought Stream. Ready.',
                timestamp: new Date().toISOString()
            });
        };

        this.ws.onclose = () => {
            this.setConnectionStatus(false);
            setTimeout(() => this.connectWebSocket(), 3000);
        };

        this.ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                this.handleMessage(message);
            } catch (e) {
                console.error('Failed to parse message:', e);
            }
        };
    }

    setConnectionStatus(connected) {
        this.isConnected = connected;
        const dot = document.getElementById('connectionDot');
        const text = document.getElementById('connectionText');

        dot.classList.toggle('connected', connected);
        text.textContent = connected ? 'Connected' : 'Reconnecting...';
    }

    handleMessage(message) {
        console.log('WS Message Received:', message.type, message.data);
        switch (message.type) {
            case 'log':
                this.addLogEntry(message.data);
                break;
            case 'blackboard_update':
                this.updateBlackboardUI(message.data);
                this.addTraceEntry('System', 'STATE_UPDATE', message.data);
                break;
            case 'node_status':
                this.updateNodeStatus(message.data.node_id, message.data.status);
                // Illuminate node based on status
                if (message.data.status === 'running') {
                    this.setActiveNode(message.data.node_name || message.data.node_id, message.data.node_id);
                    document.getElementById('interveneBtn').disabled = false;
                    this.addTraceEntry(message.data.node_name || message.data.node_id, 'STARTED');
                } else if (message.data.status === 'complete') {
                    this.illuminateNode(message.data.node_id, 'complete');
                    document.getElementById('activeNodeName').classList.remove('processing');

                    // Add to results tab
                    if (message.data.output) {
                        this.appendResult({
                            node_name: message.data.node_name || message.data.node_id,
                            output: message.data.output
                        });
                        this.addTraceEntry(message.data.node_name || message.data.node_id, 'COMPLETED', { output_len: message.data.output.length });
                    } else {
                        this.addTraceEntry(message.data.node_name || message.data.node_id, 'COMPLETED');
                    }
                    this.updateTimeline();
                } else if (message.data.status === 'failed') {
                    this.illuminateNode(message.data.node_id, 'error');
                } else if (message.data.status === 'waiting_for_approval') {
                    this.illuminateNode(message.data.node_id, 'paused');
                    document.getElementById('interveneBtn').disabled = false;
                    this.showInterventionBanner(message.data.node_id, message.data);
                }
                break;
            case 'node_output':
                // Live streaming output
                if (message.data.text) {
                    this.appendLiveOutput(message.data.text);
                }
                break;
            case 'workflow_progress':
                this.updateExecutionProgress(message.data.current, message.data.total);
                break;
            case 'workflow_complete':
                this.handleWorkflowComplete(message.data);
                break;
            case 'node_thought':
                this.appendLiveThought(message.data);
                this.addTraceEntry(message.data.node_name, 'THOUGHT', { preview: message.data.thought.substring(0, 50) + '...' });
                break;
            case 'providers':
                if (this.providerManager) {
                    this.providerManager.init();
                }
                break;
            case 'a2ui_event':
                this.appendUIComponent(message.data);
                this.addTraceEntry(message.data.node_name, 'UI_UPDATE', { type: message.data.schema.type });
                break;
        }
    }

    updateBlackboardUI(blackboard) {
        const body = document.getElementById('blackboardBody');
        if (!body) return;

        body.innerHTML = '';
        if (Object.keys(blackboard).length === 0) {
            body.innerHTML = `
                <tr>
                    <td colspan="2" style="text-align: center; color: var(--text-muted); padding: 2rem;">
                        <div style="font-size: 2rem; margin-bottom: 1rem;">🧠</div>
                        <p><b>Global Blackboard is Empty</b></p>
                        <p style="font-size: 0.85rem;">This shared memory space stores variables, narrative context, and cross-node data.</p>
                        <p style="font-size: 0.85rem;">Data appears here when nodes execute scripts or share outputs.</p>
                    </td>
                </tr>
            `;
            return;
        }

        for (const [key, value] of Object.entries(blackboard)) {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td style="color: var(--accent-primary); font-weight: 600; font-size: 0.75rem; width: 30%;">${key}</td>
                <td><div class="blackboard-value-cell" style="font-size: 0.75rem; color: var(--text-secondary);">${typeof value === 'object' ? JSON.stringify(value) : value}</div></td>
            `;
            body.appendChild(row);
        }

        // Notify user if blackboard tab isn't active
        const tab = document.querySelector('.tab-btn[data-tab="blackboard"]');
        if (tab && !tab.classList.contains('active')) {
            tab.style.color = 'var(--accent-warning)';
        }
    }

    // ============ Logging ============

    addLogEntry(data) {
        const container = document.getElementById('logContainer');
        const emptyState = document.getElementById('emptyState');

        if (emptyState) emptyState.style.display = 'none';

        const entry = document.createElement('div');
        entry.className = 'log-entry';

        const time = new Date(data.timestamp || Date.now()).toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });

        let message = this.escapeHtml(data.message);

        // Detect folder paths and add "Open" button
        if (message.includes('Session folder:') || message.includes('Saved to')) {
            const pathMatch = data.message.match(/([a-zA-Z]:\\[^ \n]+|exports\\[^ \n]+)/);
            if (pathMatch) {
                const fullPath = pathMatch[0];
                message = message.replace(fullPath, `<span class="path-link">${fullPath}</span> <button class="btn btn-xs btn-secondary" onclick="app.openFolder('${fullPath.replace(/\\/g, '\\\\')}')" style="margin-left:5px; padding: 2px 6px; font-size: 0.7rem;">📂 Open</button>`);
            }
        }

        entry.innerHTML = `
      <span class="log-time">${time}</span>
      <span class="log-speaker ${this.getSpeakerClass(data.speaker)}">${data.speaker}</span>
      <span class="log-message">${message}</span>
    `;

        container.appendChild(entry);
        container.scrollTop = container.scrollHeight;
    }

    async openFolder(path) {
        try {
            await fetch('/api/system/open-folder', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path })
            });
        } catch (e) {
            console.error('Failed to open folder:', e);
        }
    }

    getSpeakerClass(speaker) {
        const s = speaker.toLowerCase();
        if (s.includes('system')) return 'system';
        if (s.includes('error')) return 'error';
        return '';
    }

    clearLogs() {
        const container = document.getElementById('logContainer');
        container.innerHTML = '<div class="empty-state" id="emptyState"><p>Run a workflow to see logs</p></div>';
    }

    clearResults() {
        const container = document.getElementById('resultsPanel');
        container.innerHTML = '<div class="empty-state">Results appear here.</div>';
    }

    // ============ Node Status ============

    updateNodeStatus(nodeId, status) {
        this.canvas.updateNode(nodeId, { status });
    }

    // ============ Workflow Execution ============

    openMissionModal() {
        document.getElementById('missionModal').classList.add('open');
        document.getElementById('missionInput').focus();
    }

    closeMissionModal() {
        document.getElementById('missionModal').classList.remove('open');
    }

    async startMission() {
        const prompt = document.getElementById('missionInput').value.trim();
        if (!prompt) return;

        this.closeMissionModal();
        this.isRunning = true;
        this.isPaused = false;

        // Clear previous thoughts and results
        document.getElementById('thoughtStreamContent').innerHTML = '<div class="empty-state"><p>Waiting for AI reasoning...</p></div>';
        document.getElementById('resultsPanel').innerHTML = '<div class="empty-state"><p>Final results will appear here.</p></div>';

        // Reset tab view (optional, but good UX)
        // document.querySelector('.tab-btn[data-tab="thoughts"]').click();

        this.showExecutionPanel();
        this.showThoughtPanel();

        // Get workflow data
        const workflow = this.canvas.toJSON();
        workflow.name = document.getElementById('workflowName').value || 'Workflow';

        try {
            const response = await fetch('/api/workflow/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    workflow,
                    prompt
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Workflow execution failed');
            }

            const result = await response.json();
            this.handleWorkflowComplete(result);

        } catch (error) {
            console.error('Workflow error:', error);
            this.addLogEntry({
                speaker: 'Error',
                message: error.message,
                timestamp: new Date().toISOString()
            });
        }

        this.isRunning = false;
    }

    handleWorkflowComplete(result) {
        this.isRunning = false;
        this.isPaused = false;
        // Don't hide thought panel immediately, let user see the final thoughts
        this.showResultBanner(result.success, result.message || (result.success ? 'Workflow completed successfully' : 'Workflow completed with issues'));

        // Hide execution panel and reset illumination after delay
        setTimeout(() => {
            this.hideExecutionPanel();
            this.clearNodeIllumination();
            for (const [nodeId] of this.canvas.nodes) {
                this.canvas.updateNode(nodeId, { status: 'idle' });
            }
        }, 3000);
    }

    showResultBanner(success, message) {
        const banner = document.getElementById('resultBanner');
        const icon = document.getElementById('resultIcon');
        const title = document.getElementById('resultTitle');
        const msg = document.getElementById('resultMessage');

        banner.classList.remove('success', 'failure');
        banner.classList.add('show', success ? 'success' : 'failure');

        icon.textContent = success ? '✅' : '🛑';
        title.textContent = success ? 'Success' : 'Failed';
        msg.textContent = message;

        // Auto-hide after 5 seconds
        setTimeout(() => this.hideResultBanner(), 5000);
    }

    hideResultBanner() {
        document.getElementById('resultBanner').classList.remove('show');
    }

    openEdgeModal(edge) {
        this.currentEdge = edge;
        document.getElementById('edgeLabel').value = edge.label || '';
        document.getElementById('edgeType').value = edge.feedback ? 'feedback' : 'default';
        document.getElementById('edgeCondition').value = edge.condition || '';
        document.getElementById('edgeRegex').value = edge.value || ''; // Reuse value field for regex

        document.getElementById('customConditionGroup').style.display =
            edge.condition === 'custom' ? 'block' : 'none';

        const edgeModal = document.getElementById('edgeModal');
        edgeModal.classList.remove('hidden');
        edgeModal.style.display = 'flex';
    }

    // ============ Live Streaming ============


    appendLiveOutput(text) {
        // Optional: If there's a live output panel
        // For now, we mainly log it, but if we have a specific panel:
        this.addLogEntry({
            speaker: 'System',
            message: `Output: ${text.substring(0, 100)}...`,
            timestamp: new Date().toISOString()
        });
    }

    showThoughtPanel() {
        const panel = document.getElementById('thoughtStreamPanel');
        if (panel) {
            panel.style.display = 'flex';
        }
    }

    showExecutionPanel() {
        const panel = document.getElementById('executionPanel');
        if (panel) {
            panel.style.display = 'flex';
        }
    }

    hideExecutionPanel() {
        const panel = document.getElementById('executionPanel');
        if (panel) {
            panel.style.display = 'none';
        }
    }

    refreshBlackboard() {
        const container = document.getElementById('blackboardContent');
        const data = this.canvas.toJSON();

        // Simulate blackboard as a merge of all node outputs or a global object
        const blackboard = {
            system: {
                workflow: document.getElementById('workflowName').value || 'Untitled',
                nodeCount: Object.keys(data.nodes).length,
                lastUpdate: new Date().toLocaleTimeString()
            },
            context: {}
        };

        // Populate context from nodes
        Object.values(data.nodes).forEach(node => {
            if (node.output) {
                blackboard.context[node.name] = node.output;
            }
        });

        container.innerHTML = `<pre class="json-viewer">${JSON.stringify(blackboard, null, 2)}</pre>`;
    }

    // ============ Workflow Save/Load ============

    async handleSmartConnect() {
        const selectedInfo = this.canvas.getSelectedNodes();
        if (selectedInfo.length < 2) {
            this.showToast('Select at least 2 nodes to connect', 'warning');
            return;
        }

        const source = selectedInfo[0];
        const target = selectedInfo[1];

        this.canvas.addEdge(source.id, target.id, 'Flow', {
            label: 'Auto',
            condition: ''
        });

        this.addLogEntry({
            speaker: 'System',
            message: `Smart connected ${source.name} ➔ ${target.name}`
        });

        this.showToast('Connected 2 nodes');
    }

    async loadWorkflow(options = {}) {
        if (options.silent) {
            return await this.executeNativeLoad();
        }
        // Direct load - skipping the guidance modal path check for simplicity in this version
        // or ensure we default to a safe path if empty.
        const pathEl = document.getElementById('guidancePath');
        if (pathEl && this.tooltipsEnabled && (!pathEl.value || pathEl.value.includes('Loading'))) {
            // Only show hint if prompts/tooltips are enabled
            pathEl.value = 'Select file...';
        }

        // If native picker is preferred, just call it
        // return await this.executeNativeLoad(); 

        // Use the modal flow
        this.pendingGuidanceAction = 'load';
        document.getElementById('guidanceModal').classList.remove('hidden');
        document.getElementById('guidanceModal').style.display = 'flex'; // Ensure flex
    }

    async saveWorkflow(options = {}) {
        if (options.silent) {
            return await this.executeNativeSave();
        }
        this.pendingGuidanceAction = 'save';
        // await this.ensurePathLoaded(); // Remove blocking call
        document.getElementById('guidanceModal').classList.remove('hidden');
        document.getElementById('guidanceModal').style.display = 'flex';
    }

    // NOTE: handleExportWorkflow and handleDeployWorkflow are defined in the Export Functionality section below

    handleAttachWorkflow(node) {
        // Placeholder for context menu action
        this.showToast(`Attach workflow to ${node.name} (Not implemented yet)`, 'info');
    }

    handleMergeWorkflow(node) {
        // Placeholder for context menu action
        this.showToast(`Merge workflow into ${node.name} (Not implemented yet)`, 'info');
    }

    async _backgroundSync() {
        // Silent save to localStorage (Canvas does this already, but we reinforce)
        const workflow = this.canvas.toJSON();
        localStorage.setItem('orchestrator_autosave', JSON.stringify(workflow));
        console.log('Orchestrator: Background sync complete.');
    }

    async ensurePathLoaded() {
        // Deprecated helper to avoid blocking
        return true;
    }

    // NOTE: fetchSystemInfo is defined at the top of the class

    copyPathToClipboard() {
        const pathEl = document.getElementById('guidancePath');
        const path = pathEl.value || pathEl.textContent;

        navigator.clipboard.writeText(path).then(() => {
            const btn = document.getElementById('copyPathBtn');
            const originalText = btn.textContent;
            btn.textContent = '✅ Copied!';
            setTimeout(() => { btn.textContent = originalText; }, 2000);
        });
    }

    async startNativeAction() {
        const action = this.pendingGuidanceAction;
        document.getElementById('guidanceModal').classList.add('hidden');

        if (action === 'load') {
            await this.executeNativeLoad();
        } else {
            await this.executeNativeSave();
        }
    }

    async executeNativeLoad() {
        if ('showOpenFilePicker' in window) {
            try {
                const [fileHandle] = await window.showOpenFilePicker({
                    types: [{
                        description: 'Workflow JSON Files',
                        accept: { 'application/json': ['.json'] },
                    }],
                });
                const file = await fileHandle.getFile();
                const text = await file.text();
                const data = JSON.parse(text);

                this._applyWorkflowData(data);

                this.addLogEntry({
                    speaker: 'System',
                    message: `Workflow "${data.name}" loaded: ${file.name}`,
                    timestamp: new Date().toISOString()
                });
            } catch (err) {
                if (err.name !== 'AbortError') {
                    console.error('Load error:', err);
                    alert('Error loading file: ' + err.message);
                }
            }
        } else {
            // Fallback for older browsers
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = '.json';
            input.onchange = async (e) => {
                const file = e.target.files[0];
                const text = await file.text();
                const data = JSON.parse(text);
                this._applyWorkflowData(data);
            };
            input.click();
        }
    }

    async executeNativeSave() {
        const workflow = this.canvas.toJSON();
        const workflowName = document.getElementById('workflowName').value || 'Workflow';
        workflow.name = workflowName;

        if ('showSaveFilePicker' in window) {
            try {
                const handle = await window.showSaveFilePicker({
                    suggestedName: `${workflow.name.toLowerCase().replace(/\s+/g, '_')}.json`,
                    types: [{
                        description: 'Workflow JSON',
                        accept: { 'application/json': ['.json'] },
                    }],
                });
                const writable = await handle.createWritable();
                await writable.write(JSON.stringify(workflow, null, 4));
                await writable.close();

                this.addLogEntry({
                    speaker: 'System',
                    message: `Workflow "${workflow.name}" saved to local disk.`,
                    timestamp: new Date().toISOString()
                });
                this.showNotification(`💾 Workflow "${workflow.name}" Saved`, 'success');
                return true;
            } catch (err) {
                if (err.name !== 'AbortError') {
                    console.error('Save error:', err);
                    this.showNotification('❌ Failed to save workflow', 'error');
                }
                return false;
            }
        } else {
            // Fallback: download blob
            try {
                const blob = new Blob([JSON.stringify(workflow, null, 4)], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${workflow.name.toLowerCase().replace(/\s+/g, '_')}.json`;
                a.click();
                URL.revokeObjectURL(url);
                this.showNotification('💾 Workflow Exported', 'success');
                return true;
            } catch (e) {
                console.error('Export failed:', e);
                this.showNotification('❌ Failed to export workflow', 'error');
                return false;
            }
        }
    }

    _applyWorkflowData(data) {
        this.canvas.fromJSON(data);
        document.getElementById('workflowName').value = data.name || "Loaded Workflow";
    }

    async handleAttachWorkflow(node) {
        if ('showOpenFilePicker' in window) {
            try {
                const [fileHandle] = await window.showOpenFilePicker({
                    types: [{
                        description: 'Workflow JSON Files',
                        accept: { 'application/json': ['.json'] },
                    }],
                });
                const file = await fileHandle.getFile();
                const text = await file.text();
                // Validate it's JSON
                try {
                    const data = JSON.parse(text);
                    if (!data.nodes) throw new Error("Invalid workflow structure: missing 'nodes'");

                    // Update the node
                    console.log(`Attaching workflow: ${file.name}`);
                    this.canvas.updateNode(node.id, {
                        sub_workflow_path: file.name, // Store filename as path reference
                        sub_workflow_content: text // Store full content for execution
                    });

                    this.addLogEntry({
                        speaker: 'System',
                        message: `Attached sub-workflow "${file.name}" to node "${node.name}"`,
                        timestamp: new Date().toISOString()
                    });

                    // Trigger visual update (handled by node:update)
                } catch (e) {
                    alert("Invalid Workflow JSON: " + e.message);
                }
            } catch (err) {
                if (err.name !== 'AbortError') {
                    console.error('Attach error:', err);
                }
            }
        } else {
            // Fallback
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = '.json';
            input.onchange = async (e) => {
                const file = e.target.files[0];
                const text = await file.text();
                try {
                    const data = JSON.parse(text);
                    const sub_workflows = node.sub_workflows || [];
                    sub_workflows.push({
                        path: file.name,
                        content: text
                    });

                    this.canvas.updateNode(node.id, { sub_workflows });

                    this.addLogEntry({
                        speaker: 'System',
                        message: `Attached sub-workflow "${file.name}" to node "${node.name}" (${sub_workflows.length} total)`,
                        timestamp: new Date().toISOString()
                    });
                } catch (e) {
                    alert("Invalid JSON: " + e.message);
                }
            };
            input.click();
        }
    }

    async handleSmartConnect() {
        const nodes = Array.from(this.canvas.nodes.values());
        if (nodes.length < 2) {
            alert("Add at least 2 nodes to use Smart Connect.");
            return;
        }

        this.addLogEntry({
            speaker: 'System',
            message: '🧠 Analyzing node personas for logical connections...',
            timestamp: new Date().toISOString()
        });

        const smartBtn = document.getElementById('smartConnectBtn');
        const originalText = smartBtn.innerHTML;

        try {
            smartBtn.disabled = true;
            smartBtn.innerHTML = '<span>⏳</span> Thinking...';

            const response = await fetch('/api/workflow/recommend-edges', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    nodes: nodes.map(n => ({
                        id: n.id,
                        name: n.name,
                        type: n.type,
                        persona: n.persona
                    })),
                    intent: document.getElementById('workflowName').value
                })
            });

            const result = await response.json();

            if (result.edges && result.edges.length > 0) {
                this.addLogEntry({
                    speaker: 'System',
                    message: `✅ Smart Connect suggested ${result.edges.length} new connections.`,
                    timestamp: new Date().toISOString()
                });

                result.edges.forEach(edge => {
                    this.canvas.addEdge(edge.source, edge.target, edge.label || "Suggested", {
                        feedback: edge.feedback || false
                    });
                });
            } else {
                this.addLogEntry({
                    speaker: 'System',
                    message: 'ℹ️ No new connections suggested.',
                    timestamp: new Date().toISOString()
                });
            }
        } catch (e) {
            console.error('Smart Connect failed:', e);
            alert("Smart Connect failed: " + e.message);
        } finally {
            smartBtn.disabled = false;
            smartBtn.innerHTML = originalText;
        }
    }


    // ============ Template Library ============
    async loadTemplates() {
        try {
            const res = await fetch('/api/templates');
            const data = await res.json();
            const select = document.getElementById('templateSelect');
            select.innerHTML = '<option value="">-- Select a Template --</option>';

            data.templates.forEach(t => {
                const opt = document.createElement('option');
                opt.value = JSON.stringify(t); // Store full config in value or just ID? Full config is easier for now.
                opt.textContent = t.name;
                select.appendChild(opt);
            });

            select.onchange = () => {
                document.getElementById('loadTemplateBtn').disabled = !select.value;
            };

            document.getElementById('loadTemplateBtn').onclick = () => {
                try {
                    const template = JSON.parse(select.value);
                    if (confirm(`Load template '${template.name}'? This will replace the current canvas.`)) {
                        this.canvas.fromJSON(template);
                        document.getElementById('generationModal').classList.add('hidden');
                        this.addLogEntry({ speaker: 'System', message: `Loaded template: ${template.name}` });
                    }
                } catch (e) { console.error(e); }
            };

        } catch (e) {
            console.error("Failed to load templates", e);
        }
    }

    // ============ Export Functionality ============

    async handleExportWorkflow() {
        const data = this.canvas.toJSON();

        // Show loading state
        const codeArea = document.getElementById('exportCodeArea').querySelector('code');
        codeArea.textContent = "Generating script...";
        const modal = document.getElementById('exportModal');
        modal.classList.remove('hidden');
        modal.style.display = 'flex'; // Required to make modal visible

        try {
            // Fetch standalone script from backend
            const response = await fetch('/api/workflow/export', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    workflow: data,
                    prompt: "" // Not needed for export but required by schema
                })
            });

            if (!response.ok) throw new Error("Export failed");
            const result = await response.json();

            this.exportData = {
                standalone: result.code,
                api: this.generateApiClientSnippet(data)
            };

            this.switchExportTab('standalone');

        } catch (e) {
            console.error(e);
            codeArea.textContent = "Error generating export: " + e.message;
        }
    }

    async handleDeployWorkflow() {
        const data = this.canvas.toJSON();
        const btn = document.getElementById('deployWorkflowBtn');
        const originalText = btn.innerHTML;

        try {
            btn.disabled = true;
            btn.innerHTML = '<span>🐳</span> Building...';

            this.addLogEntry({
                speaker: 'System',
                message: 'Starting Docker deployment build...',
                timestamp: new Date().toISOString()
            });

            const response = await fetch('/api/workflow/deploy', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    workflow: data,
                    prompt: "deploy"
                })
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || "Deploy failed");
            }

            const result = await response.json();

            if (result.success) {
                this.addLogEntry({
                    speaker: 'System',
                    message: `✅ Deployment Success: ${result.message}`,
                    timestamp: new Date().toISOString()
                });
                alert(`Build Complete!\n\n${result.message}\n\nFiles saved to: ${result.path}`);
                // Open folder for user convenience
                this.openFolder(result.path);
            } else {
                this.addLogEntry({
                    speaker: 'System',
                    message: `⚠️ Deployment Files Generated (Build Skipped/Failed): ${result.message}`,
                    timestamp: new Date().toISOString()
                });
                alert(`Files Generated (Build Issue): ${result.message}\n\nFiles saved to: ${result.path}`);
                this.openFolder(result.path);
            }

        } catch (e) {
            console.error(e);
            this.addLogEntry({
                speaker: 'Error',
                message: `Deploy Error: ${e.message}`,
                timestamp: new Date().toISOString()
            });
            alert("Deploy Error: " + e.message);
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    }

    switchExportTab(tab) {
        if (!this.exportData) return;

        const codeArea = document.getElementById('exportCodeArea').querySelector('code');
        codeArea.textContent = this.exportData[tab];

        document.querySelectorAll('[data-export-tab]').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.exportTab === tab);
        });
    }

    // Removed generateStandaloneScript as it is replaced by backend logic


    generateApiClientSnippet(data) {
        const jsonStr = JSON.stringify(data, null, 4);
        // Escape backslashes first to preserve them in Python string, then escape single quotes
        const escapedStr = jsonStr.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
        return `import requests
import json

def call_orchestrator_api(prompt):
    url = "http://localhost:8000/api/workflow/run"
    
    workflow_data = json.loads('''${escapedStr}''')
    
    payload = {
        "workflow": workflow_data,
        "prompt": prompt
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    print(f"Triggering workflow via API...")
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        print("Workflow Success:", result.get('success'))
        # The result includes full execution trace and outputs
        return result
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None

if __name__ == "__main__":
    prompt = "Hello, complex world!"
    call_orchestrator_api(prompt)
`;
    }


    async handleMergeWorkflow(targetNode) {
        // Validate targetNode to prevent coordinate corruption
        if (targetNode && (typeof targetNode.x !== 'number' || typeof targetNode.y !== 'number')) {
            console.warn("Invalid target node coordinates, resetting to default.");
            targetNode = { ...targetNode, x: 100, y: 100 };
        }

        let pickerFailed = false;

        if ('showOpenFilePicker' in window) {
            try {
                const [fileHandle] = await window.showOpenFilePicker({
                    types: [{
                        description: 'Workflow JSON Files',
                        accept: { 'application/json': ['.json'] },
                    }],
                });
                const file = await fileHandle.getFile();
                const text = await file.text();
                this.mergeWorkflowData(text, targetNode);
            } catch (err) {
                if (err.name === 'AbortError') {
                    // User cancelled, do nothing
                    return;
                }
                console.error('File Picker API failed, trying fallback:', err);
                pickerFailed = true;
            }
        }

        // Fallback or default path
        if (!('showOpenFilePicker' in window) || pickerFailed) {
            try {
                const input = document.createElement('input');
                input.type = 'file';
                input.accept = '.json';
                input.onchange = async (e) => {
                    if (e.target.files && e.target.files[0]) {
                        const file = e.target.files[0];
                        const text = await file.text();
                        this.mergeWorkflowData(text, targetNode);
                    }
                };
                input.click();
            } catch (e) {
                alert("Failed to open file picker: " + e.message);
            }
        }
    }

    mergeWorkflowData(jsonText, targetNode) {
        try {
            const data = JSON.parse(jsonText);
            if (!data.nodes) throw new Error("Invalid workflow structure: missing 'nodes'");

            // 1. Calculate Layout Offset (Smart Positioning)
            // Position to the RIGHT of the target node (Left-to-Right flow)
            const OFFSET_X = 300; // Increased buffer
            const baseX = targetNode ? targetNode.x + OFFSET_X : 100;
            const baseY = targetNode ? targetNode.y : 100;

            // Normalize imported nodes to their own bounding box
            const nodeValues = Object.values(data.nodes);
            const minX = Math.min(...nodeValues.map(n => n.x || 0));
            const minY = Math.min(...nodeValues.map(n => n.y || 0));

            const idMap = {};
            const newNodes = [];
            const newEdges = [];

            // 2. Map IDs and Create Nodes (Remapped & Repositioned)
            nodeValues.forEach(node => {
                const newId = this.canvas.generateId();
                idMap[node.id] = newId;

                const importedNode = {
                    ...node,
                    id: newId,
                    // Shift so the leftmost node starts at baseX, maintaining relative layout
                    x: ((node.x || 0) - minX) + baseX,
                    y: ((node.y || 0) - minY) + baseY
                };
                newNodes.push(importedNode);
            });

            // 3. Add Nodes to Canvas
            newNodes.forEach(node => {
                this.canvas.addNode(node);
            });

            // 4. Add Internal Edges (Remapped)
            if (data.edges) {
                data.edges.forEach(edge => {
                    const newSource = idMap[edge.source];
                    const newTarget = idMap[edge.target];
                    if (newSource && newTarget) {
                        this.canvas.addEdge(newSource, newTarget, edge.label, {
                            feedback: edge.feedback
                        });
                        // Track internal edges to find roots
                        newEdges.push({ source: newSource, target: newTarget });
                    }
                });
            }

            // 5. Auto-Connect Target Node -> Imported Root
            if (targetNode) {
                // Find "Root" nodes (nodes in the imported set with NO incoming internal edges)
                const internalTargetIds = new Set(newEdges.map(e => e.target));
                const potentialRoots = newNodes.filter(n => !internalTargetIds.has(n.id));

                if (potentialRoots.length > 0) {
                    // Sort by X then Y to find the "top-left" most node
                    potentialRoots.sort((a, b) => (a.x - b.x) || (a.y - b.y));
                    const rootNode = potentialRoots[0];

                    this.canvas.addEdge(targetNode.id, rootNode.id, "Imported", {
                        feedback: false
                    });

                    this.addLogEntry({
                        speaker: 'System',
                        message: `Auto-connected "${targetNode.name}" to imported root "${rootNode.name}"`,
                        timestamp: new Date().toISOString()
                    });
                }
            }

            this.addLogEntry({
                speaker: 'System',
                message: `Merged workflow "${data.name || 'Imported'}" with ${newNodes.length} nodes.`,
                timestamp: new Date().toISOString()
            });

        } catch (e) {
            console.error(e);
            alert("Failed to merge workflow: " + e.message);
        }
    }

    // ============ Utilities ============

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    updateUsageStats(metrics) {
        // Update tokens
        this.totalTokens += metrics.total_tokens || 0;

        // Simple Cost Estimation (Gemini 1.5 Flash Baseline)
        // Input: $0.075 / 1M
        // Output: $0.30 / 1M
        const inputCost = (metrics.input_tokens / 1_000_000) * 0.075;
        const outputCost = (metrics.output_tokens / 1_000_000) * 0.30;
        this.totalCost += (inputCost + outputCost);

        // Update UI
        const tokenEl = document.getElementById('hudTokens');
        const costEl = document.getElementById('hudCost');

        if (tokenEl) tokenEl.textContent = this.totalTokens.toLocaleString();
        if (costEl) costEl.textContent = '$' + this.totalCost.toFixed(5);

        // Also add a subtle log entry if cost jumps significantly
        if ((inputCost + outputCost) > 0.01) {
            this.addLogEntry({
                speaker: 'System',
                message: `Cost spike: $${(inputCost + outputCost).toFixed(4)}`,
                timestamp: new Date().toISOString()
            });
        }
    }

    // ============ Trace & Thoughts ============

    appendLiveThought(data) {
        const container = document.getElementById('thoughtStreamContent');
        if (!container) return;

        // Remove empty state
        const empty = container.querySelector('.empty-state');
        if (empty) empty.remove();

        // Detect hidden usage metadata
        if (data.thought.startsWith('<<<USAGE:')) {
            try {
                const jsonStr = data.thought.match(/<<<USAGE: (.*?)>>>/)[1];
                const metrics = JSON.parse(jsonStr);
                this.updateUsageStats(metrics);
                return; // Don't show in thought stream
            } catch (e) {
                console.warn('Failed to parse usage:', e);
            }
        }

        const div = document.createElement('div');
        div.className = 'thought-item fade-in';
        div.innerHTML = `
            <div class="thought-header">
                <span class="thought-node">${this.escapeHtml(data.node_name)}</span>
                <span class="thought-time">${new Date(data.timestamp).toLocaleTimeString()}</span>
            </div>
            <div class="thought-body">${marked.parse(data.thought)}</div>
        `;

        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    }

    addTraceEntry(nodeName, type, details = {}) {
        const container = document.getElementById('traceTreeContent');
        if (!container) return;

        const empty = container.querySelector('.empty-state');
        if (empty) empty.remove();

        const item = document.createElement('div');
        item.className = 'trace-item';

        let icon = '•';
        let colorClass = '';

        switch (type) {
            case 'STARTED': icon = '🚀'; colorClass = 'text-info'; break;
            case 'COMPLETED': icon = '✅'; colorClass = 'text-success'; break;
            case 'FAILED': icon = '❌'; colorClass = 'text-danger'; break;
            case 'THOUGHT': icon = '💭'; colorClass = 'text-muted'; break;
            case 'STATE_UPDATE': icon = '🧠'; colorClass = 'text-warning'; break;
            case 'USER_ACTION': icon = '👤'; colorClass = 'text-primary'; break;
        }

        item.innerHTML = `
            <div class="trace-header">
                <span class="trace-icon">${icon}</span>
                <span class="trace-node ${colorClass}">${this.escapeHtml(nodeName)}</span>
                <span class="trace-type">${type}</span>
            </div>
            ${details.preview ? `<div class="trace-preview">${this.escapeHtml(details.preview)}</div>` : ''}
            ${details.output_len ? `<div class="trace-meta">${details.output_len} chars output</div>` : ''}
        `;

        container.prepend(item); // Newest top
    }

    appendResult({ node_name, output }) {
        const container = document.getElementById('resultsPanel');
        const emptyState = container.querySelector('.empty-state');
        if (emptyState) emptyState.style.display = 'none';

        const div = document.createElement('div');
        const isOptimizer = node_name.toLowerCase().includes('optimizer');
        div.className = `result-item ${isOptimizer ? 'optimizer-report' : ''}`;
        // Add ID for potential updates? No, just append for now.
        div.innerHTML = `
            <div class="result-header">
                <span class="result-node-name">${this.escapeHtml(node_name)}</span>
                <span class="result-time">${new Date().toLocaleTimeString()}</span>
            </div>
            <div class="result-body markdown-body">${marked.parse(output)}</div>
        `;

        container.appendChild(div);
        container.scrollTop = container.scrollHeight;

        // Optional: Badge notification on tab if hidden?
        const resultsTab = document.querySelector('.tab-btn[data-tab="results"]');
        if (resultsTab && !resultsTab.classList.contains('active')) {
            resultsTab.style.color = 'var(--primary-color)';
        }
    }

    async handleGeneration(prompt, parentId = null) {
        console.log('Generating workflow for:', prompt);

        const response = await fetch('/api/workflow/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt, parent_node_id: parentId })
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || 'Generation failed');
        }

        const data = await response.json();
        console.log('Generated Data:', data);

        if (!data.nodes || Object.keys(data.nodes).length === 0) {
            throw new Error('LLM returned no nodes.');
        }

        // Calculate origin based on parent if available
        let originX = null;
        let originY = null;

        if (parentId) {
            const parent = this.canvas.nodes.get(parentId);
            if (parent) {
                // Determine direction based on existing connections? 
                // Simple version: Place to the right
                originX = (parent.x + 350) / this.canvas.scale; // Adjust for scale? No, canvas logic handles it? 
                // Wait, canvas mergeNodes expects raw coords, but we passed offset logic there.
                // Let's passed explicit raw coords.
                originX = parent.x + 400;
                originY = parent.y;
            }
        }

        this.canvas.mergeNodes(data, originX, originY);
    }
    // ============ TRACE TREE RENDERING ============

    addDetailedTraceEntry(trace) {
        const container = document.getElementById('traceTreeContent');
        if (!container) return;

        if (container.querySelector('.empty-state')) {
            container.innerHTML = '';
        }

        const specificId = `trace-${trace.trace_id}-${trace.node_id}`;
        let itemEl = document.getElementById(specificId);

        if (!itemEl) {
            itemEl = document.createElement('div');
            itemEl.id = specificId;
            itemEl.className = 'trace-item';

            itemEl.innerHTML = `
                <div class="trace-header">
                    <span class="trace-icon">⏳</span>
                    <span class="trace-name">${this.escapeHtml(trace.node_name || trace.node_id)}</span>
                    <span class="trace-status">${trace.status}</span>
                    <span class="trace-time">${new Date(trace.timestamp).toLocaleTimeString()}</span>
                </div>
                <div class="trace-details ui-hidden"></div>
            `;

            itemEl.querySelector('.trace-header').addEventListener('click', () => {
                const details = itemEl.querySelector('.trace-details');
                details.classList.toggle('ui-hidden');
            });

            container.appendChild(itemEl);
        }

        const statusSpan = itemEl.querySelector('.trace-status');
        const iconSpan = itemEl.querySelector('.trace-icon');
        const detailsDiv = itemEl.querySelector('.trace-details');

        statusSpan.textContent = trace.status;
        statusSpan.className = `trace-status status-${trace.status.toLowerCase()}`;

        if (trace.status === 'STARTED') {
            iconSpan.textContent = '⏳';
            if (trace.inputs) {
                detailsDiv.innerHTML += `<div class="trace-section"><strong>Inputs:</strong><pre>${this.escapeHtml(JSON.stringify(trace.inputs, null, 2))}</pre></div>`;
            }
        } else if (trace.status === 'COMPLETED') {
            iconSpan.textContent = '✅';
            if (trace.outputs) {
                const outStr = typeof trace.outputs === 'string' ? trace.outputs : JSON.stringify(trace.outputs, null, 2);
                const preview = outStr.length > 200 ? outStr.substring(0, 200) + '...' : outStr;
                detailsDiv.innerHTML += `<div class="trace-section"><strong>Outputs:</strong><pre>${this.escapeHtml(preview)}</pre></div>`;
            }
        } else if (trace.status === 'FAILED') {
            iconSpan.textContent = '❌';
            if (trace.error) {
                detailsDiv.innerHTML += `<div class="trace-section error"><strong>Error:</strong><pre>${this.escapeHtml(trace.error)}</pre></div>`;
            }
        }

        container.scrollTop = container.scrollHeight;
    }
    // ============ Time-Travel Logic ============

    async updateTimeline() {
        try {
            const response = await fetch('/api/history');
            const data = await response.json();
            if (data.history) {
                this.renderTimeline(data.history);
                const scrubber = document.getElementById('timelineScrubber');
                if (data.history.length > 0) {
                    scrubber.classList.remove('hidden');
                } else {
                    scrubber.classList.add('hidden');
                }
            }
        } catch (e) {
            console.error('Failed to update timeline:', e);
        }
    }

    renderTimeline(history) {
        const track = document.getElementById('timelineTrack');
        if (!track) return;
        track.innerHTML = '';

        history.forEach((step, index) => {
            const el = document.createElement('div');
            el.className = 'timeline-step';
            el.textContent = index;
            el.title = `Step ${index}: ${step.node_name} (${step.node_id})`;
            el.onclick = () => this.selectTimelineStep(index);
            track.appendChild(el);
        });
    }

    async selectTimelineStep(index) {
        const steps = document.querySelectorAll('.timeline-step');
        steps.forEach((s, i) => {
            if (i === index) s.classList.add('active');
            else s.classList.remove('active');
        });

        const replayBtn = document.getElementById('replayBtn');
        if (replayBtn) replayBtn.disabled = false;

        this.selectedTimelineIndex = index;

        try {
            const res = await fetch(`/api/snapshot/${index}`);
            if (res.ok) {
                const snapshot = await res.json();
                this.updateBlackboardUI(snapshot.blackboard);
                this.addLogEntry({ speaker: 'System', message: `🔍 Viewing Snapshot Step ${index}` });
            }
        } catch (e) { console.error(e); }
    }

    async triggerReplay() {
        if (this.selectedTimelineIndex === undefined) return;

        if (!confirm(`Replay workflow from step ${this.selectedTimelineIndex}? This will reset subsequent progress.`)) return;

        try {
            const res = await fetch(`/api/replay/${this.selectedTimelineIndex}`, { method: 'POST' });
            this.addLogEntry({ speaker: 'System', message: `⏪ Replaying from Step ${this.selectedTimelineIndex}...` });
        } catch (e) {
            alert('Replay error: ' + e);
        }
    }

    showNotification(message, type = 'info') {
        const container = document.getElementById('notificationContainer') || this.createNotificationContainer();
        const notification = document.createElement('div');
        notification.className = `notification notification-${type} fade-in`;

        const icon = type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️';

        notification.innerHTML = `
            <span class="notification-icon">${icon}</span>
            <span class="notification-message">${message}</span>
        `;

        container.appendChild(notification);

        setTimeout(() => {
            notification.classList.add('fade-out');
            setTimeout(() => notification.remove(), 500);
        }, 3000);
    }

    createNotificationContainer() {
        const container = document.createElement('div');
        container.id = 'notificationContainer';
        container.className = 'notification-container';
        document.body.appendChild(container);
        return container;
    }

    // ============ Sidebar Collapse Logic ============

    initResizableSidebars() {
        const leftSidebar = document.getElementById('sidebarLeft');
        const rightSidebar = document.getElementById('sidebarRight');

        // Resizers
        const resizerLeft = document.getElementById('resizerLeft');
        const resizerRight = document.getElementById('resizerRightInternal'); // Use internal resizer for right side

        // Restore widths
        const savedLeft = localStorage.getItem('leftSidebarWidth');
        const savedRight = localStorage.getItem('rightSidebarWidth');

        if (savedLeft) leftSidebar.style.width = savedLeft;
        // Right sidebar is flex container, width isn't directly resizing the sidebar itself in the same way,
        // but rather the editor column relative to logs? 
        // Wait, index.html structure: 
        // sidebar-right (flex row) -> [sidebarRightEditor (flex column)] [resizerRightInternal] [sidebarRightLogs (flex column)]

        // Actually, the previous implementation resized the whole sidebar. 
        // Now "sidebarRight" has a fixed width of 600px? No, we likely want the whole RIGHT PANEL to be resizable via resizerRight (external)?
        // Wait, looking at index.html:
        // <aside id="sidebarRight"> ... </aside>
        // <div class="resizer" id="resizerRight"></div>
        // No, resizerRight was REMOVED/Changed? 
        // Let's re-read index.html structure.

        // Re-reading index.html, line 403: <div class="resizer resizer-right" id="resizerRight"></div> exists OUTSIDE sidebar.
        // So resizerRight resizes the entire Sidebar container.
        // resizerRightInternal resizes the Editor vs Logs split.

        const resizerExternal = document.getElementById('resizerRight');

        if (savedRight) rightSidebar.style.width = savedRight;

        // --- Left Sidebar Resize ---
        this.setupResizer(resizerLeft, (width) => {
            if (width < 200) width = 200;
            if (width > 500) width = 500;
            leftSidebar.style.width = `${width}px`;
            localStorage.setItem('leftSidebarWidth', `${width}px`);
        }, 'left');

        // --- Right Sidebar External Resize (Whole Panel) ---
        // For right sidebar, x position determines width relative to window edge
        this.setupResizer(resizerExternal, (x) => {
            const width = window.innerWidth - x;
            if (width < 300) width = 300;
            if (width > 800) width = 800; // Wider max for dual pane
            rightSidebar.style.width = `${width}px`;
            localStorage.setItem('rightSidebarWidth', `${width}px`);
        }, 'right');

        // --- Internal Right Splitter (Editor vs Logs) ---
        // Adjust flex-basis or width of sidebarRightEditor
        const editorCol = document.getElementById('sidebarRightEditor');
        const logsCol = document.getElementById('sidebarRightLogs');
        const internalResizer = document.getElementById('resizerRightInternal');

        if (internalResizer && editorCol && logsCol) {
            internalResizer.addEventListener('mousedown', (e) => {
                e.preventDefault();
                internalResizer.classList.add('dragging');

                const startX = e.clientX;
                const startWidth = editorCol.getBoundingClientRect().width;

                const onMouseMove = (ev) => {
                    const deltaX = ev.clientX - startX;
                    const newWidth = startWidth + deltaX; // Moving right increases editor width

                    if (newWidth < 200) return; // Min width
                    if (newWidth > rightSidebar.offsetWidth - 200) return; // Max width (leave space for logs)

                    editorCol.style.flex = 'none';
                    editorCol.style.width = `${newWidth}px`;
                };

                const onMouseUp = () => {
                    internalResizer.classList.remove('dragging');
                    document.removeEventListener('mousemove', onMouseMove);
                    document.removeEventListener('mouseup', onMouseUp);
                };

                document.addEventListener('mousemove', onMouseMove);
                document.addEventListener('mouseup', onMouseUp);
            });
        }
    }

    setupResizer(resizer, callback, side) {
        if (!resizer) return;

        resizer.addEventListener('mousedown', (e) => {
            e.preventDefault();
            resizer.classList.add('dragging');
            document.body.style.cursor = 'col-resize';

            const onMouseMove = (ev) => {
                if (side === 'left') {
                    callback(ev.clientX);
                } else {
                    callback(ev.clientX);
                }
            };

            const onMouseUp = () => {
                resizer.classList.remove('dragging');
                document.body.style.cursor = '';
                document.removeEventListener('mousemove', onMouseMove);
                document.removeEventListener('mouseup', onMouseUp);
                if (this.canvas) this.canvas.fitView(); // Refit canvas
            };

            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        });
    }

    initSidebarToggles() {
        const leftToggle = document.getElementById('collapseLeftBtn');
        const rightToggle = document.getElementById('collapseRightBtn');
        const leftSidebar = document.getElementById('sidebarLeft');
        const rightSidebar = document.getElementById('sidebarRight');

        if (leftToggle) {
            leftToggle.addEventListener('click', () => {
                leftSidebar.classList.toggle('collapsed');
                // Adjust resizer visibility?
            });
        }

        if (rightToggle) {
            rightToggle.addEventListener('click', () => {
                rightSidebar.classList.toggle('collapsed');
            });
        }
    }


    initBottomDrawer() {
        const drawer = document.getElementById('bottomDrawer');
        const toggleBtn = document.getElementById('toggleDrawerBtn');
        const handle = document.getElementById('drawerHandle');

        if (!drawer) return;

        // Restore state from localStorage
        if (localStorage.getItem('drawerMinimized') === 'true') {
            drawer.classList.add('minimized');
        }

        const savedHeight = localStorage.getItem('bottomDrawerHeight');
        if (savedHeight) {
            drawer.style.height = `${savedHeight}px`;
        }

        const toggleDrawer = () => {
            drawer.classList.toggle('minimized');
            localStorage.setItem('drawerMinimized', drawer.classList.contains('minimized'));
        };

        toggleBtn?.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleDrawer();
        });


        handle?.addEventListener('mousedown', (e) => {
            // Only trigger if clicking the handle area, not specific buttons inside if any (except toggle)
            if (e.target.closest('button')) return;

            e.preventDefault();
            const startY = e.clientY;
            const startHeight = drawer.offsetHeight;

            const onMouseMove = (ev) => {
                const dy = startY - ev.clientY; // Dragging up increases height
                let newHeight = startHeight + dy;

                if (newHeight < 40) newHeight = 40;
                if (newHeight > window.innerHeight * 0.8) newHeight = window.innerHeight * 0.8;

                drawer.style.height = `${newHeight}px`;

                if (newHeight > 60) drawer.classList.remove('minimized');
            };

            const onMouseUp = () => {
                localStorage.setItem('bottomDrawerHeight', drawer.offsetHeight);
                document.removeEventListener('mousemove', onMouseMove);
                document.removeEventListener('mouseup', onMouseUp);
            };

            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        });
    }
}

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    window.app = new OrchestratorApp();
});
