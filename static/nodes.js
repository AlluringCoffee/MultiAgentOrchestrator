/**
 * Node Editor Panel - Configuration UI for individual nodes
 */

class NodeEditor {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.currentNode = null;
    this.onSave = null;

    this.providers = [];
    this.nodeTypes = [
      { id: 'agent', name: 'Agent', icon: '🤖' },
      { id: 'auditor', name: 'Auditor', icon: '⚖️' },
      { id: 'input', name: 'Input', icon: '📥' },
      { id: 'output', name: 'Output', icon: '📤' },
      { id: 'router', name: 'Router', icon: '🔀' },
      { id: 'character', name: 'Character', icon: '🎭' },
      { id: 'director', name: 'Director', icon: '🎬' },
      { id: 'script', name: 'Script', icon: '🐍' },
      { id: 'memory', name: 'Memory', icon: '🧠' },
      { id: 'http', name: 'HTTP', icon: '🌐' },
      { id: 'openapi', name: 'OpenAPI', icon: '📜' },
      { id: 'notion', name: 'Notion', icon: '📝' },
      { id: 'google', name: 'Google', icon: '📧' },
      { id: 'rag', name: 'RAG (Librarian)', icon: '📚' },
      { id: 'mcp', name: 'MCP Client', icon: '🔌' },
      { id: 'comfy', name: 'ComfyUI (GenAI)', icon: '🎨' },
      { id: 'architect', name: 'Factory: Architect', icon: '🏗️' },
      { id: 'critic', name: 'Factory: Critic', icon: '🧐' },
      { id: 'github', name: 'GitHub Integration', icon: '🐙' }
    ];

