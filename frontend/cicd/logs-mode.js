/**
 * Logs Mode - CI/CD Build Logs and Fix Suggestions
 * 
 * This module handles:
 * 1. Loading and displaying Jenkins build logs from console URLs
 * 2. Analyzing failures using AI to identify root causes
 * 3. Displaying suggested fixes for reference (no automatic execution)
 * 
 * NOTE: This module operates independently within the Logs tab.
 * It does NOT interact with the Chat tab or execute terminal commands automatically.
 * All analysis results and suggested fixes are displayed inline for manual review.
 */

class LogsMode {
    constructor() {
        this.currentJenkinsConfig = null;
        this.currentAnsibleConfig = null;
        this.currentBuilds = [];
        this.selectedBuild = null;
        this.currentAnalysis = null;
        
        this.initializeUI();
        this.loadConfigurations();
    }
    
    initializeUI() {
        // Logs container is now in HTML, just set up event listeners
        this.setupEventListeners();
        
        // Clean up old listener if it exists
        if (this._modeChangeListener) {
            document.removeEventListener('mode:changed', this._modeChangeListener);
        }
        
        // Store listener reference for cleanup
        this._modeChangeListener = (e) => {
            if (e.detail && e.detail.mode === 'logs') {
                this.cleanupEventListeners(); // Clean up old listeners
                this.setupEventListeners();   // Set up new ones
            }
        };
        
        // Add new listener
        document.addEventListener('mode:changed', this._modeChangeListener);
    }
    
    getLogsUIHTML() {
        return `
            <div class="logs-header">
                <div class="config-section">
                    <div class="config-row">
                        <div class="config-item">
                            <label for="jenkins-config-select">Jenkins:</label>
                            <select id="jenkins-config-select">
                                <option value="">No Jenkins configured</option>
                            </select>
                            <button id="config-jenkins-btn" class="config-btn">Configure</button>
                        </div>
                        <div class="config-item">
                            <label for="ansible-config-select">Ansible:</label>
                            <select id="ansible-config-select">
                                <option value="">No Ansible configured</option>
                            </select>
                            <button id="config-ansible-btn" class="config-btn">Configure</button>
                        </div>
                    </div>
                    <div class="config-row">
                        <div class="config-item">
                            <label for="server-name-input">Server Name:</label>
                            <input type="text" id="server-name-input" placeholder="e.g., web-server-01" />
                        </div>
                        <button id="fetch-builds-btn" class="primary-btn">
                            <span class="btn-text">Fetch Builds</span>
                            <span class="spinner hidden"></span>
                        </button>
                    </div>
                    <div class="config-row console-url-section">
                        <div class="config-item console-url-item">
                            <label for="console-url-input">Or paste Console URL:</label>
                            <input type="url" id="console-url-input" placeholder="https://jenkins.example.com/job/MyJob/123/console" />
                            <small class="form-help">Direct link to specific Jenkins job console</small>
                        </div>
                        <button id="fetch-console-btn" class="primary-btn">
                            <span class="btn-text">Load Logs</span>
                            <span class="spinner hidden"></span>
                        </button>
                    </div>
                </div>

                <!-- Embedded console log section -->
                <div id="embedded-console-section" class="embedded-console-section hidden" style="width: 100%;">
                    <div class="console-container">
                        <div class="console-header">
                            <h3 id="console-title">Console Log</h3>
                            <button id="close-console-btn" class="close-btn" aria-label="Close">×</button>
                        </div>
                        <div class="console-content">
                            <div class="build-info" id="console-build-info"></div>
                            <div class="console-log">
                                <pre id="console-output"></pre>
                            </div>
                            <div class="console-actions">
                                <button id="analyze-console-btn" class="primary-btn">
                                    <span class="btn-text">🔍 Analyze Logs</span>
                                    <span class="spinner hidden"></span>
                                </button>
                            </div>
                            <div id="analysis-results" class="analysis-results hidden"></div>
                        </div>
                    </div>
                </div>
                </div>
            </div>
            
            <div class="logs-content">
                <div class="builds-list" id="builds-list">
                    <div class="no-builds-message" id="no-builds-message">
                        Configure Jenkins and fetch builds to get started
                    </div>
                </div>
            </div>
        `;
    }
    
    cleanupEventListeners() {
        // Remove fetch console button listener
        const fetchConsoleBtn = document.getElementById('fetch-console-btn');
        if (fetchConsoleBtn) {
            fetchConsoleBtn.replaceWith(fetchConsoleBtn.cloneNode(true));
        }
        // Remove config buttons listeners
        const cfgJenkinsBtn = document.getElementById('config-jenkins-btn');
        if (cfgJenkinsBtn) {
            cfgJenkinsBtn.replaceWith(cfgJenkinsBtn.cloneNode(true));
        }
        const cfgAnsibleBtn = document.getElementById('config-ansible-btn');
        if (cfgAnsibleBtn) {
            cfgAnsibleBtn.replaceWith(cfgAnsibleBtn.cloneNode(true));
        }
        
        // Clean up config selection listeners
        ['jenkins-config-select', 'ansible-config-select'].forEach(id => {
            const select = document.getElementById(id);
            if (select) {
                select.replaceWith(select.cloneNode(true));
            }
        });
    }

