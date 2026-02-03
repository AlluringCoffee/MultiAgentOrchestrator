class ProviderManager {
    constructor(app) {
        this.app = app;
        this.providers = [];
        this.container = document.getElementById('providerStatus');

        this.init();
    }

    async init() {
        await this.fetchProviders();
        this.renderStatus();

        // Setup management button
        document.getElementById('manageProvidersBtn').addEventListener('click', (e) => {
            e.stopPropagation();
            this.openManagementModal();
        });
    }

    async fetchProviders() {
        try {
            const response = await fetch('/api/providers');
            this.providers = await response.json();

            // Feature: Inject Gold Tier Providers if empty
            if (this.providers.length === 0) {
                console.log('ProviderManager: No providers found. Injecting Gold Tier defaults...');
                await this.injectGoldTierProviders();
            }
        } catch (error) {
            console.error('Failed to fetch providers:', error);
        }
    }

    async injectGoldTierProviders() {
        const goldTier = [
            {
                id: 'groq_free',
                name: 'Groq (Free)',
                type: 'groq',
                message: 'Fastest inference (Llama 3, Mixtral)',
                config: { api_key: 'YOUR_GROQ_KEY' },
                models: ['llama3-8b-8192', 'mixtral-8x7b-32768'],
                available: true
            },
            {
                id: 'together_free',
                name: 'Together AI',
                type: 'openai',
                message: 'Wide variety of open models',
                config: { base_url: 'https://api.together.xyz/v1', api_key: 'YOUR_KEY' },
                models: ['meta-llama/Llama-3-70b-chat-hf'],
                available: true
            },
            {
                id: 'openrouter_free',
                name: 'OpenRouter',
                type: 'openai',
                message: 'Aggregator for all models',
                config: { base_url: 'https://openrouter.ai/api/v1', api_key: 'YOUR_KEY' },
                models: ['anthropic/claude-3-opus', 'google/gemini-flash-1.5'],
                available: true
            },
            {
                id: 'local_ollama',
                name: 'Ollama (Local)',
                type: 'ollama',
                message: 'Private local inference',
                config: { base_url: 'http://localhost:11434' },
                models: ['llama3', 'mistral'],
                available: true
            },
            {
                id: 'gemini_free',
                name: 'Google Gemini',
                type: 'google_ai',
                message: 'Multimodal capabilities',
                config: { api_key: 'YOUR_KEY' },
                models: ['gemini-1.5-flash', 'gemini-1.5-pro'],
                available: true
            }
        ];

        // We will just set them in memory for now, user must configure/save them
        // Or we can try to POST them? Let's just render them and let user edit/save.
        // Actually, better to just set them as placeholders so user sees them immediately.
        this.providers = goldTier;
        this.renderStatus();
    }

    renderStatus() {
        this.container.innerHTML = '';
        if (this.providers.length === 0) {
            this.container.innerHTML = '<div style="font-size:0.8rem; opacity:0.6; padding:0.5rem;">No active providers</div>';
            return;
        }

        this.providers.forEach(p => {
            const item = document.createElement('div');
            item.className = 'provider-item';
            item.title = `${p.name} (${p.type})`;

            // Add click to edit
            item.style.cursor = 'pointer';
            item.onclick = () => {
                this.openManagementModal();
                this.editProvider(p.id);
            };

            const dot = document.createElement('span');
            dot.className = `provider-dot ${p.available ? 'available' : 'unavailable'}`;

            const label = document.createElement('span');
            label.textContent = p.name;

            item.appendChild(dot);
            item.appendChild(label);
            this.container.appendChild(item);
        });
    }

    openManagementModal() {
        // Create modal if it doesn't exist
        let modal = document.getElementById('providerManagementModal');
        if (!modal) {
            modal = this.createManagementModal();
        }

        this.renderManagementList();
        modal.classList.add('open');
    }

    createManagementModal() {
        const modal = document.createElement('div');
        modal.id = 'providerManagementModal';
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content" style="max-width: 800px;">
                <div class="modal-header">
                    <h3>⚙️ Provider Management</h3>
                    <button class="btn-close" id="closeProviderModal">×</button>
                </div>
                <div class="modal-body">
                    <div class="provider-mgmt-actions">
                        <button class="btn btn-primary" id="addProviderBtn">+ Add Provider</button>
                    </div>
                    <div class="provider-list-mgmt" id="providerListMgmt">
                        <!-- List injected here -->
                    </div>
                    
                        <div id="providerFormContainer" class="provider-form-container" style="display: none; border: 1px solid rgba(255,255,255,0.1); padding: 1rem; border-radius: 8px; margin-top: 1rem;">
                            <h4 id="formTitle">Add Provider</h4>
                            <div style="display: grid; grid-template-columns: 1fr 250px; gap: 1.5rem;">
                                <div class="form-fields">
                                    <div class="form-group">
                                        <label>ID</label>
                                        <input type="text" id="p_id" placeholder="ollama_custom">
                                    </div>
                                    <div class="form-group">
                                        <label>Name</label>
                                        <input type="text" id="p_name" placeholder="Personal Ollama">
                                    </div>
                                    <div class="form-group">
                                        <label>Type</label>
                                        <select id="p_type">
                                            <option value="ollama">Ollama</option>
                                            <option value="openai">OpenAI</option>
                                            <option value="anthropic">Anthropic</option>
                                            <option value="opencode">OpenCode / CLI</option>
                                            <option value="groq">Groq</option>
                                            <option value="google_ai">Google AI / Gemini</option>
                                            <option value="cli_bridge">CLI Bridge</option>
                                        </select>
                                    </div>
                                    <div class="form-group">
                                        <label>Config (JSON)</label>
                                        <textarea id="p_config" rows="3" placeholder='{"base_url": "..."}'></textarea>
                                    </div>
                                    <div class="form-group">
                                        <label>Models (Comma separated)</label>
                                        <input type="text" id="p_models" placeholder="llama3, mistral">
                                    </div>
                                </div>
                                <div class="provider-help-panel" style="background: rgba(0,0,0,0.2); border-radius: 8px; padding: 1rem; font-size: 0.85rem;">
                                    <h5 style="margin-top: 0; color: #60a5fa;">💡 Setup Help</h5>
                                    <div id="providerHelpContent" style="opacity: 0.8; line-height: 1.4;">
                                        Select a provider type to see instructions and templates.
                                    </div>
                                </div>
                            </div>
                            <div class="modal-footer" style="padding: 1rem 0 0 0;">
                                <button class="btn btn-secondary" id="cancelProviderForm">Cancel</button>
                                <button class="btn btn-primary" id="saveProviderBtn">Save Provider</button>
                            </div>
                        </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);

        // Bind Events
        modal.querySelector('#closeProviderModal').addEventListener('click', () => {
            modal.classList.remove('open');
        });

        modal.querySelector('#addProviderBtn').addEventListener('click', () => {
            this.showProviderForm();
        });

        modal.querySelector('#cancelProviderForm').addEventListener('click', () => {
            document.getElementById('providerFormContainer').style.display = 'none';
        });

        modal.querySelector('#saveProviderBtn').addEventListener('click', () => {
            this.saveProvider();
        });

        modal.querySelector('#p_type').addEventListener('change', (e) => {
            this.updateHelpContent(e.target.value);
        });

        return modal;
    }

    updateHelpContent(type) {
        const help = document.getElementById('providerHelpContent');
        const templates = {
            'ollama': {
                text: 'Connect to a local Ollama instance.',
                config: '{\n  "base_url": "http://localhost:11434"\n}'
            },
            'groq': {
                text: 'High-speed inference via Groq Cloud.',
                config: '{\n  "api_key": "your_key_here"\n}'
            },
            'google_ai': {
                text: 'Google Gemini Pro / Flash models.',
                config: '{\n  "api_key": "your_key_here"\n}'
            },
            'openai': {
                text: 'OpenAI GPT-4 / GPT-3.5.',
                config: '{\n  "api_key": "sk-...",\n  "organization": "org-..."\n}'
            },
            'anthropic': {
                text: 'Anthropic Claude 3 models.',
                config: '{\n  "api_key": "sk-ant-..."\n}'
            },
            'opencode': {
                text: 'Local CLI / Shell models.',
                config: '{\n  "command_template": "ollama run {model} \\"{prompt}\\""\n}'
            },
            'cli_bridge': {
                text: 'Bridge to external CLI tools.',
                config: '{\n  "executable": "python",\n  "args": ["script.py"]\n}'
            }
        };

        const t = templates[type] || { text: 'Unknown provider type.', config: '{}' };
        help.innerHTML = `
            <p><strong>${type.toUpperCase()}</strong></p>
            <p>${t.text}</p>
            <p>Template:</p>
            <pre style="background: #000; padding: 5px; border-radius: 4px; font-size: 0.75rem;">${t.config}</pre>
            <button class="btn btn-xs btn-outline" id="applyTemplateBtn">Apply Template</button>
        `;

        const applyBtn = help.querySelector('#applyTemplateBtn');
        if (applyBtn) {
            applyBtn.addEventListener('click', () => {
                document.getElementById('p_config').value = t.config;
            });
        }
    }

    renderManagementList() {
        const container = document.getElementById('providerListMgmt');
        container.innerHTML = '';

        this.providers.forEach(p => {
            const row = document.createElement('div');
            row.className = 'provider-mgmt-row';
            row.style = "display: flex; align-items: center; justify-content: space-between; padding: 0.75rem; border-bottom: 1px solid rgba(255,255,255,0.05);";

            row.innerHTML = `
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span class="provider-dot ${p.available ? 'available' : 'unavailable'}"></span>
                    <div>
                        <div style="font-weight: 600;">${p.name}</div>
                        <div style="font-size: 0.8rem; opacity: 0.6;">${p.id} (${p.type})</div>
                    </div>
                </div>
                <div class="row-actions" style="display: flex; gap: 5px;">
                    <button class="btn-icon edit-btn" title="Edit">✏️</button>
                    <button class="btn-icon delete-btn" title="Delete">🗑️</button>
                </div>
            `;

            // Bind events directly
            const editBtn = row.querySelector('.edit-btn');
            const deleteBtn = row.querySelector('.delete-btn');

            editBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.editProvider(p.id);
            });
            deleteBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.deleteProvider(p.id);
            });

            container.appendChild(row);
        });
    }

    showProviderForm(provider = null) {
        const container = document.getElementById('providerFormContainer');
        const title = document.getElementById('formTitle');
        title.textContent = provider ? 'Edit Provider' : 'Add Provider';

        document.getElementById('p_id').value = provider ? provider.id : '';
        document.getElementById('p_id').disabled = !!provider;
        document.getElementById('p_name').value = provider ? provider.name : '';
        document.getElementById('p_type').value = provider ? provider.type : 'ollama';
        document.getElementById('p_config').value = provider ? JSON.stringify(provider.config, null, 2) : '{}';
        document.getElementById('p_models').value = provider ? (provider.models || []).join(', ') : '';

        container.style.display = 'block';
    }

    async saveProvider() {
        const id = document.getElementById('p_id').value;
        const name = document.getElementById('p_name').value;
        const type = document.getElementById('p_type').value;
        let config = {};
        try {
            config = JSON.parse(document.getElementById('p_config').value);
        } catch (e) {
            alert('Invalid JSON in config');
            return;
        }
        const models = document.getElementById('p_models').value.split(',').map(m => m.trim()).filter(m => m);

        const providerData = { id, name, type, config, models };

        try {
            const isEdit = this.providers.some(p => p.id === id);
            const url = isEdit ? `/api/providers/${id}` : '/api/providers';
            const method = isEdit ? 'PUT' : 'POST';

            const response = await fetch(url, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(isEdit ? { name, type, config, models } : providerData)
            });

            if (response.ok) {
                await this.fetchProviders();
                this.renderStatus();
                this.renderManagementList();
                document.getElementById('providerFormContainer').style.display = 'none';

                // Refresh node editor if open
                if (this.app.nodeEditor.isOpen) {
                    this.app.nodeEditor.refreshProviders();
                }
            }
        } catch (error) {
            console.error('Failed to save provider:', error);
        }
    }

    editProvider(id) {
        const provider = this.providers.find(p => p.id === id);
        if (provider) {
            this.showProviderForm(provider);
        }
    }

    async deleteProvider(id) {
        if (!confirm(`Are you sure you want to delete the provider "${id}"?`)) return;

        try {
            const response = await fetch(`/api/providers/${id}`, { method: 'DELETE' });
            if (response.ok) {
                await this.fetchProviders();
                this.renderStatus();
                this.renderManagementList();
            }
        } catch (error) {
            console.error('Failed to delete provider:', error);
        }
    }
}
