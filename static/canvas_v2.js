/**
 * Visual Canvas - Drag-and-drop node editor with SVG connections
 */

window.VisualCanvas = class VisualCanvas {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.canvas = null;
        this.svgLayer = null;
        this.nodes = new Map();
        this.edges = [];
        this.groups = new Map();
        this.selectedNode = null;
        this.selectedGroup = null;
        this.selectedEdge = null;
        this.connecting = null;
        this.scale = 1;
        this.offset = { x: 0, y: 0 };
        this.dragging = null;
        this.dragOffset = { x: 0, y: 0 };
        this._listeners = {};

        this.init();
    }

    init() {
        this.createCanvas();
        this.bindEvents();
    }

    createCanvas() {
        // Main canvas container
        this.canvas = document.createElement('div');
        this.canvas.className = 'visual-canvas';

        // Transform layer for Zoom/Pan
        this.transformLayer = document.createElement('div');
        this.transformLayer.className = 'canvas-transform-layer';
        this.transformLayer.style.width = '20000px';
        this.transformLayer.style.height = '20000px';
        this.transformLayer.style.left = '0px';
        this.transformLayer.style.top = '0px';

        this.transformLayer.innerHTML = `
            <div class="canvas-background-dots"></div>
            <div class="canvas-background-grid"></div>
            <div class="groups-layer" id="groupsLayer" style="width:100%; height:100%;"></div>
            <svg class="connections-layer" id="connectionsLayer" style="width:100%; height:100%; overflow:visible;">
                <defs>
                    <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                        <polygon points="0 0, 10 3.5, 0 7" fill="#64748b" />
                    </marker>
                    <marker id="arrowhead-active" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                        <polygon points="0 0, 10 3.5, 0 7" fill="#6366f1" />
                    </marker>
                </defs>
            </svg>
            <div class="nodes-layer" id="nodesLayer" style="width:100%; height:100%;"></div>
        `;

        this.canvas.appendChild(this.transformLayer);
        this.container.appendChild(this.canvas);

        this.svgLayer = this.canvas.querySelector('#connectionsLayer');
        this.nodesLayer = this.canvas.querySelector('#nodesLayer');
        this.groupsLayer = this.canvas.querySelector('#groupsLayer');

        // Set initial transform
        this.updateTransform();
    }

    updateTransform() {
        this.transformLayer.style.transform = `translate(${this.offset.x}px, ${this.offset.y}px) scale(${this.scale})`;

        // Parallax effect for backgrounds
        const grid = this.transformLayer.querySelector('.canvas-background-grid');
        const dots = this.transformLayer.querySelector('.canvas-background-dots');

        if (grid) {
            // Grid moves at 1x
            grid.style.transform = `translate(${-this.offset.x % 40}px, ${-this.offset.y % 40}px)`;
        }
        if (dots) {
            // Dots move at 0.5x for depth
            dots.style.transform = `translate(${-this.offset.x * 0.5 % 120}px, ${-this.offset.y * 0.5 % 120}px)`;
        }
    }

    // ============ Animation & Visual Effects ============

    autoLayout() {
        const nodes = Array.from(this.nodes.values());
        if (nodes.length === 0) return;

        console.log('Running Auto-Layout...');

        // 1. Build Adjacency List & Calculate In-Degrees
        const adj = new Map();
        const inDegree = new Map();
        nodes.forEach(n => {
            adj.set(n.id, []);
            inDegree.set(n.id, 0);
        });

        this.edges.forEach(e => {
            if (adj.has(e.source) && inDegree.has(e.target)) {
                adj.get(e.source).push(e.target);
                inDegree.set(e.target, inDegree.get(e.target) + 1);
            }
        });

        // 2. Assign Ranks (Longest Path in DAG)
        // We use a topological-like sort, but since there might be cycles (feedback loops),
        // we ignore back-edges or just do a BFS level assignment.
        // Simple approach: BFS from 0-in-degree nodes.
        const ranks = new Map();
        const queue = [];

        nodes.forEach(n => {
            if (inDegree.get(n.id) === 0) {
                ranks.set(n.id, 0);
                queue.push(n.id);
            }
        });

        // Handle case where everyone has incoming edges (pure cycle)
        if (queue.length === 0 && nodes.length > 0) {
            // Pick arbitrary start
            ranks.set(nodes[0].id, 0);
            queue.push(nodes[0].id);
        }

        const visited = new Set();

        while (queue.length > 0) {
            const u = queue.shift();
            // cycle protection
            if (visited.has(u)) continue;
            // Limit rank depth to prevent infinite loops if logic fails
            if ((ranks.get(u) || 0) > 20) continue;

            visited.add(u);

            const neighbors = adj.get(u) || [];
            neighbors.forEach(v => {
                // If v is not visited or we found a longer path, update rank?
                // For layout, we usually want max rank.
                const newRank = (ranks.get(u) || 0) + 1;
                if (newRank > (ranks.get(v) || -1)) {
                    ranks.set(v, newRank);
                    queue.push(v);
                }
            });
        }

        // Fill in anyone missed (islands/cycles)
        nodes.forEach(n => {
            if (!ranks.has(n.id)) ranks.set(n.id, 0);
        });

        // 3. Group by Rank
        const layers = [];
        ranks.forEach((rank, nodeId) => {
            if (!layers[rank]) layers[rank] = [];
            layers[rank].push(nodeId);
        });

        // 4. Assign Coordinates
        const X_SPACING = 350;
        const Y_SPACING = 200;
        const START_X = 50;
        const START_Y = 100;

        layers.forEach((layer, rankIndex) => {
            if (!layer) return;
            // Sort logic could go here to minimize edge crossings (optional)

            layer.forEach((nodeId, nodeIndex) => {
                const node = this.nodes.get(nodeId);
                // Center the layer vertically
                const layerHeight = layer.length * Y_SPACING;
                const yOffset = (window.innerHeight - layerHeight) / 2; // Rough visual center

                node.x = START_X + (rankIndex * X_SPACING);
                node.y = Math.max(50, START_Y + (nodeIndex * Y_SPACING));

                // Update element
                const el = document.getElementById(`node-${nodeId}`);
                if (el) {
                    el.style.left = `${node.x}px`;
                    el.style.top = `${node.y}px`;
                }
            });
        });

        this.renderConnections();
        this.emit('saveRequested'); // Auto-save after layout
    }

    pulseEdge(sourceId, targetId) {
        const edge = this.edges.find(e => e.source === sourceId && e.target === targetId);
        if (!edge) return;

        const path = this.svgLayer.querySelector(`path[data-edge-id="${edge.id}"]`);
        if (!path) return;

        // Create a pulse marker
        const marker = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        marker.setAttribute('r', '4');
        marker.setAttribute('fill', 'var(--primary-color)');
        marker.style.filter = 'blur(1px)';

        const animate = document.createElementNS('http://www.w3.org/2000/svg', 'animateMotion');
        animate.setAttribute('dur', '1.5s');
        animate.setAttribute('repeatCount', '3');
        animate.setAttribute('path', path.getAttribute('d'));

        marker.appendChild(animate);
        this.svgLayer.appendChild(marker);

        setTimeout(() => marker.remove(), 4500);
    }

    // ============ Node Management ============

    addNode(nodeData) {
        const node = {
            id: nodeData.id || this.generateId(),
            name: nodeData.name || 'New Agent',
            type: nodeData.type || 'agent',
            // Correctly calculate default position relative to current viewport transform and scale
            x: nodeData.x !== undefined ? nodeData.x : ((this.container.clientWidth / (2 * this.scale)) - (this.offset.x / this.scale)),
            y: nodeData.y !== undefined ? nodeData.y : ((this.container.clientHeight / (2 * this.scale)) - (this.offset.y / this.scale)),
            persona: nodeData.persona || '',
            provider: nodeData.provider || 'simulation',
            model: nodeData.model || 'default',
            status: 'idle',
            ...nodeData
        };

        this.nodes.set(node.id, node);
        this.renderNode(node);
        return node.id;
    }

    mergeNodes(data, originX = null, originY = null) {
        if (!data || !data.nodes) return;

        // Calculate offset to place new nodes in center of view if no origin provided
        let offsetX = 0;
        let offsetY = 0;

        if (originX === null || originY === null) {
            // Viewport center
            const rect = this.container.getBoundingClientRect();
            const centerX = (rect.width / 2 - this.offset.x) / this.scale;
            const centerY = (rect.height / 2 - this.offset.y) / this.scale;

            // Assume generated nodes start at 0,0. Shift them to center.
            offsetX = centerX;
            offsetY = centerY;
        } else {
            offsetX = originX;
            offsetY = originY;
        }

        const idMap = {}; // Map old IDs to new IDs

        // 1. Add Nodes
        Object.entries(data.nodes).forEach(([key, node]) => {
            const newId = crypto.randomUUID();
            idMap[key] = newId;
            idMap[node.id] = newId; // Handle both key-based and id-based refs

            this.addNode({
                ...node,
                id: newId,
                x: (node.x || 0) + offsetX,
                y: (node.y || 0) + offsetY
            });
        });

        // 2. Add Edges
        if (data.edges) {
            data.edges.forEach(edge => {
                const sourceId = idMap[edge.source] || edge.source;
                const targetId = idMap[edge.target] || edge.target;

                // Only add if we resolved the IDs (or they exist already)
                if (this.nodes.has(sourceId) && this.nodes.has(targetId)) {
                    this.addEdge(sourceId, targetId, edge.label);
                }
            });
        }
    }

    removeNode(nodeId) {
        this.nodes.delete(nodeId);
        this.edges = this.edges.filter(e => e.source !== nodeId && e.target !== nodeId);

        const el = document.getElementById(`node-${nodeId}`);
        if (el) el.remove();

        this.renderConnections();
    }

    renderNode(node) {
        const el = document.createElement('div');
        el.className = `workflow-node ${node.type} status-${node.status}`;
        el.id = `node-${node.id}`;
        el.style.left = `${node.x}px`;
        el.style.top = `${node.y}px`;

        el.innerHTML = `
      ${node.sub_workflow_path ? '<div class="workflow-attached-indicator" title="Sub-Workflow Attached">🔗</div>' : ''}
      ${node.return_event_bubble ? '<div class="workflow-bubbling-indicator" title="Event Bubbling Enabled">📢</div>' : ''}
      <div class="node-header">
        <span class="node-icon">${this.getNodeIcon(node.type)}</span>
        <span class="node-name">${node.name}</span>
        <span class="node-status">${node.status}</span>
      </div>
      <div class="node-body">
        <div class="node-provider">
          <span class="provider-badge">${node.provider}</span>
          <span class="model-name">${node.model}</span>
        </div>
      </div>
      <div class="node-ports">
        ${node.type === 'reroute' ?
                '<div class="port port-in reroute-port" data-node="' + node.id + '" data-port="in"></div>' :
                '<div class="port port-in" data-node="' + node.id + '" data-port="in"></div><div class="port port-out" data-node="' + node.id + '" data-port="out"></div>'
            }
      </div>
    `;

        this.nodesLayer.appendChild(el);
        this.bindNodeEvents(el, node);
    }

    getNodeIcon(type) {
        const icons = {
            agent: '🤖',
            auditor: '⚖️',
            input: '📥',
            output: '📤',
            router: '🔀',
            character: '🎭',
            director: '🎬',
            optimizer: '⚙️',
            script: '🐍',
            reroute: '🔴',
            memory: '🧠',
            github: '🐙',
            rag: '📚',
            telegram_trigger: '📡',
            discord_trigger: '👾',
            huggingface: '🤗'
        };
        return icons[type] || '📦';
    }

    updateNode(nodeId, updates) {
        const node = this.nodes.get(nodeId);
        if (!node) return;

        const oldStatus = node.status;
        Object.assign(node, updates);

        const el = document.getElementById(`node-${nodeId}`);
        if (el) {
            el.className = `workflow-node ${node.type} status-${node.status}`;
            el.querySelector('.node-name').textContent = node.name;
            el.querySelector('.node-status').textContent = node.display_status || node.status;
            el.querySelector('.provider-badge').textContent = node.provider;
            el.querySelector('.model-name').textContent = node.model;

            // Update Attachment Indicator
            let indicator = el.querySelector('.workflow-attached-indicator');
            if (node.sub_workflow_path && !indicator) {
                indicator = document.createElement('div');
                indicator.className = 'workflow-attached-indicator';
                indicator.title = 'Sub-Workflow Attached';
                indicator.textContent = '🔗';
                el.insertBefore(indicator, el.firstChild);
            } else if (!node.sub_workflow_path && indicator) {
                indicator.remove();
            }

            // Update Bubbling Indicator
            let bubble = el.querySelector('.workflow-bubbling-indicator');
            if (node.return_event_bubble && !bubble) {
                bubble = document.createElement('div');
                bubble.className = 'workflow-bubbling-indicator';
                bubble.title = 'Event Bubbling Enabled';
                bubble.textContent = '📢';
                el.insertBefore(bubble, el.firstChild);
            } else if (!node.return_event_bubble && bubble) {
                bubble.remove();
            }

            // Trigger Animation if node just started running
            if (updates.status === 'running' && oldStatus !== 'running') {
                this.animateThoughts(nodeId);
            }
        }

        // If status changed, we may need to update connection animations
        if (updates.status && updates.status !== oldStatus) {
            this.renderConnections();
        }

        this.emit('node:update', node);
    }

    animateThoughts(nodeId) {
        // Find all connected edges
        const targetEdges = this.edges.filter(e => e.target === nodeId);
        targetEdges.forEach(edge => {
            this.pulseEdge(edge.source, edge.target);
        });
    }

    removeNode(nodeId) {
        this.nodes.delete(nodeId);
        this.edges = this.edges.filter(e => e.source !== nodeId && e.target !== nodeId);

        const el = document.getElementById(`node-${nodeId}`);
        if (el) el.remove();

        this.renderConnections();
    }

    // ============ Group Management ============

    addGroup(groupData) {
        const group = {
            id: groupData.id || this.generateId(),
            name: groupData.name || 'New Group',
            x: groupData.x || 100,
            y: groupData.y || 100,
            width: groupData.width || 400,
            height: groupData.height || 300,
            color: groupData.color || 'var(--accent-primary)',
            ...groupData
        };

        this.groups.set(group.id, group);
        this.renderGroup(group);
        return group.id;
    }

    renderGroup(group) {
        const el = document.createElement('div');
        el.className = 'workflow-group';
        el.id = `group-${group.id}`;
        el.style.left = `${group.x}px`;
        el.style.top = `${group.y}px`;
        el.style.width = `${group.width}px`;
        el.style.height = `${group.height}px`;
        el.style.borderColor = group.color;

        el.innerHTML = `
            <div class="group-header" style="color: ${group.color}">${group.name}</div>
        `;

        this.groupsLayer.appendChild(el);
        this.bindGroupEvents(el, group);
    }

    bindGroupEvents(el, group) {
        el.style.pointerEvents = 'auto'; // Allow interaction

        el.addEventListener('mousedown', (e) => {
            if (e.target !== el) return;
            e.stopPropagation();

            this.draggingGroup = group;
            const mouseCanvasX = (e.clientX - this.offset.x) / this.scale;
            const mouseCanvasY = (e.clientY - this.offset.y) / this.scale;

            this.dragOffset = {
                x: mouseCanvasX - group.x,
                y: mouseCanvasY - group.y
            };

            // Find nodes inside this group to drag them too
            this.nodesInGroup = Array.from(this.nodes.values()).filter(node => {
                return node.x >= group.x && node.x <= group.x + group.width &&
                    node.y >= group.y && node.y <= group.y + group.height;
            });

            this.nodeOffsets = this.nodesInGroup.map(node => ({
                id: node.id,
                dx: node.x - group.x,
                dy: node.y - group.y
            }));

            el.classList.add('dragging');
            this.selectGroup(group.id);
        });

        document.addEventListener('mousemove', (e) => {
            if (this.draggingGroup && this.draggingGroup.id === group.id) {
                const currentCanvasX = (e.clientX - this.offset.x) / this.scale;
                const currentCanvasY = (e.clientY - this.offset.y) / this.scale;

                group.x = currentCanvasX - this.dragOffset.x;
                group.y = currentCanvasY - this.dragOffset.y;

                el.style.left = `${group.x}px`;
                el.style.top = `${group.y}px`;

                // Move nodes in group
                this.nodeOffsets.forEach(off => {
                    const node = this.nodes.get(off.id);
                    if (node) {
                        node.x = group.x + off.dx;
                        node.y = group.y + off.dy;
                        const nodeEl = document.getElementById(`node-${node.id}`);
                        if (nodeEl) {
                            nodeEl.style.left = `${node.x}px`;
                            nodeEl.style.top = `${node.y}px`;
                        }
                    }
                });
                this.renderConnections();
            }
        });

        document.addEventListener('mouseup', () => {
            if (this.draggingGroup) {
                const el = document.getElementById(`group-${this.draggingGroup.id}`);
                if (el) el.classList.remove('dragging');
                this.draggingGroup = null;
            }
        });
    }

    selectGroup(groupId) {
        if (this.selectedGroup) {
            const el = document.getElementById(`group-${this.selectedGroup}`);
            if (el) el.classList.remove('selected');
        }
        this.selectedGroup = groupId;
        const el = document.getElementById(`group-${groupId}`);
        if (el) el.classList.add('selected');
    }

    updateGroup(groupId, updates) {
        const group = this.groups.get(groupId);
        if (!group) return;
        Object.assign(group, updates);
        const el = document.getElementById(`group-${groupId}`);
        if (el) {
            el.style.left = `${group.x}px`;
            el.style.top = `${group.y}px`;
            el.style.width = `${group.width}px`;
            el.style.height = `${group.height}px`;
            el.querySelector('.group-header').textContent = group.name;
            el.querySelector('.group-header').style.color = group.color;
            el.style.borderColor = group.color;
        }
    }

    // ============ Edge Management ============

    addEdge(sourceId, targetId, label = '', data = {}) {
        if (sourceId === targetId) return;

        // Check if edge already exists
        const exists = this.edges.some(e => e.source === sourceId && e.target === targetId);
        if (exists) return;

        const edge = {
            id: this.generateId(),
            source: sourceId,
            target: targetId,
            label,
            ...data // Preserve feedback, condition, etc.
        };

        this.edges.push(edge);
        this.renderConnections();
        return edge.id;
    }

    removeEdge(edgeId) {
        this.edges = this.edges.filter(e => e.id !== edgeId);
        this.renderConnections();
    }

    updateEdge(edgeId, updates) {
        const edge = this.edges.find(e => e.id === edgeId);
        if (edge) {
            Object.assign(edge, updates);
            this.renderConnections();
        }
    }

    renderConnections() {
        if (this.renderRequested) return;
        this.renderRequested = true;

        requestAnimationFrame(() => {
            this._doRenderConnections();
            this.renderRequested = false;
        });
    }

    _doRenderConnections() {
        this.svgLayer.innerHTML = '';

        // Ensure SVG layer covers the entire possible canvas bounds
        // (Handled by CSS width/height: 100% of parent 20000px layer)

        // Count edges per target to support spreading
        const targetCounts = {};
        this.edges.forEach(e => {
            targetCounts[e.target] = (targetCounts[e.target] || 0) + 1;
        });

        // Track used index per target for offsetting
        const targetIndexMap = {};

        for (const edge of this.edges) {
            const sourceNode = this.nodes.get(edge.source);
            const targetNode = this.nodes.get(edge.target);

            if (!sourceNode || !targetNode || (sourceNode.type === 'reroute' && targetNode.type === 'reroute')) continue;

            const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');

            // Calculate spreading offset for target
            const totalAtTarget = targetCounts[edge.target] || 1;
            const idxAtTarget = targetIndexMap[edge.target] || 0;
            targetIndexMap[edge.target] = idxAtTarget + 1;

            // Offset Y slightly if multiple connections hit the same target
            // Spread factor: spacing 15px apart, centered around middle
            const spreadOffset = (totalAtTarget > 1) ? (idxAtTarget - (totalAtTarget - 1) / 2) * 15 : 0;

            const sourceX = sourceNode.x + 220;
            const sourceY = sourceNode.y + 40;
            const targetX = targetNode.x;
            const targetY = targetNode.y + 40 + spreadOffset;

            // 1. connection path
            const path = this.createConnectionPath(sourceNode, targetNode, edge, spreadOffset);
            group.appendChild(path);

            // 2. Source Bubble (Output)
            const srcBubble = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            srcBubble.setAttribute('cx', sourceX);
            srcBubble.setAttribute('cy', sourceY);
            srcBubble.setAttribute('r', '5');
            srcBubble.setAttribute('fill', '#10b981'); // Green
            srcBubble.setAttribute('class', 'connection-port');
            group.appendChild(srcBubble);

            // 3. Target Bubble (Input)
            const tgtBubble = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            tgtBubble.setAttribute('cx', targetX);
            tgtBubble.setAttribute('cy', targetY);
            tgtBubble.setAttribute('r', '5');
            tgtBubble.setAttribute('fill', '#ef4444'); // Red
            tgtBubble.setAttribute('class', 'connection-port');
            group.appendChild(tgtBubble);

            // 4. Label if exists
            if (edge.label) {
                const midX = (sourceX + targetX) / 2;
                const midY = (sourceY + targetY) / 2 - 10;
                const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                text.setAttribute('x', midX);
                text.setAttribute('y', midY);
                text.setAttribute('class', 'connection-label');
                text.setAttribute('text-anchor', 'middle');
                text.textContent = edge.label;
                group.appendChild(text);
            }

            this.svgLayer.appendChild(group);
        }
    }

    createConnectionPath(source, target, edge, spreadOffset = 0) {
        const sourceX = source.x + 220; // Match new node width
        const sourceY = source.y + 40;  // Middle height
        const targetX = target.x;       // Left side of node
        const targetY = target.y + 40 + spreadOffset;

        // Enhanced "ComfyUI-style" Spline
        const dist = Math.abs(targetX - sourceX);
        const horizontalVelocity = Math.min(dist * 0.6, 200); // Caps the "bend"

        const cp1x = sourceX + horizontalVelocity;
        const cp1y = sourceY;

        const cp2x = targetX - horizontalVelocity;
        const cp2y = targetY;

        const d = `M ${sourceX} ${sourceY} C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${targetX} ${targetY}`;

        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', d);

        let classes = ['connection-line'];
        if (source.status === 'running' || target.status === 'running') {
            classes.push('active');
            classes.push('animated');
        }
        if (edge.feedback) classes.push('feedback');

        if (this.selectedEdge && this.selectedEdge.id === edge.id) {
            classes.push('selected');
        }

        path.setAttribute('class', classes.join(' '));
        path.setAttribute('data-edge-id', edge.id);
        path.setAttribute('marker-end', target.status === 'running' ? 'url(#arrowhead-active)' : 'url(#arrowhead)');

        // Add click handler for edge configuration
        path.addEventListener('click', (e) => {
            e.stopPropagation();
            this.selectEdge(edge.id);
        });

        return path;
    }

    // ============ Event Handling ============

    bindEvents() {
        // Fit View Button
        const fitBtn = document.getElementById('fitViewBtn');
        if (fitBtn) {
            fitBtn.addEventListener('click', () => this.fitView());
        }

        // ============ Zoom (Wheel) ============
        this.container.addEventListener('wheel', (e) => {
            e.preventDefault();
            // Use e.deltaY directly for smooth zooming (approx 0.001 sensitivity)
            // Clamp delta to prevent massive jumps on fast scrolls
            const sensitivity = 0.001;
            const delta = -e.deltaY * sensitivity;

            // Limit zoom range
            const newScale = Math.min(Math.max(0.1, this.scale + delta), 3.0);

            // Zoom towards mouse pointer
            // 1. Get mouse pos relative to container
            const rect = this.container.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const mouseY = e.clientY - rect.top;

            // 2. Calculate offset adjust to keep mouse fixed
            // (mouseX - offsetX) / scale = canvasX
            const canvasX = (mouseX - this.offset.x) / this.scale;
            const canvasY = (mouseY - this.offset.y) / this.scale;

            // 3. Update scale
            this.scale = newScale;

            // 4. Recalculate offset
            // mouseX = canvasX * newScale + newOffsetX
            this.offset.x = mouseX - canvasX * this.scale;
            this.offset.y = mouseY - canvasY * this.scale;

            this.updateTransform();
        });

        // ============ Pan (Drag Background) ============
        // ============ Pan (Drag Background) ============
        this.container.addEventListener('mousedown', (e) => {
            // Only pan if clicking on background
            // We must include nodesLayer because it sits on top of everything
            if (e.target === this.canvas ||
                e.target === this.transformLayer ||
                e.target === this.nodesLayer ||
                e.target.classList.contains('canvas-background-grid')) {

                this.isPanning = true;
                this.hasMoved = false; // Track if we actually dragged
                this.startPan = { x: e.clientX, y: e.clientY };
                this.startOffset = { ...this.offset };
                this.container.style.cursor = 'grabbing';
            }
        });

        window.addEventListener('mousemove', (e) => {
            if (this.isPanning) {
                const dx = e.clientX - this.startPan.x;
                const dy = e.clientY - this.startPan.y;

                // Only consider it a move if significant (jitter threshold)
                if (Math.abs(dx) > 2 || Math.abs(dy) > 2) {
                    this.hasMoved = true;
                }

                this.offset.x = this.startOffset.x + dx;
                this.offset.y = this.startOffset.y + dy;

                requestAnimationFrame(() => this.updateTransform());
            } else if (this.connecting) {
                this.updateTempConnection(e);
            }
        });

        window.addEventListener('mouseup', () => {
            if (this.isPanning) {
                this.isPanning = false;
                this.container.style.cursor = 'default';
                // Delay clearing hasMoved slightly so click event can see it
                setTimeout(() => { this.hasMoved = false; }, 50);
            }
            if (this.connecting) {
                this.cancelConnection();
            }
        });

        // ============ Selection ============
        // Click to deselect
        this.canvas.addEventListener('click', (e) => {
            // If we just finished panning, don't treat as click
            if (this.hasMoved) {
                e.stopPropagation();
                return;
            }

            if (e.target === this.canvas || e.target === this.nodesLayer || e.target === this.transformLayer) {
                this.deselectAll();
            }
        });

        // Keyboard Shortcuts
        window.addEventListener('keydown', (e) => this.handleKeyDown(e));

        // Global Context Menu (Background)
        this.canvas.addEventListener('contextmenu', (e) => {
            if (e.target === this.canvas || e.target === this.nodesLayer || e.target === this.transformLayer || e.target.classList.contains('canvas-background-grid')) {
                this.showGlobalContextMenu(e);
            }
        });
    }

    handleKeyDown(e) {
        if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;

        const step = 10;
        switch (e.key) {
            case 'Delete':
            case 'Backspace':
                if (this.selectedNode) {
                    if (confirm(`Remove selected node?`)) {
                        this.removeNode(this.selectedNode);
                        this.deselectAll();
                    }
                } else if (this.selectedEdge) {
                    if (confirm(`Remove selected connection?`)) {
                        this.removeEdge(this.selectedEdge.id);
                        this.deselectAll();
                    }
                }
                break;
            case 'ArrowLeft': if (this.selectedNode) this.nudgeNode(this.selectedNode, -step, 0); break;
            case 'ArrowRight': if (this.selectedNode) this.nudgeNode(this.selectedNode, step, 0); break;
            case 'ArrowUp': if (this.selectedNode) this.nudgeNode(this.selectedNode, 0, -step); break;
            case 'ArrowDown': if (this.selectedNode) this.nudgeNode(this.selectedNode, 0, step); break;
            case 's':
                if (e.ctrlKey || e.metaKey) {
                    e.preventDefault();
                    this.emit('saveRequested');
                }
                break;
            case 'Enter':
                if (e.ctrlKey || e.metaKey) {
                    e.preventDefault();
                    this.emit('runRequested');
                }
                break;
            case ' ':
                if (!['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) {
                    e.preventDefault();
                    this.showSearchMenu();
                }
                break;
        }
    }

    nudgeNode(nodeId, dx, dy) {
        const node = this.nodes.get(nodeId);
        if (node) {
            node.x += dx;
            node.y += dy;
            const el = document.getElementById(`node-${nodeId}`);
            if (el) {
                el.style.left = `${node.x}px`;
                el.style.top = `${node.y}px`;
            }
            this.renderConnections();
        }
    }

    bindNodeEvents(el, node) {
        // Drag handling
        el.addEventListener('mousedown', (e) => {
            if (e.target.classList.contains('port')) return;
            e.stopPropagation(); // Prevent panning when dragging node

            this.dragging = node;
            // Calculate offset logic needs to account for scale
            // The existing node.x/y are in canvas space
            // e.clientX is in screen space

            // We store the initial mouse diff in screen space, scaled to canvas space
            const mouseCanvasX = (e.clientX - this.offset.x) / this.scale;
            const mouseCanvasY = (e.clientY - this.offset.y) / this.scale;

            this.dragOffset = {
                x: mouseCanvasX - node.x,
                y: mouseCanvasY - node.y
            };

            el.classList.add('dragging');
            e.preventDefault();
        });

        // Click on Reroute node handle (entire node is a port)
        if (node.type === 'reroute') {
            el.addEventListener('mousedown', (e) => {
                if (e.button === 0 && !e.shiftKey) {
                    this.startConnection(node.id);
                }
            });
        }

        document.addEventListener('mousemove', (e) => {
            if (this.dragging && this.dragging.id === node.id) {
                // Convert current mouse to canvas space
                const currentCanvasX = (e.clientX - this.offset.x) / this.scale;
                const currentCanvasY = (e.clientY - this.offset.y) / this.scale;

                node.x = currentCanvasX - this.dragOffset.x;
                node.y = currentCanvasY - this.dragOffset.y;

                el.style.left = `${node.x}px`;
                el.style.top = `${node.y}px`;
                this.renderConnections();
            }
        });

        document.addEventListener('mouseup', () => {
            if (this.dragging) {
                const el = document.getElementById(`node-${this.dragging.id}`);
                if (el) el.classList.remove('dragging');
                this.dragging = null;
            }
        });

        // Selection
        el.addEventListener('click', (e) => {
            e.stopPropagation();
            this.selectNode(node.id);
        });

        // Port connections
        const ports = el.querySelectorAll('.port');
        ports.forEach(port => {
            port.addEventListener('mousedown', (e) => {
                e.stopPropagation();
                if (port.dataset.port === 'out') {
                    this.startConnection(node.id);
                }
            });

            port.addEventListener('mouseup', (e) => {
                e.stopPropagation();
                if (this.connecting && port.dataset.port === 'in') {
                    this.completeConnection(node.id);
                }
            });
        });

        // Double-click to edit
        el.addEventListener('dblclick', () => {
            this.openNodeEditor(node.id);
        });

        // Context Menu
        el.addEventListener('contextmenu', (e) => {
            this.showContextMenu(e, node);
        });
    }

    // ============ Selection ============

    selectNode(nodeId) {
        this.deselectAll();
        this.selectedNode = nodeId;

        const el = document.getElementById(`node-${nodeId}`);
        if (el) el.classList.add('selected');

        // Emit selection event
        this.emit('nodeSelected', this.nodes.get(nodeId));
    }

    deselectAll() {
        if (this.selectedNode) {
            const el = document.getElementById(`node-${this.selectedNode}`);
            if (el) el.classList.remove('selected');
        }
        if (this.selectedEdge) {
            this.selectedEdge = null;
            this.renderConnections();
        }
        this.selectedNode = null;
        this.emit('nodeDeselected');
    }

    selectEdge(edgeId) {
        this.deselectAll();
        this.selectedEdge = this.edges.find(e => e.id === edgeId);
        this.renderConnections();
        if (this.selectedEdge) {
            this.emit('edgeSelected', this.selectedEdge);
        }
    }

    // ============ Connection Drawing ============

    startConnection(sourceId) {
        this.connecting = { source: sourceId };
        this.canvas.classList.add('connecting');
    }

    async completeConnection(targetId) {
        if (this.connecting) {
            const sourceId = this.connecting.source;
            if (sourceId === targetId) {
                this.cancelConnection();
                return;
            }

            // Check if exists
            const exists = this.edges.some(e => e.source === sourceId && e.target === targetId);
            if (exists) {
                this.cancelConnection();
                return;
            }

            // Prompt for intent
            const reason = prompt("Why are you connecting these agents? (Optional for intelligent suggestions)");
            let label = '';

            if (reason) {
                try {
                    const sourceNode = this.nodes.get(sourceId);
                    const targetNode = this.nodes.get(targetId);

                    // Show loading cursor
                    document.body.style.cursor = 'wait';

                    const response = await fetch('/api/connection/suggest', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            source_persona: sourceNode.persona || '',
                            target_persona: targetNode.persona || '',
                            user_intent: reason
                        })
                    });

                    const data = await response.json();
                    label = data.label || reason;

                    // Note: In a full implementation, we'd also auto-add the agreement rule to sourceNode
                    if (data.rule_name && this.emit) {
                        const rule = {
                            name: data.rule_name,
                            type: data.rule_type,
                            value: data.rule_value,
                            required: true
                        };
                        // Emit event for the NodeEditor or main app to handle adding the rule if desired
                        // For now, we just stick to the label for the edge
                    }

                } catch (error) {
                    console.error('Connection suggestion failed:', error);
                    label = reason; // Fallback to user input
                } finally {
                    document.body.style.cursor = 'default';
                }
            }

            this.addEdge(sourceId, targetId, label);
            this.cancelConnection();
        }
    }

    cancelConnection() {
        this.connecting = null;
        this.canvas.classList.remove('connecting');
        // Remove temp line if exists
        const tempLine = this.svgLayer.querySelector('.temp-connection');
        if (tempLine) tempLine.remove();
    }

    updateTempConnection(e) {
        const source = this.nodes.get(this.connecting.source);
        if (!source) return;

        let tempLine = this.svgLayer.querySelector('.temp-connection');
        if (!tempLine) {
            tempLine = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            tempLine.setAttribute('class', 'connection-line temp-connection');
            this.svgLayer.appendChild(tempLine);
        }

        // Calculate source pos in canvas space
        const sourceX = source.x + 220;
        const sourceY = source.y + 40;

        // Calculate target (mouse) in canvas space
        const rect = this.canvas.getBoundingClientRect();

        const targetX = (e.clientX - rect.left - this.offset.x) / this.scale;
        const targetY = (e.clientY - rect.top - this.offset.y) / this.scale;

        const midX = (sourceX + targetX) / 2;
        const d = `M ${sourceX} ${sourceY} C ${midX} ${sourceY}, ${midX} ${targetY}, ${targetX} ${targetY}`;
        tempLine.setAttribute('d', d);
    }

    // ============ Node Editor ============

    openNodeEditor(nodeId) {
        const node = this.nodes.get(nodeId);
        if (!node) return;

        this.emit('openEditor', node);
    }

    // ============ Serialization ============

    toJSON() {
        return {
            nodes: Object.fromEntries(this.nodes),
            edges: this.edges,
            groups: Object.fromEntries(this.groups)
        };
    }

    fromJSON(data) {
        this.clear();
        if (!data || !data.nodes) return;

        if (data.groups) {
            for (const [id, group] of Object.entries(data.groups)) {
                this.addGroup({ ...group, id });
            }
        }

        // Migration logic: calculate average offset if many nodes are far off-screen
        let totalX = 0, totalY = 0, count = 0;
        const nodesData = Object.values(data.nodes);

        nodesData.forEach(node => {
            if (node.x !== undefined && node.y !== undefined) {
                totalX += node.x;
                totalY += node.y;
                count++;
            }
        });

        const avgX = count > 0 ? totalX / count : 0;
        const avgY = count > 0 ? totalY / count : 0;

        // If average position is extremely far (buggy versions often spawned at -50000 range)
        const needsResettlement = Math.abs(avgX) > 10000 || Math.abs(avgY) > 10000;

        for (const [id, node] of Object.entries(data.nodes)) {
            let x = node.x;
            let y = node.y;

            // Basic migration: ensure x and y are numbers and handle missing values
            if (typeof x !== 'number') x = 0;
            if (typeof y !== 'number') y = 0;

            if (needsResettlement) {
                // Shift nodes back toward center if they are in the "lost" zone
                if (x < -10000) x += 50000;
                if (y < -10000) y += 50000;
            }

            const sanitizedNode = { ...node, id, x, y, status: 'idle' };
            this.addNode(sanitizedNode);
        }

        if (data.edges) {
            for (const edge of data.edges) {
                const { source, target, label, id, ...rest } = edge;
                this.addEdge(source, target, label, rest);
            }
        }

        // Delay fitView slightly to ensure container dimensions are ready
        setTimeout(() => this.fitView(), 100);
    }

    clear() {
        this.nodes.clear();
        this.edges = [];
        this.nodesLayer.innerHTML = '';
        this.svgLayer.innerHTML = '';
    }

    // ============ Context Menu ============

    showContextMenu(e, node) {
        e.preventDefault();

        // Remove existing context menu if any
        this.closeContextMenu();

        const menu = document.createElement('div');
        menu.className = 'context-menu';

        let x = e.clientX;
        let y = e.clientY;

        // Menu will be positioned after items are rendered to get accurate size
        menu.style.left = '-1000px';
        menu.style.top = '-1000px';
        document.body.appendChild(menu);


        // Menu Items
        const items = [
            {
                label: 'Attach Workflow...',
                icon: '🔗',
                action: () => this.emit('attachWorkflowRequested', node)
            },
            {
                label: 'Import & Connect Workflow...',
                icon: '📥',
                action: () => this.emit('mergeWorkflowRequested', node)
            },
            {
                label: node.return_event_bubble ? 'Disable Event Bubbling' : 'Enable Event Bubbling',
                icon: node.return_event_bubble ? '🔇' : '📢',
                action: () => {
                    const newValue = !node.return_event_bubble;
                    this.updateNode(node.id, { return_event_bubble: newValue });
                    this.emit('nodeUpdated', this.nodes.get(node.id)); // Notify backend/storage
                }
            },
            {
                label: 'Auto-Repair Node...',
                icon: '🔧',
                action: () => {
                    this.updateNode(node.id, { status: 'idle', error: null });
                    this.emit('repairRequested', node);
                }
            },
            {
                label: 'Upgrade to Premium Tier',
                icon: '💎',
                action: () => {
                    this.updateNode(node.id, { tier: 'paid' });
                    this.emit('nodeUpdated', this.nodes.get(node.id));
                }
            },
            { divider: true },
            {
                label: 'Delete Node',
                icon: '🗑️',
                danger: true,
                action: () => {
                    if (confirm(`Delete node "${node.name}"?`)) {
                        this.removeNode(node.id);
                    }
                }
            }
        ];

        this.renderMenuItems(menu, items);

        // Dynamic boundary checking
        const menuRect = menu.getBoundingClientRect();
        if (x + menuRect.width > window.innerWidth) x -= menuRect.width;
        if (y + menuRect.height > window.innerHeight) y -= menuRect.height;

        menu.style.left = `${Math.max(10, x)}px`;
        menu.style.top = `${Math.max(10, y)}px`;

        this.ctxMenu = menu;

        // Prevent context menu clicks from bubbling to canvas
        menu.addEventListener('mousedown', (ev) => ev.stopPropagation());
        menu.addEventListener('click', (ev) => ev.stopPropagation());

        // Close on click outside
        const closeHandler = (ev) => {
            if (!menu.contains(ev.target)) {
                this.closeContextMenu();
                document.removeEventListener('mousedown', closeHandler);
            }
        };
        document.addEventListener('mousedown', closeHandler);
    }

    // ============ Global Context Menu ============

    showGlobalContextMenu(e) {
        e.preventDefault();
        this.closeContextMenu();

        const menu = document.createElement('div');
        menu.className = 'context-menu global-menu';

        let x = e.clientX;
        let y = e.clientY;
        if (x + 220 > window.innerWidth) x -= 220;
        if (y + 300 > window.innerHeight) y -= 300;

        menu.style.left = `${x}px`;
        menu.style.top = `${y}px`;

        const rect = this.container.getBoundingClientRect();
        const canvasX = (e.clientX - rect.left - this.offset.x) / this.scale;
        const canvasY = (e.clientY - rect.top - this.offset.y) / this.scale;

        const items = [
            {
                label: 'Add Agent',
                icon: '🤖',
                action: () => this.addNode({ type: 'agent', x: canvasX, y: canvasY })
            },
            {
                label: 'Add CLI Tool',
                icon: '🐚',
                action: () => this.showCLISelectorMenu(e, canvasX, canvasY)
            },
            {
                label: 'Add Auditor',
                icon: '⚖️',
                action: () => this.addNode({ type: 'auditor', x: canvasX, y: canvasY })
            },
            {
                label: 'Add Group',
                icon: '📦',
                action: () => this.addGroup({ x: canvasX, y: canvasY })
            },
            { divider: true },
            {
                label: 'Fit View',
                icon: '🔍',
                action: () => this.fitView()
            },
            {
                label: 'Clear Canvas',
                icon: '🗑️',
                danger: true,
                action: () => {
                    if (confirm('Clear entire canvas?')) this.clear();
                }
            }
        ];

        this.renderMenuItems(menu, items);
        document.body.appendChild(menu);
        this.ctxMenu = menu;

        const closeHandler = (ev) => {
            if (!menu.contains(ev.target)) {
                this.closeContextMenu();
                document.removeEventListener('mousedown', closeHandler);
            }
        };
        document.addEventListener('mousedown', closeHandler);
    }

    showCLISelectorMenu(e, x, y) {
        this.closeContextMenu();
        const menu = document.createElement('div');
        menu.className = 'context-menu cli-menu';
        menu.style.left = `${e.clientX}px`;
        menu.style.top = `${e.clientY}px`;

        const items = [
            { label: 'Aider (Pair Programming)', icon: '🛠️', action: () => this.addNode({ type: 'script', name: 'Aider', icon: '🛠️', x, y, provider: 'cli', model: 'aider' }) },
            { label: 'Claude Code CLI', icon: '🐚', action: () => this.addNode({ type: 'script', name: 'Claude Code', icon: '🐚', x, y, provider: 'cli', model: 'claude-code' }) },
            { label: 'Ollama CLI', icon: '🦙', action: () => this.addNode({ type: 'agent', name: 'Ollama Agent', icon: '🦙', x, y, provider: 'ollama' }) },
            { label: 'Fabric (Human Augment)', icon: '🧶', action: () => this.addNode({ type: 'script', name: 'Fabric Context', icon: '🧶', x, y, provider: 'cli', model: 'fabric' }) }
        ];

        this.renderMenuItems(menu, items);
        document.body.appendChild(menu);
        this.ctxMenu = menu;
    }

    renderMenuItems(menu, items) {
        items.forEach(item => {
            if (item.divider) {
                const div = document.createElement('div');
                div.className = 'context-menu-divider';
                menu.appendChild(div);
                return;
            }

            const div = document.createElement('div');
            div.className = `context-menu-item ${item.danger ? 'danger' : ''}`;
            div.innerHTML = `<span class="icon">${item.icon}</span> ${item.label}`;
            div.addEventListener('click', (ev) => {
                ev.stopPropagation(); // Prevent canvas background click
                item.action();
                this.closeContextMenu();
            });
            menu.appendChild(div);
        });
    }

    closeContextMenu() {
        if (this.ctxMenu) {
            this.ctxMenu.remove();
            this.ctxMenu = null;
        }
    }

    tidyLayout() {
        this.autoLayout();
        this.fitToContainer();
    }

    // ============ Global View Control ============
    fitView() {
        this.fitToContainer();
    }

    fitToContainer() {
        const nodes = Array.from(this.nodes.values());
        if (nodes.length === 0) {
            this.scale = 1;
            this.offset = { x: 0, y: 0 };
            this.updateTransform();
            return;
        }

        // Calculate bounds
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        nodes.forEach(n => {
            minX = Math.min(minX, n.x);
            minY = Math.min(minY, n.y);
            maxX = Math.max(maxX, n.x + 240);
            maxY = Math.max(maxY, n.y + 120);
        });

        const padding = 100;
        const width = maxX - minX;
        const height = maxY - minY;

        const containerWidth = this.container.clientWidth;
        const containerHeight = this.container.clientHeight;

        if (containerWidth === 0 || containerHeight === 0) return;

        const scaleX = (containerWidth - padding * 2) / width;
        const scaleY = (containerHeight - padding * 2) / height;
        let newScale = Math.min(scaleX, scaleY);

        // Clamp scale logic
        newScale = Math.min(Math.max(newScale, 0.4), 1.2);

        this.scale = newScale;

        // Center the bounding box in the container
        this.offset.x = (containerWidth - width * newScale) / 2 - minX * newScale;
        this.offset.y = (containerHeight - height * newScale) / 2 - minY * newScale;

        this.updateTransform();
    }

    // ============ Clipboard ============
    copySelected() {
        return Math.random().toString(36).substr(2, 8);
    }

    // ============ Utilities ============

    generateId() {
        return Math.random().toString(36).substr(2, 8);
    }

    // Simple event emitter

    on(event, callback) {
        if (!this._listeners[event]) this._listeners[event] = [];
        this._listeners[event].push(callback);
    }

    emit(event, data) {
        if (this._listeners[event]) {
            this._listeners[event].forEach(cb => cb(data));
        }
    }
}