    setupEventListeners() {
        this.cleanupEventListeners(); // Clean up any existing listeners first
        
        // Fetch console button
        const fetchConsoleBtn = document.getElementById('fetch-console-btn');
        if (fetchConsoleBtn) {
            fetchConsoleBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.fetchConsoleFromUrl();
            });
        }

        // Config buttons (ensure working even if inline onclick fails)
        const cfgJenkinsBtn = document.getElementById('config-jenkins-btn');
        if (cfgJenkinsBtn) {
            cfgJenkinsBtn.addEventListener('click', (e) => {
                e.preventDefault();
                if (typeof this.showJenkinsConfigModal === 'function') {
                    this.showJenkinsConfigModal();
                } else if (typeof window.openJenkinsConfigModal === 'function') {
                    window.openJenkinsConfigModal();
                }
            });
        }
        const cfgAnsibleBtn = document.getElementById('config-ansible-btn');
        if (cfgAnsibleBtn) {
            cfgAnsibleBtn.addEventListener('click', (e) => {
                e.preventDefault();
                if (typeof this.showAnsibleConfigModal === 'function') {
                    this.showAnsibleConfigModal();
                } else if (typeof window.openAnsibleConfigModal === 'function') {
                    window.openAnsibleConfigModal();
                }
            });
        }
        
        // Config selection changes
        const jenkinsSelect = document.getElementById('jenkins-config-select');
        if (jenkinsSelect) {
            jenkinsSelect.addEventListener('change', (e) => {
                this.currentJenkinsConfig = e.target.value || null;
            });
        }
        
        const ansibleSelect = document.getElementById('ansible-config-select');
        if (ansibleSelect) {
            ansibleSelect.addEventListener('change', (e) => {
                this.currentAnsibleConfig = e.target.value || null;
            });
        }
    }
    
    async loadConfigurations() {
        try {
            const userId = 'system'; // In real app, get from current user
            
            // Load Jenkins configurations
            const jenkinsResponse = await fetch(`/cicd/jenkins/configs?user_id=${userId}`);
            if (jenkinsResponse.ok) {
                const jenkinsData = await jenkinsResponse.json();
                this.populateJenkinsConfigs(jenkinsData.configs || []);
            }
            
            // Load Ansible configurations  
            const ansibleResponse = await fetch(`/cicd/ansible/configs?user_id=${userId}`);
            if (ansibleResponse.ok) {
                const ansibleData = await ansibleResponse.json();
                this.populateAnsibleConfigs(ansibleData.configs || []);
            }
            
        } catch (error) {
            console.error('Failed to load configurations:', error);
        }
    }
    
    populateJenkinsConfigs(configs) {
        const select = document.getElementById('jenkins-config-select');
        if (!select) return;
        
        // Clear existing options and set a helpful default
        select.innerHTML = '<option value="">Select Jenkins...</option>';
        
        if (Array.isArray(configs) && configs.length > 0) {
            configs.forEach(config => {
                // Create an option that includes the config name and a delete button
                const option = document.createElement('option');
                option.value = config.id;
                // Include base URL in a way that's visually distinct
                option.textContent = `${config.name} (${config.base_url})`;
                select.appendChild(option);
            });
            
            // Create delete button for the selected config
            const wrapper = select.closest('.config-item');
            if (wrapper) {
                // Create a container for the select and delete button
                const selectContainer = document.createElement('div');
                selectContainer.style.display = 'flex';
                selectContainer.style.alignItems = 'center';
                selectContainer.style.gap = '8px';
                selectContainer.style.flex = '1';
                
                // Move select into container
                select.parentNode.insertBefore(selectContainer, select);
                selectContainer.appendChild(select);
                select.style.flex = '1';
                
                // Create delete button
                const deleteButton = document.createElement('button');
                deleteButton.className = 'icon-button delete-config';
                deleteButton.innerHTML = '🗑️';
                deleteButton.title = 'Delete configuration';
                deleteButton.style.visibility = select.value ? 'visible' : 'hidden';
                
                deleteButton.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    const id = select.value;
                    if (!id) return;
                    
                    if (!confirm('Delete selected Jenkins configuration?')) return;
                    
                    try {
                        const resp = await fetch(`/cicd/jenkins/configs/${id}`, { method: 'DELETE' });
                        const data = await resp.json();
                        if (resp.ok) {
                            showToast('Jenkins configuration deleted', 'success');
                            this.loadConfigurations();
                        } else {
                            showToast(data.error || 'Failed to delete Jenkins configuration', 'error');
                        }
                    } catch (e) {
                        showToast('Error deleting Jenkins configuration: ' + e.message, 'error');
                    }
                });
                
                // Add delete button to container
                selectContainer.appendChild(deleteButton);
                
                // Update delete button visibility on select change
                select.addEventListener('change', () => {
                    deleteButton.style.visibility = select.value ? 'visible' : 'hidden';
                });
            }
        } else {
            // Keep default only
            console.warn('[LogsMode] No Jenkins configs found for dropdown');
        }
        
        // Select first config if only one exists
        if (configs.length === 1) {
            select.value = configs[0].id;
            this.currentJenkinsConfig = configs[0].id;
        }
    }
    
    populateAnsibleConfigs(configs) {
        const select = document.getElementById('ansible-config-select');
        if (!select) return;
        
        // Clear existing options and set a helpful default
        select.innerHTML = '<option value="">Select Ansible...</option>';
        
        if (Array.isArray(configs) && configs.length > 0) {
            configs.forEach(config => {
                const option = document.createElement('option');
                option.value = config.id;
                option.textContent = `${config.name} (${config.local_path})`;
                select.appendChild(option);
            });
            
            // Create delete button for the selected config
            const wrapper = select.closest('.config-item');
            if (wrapper) {
                // Create a container for the select and delete button
                const selectContainer = document.createElement('div');
                selectContainer.style.display = 'flex';
                selectContainer.style.alignItems = 'center';
                selectContainer.style.gap = '8px';
                selectContainer.style.flex = '1';
                
                // Move select into container
                select.parentNode.insertBefore(selectContainer, select);
                selectContainer.appendChild(select);
                select.style.flex = '1';
                
                // Create delete button
                const deleteButton = document.createElement('button');
                deleteButton.className = 'icon-button delete-config';
                deleteButton.innerHTML = '🗑️';
                deleteButton.title = 'Delete configuration';
                deleteButton.style.visibility = select.value ? 'visible' : 'hidden';
                
                deleteButton.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    const id = select.value;
                    if (!id) return;
                    
                    if (!confirm('Delete selected Ansible configuration?')) return;
                    
                    try {
                        const resp = await fetch(`/cicd/ansible/configs/${id}`, { method: 'DELETE' });
                        const data = await resp.json();
                        if (resp.ok) {
                            showToast('Ansible configuration deleted', 'success');
                            this.loadConfigurations();
                        } else {
                            showToast(data.error || 'Failed to delete Ansible configuration', 'error');
                        }
                    } catch (e) {
                        showToast('Error deleting Ansible configuration: ' + e.message, 'error');
                    }
                });
                
                // Add delete button to container
                selectContainer.appendChild(deleteButton);
                
                // Update delete button visibility on select change
                select.addEventListener('change', () => {
                    deleteButton.style.visibility = select.value ? 'visible' : 'hidden';
                });
            }
        } else {
            // Keep default only
            console.warn('[LogsMode] No Ansible configs found for dropdown');
        }
        
        // Select first config if only one exists
        if (configs.length === 1) {
            select.value = configs[0].id;
            this.currentAnsibleConfig = configs[0].id;
        }
    }

    async fetchConsoleFromUrl() {
        const consoleUrlInput = document.getElementById('console-url-input');
        const fetchBtn = document.getElementById('fetch-console-btn');
        
        const consoleUrl = consoleUrlInput ? consoleUrlInput.value.trim() : '';
        
        if (!consoleUrl) {
            showToast('Please enter a Jenkins console URL', 'error');
            return;
        }
        
        // Basic URL validation
        if (!consoleUrl.includes('/console')) {
            showToast('URL should end with /console (e.g., /job/MyJob/123/console)', 'error');
            return;
        }
        
        window.setButtonLoading(fetchBtn, true);
        showToast(`Fetching console logs...`, 'info');
        
        try {
            const response = await fetch('/cicd/jenkins/console', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    console_url: consoleUrl,
                    jenkins_config_id: this.currentJenkinsConfig
                })
            });
            
            const data = await response.json();
            console.log('Received response:', data); // Debug log
            
            if (data.success) {
                // Show the embedded console section with the logs
                const consoleSection = document.getElementById('embedded-console-section');
                console.log('Console section element:', consoleSection); // Debug log
                
                if (!consoleSection) {
                    console.error('Could not find embedded-console-section');
                    return;
                }

                // Update title
                const title = document.getElementById('console-title');
                if (title) {
                    title.textContent = `Console Log: ${data.job_name} #${data.build_number}`;
                } else {
                    console.error('Could not find console-title element');
                }

                // Update build info
                const buildInfo = document.getElementById('console-build-info');
                if (buildInfo) {
                    buildInfo.innerHTML = `
                        <div><strong>Job:</strong> ${data.job_name}</div>
                        <div><strong>Build:</strong> #${data.build_number}</div>
                        <div><strong>Source:</strong> <a href="${consoleUrl}" target="_blank">View in Jenkins</a></div>
                    `;
                } else {
                    console.error('Could not find console-build-info element');
                }

                // Update console output
                const output = document.getElementById('console-output');
                if (output) {
                    console.log('Setting console output, length:', data.console_log.length); // Debug log
                    output.textContent = this.escapeHtml(data.console_log);
                } else {
                    console.error('Could not find console-output element');
                }

                // Store log data for analysis
                consoleSection.dataset.logPayload = JSON.stringify({
                    job_name: data.job_name,
                    build_number: data.build_number,
                    console_log: data.console_log
                });

                // Show the console section
                consoleSection.classList.remove('hidden');
                console.log('Removed hidden class from console section'); // Debug log

                // Setup close button
                const closeBtn = document.getElementById('close-console-btn');
                if (closeBtn) {
                    closeBtn.onclick = () => {
                        consoleSection.classList.add('hidden');
                        if (output) output.textContent = '';
                        if (buildInfo) buildInfo.innerHTML = '';
                        const analysisResults = document.getElementById('analysis-results');
                        if (analysisResults) {
                            analysisResults.innerHTML = '';
                            analysisResults.classList.add('hidden');
                        }
                    };
                } else {
                    console.error('Could not find close-console-btn element');
                }

                // Setup analyze button
                const analyzeBtn = document.getElementById('analyze-console-btn');
                if (analyzeBtn) {
                    // Remove any existing listeners
                    const newAnalyzeBtn = analyzeBtn.cloneNode(true);
                    analyzeBtn.parentNode.replaceChild(newAnalyzeBtn, analyzeBtn);
                    
                    newAnalyzeBtn.addEventListener('click', async (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        try {
                            await this.analyzeConsoleLog({
                                job_name: data.job_name,
                                build_number: data.build_number,
                                console_log: data.console_log,
                                original_url: consoleUrl
                            }, newAnalyzeBtn);
                        } catch (error) {
                            console.error('[LogsMode] Error in analyze button:', error);
                        }
                    });
                } else {
                    console.error('Could not find analyze-console-btn element');
                }

                // Make sure the console section is visible and scroll it into view
                consoleSection.style.display = 'block';
                consoleSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
                console.log('Scrolled console section into view'); // Debug log
                
                showToast(`Fetched console for ${data.job_name} #${data.build_number}`, 'success');
            } else {
                showToast(`Failed to fetch console: ${data.error}`, 'error');
            }
            
        } catch (error) {
            showToast(`Error fetching console: ${error.message}`, 'error');
        } finally {
            window.setButtonLoading(fetchBtn, false);
        }
    }

    _installGlobalConsoleModalHandlers() {
        document.addEventListener('click', async (e) => {
            const target = e.target;
            if (!target) return;
            // Close handlers (X and footer Close)
            if (target.id === 'console-modal-close' || target.id === 'console-close-btn' || target.closest('#console-modal-close') || target.closest('#console-close-btn')) {
                const modal = document.getElementById('console-log-modal');
                if (modal) {
                    e.preventDefault();
                    e.stopPropagation();
                    modal.remove();
                }
                return;
            }
            // Analyze handler
            if (target.id === 'analyze-console-btn' || target.closest('#analyze-console-btn')) {
                const modal = document.getElementById('console-log-modal');
                if (!modal) return;
                const payloadStr = modal.dataset && modal.dataset.logPayload;
                if (!payloadStr) return;
                try {
                    const payload = JSON.parse(payloadStr);
                    const analyzeBtn = document.getElementById('analyze-console-btn');
                    if (analyzeBtn && window.logsMode && typeof window.logsMode.analyzeConsoleLog === 'function') {
                        e.preventDefault();
                        e.stopPropagation();
                        await window.logsMode.analyzeConsoleLog(payload, analyzeBtn);
                    }
                } catch (err) {
                    console.error('[LogsMode] Failed to parse modal payload:', err);
                }
            }
        }, true);
    }

    showConsoleLogModal(logData) {
        const consoleSection = document.getElementById('embedded-console-section');
        if (!consoleSection) return;

        // Update console title
        const title = document.getElementById('console-title');
        if (title) {
            title.textContent = `Console Log: ${logData.job_name} #${logData.build_number}`;
        }

        // Update build info
        const buildInfo = document.getElementById('console-build-info');
        if (buildInfo) {
            buildInfo.innerHTML = `
                <div><strong>Job:</strong> ${logData.job_name}</div>
                <div><strong>Build:</strong> #${logData.build_number}</div>
                <div><strong>Source:</strong> <a href="${logData.original_url}" target="_blank">View in Jenkins</a></div>
            `;
        }

        // Update console output
        const output = document.getElementById('console-output');
        if (output) {
            output.textContent = this.escapeHtml(logData.console_log);
        }

        // Store log data for analysis
        consoleSection.dataset.logPayload = JSON.stringify({
            job_name: logData.job_name,
            build_number: logData.build_number,
            console_log: logData.console_log
        });

        // Show the console section
        consoleSection.classList.remove('hidden');

        // Setup close button
        const closeBtn = document.getElementById('close-console-btn');
        if (closeBtn) {
            closeBtn.onclick = () => {
                consoleSection.classList.add('hidden');
                // Clear the content when closing
                if (output) output.textContent = '';
                if (buildInfo) buildInfo.innerHTML = '';
                const analysisResults = document.getElementById('analysis-results');
                if (analysisResults) analysisResults.innerHTML = '';
                analysisResults.classList.add('hidden');
            };
        }

        // Setup analyze button
        const analyzeBtn = document.getElementById('analyze-console-btn');
        if (analyzeBtn) {
            // Remove any existing listener
            const newAnalyzeBtn = analyzeBtn.cloneNode(true);
            analyzeBtn.parentNode.replaceChild(newAnalyzeBtn, analyzeBtn);
            
            newAnalyzeBtn.addEventListener('click', async (e) => {
                e.preventDefault();
                e.stopPropagation();
                try {
                    await this.analyzeConsoleLog(logData, newAnalyzeBtn);
                } catch (error) {
                    console.error('[LogsMode] Error in analyze button:', error);
                }
            });
        }

        // Scroll the console section into view
        consoleSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        
    }
    
    async analyzeConsoleLog(logData, analyzeBtn) {
        // Prevent multiple analyze calls
        if (analyzeBtn.disabled) return;
        
        window.setButtonLoading(analyzeBtn, true);
        analyzeBtn.disabled = true; // Prevent multiple clicks
        
        let resultsDiv = document.getElementById('analysis-results');
        if (!resultsDiv) {
            const consoleSection = document.getElementById('embedded-console-section');
            if (consoleSection) resultsDiv = consoleSection.querySelector('#analysis-results');
        }
        if (!resultsDiv) {
            console.error('[LogsMode] analysis-results container not found');
            showToast('Unable to show analysis area. Please try reloading the Logs tab.', 'error');
            window.setButtonLoading(analyzeBtn, false);
            analyzeBtn.disabled = false;
            return;
        }
        resultsDiv.innerHTML = '<div class="loading">Analyzing console log for errors and solutions...</div>';
        resultsDiv.classList.remove('hidden');
        
        try {
            // Use builds/<id>/analyze when we can match a saved build; otherwise fallback to direct analyzer
            let response, data;
            if (this.selectedBuild && this.selectedBuild.id) {
                response = await fetch(`/cicd/builds/${this.selectedBuild.id}/analyze`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        jenkins_config_id: this.currentJenkinsConfig ? parseInt(this.currentJenkinsConfig) : undefined,
                        ansible_config_id: this.currentAnsibleConfig ? parseInt(this.currentAnsibleConfig) : undefined
                    })
                });
                data = await response.json();
                if (!response.ok) throw new Error(data.error || 'Analyze request failed');
            } else {
                response = await fetch('/cicd/analyze/console', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        console_log: logData.console_log,
                        job_name: logData.job_name,
                        build_number: logData.build_number,
                        jenkins_config_id: this.currentJenkinsConfig ? parseInt(this.currentJenkinsConfig) : undefined,
                        user_id: 'system'
                    })
                });
                data = await response.json();
                if (!response.ok) throw new Error(data.error || 'Analyze request failed');
            }
            
            // Normalize analysis payload
            const analysis = data.analysis || data;
            if (analysis && (analysis.success === undefined || analysis.success === true)) {
                try {
                    console.log('[LogsMode] Analysis received', {
                        hasAnalysis: !!analysis,
                        suggestedCommandsCount: (analysis.suggested_commands || []).length,
                        suggestedStepsCount: (analysis.suggested_steps || []).length,
                        hasPlaybook: !!analysis.suggested_playbook
                    });
                } catch (_) {}
                this.displayAnalysisResults(analysis, resultsDiv);
            } else {
                resultsDiv.innerHTML = `<div class=\"error\">Analysis failed: ${analysis.error || data.error || 'Unknown error'}</div>`;
            }
            
        } catch (error) {
            console.error('[LogsMode] analyzeConsoleLog error:', error);
            resultsDiv.innerHTML = `<div class=\"error\">Error analyzing console: ${error.message}</div>`;
        } finally {
            window.setButtonLoading(analyzeBtn, false);
            analyzeBtn.disabled = false;
        }
    }
    
    displayAnalysisResults(analysis, container) {
        // Prefer suggested_steps; if absent, derive simple steps from commands for UI
        const stepsToShow = (analysis.suggested_steps && analysis.suggested_steps.length > 0)
            ? analysis.suggested_steps
            : (analysis.suggested_commands || []).map(cmd => `Run: ${cmd}`);

        // Sanitize steps: remove JSON artifacts, surrounding quotes, and trailing commas
        const cleanedSteps = (stepsToShow || [])
            .map((raw) => {
                if (raw == null) return '';
                let s = String(raw).trim();
                // Drop obvious JSON wrapper lines
                if (/^\{\s*$/.test(s)) return '';
                if (/^\}\s*,?$/.test(s)) return '';
                if (/^\[$/.test(s)) return '';
                if (/^\]\s*,?$/.test(s)) return '';
                if (/^"?steps"?\s*:\s*\[\s*$/.test(s)) return '';
                // Remove surrounding single/double quotes first so numbering at start is detectable
                s = s.replace(/^['"]/, '').replace(/['"]\s*$/, '');
                // Strip ANY repeated leading numeric markers (e.g., '1.', '1)', '1:', '1;', including '1.1.') and bullets
                s = s.replace(/^(?:\d+[\.\):;]\s*)+/, '').replace(/^[\-\*]\s*/, '');
                // Clean any leftover leading punctuation
                s = s.replace(/^[\.:;,-]+\s*/, '');
                // Remove a dangling trailing comma
                s = s.replace(/,\s*$/, '');
                return s.trim();
            })
            .filter(s => s && s !== '{' && s !== '}' && s !== '[' && s !== ']');

        const resultsHTML = `
            <div class="analysis-summary">
                <h4>🔍 Error Analysis</h4>
                <div class="error-summary">
                    <p><strong>Root Cause:</strong> ${analysis.root_cause || 'Could not determine'}</p>
                    <p><strong>Error Summary:</strong> ${analysis.error_summary || 'No specific error identified'}</p>
                    <p><strong>Confidence:</strong> ${Math.round((analysis.confidence || analysis.confidence_score || 0) * 100)}%</p>
                </div>
            </div>
            
            ${cleanedSteps && cleanedSteps.length > 0 ? `
                <div class="suggested-steps">
                    <h4>📝 Suggested Steps</h4>
                    <ol class="steps-list">
                        ${cleanedSteps.map(step => `
                            <li class="step-item">${this.escapeHtml(step)}</li>
                        `).join('')}
                    </ol>
                    <p class="note"><em>These are AI-suggested steps based on the detected root cause and error summary.</em></p>
                </div>
            ` : ''}
            
            ${analysis.suggested_playbook ? `
                <div class="suggested-playbook">
                    <h4>🔧 Suggested Ansible Playbook</h4>
                    <pre><code>${this.escapeHtml(analysis.suggested_playbook)}</code></pre>
                </div>
            ` : ''}
        `;
        
        try { console.log('[LogsMode] Rendering analysis results'); } catch (_) {}
        container.innerHTML = resultsHTML;
    }
    
    escapeHtml(text) {
        if (text === null || text === undefined) return '';
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        const s = String(text);
        return s.replace(/[&<>"']/g, m => map[m]);
    }
    
    renderVisibleLogLines(container, logLines, startIndex, visibleLines, lineHeight) {
        const buffer = 10; // Extra lines to render above/below viewport
        const start = Math.max(0, startIndex - buffer);
        const end = Math.min(logLines.length, startIndex + visibleLines + buffer);
        
        // Create lines HTML
        const linesHtml = document.createElement('div');
        for (let i = start; i < end; i++) {
            const line = document.createElement('div');
            line.className = 'log-line';
            line.style.position = 'absolute';
            line.style.top = `${i * lineHeight}px`;
            line.style.left = '0';
            line.style.right = '0';
            line.style.height = `${lineHeight}px`;
            line.textContent = logLines[i];
            
            // Add line number
            const lineNum = document.createElement('span');
            lineNum.className = 'line-number';
            lineNum.textContent = `${i + 1}`;
            line.insertBefore(lineNum, line.firstChild);
            
            linesHtml.appendChild(line);
        }
        
        // Replace content
        container.innerHTML = '';
        container.appendChild(linesHtml);
    }

    appendLogsToModal(newLogs) {
        const consoleLog = document.querySelector('.console-log pre');
        if (consoleLog) {
            consoleLog.textContent += '\n' + newLogs;
            // Scroll to bottom of new content
            consoleLog.scrollTop = consoleLog.scrollHeight;
        }
    }

    addLoadMoreLogsButton(buildId, nextOffset) {
        const consoleLog = document.querySelector('.console-log');
        if (!consoleLog) return;
        
        // Remove existing button if any
        const existingBtn = document.getElementById('load-more-logs');
        if (existingBtn) existingBtn.remove();
        
        const loadMoreBtn = document.createElement('button');
        loadMoreBtn.id = 'load-more-logs';
        loadMoreBtn.className = 'load-more-btn';
        loadMoreBtn.textContent = 'Load More Logs';
        
        loadMoreBtn.addEventListener('click', () => {
            this.viewBuildLogs(buildId, nextOffset);
        });
        
        consoleLog.parentNode.insertBefore(loadMoreBtn, consoleLog.nextSibling);
    }
    
    displayBuilds(builds) {
        const buildsList = document.getElementById('builds-list');
        const noBuildsMessage = document.getElementById('no-builds-message');
        
        if (!buildsList) return;
        
        if (builds.length === 0) {
            buildsList.innerHTML = '<div class="no-builds-message">No builds found for the specified criteria</div>';
            return;
        }
        
        // Hide no builds message
        if (noBuildsMessage) {
            noBuildsMessage.classList.add('hidden');
        }
        
        // Create builds table
        const table = document.createElement('table');
        table.className = 'builds-table';
        table.innerHTML = `
            <thead>
                <tr>
                    <th>Job Name</th>
                    <th>Build #</th>
                    <th>Status</th>
                    <th>Duration</th>
                    <th>Started</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                ${builds.map(build => this.createBuildRow(build)).join('')}
            </tbody>
        `;
        
        buildsList.innerHTML = '';
        buildsList.appendChild(table);
        
        // Add event listeners to action buttons
        this.setupBuildActionListeners();
    }
    
    createBuildRow(build) {
        const statusClass = build.status.toLowerCase();
        const duration = build.duration ? `${Math.round(build.duration / 1000)}s` : 'N/A';
        const startedAt = build.started_at ? new Date(build.started_at).toLocaleString() : 'N/A';
        
        const actions = [];
        actions.push(`<button class="action-btn view-logs-btn" data-build-id="${build.id}">View Logs</button>`);
        
        if (['failure', 'aborted', 'unstable'].includes(statusClass)) {
            actions.push(`<button class="action-btn fix-btn" data-build-id="${build.id}">Fix</button>`);
        }
        
        return `
            <tr class="build-row ${statusClass}">
                <td class="job-name">${build.job_name}</td>
                <td class="build-number">${build.build_number}</td>
                <td class="status">
                    <span class="status-badge ${statusClass}">${build.status}</span>
                </td>
                <td class="duration">${duration}</td>
                <td class="started-at">${startedAt}</td>
                <td class="actions">${actions.join(' ')}</td>
            </tr>
        `;
    }
    
    setupBuildActionListeners() {
        // View logs buttons
        document.querySelectorAll('.view-logs-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const buildId = e.target.getAttribute('data-build-id');
                this.viewBuildLogs(buildId);
            });
        });
        
        // Fix buttons
        document.querySelectorAll('.fix-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const buildId = e.target.getAttribute('data-build-id');
                this.analyzeAndFix(buildId);
            });
        });
    }
    
    async viewBuildLogs(buildId, offset = 0) {
        if (!this.currentJenkinsConfig) {
            showToast('Please configure Jenkins connection first', 'error');
            return;
        }
        
        // Show loading indicator
        const loadingEl = document.createElement('div');
        loadingEl.className = 'logs-loading';
        loadingEl.innerHTML = '<span class="spinner"></span> Loading build logs...';
        document.body.appendChild(loadingEl);
        
        try {
            // Request logs with pagination support
            const response = await fetch(
                `/cicd/builds/${buildId}/logs?` + 
                `jenkins_config_id=${this.currentJenkinsConfig}&` +
                `lines=1000&offset=${offset}`
            );
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                if (offset === 0) {
                    // First page - show modal
                    this.showLogsModal(data.build, data.console_log);
                } else {
                    // Append to existing modal
                    this.appendLogsToModal(data.console_log);
                }
                
                // If there are more logs, add load more button
                if (data.has_more) {
                    this.addLoadMoreLogsButton(buildId, offset + 1000);
                }
            } else {
                const error = data.error || 'Unknown error occurred';
                showToast(`Failed to load logs: ${error}`, 'error');
            }
            
        } catch (error) {
            showToast(`Error loading logs: ${error.message}`, 'error');
        } finally {
            // Remove loading indicator
            loadingEl.remove();
        }
    }
    
    showLogsModal(build, consoleLog) {
        // Create modal if it doesn't exist
        let modal = document.getElementById('build-logs-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'build-logs-modal';
            modal.className = 'modal';
            document.body.appendChild(modal);
        }
        
        // Split logs into lines for virtualization
        const logLines = (consoleLog || 'No console log available').split('\n');
        const totalLines = logLines.length;
        
        modal.innerHTML = `
            <div class="modal-content large">
                <div class="modal-header">
                    <h2>Build Logs - ${build.job_name} #${build.build_number}</h2>
                    <button class="close-modal" id="close-logs-modal">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="build-info">
                        <span><strong>Status:</strong> <span class="status-badge ${build.status.toLowerCase()}">${build.status}</span></span>
                        <span><strong>Duration:</strong> ${build.duration ? Math.round(build.duration / 1000) + 's' : 'N/A'}</span>
                        <span><strong>Started:</strong> ${build.started_at ? new Date(build.started_at).toLocaleString() : 'N/A'}</span>
                        <span><strong>Log Lines:</strong> ${totalLines}</span>
                    </div>
                    <div class="console-log" id="virtual-console-log">
                        <div class="log-content" style="position: relative;"></div>
                    </div>
                </div>
            </div>
        `;
        
        // Setup virtual scrolling
        const virtualConsole = document.getElementById('virtual-console-log');
        const logContent = virtualConsole.querySelector('.log-content');
        const lineHeight = 20; // px
        const visibleLines = Math.ceil(virtualConsole.clientHeight / lineHeight);
        let lastScrollTop = 0;
        
        // Set content height
        // Add extra bottom space so the last lines aren't hidden under the viewport/borders
        const extraBottom = lineHeight * 3; // spacer for comfortable scrolling past the last line
        logContent.style.height = `${(totalLines * lineHeight) + extraBottom}px`;
        
        // Initial render
        this.renderVisibleLogLines(logContent, logLines, 0, visibleLines, lineHeight);
        
        // Handle scroll
        virtualConsole.addEventListener('scroll', () => {
            const scrollTop = virtualConsole.scrollTop;
            const startIndex = Math.floor(scrollTop / lineHeight);
            
            // Only re-render if scrolled to new lines
            if (Math.abs(scrollTop - lastScrollTop) >= lineHeight) {
                this.renderVisibleLogLines(logContent, logLines, startIndex, visibleLines, lineHeight);
                lastScrollTop = scrollTop;
            }
        });
        
        modal.classList.remove('hidden');
        
        // Close button handler
        document.getElementById('close-logs-modal').addEventListener('click', () => {
            modal.classList.add('hidden');
        });
        
        // Click outside to close
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.add('hidden');
            }
        });
    }
    
    async analyzeAndFix(buildId) {
        if (!this.currentJenkinsConfig) return;
        
        showToast('Analyzing build failure...', 'info');
        
        try {
            const response = await fetch(`/cicd/builds/${buildId}/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    jenkins_config_id: parseInt(this.currentJenkinsConfig),
                    ansible_config_id: this.currentAnsibleConfig ? parseInt(this.currentAnsibleConfig) : null
                })
            });
            
            const analysis = await response.json();
            
            if (analysis.success) {
                this.currentAnalysis = analysis;
                // Note: This method is kept for backward compatibility but analysis should be done via Analyze Logs button
                showToast('Analysis complete', 'success');
            } else {
                showToast(`Analysis failed: ${analysis.error}`, 'error');
            }
            
        } catch (error) {
            showToast(`Error analyzing build: ${error.message}`, 'error');
        }
    }
    
    // Removed: displayAnalysisResults method that integrated with Chat tab
    // Analysis results are now displayed within the Logs tab using displayAnalysisResults(analysis, container) method
    
    // Removed: showFixButtons and executeFix methods
    // These methods were responsible for executing commands in terminal/chat
    // Per requirements: no terminal execution, only display analysis and suggested fixes
    
    // Small helpers to keep modal handlers DRY
    _withButtonLoading(btn, fn) {
        if (typeof setButtonLoading === 'function') {
            setButtonLoading(btn, true);
        } else if (typeof window.setButtonLoading === 'function') {
            window.setButtonLoading(btn, true);
        } else {
            btn.disabled = true;
        }
        const finalize = () => {
            if (typeof setButtonLoading === 'function') {
                setButtonLoading(btn, false);
            } else if (typeof window.setButtonLoading === 'function') {
                window.setButtonLoading(btn, false);
            } else {
                btn.disabled = false;
            }
        };
        try {
            const result = fn();
            if (result && typeof result.finally === 'function') {
                return result.finally(finalize);
            }
            finalize();
            return result;
        } catch (e) {
            finalize();
            throw e;
        }
    }

    async _postJson(url, body) {
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        return response.json();
    }

    // Save Jenkins configuration via backend API
    async saveJenkinsConfig(name, baseUrl, username, password, apiToken) {
        const payload = {
            name,
            base_url: baseUrl,
            username,
            password,
            api_token: apiToken,
            user_id: 'system'
        };
        return this._postJson('/cicd/jenkins/connect', payload);
    }

    showJenkinsConfigModal() {
        // Remove any existing modal with same ID to avoid duplicate elements
        try {
            const existing = document.getElementById('jenkins-config-modal');
            if (existing) existing.remove();
        } catch (_) {}
        // Create modal HTML
        const modalHTML = `
            <div class="modal-overlay" id="jenkins-config-modal">
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>Configure Jenkins Connection</h3>
                        <button class="modal-close" id="jenkins-modal-close">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div class="form-group">
                            <label for="jenkins-name">Configuration Name:</label>
                            <input type="text" id="jenkins-name" placeholder="e.g., Production Jenkins" value="Jenkins Config" />
                        </div>
                        <div class="form-group">
                            <label for="jenkins-url">Jenkins URL:</label>
                            <input type="url" id="jenkins-url" placeholder="https://jenkins.example.com" />
                        </div>
                        <div class="form-group">
                            <label for="jenkins-username">Username:</label>
                            <input type="text" id="jenkins-username" placeholder="your-jenkins-username" />
                        </div>
                        <div class="form-group">
                            <label for="jenkins-token">API Token: <span class="required">*</span></label>
                            <input type="password" id="jenkins-token" placeholder="Your Jenkins API token" />
                            <small class="form-help">Jenkins API token (required for authentication)</small>
                        </div>
                        <div class="form-group">
                            <label for="jenkins-password">Password:</label>
                            <input type="password" id="jenkins-password" placeholder="Optional: Your Jenkins password" />
                            <small class="form-help">Optional: Jenkins login password</small>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button id="jenkins-config-cancel" class="secondary-btn">Cancel</button>
                        <button id="jenkins-config-save" class="primary-btn">
                            <span class="btn-text">Test & Save</span>
                            <span class="spinner hidden"></span>
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        // Add modal to page
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // Setup event listeners
        const modal = document.getElementById('jenkins-config-modal');
        const closeBtn = document.getElementById('jenkins-modal-close');
        const cancelBtn = document.getElementById('jenkins-config-cancel');
        const saveBtn = document.getElementById('jenkins-config-save');
        
        const closeModal = () => {
            modal.remove();
        };
        
        closeBtn.onclick = closeModal;
        cancelBtn.onclick = closeModal;
        modal.onclick = (e) => {
            if (e.target === modal) closeModal();
        };
        
        saveBtn.onclick = async () => {
            const name = document.getElementById('jenkins-name').value.trim();
            const baseUrl = document.getElementById('jenkins-url').value.trim();
            const username = document.getElementById('jenkins-username').value.trim();
            const password = document.getElementById('jenkins-password').value.trim();
            const apiToken = document.getElementById('jenkins-token').value.trim();
            
            if (!name || !baseUrl || !username || !apiToken) {
                alert('Please fill in all required fields (Name, URL, Username, API Token)');
                return;
            }
            
            await this._withButtonLoading(saveBtn, async () => {
                try {
                    if (typeof showToast === 'function') showToast('Saving Jenkins configuration…', 'info');
                    const result = await this.saveJenkinsConfig(name, baseUrl, username, password, apiToken);
                    if (result && result.success) {
                        // Refresh configurations to populate dropdown immediately
                        try {
                            await this.loadConfigurations();
                        } catch (_) {}
                        const select = document.getElementById('jenkins-config-select');
                        if (select && result.config_id) {
                            select.value = String(result.config_id);
                            this.currentJenkinsConfig = String(result.config_id);
                        }
                        closeModal();
                    } else {
                        if (typeof showToast === 'function') showToast(result && result.error ? result.error : 'Failed to save Jenkins configuration', 'error');
                    }
                } catch (error) {
                    console.error('Error saving Jenkins config:', error);
                    if (typeof showToast === 'function') {
                        showToast(`Error: ${error.message}`, 'error');
                    } else {
                        alert(`Error: ${error.message}`);
                    }
                }
            });
        };
        
        // Focus first input
        setTimeout(() => {
            document.getElementById('jenkins-name').focus();
        }, 100);
    }

    showAnsibleConfigModal() {
        // Remove any existing modal with same ID to avoid duplicate elements
        try {
            const existing = document.getElementById('ansible-config-modal');
            if (existing) existing.remove();
        } catch (_) {}
        const modalHTML = `
            <div class="modal-overlay" id="ansible-config-modal">
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>Configure Ansible Connection</h3>
                        <button class="modal-close" id="ansible-modal-close">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div class="form-group">
                            <label for="ansible-name">Configuration Name:</label>
                            <input type="text" id="ansible-name" placeholder="e.g., Production Ansible" value="Ansible Config" />
                        </div>
                        <div class="form-group">
                            <label for="ansible-path">Local Ansible Path: <span class="required">*</span></label>
                            <input type="text" id="ansible-path" placeholder="/path/to/ansible" />
                            <small class="form-help">Path to your local Ansible directory</small>
                        </div>
                        <div class="form-group">
                            <label for="ansible-repo">Git Repository URL:</label>
                            <input type="url" id="ansible-repo" placeholder="https://github.com/user/ansible-repo.git" />
                            <small class="form-help">Optional: Git repository for Ansible playbooks</small>
                        </div>
                        <div class="form-group">
                            <label for="ansible-branch">Git Branch:</label>
                            <input type="text" id="ansible-branch" placeholder="main" value="main" />
                            <small class="form-help">Git branch to use (default: main)</small>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button id="ansible-config-cancel" class="secondary-btn">Cancel</button>
                        <button id="ansible-config-save" class="primary-btn">
                            <span class="btn-text">Save Configuration</span>
                            <span class="spinner hidden"></span>
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        // Add modal to page
        document.body.insertAdjacentHTML('beforeend', modalHTML);

        // Setup event listeners
        const modal = document.getElementById('ansible-config-modal');
        const closeBtn = document.getElementById('ansible-modal-close');
        const cancelBtn = document.getElementById('ansible-config-cancel');
        const saveBtn = document.getElementById('ansible-config-save');
        
        const closeModal = () => { modal.remove(); };
        closeBtn.onclick = closeModal;
        cancelBtn.onclick = closeModal;
        modal.onclick = (e) => { if (e.target === modal) closeModal(); };

        // Save handler
        saveBtn.onclick = async () => {
            const name = document.getElementById('ansible-name').value.trim();
            const localPath = document.getElementById('ansible-path').value.trim();
            const gitRepo = document.getElementById('ansible-repo').value.trim();
            const branch = document.getElementById('ansible-branch').value.trim() || 'main';

            if (!name || !localPath) {
                alert('Please fill in all required fields (Name, Local Path)');
                return;
            }

            await this._withButtonLoading(saveBtn, async () => {
                try {
                    if (typeof showToast === 'function') showToast('Saving Ansible configuration…', 'info');
                    const requestBody = { name, local_path: localPath, user_id: 'system' };
                    if (gitRepo && gitRepo.trim()) {
                        requestBody.git_repo_url = gitRepo.trim();
                        requestBody.git_branch = branch;
                    }
                    const data = await this._postJson('/cicd/ansible/connect', requestBody);
                    if (data.success) {
                        showToast(`Ansible configuration '${name}' saved`, 'success');
                        await this.loadConfigurations();
                        closeModal();
                    } else {
                        showToast(`Failed to save Ansible config: ${data.error}`, 'error');
                    }
                } catch (error) {
                    showToast(`Error saving Ansible config: ${error.message}`, 'error');
                }
            });
        };
    }
}

// Global helpers to force-open config modals (works even if instance not yet bound)
window.openJenkinsConfigModal = function() {
    if (typeof showToast === 'function') showToast('Opening Jenkins configuration…', 'info');
    try {
        if (window.logsMode && typeof window.logsMode.showJenkinsConfigModal === 'function') {
            window.logsMode.showJenkinsConfigModal();
        } else {
            const tmp = new LogsMode();
            tmp.showJenkinsConfigModal();
        }
    } catch (e) {
        console.error('Failed to open Jenkins config modal:', e);
    }
};

window.openAnsibleConfigModal = function() {
    if (typeof showToast === 'function') showToast('Opening Ansible configuration…', 'info');
    try {
        if (window.logsMode && typeof window.logsMode.showAnsibleConfigModal === 'function') {
            window.logsMode.showAnsibleConfigModal();
        } else {
            const tmp = new LogsMode();
            tmp.showAnsibleConfigModal();
        }
    } catch (e) {
        console.error('Failed to open Ansible config modal:', e);
    }
};

// Global ESC handler for modal cleanup
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        const topModal = document.querySelector('.modal-overlay:last-of-type');
        if (topModal) {
            topModal.remove();
        }
        // Also handle build logs modal (non-overlay)
        const buildLogs = document.getElementById('build-logs-modal');
        if (buildLogs && !buildLogs.classList.contains('hidden')) {
            buildLogs.classList.add('hidden');
        }
    }
}, true);

// Initialize logs mode when DOM is loaded
let logsMode = null;

window.logsMode = null;

document.addEventListener('DOMContentLoaded', () => {
    // Initialize logs mode after a short delay to ensure other components are ready
    setTimeout(() => {
        logsMode = new LogsMode();
        window.logsMode = logsMode;
    }, 100);
});

// Namespacing shim for modularity (non-breaking)
(function(){
  try {
    window.Modules = window.Modules || {};
    window.Modules.CICD = { LogsMode };
  } catch (_) { /* ignore if window not available */ }
})();