    this.init();
  }

  init() {
    this.render();
    this.bindEvents();
    this.refreshProviders();
  }

  async refreshProviders() {
    try {
      const response = await fetch('/api/providers');
      this.providers = await response.json();

      // Update UI if form is visible
      const providerSelect = document.getElementById('nodeProvider');
      if (providerSelect) {
        const currentVal = providerSelect.value;
        providerSelect.innerHTML = this.providers.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
        providerSelect.value = currentVal;
      }
    } catch (error) {
      console.error('Failed to fetch providers in NodeEditor:', error);
    }
  }

  render() {
    this.container.innerHTML = `
      <div class="node-editor-panel" id="nodeEditorPanel">
        <div class="editor-header">
          <h3>Node Configuration</h3>
          <button class="btn-close" id="closeEditor">×</button>
        </div>
        
        <div class="editor-body">
          <div class="editor-placeholder" id="editorPlaceholder">
            <p>Select a node to configure</p>
          </div>
          
          <form class="editor-form" id="editorForm" style="display: none;">
            <!-- Basic Info - Always visible -->
            <div class="form-section">
              <div class="form-group">
                <label for="nodeName">Name</label>
                <input type="text" id="nodeName" placeholder="Agent Name">
              </div>
              
              <div class="form-group">
                <label for="nodeType">Type</label>
                <select id="nodeType">
                  ${this.nodeTypes.map(t => `<option value="${t.id}">${t.icon} ${t.name}</option>`).join('')}
                </select>
              </div>
            </div>
            
            <!-- LLM Provider Accordion -->
            <div class="accordion-section" id="llmProviderAccordion">
              <div class="accordion-header" data-accordion="llmProviderAccordion">
                <div class="accordion-header-left">
                  <span class="accordion-icon">🤖</span>
                  <span class="accordion-title">LLM Provider</span>
                  <span class="accordion-status-dot"></span>
                </div>
                <span class="accordion-chevron">▼</span>
              </div>
              <div class="accordion-content">
                <div class="form-group">
                  <label for="nodeProvider">Provider</label>
                  <div style="display: flex; gap: 8px; align-items: center;">
                    <select id="nodeProvider" style="flex: 1;">
                      ${this.providers.map(p => `<option value="${p.id}">${p.name}</option>`).join('')}
                    </select>
                    <button type="button" class="btn-icon" id="infoProviderBtn" title="Setup Instructions">📘</button>
                  </div>
                </div>
                
                <div class="form-group">
                  <label for="nodeModel">Model</label>
                  <select id="nodeModel">
                    <option value="default">Default</option>
                  </select>
                </div>
              </div>
            </div>
            
            <!-- Intelligence & Scaling Accordion -->
            <div class="accordion-section collapsed" id="scalingAccordion">
              <div class="accordion-header" data-accordion="scalingAccordion">
                <div class="accordion-header-left">
                  <span class="accordion-icon">⚡</span>
                  <span class="accordion-title">Intelligence & Scaling</span>
                  <span class="accordion-status-dot"></span>
                </div>
                <span class="accordion-chevron">▼</span>
              </div>
              <div class="accordion-content">
                <div class="form-group checkbox-group" style="display: flex; gap: 0.5rem; align-items: center;">
                  <input type="checkbox" id="nodeInternet" checked>
                  <label for="nodeInternet" style="margin: 0; cursor: pointer;">🌐 Internet Access (Search/Fetch)</label>
                </div>

                <div class="form-group" style="margin-top: 0.5rem;">
                  <label for="nodeTier">Resource Tier</label>
                  <div style="display: flex; gap: 8px; align-items: center;">
                    <select id="nodeTier" style="flex: 1;">
                      <option value="free">Free Tier (Efficiency)</option>
                      <option value="paid">Premium Tier (Max Reasoning)</option>
                    </select>
                    <div class="help-trigger" title="Premium tier enables high-weight models (like Gemini 1.5 Pro) for complex reasoning.">❓</div>
                  </div>
                </div>

                <div class="form-group">
                  <label for="nodeBudget">Token Allowance</label>
                  <input type="number" id="nodeBudget" placeholder="e.g. 4096" value="4096">
                </div>

                <div class="form-group" style="margin-top: 1rem;">
                   <button type="button" class="btn btn-outline" id="testProviderBtn" style="width: 100%; display: flex; align-items: center; justify-content: center; gap: 0.5rem;">
                     <span>⚡</span> Test Configuration
                   </button>
                </div>
              </div>
            </div>
            
            <!-- Persona / System Prompt Accordion -->
            <div class="accordion-section" id="personaAccordion">
              <div class="accordion-header" data-accordion="personaAccordion">
                <div class="accordion-header-left">
                  <span class="accordion-icon">💭</span>
                  <span class="accordion-title" id="personaLabel">Persona / System Prompt</span>
                  <span class="accordion-status-dot"></span>
                </div>
                <span class="accordion-chevron">▼</span>
              </div>
              <div class="accordion-content">
                <div class="form-group">
                  <textarea id="nodePersona" rows="6" placeholder="Enter the agent's system prompt..."></textarea>
                </div>
                
                 <div class="form-group" id="backstoryGroup" style="display: none;">
                  <label for="nodeBackstory">Backstory & Traits</label>
                  <textarea id="nodeBackstory" rows="4" placeholder="Describe the character's history and personality..."></textarea>
                </div>

                 <div class="form-group checkbox-group" style="display: flex; gap: 0.5rem; align-items: center; margin-top: 1rem;">
                  <input type="checkbox" id="nodeApproval">
                  <label for="nodeApproval" style="margin: 0; cursor: pointer;">Requires Human Approval (Pause)</label>
                </div>
              </div>
            </div>

            <!-- Script Editor Accordion (hidden by default) -->
            <div class="accordion-section" id="scriptSection" style="display: none;">
              <div class="accordion-header" data-accordion="scriptSection">
                <div class="accordion-header-left">
                  <span class="accordion-icon">🐍</span>
                  <span class="accordion-title">Python Script</span>
                  <span class="accordion-status-dot"></span>
                </div>
                <span class="accordion-chevron">▼</span>
              </div>
              <div class="accordion-content">
                <p class="form-hint">Direct access to workflow state.</p>
                <div class="form-group">
                  <label style="font-size: 0.75rem; color: var(--text-muted);">Available Keys: <code>blackboard</code>, <code>input</code>, <code>history</code></label>
                  <textarea id="nodeScript" rows="12" style="font-family: 'JetBrains Mono', monospace; font-size: 0.85em; background: #1a1a1a; color: #a9b7c6; border-color: #323232;" placeholder="# Write to blackboard:\nblackboard['my_var'] = 'value'\n\n# Read from input:\noutput = f'Processed: {input}'"></textarea>
                </div>
              </div>
            </div>

            <!-- Memory Configuration Accordion -->
            <div class="accordion-section" id="memorySection" style="display: none;">
              <div class="accordion-header" data-accordion="memorySection">
                <div class="accordion-header-left">
                  <span class="accordion-icon">🧠</span>
                  <span class="accordion-title">Memory Action</span>
                  <span class="accordion-status-dot"></span>
                </div>
                <span class="accordion-chevron">▼</span>
              </div>
              <div class="accordion-content">
                <div class="form-group">
                  <label for="memoryAction">Action Mode</label>
                  <select id="memoryAction">
                    <option value="retrieve">Retrieve (Search & Recall)</option>
                    <option value="store">Store (Embed & Save)</option>
                  </select>
                </div>
                <div class="form-group">
                  <label for="memoryTags">Tags (Comma separated)</label>
                  <input type="text" id="memoryTags" class="form-control" placeholder="e.g. important, user-preference">
                </div>
                <div class="form-group">
                  <label for="memoryLimit">Limit (Retrieve only)</label>
                  <input type="number" id="memoryLimit" class="form-control" value="5" min="1" max="20">
                </div>
                <p class="form-hint" style="margin-top: 5px;" id="memoryHint">Input text will be used as content (Store) or query (Retrieve).</p>
              </div>
            </div>

            <!-- RAG Configuration Accordion -->
            <div class="accordion-section" id="ragSection" style="display: none;">
              <div class="accordion-header" data-accordion="ragSection">
                <div class="accordion-header-left">
                  <span class="accordion-icon">📚</span>
                  <span class="accordion-title">RAG (Knowledge Retrieval)</span>
                  <span class="accordion-status-dot"></span>
                </div>
                <span class="accordion-chevron">▼</span>
              </div>
              <div class="accordion-content">
                <div class="form-group">
                  <label for="ragSource">Knowledge Source (Path or ID)</label>
                  <input type="text" id="ragSource" class="form-control" placeholder="knowledge_base">
                </div>
                <div class="form-group">
                  <label for="ragChunkSize">Chunk Size</label>
                  <input type="number" id="ragChunkSize" class="form-control" value="1000">
                </div>
                <div class="form-group">
                  <label for="ragOverlap">Chunk Overlap</label>
                  <input type="number" id="ragOverlap" class="form-control" value="200">
                </div>
                <div class="form-group checkbox-group" style="display: flex; gap: 0.5rem; align-items: center;">
                  <input type="checkbox" id="ragMultiQuery" checked>
                  <label for="ragMultiQuery" style="margin: 0; cursor: pointer;">Enable Multi-Query Expansion</label>
                </div>
                <div class="form-group">
                  <label for="ragTopK">Top K (Chunks to fetch)</label>
                  <input type="number" id="ragTopK" class="form-control" value="5">
                </div>
              </div>
            </div>

            <!-- HTTP Configuration Accordion -->
            <div class="accordion-section" id="httpSection" style="display: none;">
              <div class="accordion-header" data-accordion="httpSection">
                <div class="accordion-header-left">
                  <span class="accordion-icon">🌐</span>
                  <span class="accordion-title">HTTP Request</span>
                  <span class="accordion-status-dot"></span>
                </div>
                <span class="accordion-chevron">▼</span>
              </div>
              <div class="accordion-content">
                <div class="form-group">
                  <label>Method & URL</label>
                  <div style="display: flex; gap: 5px;">
                      <select id="httpMethod" style="width: 100px;">
                          <option value="GET">GET</option>
                          <option value="POST">POST</option>
                          <option value="PUT">PUT</option>
                          <option value="DELETE">DELETE</option>
                          <option value="PATCH">PATCH</option>
                      </select>
                      <input type="text" id="httpUrl" placeholder="https://api.example.com/v1/resource">
                  </div>
                </div>
                <div class="form-group">
                  <label>Headers (JSON)</label>
                  <textarea id="httpHeaders" rows="3" class="code-font" placeholder='{ "Authorization": "Bearer token" }'></textarea>
                </div>
                <div class="form-group">
                  <label>Body (JSON or Text)</label>
                  <textarea id="httpBody" rows="5" class="code-font" placeholder='{ "key": "value" }'></textarea>
                </div>
                <div class="form-group">
                   <label>Auth Type</label>
                   <select id="httpAuthType">
                       <option value="none">None</option>
                       <option value="basic">Basic Auth</option>
                       <option value="bearer">Bearer Token</option>
                   </select>
                </div>
              </div>
            </div>

            <!-- OpenAPI Configuration Accordion -->
            <div class="accordion-section" id="openapiSection" style="display: none;">
              <div class="accordion-header" data-accordion="openapiSection">
                <div class="accordion-header-left">
                  <span class="accordion-icon">📜</span>
                  <span class="accordion-title">OpenAPI Client</span>
                  <span class="accordion-status-dot"></span>
                </div>
                <span class="accordion-chevron">▼</span>
              </div>
              <div class="accordion-content">
                <div class="form-group">
                  <label>Spec URL / Text</label>
                  <div style="display: flex; gap: 5px;">
                      <input type="text" id="openapiUrl" placeholder="https://api.example.com/openapi.json">
                      <button type="button" class="btn btn-secondary btn-sm" id="loadSpecBtn">Load</button>
                  </div>
                </div>
                
                <div class="form-group" id="openapiOpsGroup" style="display: none;">
                   <label>Operation</label>
                   <select id="openapiOperation">
                       <option value="">Select an operation...</option>
                   </select>
                </div>

                <div class="form-group" id="openapiParamsGroup" style="display: none;">
                   <label>Parameters</label>
                   <div id="openapiParamsContainer" style="display: flex; flex-direction: column; gap: 10px; padding: 10px; background: rgba(0,0,0,0.1); border-radius: 4px;">
                       <!-- Dynamic params here -->
                   </div>
                </div>
              </div>
            </div>

            <!-- Notion Configuration Accordion -->
            <div class="accordion-section" id="notionSection" style="display: none;">
              <div class="accordion-header" data-accordion="notionSection">
                <div class="accordion-header-left">
                  <span class="accordion-icon">📝</span>
                  <span class="accordion-title">Notion Integration</span>
                  <span class="accordion-status-dot"></span>
                </div>
                <span class="accordion-chevron">▼</span>
              </div>
              <div class="accordion-content">
                <div class="form-group">
                    <label>API Key (Secret)</label>
                    <input type="password" class="form-control" id="notionApiKey" placeholder="secret_...">
                </div>
                <div class="form-group">
                    <label>Operation</label>
                    <select class="form-control" id="notionOperation">
                        <option value="query_database">Query Database</option>
                        <option value="get_page">Get Page</option>
                        <option value="create_page">Create Page</option>
                        <option value="append_block">Append Block Children</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Resource ID (Database or Page ID)</label>
                    <input type="text" class="form-control" id="notionResourceId" placeholder="uuid...">
                </div>
                <div class="form-group">
                    <label>Body (JSON - Filter, Sort, or Content)</label>
                    <textarea class="form-control" id="notionBody" rows="5" placeholder='{ "filter": { ... } }'></textarea>
                </div>
              </div>
            </div>

            <!-- Google Configuration Accordion -->
            <div class="accordion-section" id="googleSection" style="display: none;">
              <div class="accordion-header" data-accordion="googleSection">
                <div class="accordion-header-left">
                  <span class="accordion-icon">📧</span>
                  <span class="accordion-title">Google Workspace</span>
                  <span class="accordion-status-dot"></span>
                </div>
                <span class="accordion-chevron">▼</span>
              </div>
              <div class="accordion-content">
                 <div class="form-group">
                    <label>Service</label>
                    <select class="form-control" id="googleService">
                        <option value="gmail">Gmail</option>
                        <option value="calendar">Google Calendar</option>
                    </select>
                 </div>
                 <div class="form-group">
                    <label>Access Token (OAuth)</label>
                    <input type="password" class="form-control" id="googleToken" placeholder="ya29...">
                 </div>
                 <div class="form-group">
                    <label>Operation</label>
                    <select class="form-control" id="googleOperation">
                        <!-- Gmail Ops -->
                        <option value="list_messages">List Messages (Gmail)</option>
                        <option value="send_email">Send Email (Gmail)</option>
                        <!-- Calendar Ops -->
                        <option value="list_events">List Events (Calendar)</option>
                        <option value="create_event">Create Event (Calendar)</option>
                    </select>
                 </div>
                 <div class="form-group">
                     <label>Calendar ID (for Calendar)</label>
                     <input type="text" class="form-control" id="googleCalendarId" placeholder="primary">
                 </div>
                 <div class="form-group">
                    <label>Body (JSON)</label>
                    <textarea class="form-control" id="googleBody" rows="5" placeholder='{ "q": "from:me" }'></textarea>
                 </div>
              </div>
            </div>

            <!-- GitHub Configuration Accordion -->
            <div class="accordion-section" id="githubSection" style="display: none;">
              <div class="accordion-header" data-accordion="githubSection">
                <div class="accordion-header-left">
                  <span class="accordion-icon">🐙</span>
                  <span class="accordion-title">GitHub Integration</span>
                  <span class="accordion-status-dot"></span>
                </div>
                <span class="accordion-chevron">▼</span>
              </div>
              <div class="accordion-content" id="githubConfig">
                <div class="form-group">
                    <label>Integration Mode</label>
                    <select class="form-control" id="ghMode">
                        <option value="cli">Git CLI (Clone/Pull)</option>
                        <option value="api">GitHub API (Issues/Data)</option>
                    </select>
                </div>
                <div id="ghCliFields">
                    <div class="form-group">
                        <label>Repo URL</label>
                        <input type="text" class="form-control" id="ghRepo" placeholder="https://github.com/user/repo.git">
                    </div>
                    <div class="form-group">
                        <label>Action</label>
                        <select class="form-control" id="ghAction">
                            <option value="clone">Clone</option>
                            <option value="pull">Pull</option>
                        </select>
                    </div>
                </div>
                <div id="ghApiFields" style="display:none;">
                    <div class="form-group">
                        <label>API Token</label>
                        <input type="password" class="form-control" id="ghToken" placeholder="ghp_...">
                    </div>
                    <div class="form-group">
                        <label>Operation</label>
                        <select class="form-control" id="ghOperation">
                            <option value="get_user">Get User</option>
                            <option value="list_repos">List Repos</option>
                            <option value="create_issue">Create Issue</option>
                            <option value="get_issue">Get Issue</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Owner</label>
                        <input type="text" class="form-control" id="ghOwner" placeholder="owner">
                    </div>
                    <div class="form-group">
                        <label>Repo Name</label>
                        <input type="text" class="form-control" id="ghRepoName" placeholder="repo">
                    </div>
                    <div class="form-group">
                        <label>JSON Body</label>
                        <textarea class="form-control" id="ghBody" rows="3" placeholder='{"title": "Bug", "body": "Fix it"}'></textarea>
                    </div>
                </div>
              </div>
            </div>

            <!-- HuggingFace Configuration Accordion -->
            <div class="accordion-section" id="hfSection" style="display: none;">
              <div class="accordion-header" data-accordion="hfSection">
                <div class="accordion-header-left">
                  <span class="accordion-icon">🤗</span>
                  <span class="accordion-title">HuggingFace Model</span>
                  <span class="accordion-status-dot"></span>
                </div>
                <span class="accordion-chevron">▼</span>
              </div>
              <div class="accordion-content" id="hfConfig">
                <div class="form-group">
                    <label>Repo ID</label>
                    <input type="text" class="form-control" id="hfRepo" placeholder="google/gemma-2b">
                </div>
                <div class="form-group">
                    <label>Filename</label>
                    <input type="text" class="form-control" id="hfFile" placeholder="model.safetensors">
                </div>
              </div>
            </div>

            <!-- MCP Configuration Accordion -->
            <div class="accordion-section" id="mcpSection" style="display: none;">
              <div class="accordion-header" data-accordion="mcpSection">
                <div class="accordion-header-left">
                  <span class="accordion-icon">🔌</span>
                  <span class="accordion-title">MCP Client</span>
                  <span class="accordion-status-dot"></span>
                </div>
                <span class="accordion-chevron">▼</span>
              </div>
              <div class="accordion-content" id="mcpConfig">
                <div class="form-group">
                    <label>Command (Full Path/Binary)</label>
                    <input type="text" class="form-control" id="mcpCommand" placeholder="python tests/mcp_server_dummy.py">
                </div>
                 <div class="form-group">
                    <label>Tool Name (Optional)</label>
                    <input type="text" class="form-control" id="mcpTool" placeholder="echo">
                    <small class="form-hint">Leave empty to verify connection & list tools.</small>
                </div>
                <div class="form-group">
                    <label>Tool Arguments (JSON)</label>
                    <textarea class="form-control" id="mcpArgs" rows="2" placeholder='{"message": "hello"}'></textarea>
                </div>
              </div>
            </div>

            <!-- ComfyUI Configuration Accordion -->
            <div class="accordion-section" id="comfySection" style="display: none;">
              <div class="accordion-header" data-accordion="comfySection">
                <div class="accordion-header-left">
                  <span class="accordion-icon">🎨</span>
                  <span class="accordion-title">ComfyUI (GenAI)</span>
                  <span class="accordion-status-dot"></span>
                </div>
                <span class="accordion-chevron">▼</span>
              </div>
              <div class="accordion-content" id="comfyConfig">
                <div class="form-group">
                    <label>Base URL</label>
                    <input type="text" class="form-control" id="comfyUrl" value="http://127.0.0.1:8188">
                </div>
                 <div class="form-group">
                    <label>Mode</label>
                    <select class="form-control" id="comfyMode">
                        <option value="prompt">Prompt (Text-to-Image)</option>
                        <option value="workflow">Workflow (JSON)</option>
                    </select>
                </div>
                <div class="form-group" id="comfyPromptGroup">
                    <label>Prompt (Positive)</label>
                    <textarea class="form-control" id="comfyPrompt" rows="3" placeholder="A futuristic city..."></textarea>
                </div>
                <div class="form-group" id="comfyWorkflowGroup" style="display:none;">
                    <label>Workflow JSON</label>
                    <textarea class="form-control" id="comfyWorkflowJson" rows="6" placeholder="{ ... }"></textarea>
                </div>
              </div>
            </div>

            <!-- Factory Configuration Accordion -->
            <div class="accordion-section" id="factorySection" style="display: none;">
              <div class="accordion-header" data-accordion="factorySection">
                <div class="accordion-header-left">
                  <span class="accordion-icon">🏗️</span>
                  <span class="accordion-title">Factory Mode</span>
                  <span class="accordion-status-dot"></span>
                </div>
                <span class="accordion-chevron">▼</span>
              </div>
              <div class="accordion-content" id="factoryConfig">
                <div class="alert alert-info" style="font-size:0.8rem;">
                    🏗️ <b>Factory Mode:</b> This node analyzes topology and can generate/suggest workflow improvements.
                </div>
                <div class="form-group">
                    <label>Design Goals / Focus</label>
                    <textarea class="form-control" id="factoryGoals" rows="2" placeholder="e.g. Optimize for token usage, or add verification steps."></textarea>
                </div>
              </div>
            </div>

            <!-- Telegram Configuration Accordion -->
            <div class="accordion-section" id="telegramSection" style="display: none;">
              <div class="accordion-header" data-accordion="telegramSection">
                <div class="accordion-header-left">
                  <span class="accordion-icon">📡</span>
                  <span class="accordion-title">Telegram Bot Link</span>
                  <span class="accordion-status-dot"></span>
                </div>
                <span class="accordion-chevron">▼</span>
              </div>
              <div class="accordion-content">
                 <div class="form-group">
                    <label>Bot Token</label>
                    <input type="password" class="form-control" id="telegramToken" placeholder="123456:ABC-DEF...">
                 </div>
                 <div class="form-group">
                    <label>Default Chat ID</label>
                    <input type="text" class="form-control" id="telegramChatId" placeholder="123456789">
                 </div>
                 <div class="form-group">
                    <label>Webhook URL</label>
                    <div id="telegramWebhookCopy" style="background: rgba(0,0,0,0.3); padding: 8px; border-radius: 4px; font-family: monospace; font-size: 0.75rem; word-break: break-all; border: 1px solid var(--border-color);">
                      Waiting for token...
                    </div>
                    <small class="form-hint">Set this URL in your Telegram bot settings.</small>
                 </div>
              </div>
            </div>

            <!-- Discord Configuration Accordion -->
            <div class="accordion-section" id="discordSection" style="display: none;">
              <div class="accordion-header" data-accordion="discordSection">
                <div class="accordion-header-left">
                  <span class="accordion-icon">💬</span>
                  <span class="accordion-title">Discord Integration</span>
                  <span class="accordion-status-dot"></span>
                </div>
                <span class="accordion-chevron">▼</span>
              </div>
              <div class="accordion-content">
                 <div class="form-group">
                    <label>Webhook URL (Fast Outgoing)</label>
                    <input type="text" class="form-control" id="discordWebhookUrl" placeholder="https://discord.com/api/webhooks/...">
                 </div>
                 <div class="form-group">
                    <label>Bot Token</label>
                    <input type="password" class="form-control" id="discordBotToken" placeholder="Bot MTIz...">
                 </div>
                 <div class="form-group">
                    <label>Channel ID</label>
                    <input type="text" class="form-control" id="discordChannelId" placeholder="123456789...">
                 </div>
              </div>
            </div>

            <!-- Browser Configuration Accordion -->
            <div class="accordion-section" id="browserSection" style="display: none;">
              <div class="accordion-header" data-accordion="browserSection">
                <div class="accordion-header-left">
                  <span class="accordion-icon">🖥️</span>
                  <span class="accordion-title">Browser Control (Operator)</span>
                  <span class="accordion-status-dot"></span>
                </div>
                <span class="accordion-chevron">▼</span>
              </div>
              <div class="accordion-content">
                 <div class="form-group">
                    <label>URL</label>
                    <input type="text" class="form-control" id="browserUrl" placeholder="https://example.com">
                 </div>
                 <div class="form-group">
                    <label>Action</label>
                    <select class="form-control" id="browserAction">
                        <option value="navigate">Navigate</option>
                        <option value="click">Click</option>
                        <option value="type">Type</option>
                        <option value="extract">Extract Content</option>
                    </select>
                 </div>
                 <div class="form-group">
                    <label>Selector (CSS)</label>
                    <input type="text" class="form-control" id="browserSelector" placeholder=".btn-submit">
                 </div>
              </div>
            </div>

            <!-- Shell Configuration Accordion -->
            <div class="accordion-section" id="shellSection" style="display: none;">
              <div class="accordion-header" data-accordion="shellSection">
                <div class="accordion-header-left">
                  <span class="accordion-icon">🐚</span>
                  <span class="accordion-title">Shell Command (Operator)</span>
                  <span class="accordion-status-dot"></span>
                </div>
                <span class="accordion-chevron">▼</span>
              </div>
              <div class="accordion-content">
                 <div class="form-group">
                    <label>Command</label>
                    <input type="text" class="form-control" id="shellCommand" placeholder="ls -la">
                 </div>
                 <div class="form-group">
                    <label>Working Directory</label>
                    <input type="text" class="form-control" id="shellCwd" placeholder=".">
                 </div>
              </div>
            </div>

            <!-- System Configuration Accordion -->
            <div class="accordion-section" id="systemSection" style="display: none;">
              <div class="accordion-header" data-accordion="systemSection">
                <div class="accordion-header-left">
                  <span class="accordion-icon">⚙️</span>
                  <span class="accordion-title">System Actions</span>
                  <span class="accordion-status-dot"></span>
                </div>
                <span class="accordion-chevron">▼</span>
              </div>
              <div class="accordion-content">
                 <div class="form-group">
                    <label>Action</label>
                    <select class="form-control" id="systemAction">
                        <option value="notify">Notify (OS)</option>
                    </select>
                 </div>
                 <div class="form-group">
                    <label>Message</label>
                    <input type="text" class="form-control" id="systemMessage" placeholder="Task completed!">
                 </div>
              </div>
            </div>

            <!-- A2UI Configuration Accordion -->
            <div class="accordion-section" id="a2uiSection" style="display: none;">
              <div class="accordion-header" data-accordion="a2uiSection">
                <div class="accordion-header-left">
                  <span class="accordion-icon">🎨</span>
                  <span class="accordion-title">Generative UI (Artist)</span>
                  <span class="accordion-status-dot"></span>
                </div>
                <span class="accordion-chevron">▼</span>
              </div>
              <div class="accordion-content">
                 <div class="form-group">
                    <label>Component Type</label>
                    <select class="form-control" id="a2uiComponentType">
                        <option value="card">Card (Text + Image)</option>
                        <option value="form">Interactive Form</option>
                        <option value="buttons">Action Buttons</option>
                        <option value="chart">Data Chart</option>
                    </select>
                 </div>
                 <div class="form-group">
                    <label>Title</label>
                    <input type="text" class="form-control" id="a2uiTitle" placeholder="Agent Response">
                 </div>
                 <!-- This will be expanded dynamically based on type -->
                 <div id="a2uiDynamicConfig"></div>
              </div>
            </div>

            <!-- Sub-Workflows Accordion -->
            <div class="accordion-section collapsed" id="subWorkflowsAccordion">
              <div class="accordion-header" data-accordion="subWorkflowsAccordion">
                <div class="accordion-header-left">
                  <span class="accordion-icon">🔗</span>
                  <span class="accordion-title">Attached Sub-Workflows</span>
                  <span class="accordion-status-dot"></span>
                </div>
                <span class="accordion-chevron">▼</span>
              </div>
              <div class="accordion-content">
                <p class="form-hint">Fractal execution: these workflows run inside this node.</p>
                <div id="subWorkflowList" class="sub-workflow-list"></div>
                <p id="noSubWorkflows" class="form-hint" style="text-align: center; margin-top: 10px;">No workflows attached.</p>
              </div>
            </div>
            
            <!-- Agreement Rules Accordion -->
            <div class="accordion-section collapsed" id="agreementRulesAccordion">
              <div class="accordion-header" data-accordion="agreementRulesAccordion">
                <div class="accordion-header-left">
                  <span class="accordion-icon">📋</span>
                  <span class="accordion-title">Agreement Rules</span>
                  <span class="accordion-status-dot"></span>
                </div>
                <span class="accordion-chevron">▼</span>
              </div>
              <div class="accordion-content">
                <p class="form-hint">Conditions that must pass before output continues to next node</p>
                
                <div id="agreementRules"></div>
                
                <button type="button" class="btn btn-secondary" id="addRuleBtn">+ Add Rule</button>
              </div>
            </div>
            
            <!-- Actions -->
            <div class="form-actions">
              <button type="button" class="btn btn-secondary" id="steerAgentBtn" title="Inject instruction while running">🎮 Steer Agent</button>
              <div style="flex:1"></div>
              <button type="button" class="btn btn-danger" id="deleteNodeBtn">Delete Node</button>
              <button type="submit" class="btn btn-primary">Save Changes</button>
            </div>
          </form>
        </div>
      </div>
    `;

    // Initialize accordion toggle behavior
    this.initAccordions();
  }

  initAccordions() {
    const headers = this.container.querySelectorAll('.accordion-header');
    headers.forEach(header => {
      header.addEventListener('click', () => {
        const accordionId = header.dataset.accordion;
        const section = document.getElementById(accordionId);
        if (section) {
          section.classList.toggle('collapsed');
          this.saveAccordionStates();
        }
      });
    });
  }

  saveAccordionStates() {
    const states = {};
    this.container.querySelectorAll('.accordion-section').forEach(section => {
      if (section.id) {
        states[section.id] = section.classList.contains('collapsed');
      }
    });
    localStorage.setItem('orchestrator_node_editor_accordions', JSON.stringify(states));
  }

  restoreAccordionStates() {
    const saved = localStorage.getItem('orchestrator_node_editor_accordions');
    if (!saved) return;
    try {
      const states = JSON.parse(saved);
      Object.entries(states).forEach(([id, isCollapsed]) => {
        const section = document.getElementById(id);
        if (section) {
          if (isCollapsed) {
            section.classList.add('collapsed');
          } else {
            section.classList.remove('collapsed');
          }
        }
      });
    } catch (e) {
      console.error('Failed to restore accordion states', e);
    }
  }

  updateAccordionStatusDots() {
    const sections = [
      { id: 'llmProviderAccordion', fields: ['nodeProvider', 'nodeModel'] },
      { id: 'scalingAccordion', fields: ['nodeBudget'] },
      { id: 'personaAccordion', fields: ['nodePersona', 'nodeBackstory', 'nodeApproval'] },
      { id: 'scriptSection', fields: ['nodeScript'] },
      { id: 'memorySection', fields: ['memoryTags'] },
      { id: 'ragSection', fields: ['ragSource'] },
      { id: 'httpSection', fields: ['httpUrl', 'httpBody', 'httpHeaders'] },
      { id: 'openapiSection', fields: ['openapiUrl', 'openapiOperation'] },
      { id: 'notionSection', fields: ['notionApiKey', 'notionResourceId', 'notionBody'] },
      { id: 'googleSection', fields: ['googleToken', 'googleCalendarId', 'googleBody'] },
      { id: 'githubSection', fields: ['ghRepo', 'ghToken', 'ghBody', 'ghOwner', 'ghRepoName'] },
      { id: 'hfSection', fields: ['hfRepo', 'hfFile'] },
      { id: 'mcpSection', fields: ['mcpCommand', 'mcpTool', 'mcpArgs'] },
      { id: 'comfySection', fields: ['comfyUrl', 'comfyPrompt', 'comfyWorkflowJson'] },
      { id: 'factorySection', fields: ['factoryGoals'] },
      { id: 'telegramSection', fields: ['telegramToken', 'telegramChatId'] },
      { id: 'discordSection', fields: ['discordWebhookUrl', 'discordBotToken', 'discordChannelId'] },
      { id: 'browserSection', fields: ['browserUrl', 'browserSelector'] },
      { id: 'shellSection', fields: ['shellCommand', 'shellCwd'] },
      { id: 'systemSection', fields: ['systemMessage'] },
      { id: 'a2uiSection', fields: ['a2uiTitle'] }
    ];

    sections.forEach(s => {
      const sectionEl = document.getElementById(s.id);
      if (!sectionEl) return;

      const hasData = s.fields.some(fieldId => {
        const el = document.getElementById(fieldId);
        if (!el) return false;
        if (el.type === 'checkbox') return el.checked;
        if (el.type === 'select-one') {
          // Check if it has a non-default/non-empty value
          if (fieldId === 'nodeProvider') return el.value !== 'mock';
          if (fieldId === 'nodeModel') return el.value !== 'default' && el.value !== '';
          return el.value !== '';
        }
        return el.value && el.value.trim() !== '';
      });

      if (hasData) {
        sectionEl.classList.add('has-data');
      } else {
        sectionEl.classList.remove('has-data');
      }
    });

    // Sub-workflows and rules need special checks
    const subWorkflows = document.getElementById('subWorkflowList')?.children.length > 0;
    const rules = document.getElementById('agreementRules')?.children.length > 0;

    if (rules) document.getElementById('agreementRulesAccordion')?.classList.add('has-data');
    else document.getElementById('agreementRulesAccordion')?.classList.remove('has-data');
  }

  updateSecurityWarning() {
    const typeEl = this.container.querySelector('#nodeType');
    const providerEl = this.container.querySelector('#nodeProvider');
    if (!typeEl || !providerEl) return;

    const type = typeEl.value;
    const provider = providerEl.value;

    const needsWarning = ['cli', 'opencode', 'gemini'].includes(provider) ||
      ['script', 'mcp', 'shell'].includes(type);

    let warningEl = document.getElementById('cliWarning');
    if (needsWarning) {
      if (!warningEl) {
        warningEl = document.createElement('div');
        warningEl.id = 'cliWarning';
        warningEl.className = 'alert alert-warning';
        warningEl.style.marginTop = '10px';
        warningEl.style.fontSize = '0.8rem';

        // Insert after LLM Provider Accordion or first form section
        const target = document.getElementById('llmProviderAccordion') || this.container.querySelector('.form-section');
        if (target) {
          target.insertAdjacentElement('afterend', warningEl);
        }
      }
      warningEl.innerHTML = '⚠️ <b>Security Alert:</b> High-privilege node. Ensure you trust the generated code/commands.';
    } else if (warningEl) {
      warningEl.remove();
    }
  }

  bindEvents() {
    // Close button
    this.container.querySelector('#closeEditor').addEventListener('click', () => {
      this.close();
    });

    // Provider change updates models
    this.container.querySelector('#nodeProvider').addEventListener('change', (e) => {
      this.updateModelOptions(e.target.value);
      this.updateAccordionStatusDots();
    });

    // Global update on any input
    this.container.querySelector('#editorForm').addEventListener('input', () => {
      this.updateAccordionStatusDots();
    });
    this.container.querySelector('#editorForm').addEventListener('change', () => {
      this.updateAccordionStatusDots();
    });


    // Test Provider
    this.container.querySelector('#testProviderBtn').addEventListener('click', async (e) => {
      const btn = e.currentTarget;
      const originalText = btn.innerHTML;
      const providerId = document.getElementById('nodeProvider').value;
      const model = document.getElementById('nodeModel').value;
      const persona = document.getElementById('nodePersona').value;

      let testPrompt;
      if (['cli', 'opencode', 'gemini'].includes(providerId)) {
        // For CLI, we don't want to accidentally run a complex command.
        // Just confirm.
        if (!confirm("⚠️ Execute test command?\nThis will run the configured tool on your system.")) return;
        testPrompt = "Test: Connection verified.";
      } else {
        testPrompt = prompt("Enter a test message for this agent:", "Hello, who are you?");
        if (!testPrompt) return;
      }

      try {
        btn.disabled = true;
        btn.innerHTML = '<span>⏳</span> Testing...';

        const response = await fetch('/api/node/test', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            provider: providerId,
            model: model,
            persona: persona,
            prompt: testPrompt,
            provider_config: {} // Basic config for now
          })
        });

        const result = await response.json();

        if (result.success) {
          this.showToast('Test Successful! Response in console.', 'success');
          console.log("Test Response:", result.output);
          // Maybe show a modal instead of alert for long text? 
          // For now, let's just alert the output but make it nicer if we could.
          // Actually, stick to alert for the OUTPUT content because it's large, but use toast for status.
          alert(result.output);
        } else {
          this.showToast(`Error: ${result.error}`, 'error');
        }
      } catch (err) {
        this.showToast(`Failed to test: ${err.message}`, 'error');
      } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
      }
    });

    // Provider Info / Help Templates
    this.container.querySelector('#infoProviderBtn').addEventListener('click', () => {
      const providerId = document.getElementById('nodeProvider').value;
      const provider = this.providers.find(p => p.id === providerId);

      const templates = {
        'groq': {
          title: 'Groq Setup',
          instructions: 'Enter your API key from the Groq console.',
          template: '{\n  "api_key": "gsk_...",\n  "model": "llama-3.1-70b-versatile"\n}'
        },
        'ollama': {
          title: 'Ollama Setup',
          instructions: 'Ensure Ollama is running locally on port 11434.',
          template: '{\n  "base_url": "http://localhost:11434",\n  "model": "llama3"\n}'
        },
        'cli': {
          title: 'CLI Tool Setup',
          instructions: 'This node executes tasks via local CLI tools. Ensure the tool is installed in your system PATH.',
          template: '{\n  "working_dir": "./",\n  "auto_approve": false,\n  "stream_logs": true\n}'
        },
        'google_ai': {
          title: 'Google AI (Gemini) Setup',
          instructions: 'Get your API key from Google AI Studio.',
          template: '{\n  "api_key": "...", \n  "model": "gemini-1.5-pro"\n}'
        },
        'mock': {
          title: 'Simulation Mode',
          instructions: 'Used for testing without an AI backend.',
          template: '{}'
        }
      };

      const info = templates[provider?.type] || templates['mock'];

      const modalHtml = `
        <div class="modal open" id="providerHelpModal">
          <div class="modal-content">
            <div class="modal-header">
              <h3>${info.title}</h3>
              <button class="btn-close" onclick="this.closest('.modal').remove()">×</button>
            </div>
            <div class="modal-body">
              <p>${info.instructions}</p>
              <div class="form-group">
                <label>Config Template (JSON):</label>
                <div class="code-block" style="background:#1a1a1a; padding:10px; border-radius:4px; font-family:monospace; white-space:pre; margin-top:5px; border: 1px solid #333; color: #a9b7c6;">${info.template}</div>
              </div>
            </div>
            <div class="modal-footer">
              <button class="btn btn-primary" onclick="this.closest('.modal').remove()">Got it</button>
            </div>
          </div>
        </div>
      `;
      document.body.insertAdjacentHTML('beforeend', modalHtml);
    });

    // Add rule button
    this.container.querySelector('#addRuleBtn').addEventListener('click', () => {
      this.addAgreementRule();
    });

    // Steer Agent Button
    this.container.querySelector('#steerAgentBtn').addEventListener('click', async () => {
      if (!this.currentNode) return;
      const feedback = prompt("🗣️ Inject Feedback/Instruction to Agent:\n(This will be added to the agent's context immediately)", "Focus on...");
      if (!feedback) return;

      try {
        const res = await fetch(`/api/node/${this.currentNode.id}/feedback`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ feedback })
        });
        const data = await res.json();
        if (data.success) {
          this.showToast("✅ Feedback Sent! Agent will see this.", "success");
        } else {
          this.showToast("Error: " + data.error, "error");
        }
      } catch (e) {
        console.error(e);
        this.showToast("Failed to send feedback", "error");
      }
    });

    // Delete node button
    this.container.querySelector('#deleteNodeBtn').addEventListener('click', () => {
      if (this.currentNode && confirm(`Delete node "${this.currentNode.name}"?`)) {
        this.emit('deleteNode', this.currentNode.id);
        this.close();
      }
    });

    // Open editor implementation
    // Node Type Change Handler - Unified and simplified
    this.container.querySelector('#nodeType').addEventListener('change', (e) => {
      const type = e.target.value;
      const noteBackstoryGroup = document.getElementById('backstoryGroup');
      const personaLabel = document.getElementById('personaLabel');
      const personaInput = document.getElementById('nodePersona');

      // Update Persona Labels based on type
      if (['character', 'agent', 'director'].includes(type)) {
        noteBackstoryGroup.style.display = 'block';
        if (type === 'character') {
          personaLabel.innerText = "Current Role / Scene Goal";
          personaInput.placeholder = "What is the character trying to achieve in this scene?";
        } else {
          personaLabel.innerText = "Persona / System Prompt";
          personaInput.placeholder = "Enter the agent's system prompt...";
        }
      } else {
        noteBackstoryGroup.style.display = 'none';
        personaLabel.innerText = "Configuration / Prompt";
      }

      // Visibility Logic
      const hideAllSpecial = () => {
        const specialSections = [
          'httpSection', 'openapiSection', 'notionSection', 'googleSection',
          'ragSection', 'telegramSection', 'discordSection', 'browserSection',
          'shellSection', 'systemSection', 'a2uiSection', 'githubSection',
          'hfSection', 'mcpSection', 'comfySection', 'factorySection', 'memorySection',
          'scriptSection'
        ];
        specialSections.forEach(id => {
          const el = document.getElementById(id);
          if (el) el.style.display = 'none';
        });
      };

      hideAllSpecial();

      // Core Accordions
      const llmAccordion = document.getElementById('llmProviderAccordion');
      const personaAccordion = document.getElementById('personaAccordion');
      const scalingAccordion = document.getElementById('scalingAccordion');

      const isInternal = ['input', 'output'].includes(type);
      const isScript = type === 'script';

      llmAccordion.style.display = (isInternal || isScript) ? 'none' : 'block';
      personaAccordion.style.display = isInternal ? 'none' : 'block';
      scalingAccordion.style.display = (isInternal || isScript) ? 'none' : 'block';

      // Show relevant special section
      const typeToSection = {
        'script': 'scriptSection',
        'memory': 'memorySection',
        'rag': 'ragSection',
        'http': 'httpSection',
        'openapi': 'openapiSection',
        'notion': 'notionSection',
        'google': 'googleSection',
        'github': 'githubSection',
        'huggingface': 'hfSection',
        'mcp': 'mcpSection',
        'comfy': 'comfySection',
        'architect': 'factorySection',
        'critic': 'factorySection',
        'telegram_trigger': 'telegramSection',
        'discord_trigger': 'discordSection',
        'browser': 'browserSection',
        'shell': 'shellSection',
        'system': 'systemSection',
        'a2ui': 'a2uiSection'
      };

      const targetId = typeToSection[type];
      if (targetId) {
        const el = document.getElementById(targetId);
        if (el) el.style.display = 'block';
      }

      this.updateSecurityWarning();
    });

    // Provider change updates models and warnings
    this.container.querySelector('#nodeProvider').addEventListener('change', (e) => {
      this.updateModelOptions(e.target.value);
      this.updateSecurityWarning();
      this.updateAccordionStatusDots();
    });

    // Global update on any input to refresh status dots
    this.container.querySelector('#editorForm').addEventListener('input', () => {
      this.updateAccordionStatusDots();
    });
    this.container.querySelector('#editorForm').addEventListener('change', () => {
      this.updateAccordionStatusDots();
    });

    // Form submit
    this.container.querySelector('#editorForm').addEventListener('submit', (e) => {
      e.preventDefault();
      this.saveNode();
    });

    // ============ OpenAPI Events ============
    const loadSpecBtn = this.container.querySelector('#loadSpecBtn');
    if (loadSpecBtn) {
      loadSpecBtn.addEventListener('click', async () => {
        const urlInput = this.container.querySelector('#openapiUrl');
        const url = urlInput.value.trim();
        if (!url) {
          this.showToast('Please enter a Spec URL', 'error');
          return;
        }

        loadSpecBtn.disabled = true;
        loadSpecBtn.innerHTML = 'Loading...';

        try {
          // Determine if parsing logic is local or via API
          // We'll use the API endpoint we created
          const res = await fetch('/api/tools/parse-openapi', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url })
          });
          const result = await res.json();

          if (result.success && result.data) {
            this.showToast('Spec loaded successfully', 'success');

            // Store operations momentarily on the instance or node?
            // Best to cache on the node object itself so saving works
            if (this.currentNode) {
              this.currentNode._openapi_ops = result.data.operations;
              // We assume result.data.operations is the list
            }

            this.populateOpenApiOperations(result.data.operations);
            document.getElementById('openapiOpsGroup').style.display = 'block';
          } else {
            this.showToast('Failed to load spec', 'error');
          }
        } catch (e) {
          this.showToast('Error: ' + e.message, 'error');
        } finally {
          loadSpecBtn.disabled = false;
          loadSpecBtn.innerHTML = 'Load';
        }
      });
    }

    const opSelect = this.container.querySelector('#openapiOperation');
    if (opSelect) {
      opSelect.addEventListener('change', (e) => {
        const opId = e.target.value;
        if (!opId || !this.currentNode || !this.currentNode._openapi_ops) return;

        const op = this.currentNode._openapi_ops.find(o => o.id === opId);
        if (op) {
          this.renderOpenApiParams(op);
        }
      });
    }
  }

  populateOpenApiOperations(ops) {
    const select = this.container.querySelector('#openapiOperation');
    select.innerHTML = '<option value="">Select an operation...</option>';
    ops.forEach(op => {
      const opt = document.createElement('option');
      opt.value = op.id;
      opt.textContent = `${op.method} ${op.path} - ${op.summary || op.id}`;
      select.appendChild(opt);
    });
  }

  renderOpenApiParams(op) {
    const group = document.getElementById('openapiParamsGroup');
    const container = document.getElementById('openapiParamsContainer');
    container.innerHTML = '';

    if (!op.params || op.params.length === 0) {
      group.style.display = 'none';
      return;
    }

    group.style.display = 'block';
    op.params.forEach(p => {
      const div = document.createElement('div');
      div.className = 'form-group-sm';
      div.innerHTML = `
            <label style="font-size:0.85em; color: var(--text-muted);">${p.name} ${p.required ? '*' : ''} <span style="font-size:0.7em; opacity:0.7">(${p.in})</span></label>
            <input type="text" class="form-control openapi-param-input" data-param-name="${p.name}" data-param-in="${p.in}" placeholder="${p.description || ''}">
          `;
      container.appendChild(div);
    });
  }

  showToast(message, type = 'info') {
    // Simple toast implementation
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
      toastContainer = document.createElement('div');
      toastContainer.id = 'toast-container';
      toastContainer.style.cssText = `
              position: fixed; bottom: 20px; right: 20px; z-index: 10000;
              display: flex; flex-direction: column; gap: 10px;
          `;
      document.body.appendChild(toastContainer);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.style.cssText = `
          background: ${type === 'error' ? '#ef4444' : '#10b981'};
          color: white; padding: 12px 24px; border-radius: 8px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1); font-family: system-ui;
          animation: slideIn 0.3s ease-out;
      `;
    toast.textContent = message;

    toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }

  open(node) {
    this.currentNode = node;

    // Show form, hide placeholder
    const placeholder = this.container.querySelector('#editorPlaceholder');
    const form = this.container.querySelector('#editorForm');

    if (placeholder) placeholder.style.display = 'none';
    if (form) form.style.display = 'block';

    if (!form) {
      console.error("NodeEditor: Editor form not found in container.");
      return;
    }

    // Populate fields
    this.container.querySelector('#nodeName').value = node.name || '';
    this.container.querySelector('#nodeType').value = node.type || 'agent';
    this.container.querySelector('#nodeProvider').value = node.provider || 'simulation';
    this.updateModelOptions(node.provider || 'simulation');
    this.container.querySelector('#nodeModel').value = node.model || 'default';
    this.container.querySelector('#nodePersona').value = node.persona || '';

    // Narrative Fields
    this.container.querySelector('#nodeBackstory').value = node.backstory || '';
    this.container.querySelector('#nodeInternet').checked = node.internet_access || false;
    this.container.querySelector('#nodeApproval').checked = node.requires_approval || false;

    // Challenge Features
    this.container.querySelector('#nodeTier').value = node.tier || 'free';
    this.container.querySelector('#nodeBudget').value = node.token_budget || 4096;

    // Script Logic
    if (this.container.querySelector('#nodeScript')) {
      this.container.querySelector('#nodeScript').value = node.script_code || '';
    }

    // Memory Logic
    if (this.container.querySelector('#memoryAction')) {
      const config = node.memory_config || node.provider_config || {};
      this.container.querySelector('#memoryAction').value = config.action || 'retrieve';
      this.container.querySelector('#memoryTags').value = Array.isArray(config.tags) ? config.tags.join(', ') : (config.tags || '');
      this.container.querySelector('#memoryLimit').value = config.limit || 5;
    }

    // HTTP Logic
    if (this.container.querySelector('#httpSection')) {
      const config = node.provider_config || {};
      this.container.querySelector('#httpMethod').value = config.method || 'GET';
      this.container.querySelector('#httpUrl').value = config.url || '';
      this.container.querySelector('#httpHeaders').value = config.headers ? JSON.stringify(config.headers, null, 2) : '';
      this.container.querySelector('#httpBody').value = config.body ? (typeof config.body === 'object' ? JSON.stringify(config.body, null, 2) : config.body) : '';
      this.container.querySelector('#httpAuthType').value = config.auth_type || 'none';
    }

    // OpenAPI Logic
    if (this.container.querySelector('#openapiSection') && node.type === 'openapi') {
      const config = node.provider_config || {};
      this.container.querySelector('#openapiUrl').value = config.url || '';

      // Restore operations cache
      if (config._ops_cache) {
        node._openapi_ops = config._ops_cache;
        this.populateOpenApiOperations(config._ops_cache);
        document.getElementById('openapiOpsGroup').style.display = 'block';

        if (config.operationId) {
          this.container.querySelector('#openapiOperation').value = config.operationId;

          // Trigger change to render params
          const op = node._openapi_ops.find(o => o.id === config.operationId);
          if (op) {
            this.renderOpenApiParams(op);

            // Restore param values
            if (config.params) {
              const inputs = this.container.querySelectorAll('.openapi-param-input');
              inputs.forEach(input => {
                const name = input.dataset.paramName;
                if (config.params[name]) {
                  input.value = config.params[name];
                }
              });
            }
          }
        }
      }
    }

    // Notion Logic
    if (this.container.querySelector('#notionSection') && node.type === 'notion') {
      const config = node.provider_config || {};
      this.container.querySelector('#notionApiKey').value = config.api_key || '';
      this.container.querySelector('#notionOperation').value = config.operation || 'query_database';
      this.container.querySelector('#notionResourceId').value = config.resource_id || '';
      this.container.querySelector('#notionBody').value = config.body ? (typeof config.body === 'object' ? JSON.stringify(config.body, null, 2) : config.body) : '';
    }

    // Google Logic
    if (this.container.querySelector('#googleSection') && node.type === 'google') {
      const config = node.provider_config || {};
      this.container.querySelector('#googleService').value = config.service || 'gmail';
      this.container.querySelector('#googleToken').value = config.api_token || '';
      this.container.querySelector('#googleOperation').value = config.operation || 'list_messages';
      this.container.querySelector('#googleCalendarId').value = (config.params && config.params.calendar_id) || 'primary';
      this.container.querySelector('#googleBody').value = config.body ? (typeof config.body === 'object' ? JSON.stringify(config.body, null, 2) : config.body) : '';
    }

    // RAG Logic
    if (this.container.querySelector('#ragSection') && node.type === 'rag') {
      const config = node.provider_config || {};
      this.container.querySelector('#ragSource').value = config.source_path || 'knowledge_base';
      this.container.querySelector('#ragChunkSize').value = config.chunk_size || 1000;
      this.container.querySelector('#ragOverlap').value = config.chunk_overlap || 200;
      this.container.querySelector('#ragMultiQuery').checked = config.multi_query !== false;
      this.container.querySelector('#ragTopK').value = config.top_k || 5;
    }

    // Telegram Logic
    if (this.container.querySelector('#telegramSection') && node.type === 'telegram_trigger') {
      const config = node.provider_config || {};
      this.container.querySelector('#telegramToken').value = config.bot_token || '';
      this.container.querySelector('#telegramChatId').value = config.chat_id || '';

      const host = window.location.origin;
      this.container.querySelector('#telegramWebhookCopy').innerText = config.bot_token ? `${host}/api/webhooks/telegram/${config.bot_token}` : "Enter token to see URL";
    }

    // Discord Logic
    if (this.container.querySelector('#discordSection') && node.type === 'discord_trigger') {
      const config = node.provider_config || {};
      this.container.querySelector('#discordWebhookUrl').value = config.webhook_url || '';
      this.container.querySelector('#discordBotToken').value = config.bot_token || '';
      this.container.querySelector('#discordChannelId').value = config.channel_id || '';
    }

    // Browser Logic
    if (this.container.querySelector('#browserSection') && node.type === 'browser') {
      const config = node.provider_config || node.inputs || {};
      this.container.querySelector('#browserUrl').value = config.url || '';
      this.container.querySelector('#browserAction').value = config.action || 'navigate';
      this.container.querySelector('#browserSelector').value = config.selector || '';
    }

    // Shell Logic
    if (this.container.querySelector('#shellSection') && node.type === 'shell') {
      const config = node.provider_config || node.inputs || {};
      this.container.querySelector('#shellCommand').value = config.command || '';
      this.container.querySelector('#shellCwd').value = config.cwd || '.';
    }

    // System Logic
    if (this.container.querySelector('#systemSection') && node.type === 'system') {
      const config = node.provider_config || node.inputs || {};
      this.container.querySelector('#systemAction').value = config.action || 'notify';
      this.container.querySelector('#systemMessage').value = config.message || config.text || '';
    }

    // A2UI Logic
    if (this.container.querySelector('#a2uiSection') && node.type === 'a2ui') {
      const config = node.provider_config || {};
      this.container.querySelector('#a2uiComponentType').value = config.component_type || 'card';
      this.container.querySelector('#a2uiTitle').value = config.title || '';
    }

    // MCP Logic
    if (this.container.querySelector('#mcpConfig') && node.type === 'mcp') {
      const config = node.provider_config || {};
      this.container.querySelector('#mcpCommand').value = config.command || '';
      this.container.querySelector('#mcpTool').value = config.tool_name || '';
      this.container.querySelector('#mcpArgs').value = config.tool_args ? (typeof config.tool_args === 'object' ? JSON.stringify(config.tool_args, null, 2) : config.tool_args) : '';
    }

    // ComfyUI Logic
    if (this.container.querySelector('#comfyConfig') && node.type === 'comfy') {
      const config = node.provider_config || {};
      this.container.querySelector('#comfyUrl').value = config.base_url || 'http://127.0.0.1:8188';
      this.container.querySelector('#comfyMode').value = config.mode || 'prompt';
      this.container.querySelector('#comfyPrompt').value = config.prompt || '';
      this.container.querySelector('#comfyWorkflowJson').value = config.workflow_json ? (typeof config.workflow_json === 'object' ? JSON.stringify(config.workflow_json, null, 2) : config.workflow_json) : '';

      // Trigger visibility
      this.container.querySelector('#comfyMode').dispatchEvent(new Event('change'));
    }

    // Factory Logic
    if (this.container.querySelector('#factoryConfig') && ['architect', 'critic'].includes(node.type)) {
      const config = node.provider_config || {};
      this.container.querySelector('#factoryGoals').value = config.goals || '';
    }

    // Trigger type change to update UI
    this.container.querySelector('#nodeType').dispatchEvent(new Event('change'));

    // GitHub Logic (must be after dispatch so HTML is injected)
    if (this.container.querySelector('#githubConfig') && node.type === 'github') {
      const config = node.provider_config || node.config || {};
      const mode = config.mode || 'cli';
      const modeSelect = this.container.querySelector('#ghMode');
      if (modeSelect) {
        modeSelect.value = mode;
        modeSelect.dispatchEvent(new Event('change')); // Trigger visibility

        if (mode === 'api') {
          this.container.querySelector('#ghToken').value = config.api_token || '';
          this.container.querySelector('#ghOperation').value = config.operation || 'get_user';
          this.container.querySelector('#ghOwner').value = config.owner || '';
          this.container.querySelector('#ghRepoName').value = config.repo || '';
          this.container.querySelector('#ghBody').value = config.body ? (typeof config.body === 'object' ? JSON.stringify(config.body, null, 2) : config.body) : '';
        } else {
          this.container.querySelector('#ghRepo').value = config.repo || '';
          this.container.querySelector('#ghAction').value = config.action || 'clone';
        }
      }
    }

    // Load agreement rules
    this.loadAgreementRules(node.agreement_rules || []);

    // Load sub-workflows
    this.loadSubWorkflows(node.sub_workflows || []);

    // Restore accordion states (collapsed/expanded)
    this.restoreAccordionStates();

    // Update status dots and security warnings
    this.updateAccordionStatusDots();
    this.updateSecurityWarning();

    // Show panel
    this.container.classList.add('open');
  }

  close() {
    this.currentNode = null;
    this.container.classList.remove('open');
    const placeholder = this.container.querySelector('#editorPlaceholder');
    const form = this.container.querySelector('#editorForm');

    if (placeholder) placeholder.style.display = 'block';
    if (form) form.style.display = 'none';
  }

  updateModelOptions(providerId) {
    const provider = this.providers.find(p => p.id === providerId);
    const modelSelect = this.container.querySelector('#nodeModel');

    // Recommendations Map (User requested expansion)
    const PRESETS = {
      'ollama': [
        { id: 'llama3', name: 'Llama 3 (Standard)', note: 'Good balance' },
        { id: 'mistral', name: 'Mistral 7B', note: 'Fast & Smart' },
        { id: 'deepseek-v3', name: 'DeepSeek V3', note: 'Top Logic' },
        { id: 'qwen2.5-coder', name: 'Qwen 2.5 Coder', note: 'Coding Expert' }
      ],
      'cli': [
        { id: 'aider', name: 'Aider Engine', note: 'Pair Programming' },
        { id: 'claude-code', name: 'Claude Code', note: 'Codebase Expert' },
        { id: 'fabric', name: 'Fabric Patterns', note: 'Workflow Augment' }
      ]
    };

    if (provider && provider.type === 'ollama') {
      const available = new Set(provider.models || []);

      let html = '<option value="default">Default</option>';
      html += '<optgroup label="Installed">';

      // List installed models
      let hasInstalled = false;
      provider.models.forEach(m => {
        html += `<option value="${m}">${m}</option>`;
        hasInstalled = true;
      });
      if (!hasInstalled) html += '<option disabled>No models found</option>';
      html += '</optgroup>';

      // List Recommended (if not installed)
      const missingPresets = PRESETS['ollama'].filter(p => !available.has(p.id));
      if (missingPresets.length > 0) {
        html += '<optgroup label="Recommended (Download via Ollama)">';
        missingPresets.forEach(p => {
          html += `<option value="${p.id}" disabled>☁️ ${p.name} - ${p.note}</option>`;
        });
        html += '</optgroup>';
      }

      modelSelect.innerHTML = html;
    } else {
      // Standard provider
      modelSelect.innerHTML = provider
        ? provider.models.map(m => `<option value="${m}">${m}</option>`).join('')
        : '<option value="default">Default</option>';
    }
  }

  loadAgreementRules(rules) {
    const container = this.container.querySelector('#agreementRules');
    container.innerHTML = '';

    rules.forEach((rule, index) => {
      this.addAgreementRule(rule, index);
    });
  }

  addAgreementRule(rule = {}, index = null) {
    const container = this.container.querySelector('#agreementRules');
    const ruleIndex = index !== null ? index : container.children.length;

    const ruleEl = document.createElement('div');
    ruleEl.className = 'agreement-rule';
    ruleEl.innerHTML = `
      <select class="rule-type" data-index="${ruleIndex}">
        <option value="contains" ${rule.type === 'contains' ? 'selected' : ''}>Contains</option>
        <option value="not_contains" ${rule.type === 'not_contains' ? 'selected' : ''}>Not Contains</option>
        <option value="min_words" ${rule.type === 'min_words' ? 'selected' : ''}>Min Words</option>
        <option value="max_words" ${rule.type === 'max_words' ? 'selected' : ''}>Max Words</option>
      </select>
      <input type="text" class="rule-value" value="${rule.value || ''}" placeholder="Value">
      <label class="rule-required">
        <input type="checkbox" class="rule-required-check" ${rule.required !== false ? 'checked' : ''}> Required
      </label>
      <button type="button" class="btn-remove-rule">×</button>
    `;

    ruleEl.querySelector('.btn-remove-rule').addEventListener('click', () => {
      ruleEl.remove();
    });

    container.appendChild(ruleEl);
  }

  getAgreementRules() {
    const container = this.container.querySelector('#agreementRules');
    const rules = [];

    container.querySelectorAll('.agreement-rule').forEach((el, index) => {
      rules.push({
        name: `rule_${index}`,
        type: el.querySelector('.rule-type').value,
        value: el.querySelector('.rule-value').value,
        required: el.querySelector('.rule-required-check').checked
      });
    });

    return rules;
  }

  saveNode() {
    if (!this.currentNode) return;

    let updatedNode = {
      ...this.currentNode,
      name: this.container.querySelector('#nodeName').value,
      type: this.container.querySelector('#nodeType').value,
      requires_approval: this.container.querySelector('#nodeApproval').checked,
      tier: this.container.querySelector('#nodeTier').value,
      token_budget: parseInt(this.container.querySelector('#nodeBudget').value) || 4096,
      agreement_rules: this.getAgreementRules()
    };

    // Type specific saving
    if (updatedNode.type === 'script') {
      updatedNode.script_code = this.container.querySelector('#nodeScript').value;
    } else if (updatedNode.type === 'github') {
      updatedNode.config = {
        repo: this.container.querySelector('#ghRepo') ? this.container.querySelector('#ghRepo').value : '',
        action: this.container.querySelector('#ghAction') ? this.container.querySelector('#ghAction').value : 'clone'
      };
    } else if (updatedNode.type === 'huggingface') {
      updatedNode.config = {
        repo_id: this.container.querySelector('#hfRepo') ? this.container.querySelector('#hfRepo').value : '',
        filename: this.container.querySelector('#hfFile') ? this.container.querySelector('#hfFile').value : ''
      };
    } else if (updatedNode.type === 'memory') {
      updatedNode.memory_config = {
        action: this.container.querySelector('#memoryAction').value,
        tags: this.container.querySelector('#memoryTags').value.split(',').map(t => t.trim()).filter(t => t),
        limit: parseInt(this.container.querySelector('#memoryLimit').value) || 5
      };
      // Backward compatibility
      updatedNode.provider_config = updatedNode.memory_config;
      updatedNode.provider = this.container.querySelector('#nodeProvider').value;
    } else if (updatedNode.type === 'http') {
      updatedNode.provider = 'http'; // Virtual provider
      let headers = {};
      try { headers = JSON.parse(this.container.querySelector('#httpHeaders').value || '{}'); } catch (e) { }

      let body = this.container.querySelector('#httpBody').value;
      try {
        if (body.trim().startsWith('{') || body.trim().startsWith('[')) {
          body = JSON.parse(body);
        }
      } catch (e) { }

      updatedNode.provider_config = {
        method: this.container.querySelector('#httpMethod').value,
        url: this.container.querySelector('#httpUrl').value,
        headers: headers,
        body: body,
        auth_type: this.container.querySelector('#httpAuthType').value
      };
    } else if (updatedNode.type === 'openapi') {
      updatedNode.provider = 'openapi';
      const params = {};
      this.container.querySelectorAll('.openapi-param-input').forEach(input => {
        if (input.value) {
          params[input.dataset.paramName] = input.value;
        }
      });

      updatedNode.provider_config = {
        url: this.container.querySelector('#openapiUrl').value,
        operationId: this.container.querySelector('#openapiOperation').value,
        params: params,
        // Cache ops to re-populate on reload if desired, but might be heavy.
        // For now, relies on user re-clicking Load if they need to change op, 
        // BUT wait - if they close/open editor, ops are lost from DOM.
        // We should persist ops in provider_config so open() can restore them.
        _ops_cache: this.currentNode._openapi_ops
      };

      if (this.currentNode._openapi_ops) {
        const op = this.currentNode._openapi_ops.find(o => o.id === updatedNode.provider_config.operationId);
        if (op) {
          updatedNode.provider_config.method = op.method;
          updatedNode.provider_config.path = op.path;
        }
      }
    } else if (updatedNode.type === 'notion') {
      updatedNode.provider = 'notion';
      let body = this.container.querySelector('#notionBody').value;
      try {
        if (body) body = JSON.parse(body);
      } catch (e) { }

      updatedNode.provider_config = {
        api_key: this.container.querySelector('#notionApiKey').value,
        operation: this.container.querySelector('#notionOperation').value,
        resource_id: this.container.querySelector('#notionResourceId').value,
        body: body
      };
    } else if (updatedNode.type === 'google') {
      updatedNode.provider = 'google';
      let body = this.container.querySelector('#googleBody').value;
      try { if (body) body = JSON.parse(body); } catch (e) { }

      updatedNode.provider_config = {
        service: this.container.querySelector('#googleService').value,
        api_token: this.container.querySelector('#googleToken').value,
        operation: this.container.querySelector('#googleOperation').value,
        params: {
          calendar_id: this.container.querySelector('#googleCalendarId').value
        },
        body: body
      };
    } else if (updatedNode.type === 'github') {
      updatedNode.provider = 'github';
      const mode = this.container.querySelector('#ghMode').value;

      if (mode === 'api') {
        let body = this.container.querySelector('#ghBody').value;
        try { if (body) body = JSON.parse(body); } catch (e) { }

        updatedNode.provider_config = {
          mode: 'api',
          api_token: this.container.querySelector('#ghToken').value,
          operation: this.container.querySelector('#ghOperation').value,
          owner: this.container.querySelector('#ghOwner').value,
          repo: this.container.querySelector('#ghRepoName').value,
          body: body
        };
      } else {
        updatedNode.provider_config = {
          mode: 'cli',
          repo: this.container.querySelector('#ghRepo').value,
          action: this.container.querySelector('#ghAction').value
        };
        // Legacy compat
        updatedNode.config = updatedNode.provider_config;
        updatedNode.provider = this.container.querySelector('#nodeProvider').value;
      }
    } else if (updatedNode.type === 'rag') {
      updatedNode.provider = this.container.querySelector('#nodeProvider').value;
      updatedNode.model = this.container.querySelector('#nodeModel').value;
      updatedNode.persona = this.container.querySelector('#nodePersona').value;
      updatedNode.provider_config = {
        source_path: this.container.querySelector('#ragSource').value,
        chunk_size: parseInt(this.container.querySelector('#ragChunkSize').value) || 1000,
        chunk_overlap: parseInt(this.container.querySelector('#ragOverlap').value) || 200,
        multi_query: this.container.querySelector('#ragMultiQuery').checked,
        top_k: parseInt(this.container.querySelector('#ragTopK').value) || 5
      };
    } else if (updatedNode.type === 'telegram_trigger') {
      updatedNode.provider_config = {
        bot_token: this.container.querySelector('#telegramToken').value,
        chat_id: this.container.querySelector('#telegramChatId').value
      };
    } else if (updatedNode.type === 'discord_trigger') {
      updatedNode.provider_config = {
        webhook_url: this.container.querySelector('#discordWebhookUrl').value,
        bot_token: this.container.querySelector('#discordBotToken').value,
        channel_id: this.container.querySelector('#discordChannelId').value
      };
    } else if (updatedNode.type === 'browser') {
      updatedNode.inputs = {
        url: this.container.querySelector('#browserUrl').value,
        action: this.container.querySelector('#browserAction').value,
        selector: this.container.querySelector('#browserSelector').value
      };
      updatedNode.provider_config = updatedNode.inputs;
    } else if (updatedNode.type === 'shell') {
      updatedNode.inputs = {
        command: this.container.querySelector('#shellCommand').value,
        cwd: this.container.querySelector('#shellCwd').value
      };
      updatedNode.provider_config = updatedNode.inputs;
    } else if (updatedNode.type === 'system') {
      updatedNode.inputs = {
        action: this.container.querySelector('#systemAction').value,
        message: this.container.querySelector('#systemMessage').value
      };
      updatedNode.provider_config = updatedNode.inputs;
    } else if (updatedNode.type === 'a2ui') {
      updatedNode.provider_config = {
        component_type: this.container.querySelector('#a2uiComponentType').value,
        title: this.container.querySelector('#a2uiTitle').value
      };
      updatedNode.inputs = updatedNode.provider_config;
    } else if (['architect', 'critic'].includes(updatedNode.type)) {
      updatedNode.provider = this.container.querySelector('#nodeProvider').value;
      updatedNode.model = this.container.querySelector('#nodeModel').value;
      updatedNode.persona = this.container.querySelector('#nodePersona').value;
      updatedNode.provider_config = {
        goals: this.container.querySelector('#factoryGoals').value
      };
    } else {
      // Standard Agent
      updatedNode.provider = this.container.querySelector('#nodeProvider').value;
      updatedNode.model = this.container.querySelector('#nodeModel').value;
      updatedNode.persona = this.container.querySelector('#nodePersona').value;
      updatedNode.backstory = this.container.querySelector('#nodeBackstory').value;
      updatedNode.internet_access = this.container.querySelector('#nodeInternet').checked;
    }

    this.emit('saveNode', { id: this.currentNode.id, updates: updatedNode });
  }

  // Simple event emitter
  _listeners = {};

  on(event, callback) {
    if (!this._listeners[event]) this._listeners[event] = [];
    this._listeners[event].push(callback);
  }

  emit(event, data) {
    if (this._listeners[event]) {
      this._listeners[event].forEach(cb => cb(data));
    }
  }

  loadSubWorkflows(workflows) {
    const container = document.getElementById('subWorkflowList');
    const emptyState = document.getElementById('noSubWorkflows');
    if (!container) return;

    container.innerHTML = '';

    if (!workflows || workflows.length === 0) {
      if (emptyState) emptyState.style.display = 'block';
      return;
    }

    if (emptyState) emptyState.style.display = 'none';

    workflows.forEach((sw, index) => {
      const item = document.createElement('div');
      item.className = 'sub-workflow-item';
      item.innerHTML = `
        <span class="sw-name" style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1;">📄 ${sw.path || 'Embedded'}</span>
        <button type="button" class="btn-remove-rule" data-index="${index}">×</button>
      `;

      item.querySelector('.btn-remove-rule').addEventListener('click', () => {
        this.currentNode.sub_workflows.splice(index, 1);
        this.loadSubWorkflows(this.currentNode.sub_workflows);
        this.saveNode();
      });

      container.appendChild(item);
    });
  }
}

// Export
window.NodeEditor = NodeEditor;
