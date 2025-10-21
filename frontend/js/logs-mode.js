/**
 * Logs Mode - CI/CD Build Logs and Fix Suggestions
 * 
 * This module handles displaying Jenkins build logs, analyzing failures,
 * and executing AI-suggested fix commands with user confirmation.
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
                            <span class="btn-text">Analyze Console</span>
                            <span class="spinner hidden"></span>
                        </button>
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
    
    setupEventListeners() {
        // Use setTimeout to ensure DOM elements are available
        setTimeout(() => {
            // Configuration buttons
            const configJenkinsBtn = document.getElementById('config-jenkins-btn');
            if (configJenkinsBtn) {
                configJenkinsBtn.addEventListener('click', () => this.showJenkinsConfigModal());
                console.log('Jenkins config button event listener added');
            } else {
                console.warn('Jenkins config button not found');
            }
            
            const configAnsibleBtn = document.getElementById('config-ansible-btn');
            if (configAnsibleBtn) {
                configAnsibleBtn.addEventListener('click', () => this.showAnsibleConfigModal());
            }
            
            // Fetch console button
            const fetchConsoleBtn = document.getElementById('fetch-console-btn');
            if (fetchConsoleBtn) {
                fetchConsoleBtn.addEventListener('click', () => this.fetchConsoleFromUrl());
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
        }, 200);
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
        
        // Clear existing options except first
        select.innerHTML = '<option value="">Select Jenkins...</option>';
        
        configs.forEach(config => {
            const option = document.createElement('option');
            option.value = config.id;
            option.textContent = `${config.name} (${config.base_url})`;
            select.appendChild(option);
        });
        
        if (configs.length === 1) {
            select.value = configs[0].id;
            this.currentJenkinsConfig = configs[0].id;
        }
    }
    
    populateAnsibleConfigs(configs) {
        const select = document.getElementById('ansible-config-select');
        if (!select) return;
        
        // Clear existing options except first
        select.innerHTML = '<option value="">Select Ansible...</option>';
        
        configs.forEach(config => {
            const option = document.createElement('option');
            option.value = config.id;
            option.textContent = `${config.name} (${config.local_path})`;
            select.appendChild(option);
        });
        
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
            window.appendMessage('Please enter a Jenkins console URL', 'system');
            return;
        }
        
        // Basic URL validation
        if (!consoleUrl.includes('/console')) {
            window.appendMessage('URL should end with /console (e.g., /job/MyJob/123/console)', 'system');
            return;
        }
        
        window.setButtonLoading(fetchBtn, true);
        window.appendMessage(`Fetching console logs from: ${consoleUrl}`, 'system');
        
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
            
            if (data.success) {
                // Display the console log in a modal or dedicated section
                this.showConsoleLogModal({
                    job_name: data.job_name,
                    build_number: data.build_number,
                    console_log: data.console_log,
                    original_url: consoleUrl
                });
                
                window.appendMessage(`Successfully fetched console for ${data.job_name} #${data.build_number}`, 'system');
            } else {
                window.appendMessage(`Failed to fetch console: ${data.error}`, 'system');
            }
            
        } catch (error) {
            window.appendMessage(`Error fetching console: ${error.message}`, 'system');
        } finally {
            window.setButtonLoading(fetchBtn, false);
        }
    }
    
    showConsoleLogModal(logData) {
        const modalHTML = `
            <div class="modal-overlay" id="console-log-modal">
                <div class="modal-content large">
                    <div class="modal-header">
                        <h3>Console Log: ${logData.job_name} #${logData.build_number}</h3>
                        <button class="modal-close" id="console-modal-close">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div class="build-info">
                            <div><strong>Job:</strong> ${logData.job_name}</div>
                            <div><strong>Build:</strong> #${logData.build_number}</div>
                            <div><strong>Source:</strong> <a href="${logData.original_url}" target="_blank">View in Jenkins</a></div>
                        </div>
                        <div class="console-log">
                            <pre id="console-output">${this.escapeHtml(logData.console_log)}</pre>
                        </div>
                        <div class="console-actions">
                            <button id="analyze-console-btn" class="primary-btn">
                                <span class="btn-text">🔍 Analyze & Suggest Fix</span>
                                <span class="spinner hidden"></span>
                            </button>
                        </div>
                        <div id="analysis-results" class="analysis-results hidden">
                            <!-- Analysis results will be inserted here -->
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button id="console-close-btn" class="secondary-btn">Close</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // Setup event listeners
        const modal = document.getElementById('console-log-modal');
        const closeBtn = document.getElementById('console-modal-close');
        const closeFooterBtn = document.getElementById('console-close-btn');
        const analyzeBtn = document.getElementById('analyze-console-btn');
        
        const closeModal = () => {
            modal.remove();
        };
        
        closeBtn.onclick = closeModal;
        closeFooterBtn.onclick = closeModal;
        modal.onclick = (e) => {
            if (e.target === modal) closeModal();
        };
        
        analyzeBtn.onclick = async () => {
            await this.analyzeConsoleLog(logData, analyzeBtn);
        };
    }
    
    async analyzeConsoleLog(logData, analyzeBtn) {
        window.setButtonLoading(analyzeBtn, true);
        
        const resultsDiv = document.getElementById('analysis-results');
        resultsDiv.innerHTML = '<div class="loading">Analyzing console log for errors and solutions...</div>';
        resultsDiv.classList.remove('hidden');
        
        try {
            // Use the existing AI analyzer endpoint
            const response = await fetch('/cicd/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    console_log: logData.console_log,
                    job_name: logData.job_name,
                    build_number: logData.build_number,
                    user_id: 'system'
                })
            });
            
            const data = await response.json();
            
            if (data.success && data.analysis) {
                this.displayAnalysisResults(data.analysis, resultsDiv);
            } else {
                resultsDiv.innerHTML = `<div class="error">Analysis failed: ${data.error || 'Unknown error'}</div>`;
            }
            
        } catch (error) {
            resultsDiv.innerHTML = `<div class="error">Error analyzing console: ${error.message}</div>`;
        } finally {
            window.setButtonLoading(analyzeBtn, false);
        }
    }
    
    displayAnalysisResults(analysis, container) {
        const resultsHTML = `
            <div class="analysis-summary">
                <h4>🔍 Error Analysis</h4>
                <div class="error-summary">
                    <strong>Root Cause:</strong> ${analysis.root_cause || 'Could not determine'}<br>
                    <strong>Error Summary:</strong> ${analysis.error_summary || 'No specific error identified'}<br>
                    <strong>Confidence:</strong> ${Math.round((analysis.confidence || 0) * 100)}%
                </div>
            </div>
            
            ${analysis.suggested_commands && analysis.suggested_commands.length > 0 ? `
                <div class="suggested-commands">
                    <h4>💡 Suggested Fix Commands</h4>
                    <div class="commands-list">
                        ${analysis.suggested_commands.map((cmd, i) => `
                            <div class="command-item">
                                <code>${cmd}</code>
                            </div>
                        `).join('')}
                    </div>
                    <div class="fix-actions">
                        <button class="fix-execute-btn" onclick="logsMode.executeSuggestedFix(${JSON.stringify(analysis).replace(/"/g, '&quot;')})">
                            ✅ Execute Fix Commands
                        </button>
                        <button class="fix-cancel-btn" onclick="this.style.display='none'">
                            ❌ Cancel
                        </button>
                    </div>
                </div>
            ` : ''}
            
            ${analysis.suggested_playbook ? `
                <div class="suggested-playbook">
                    <h4>🔧 Suggested Ansible Playbook</h4>
                    <pre><code>${analysis.suggested_playbook}</code></pre>
                </div>
            ` : ''}
        `;
        
        container.innerHTML = resultsHTML;
    }
    
    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }
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
    
    async viewBuildLogs(buildId) {
        if (!this.currentJenkinsConfig) return;
        
        try {
            const response = await fetch(`/cicd/builds/${buildId}/logs?jenkins_config_id=${this.currentJenkinsConfig}&lines=200`);
            const data = await response.json();
            
            if (data.success) {
                this.showLogsModal(data.build, data.console_log);
            } else {
                window.appendMessage(`Failed to load logs: ${data.error}`, 'system');
            }
            
        } catch (error) {
            window.appendMessage(`Error loading logs: ${error.message}`, 'system');
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
                    </div>
                    <div class="console-log">
                        <pre>${consoleLog || 'No console log available'}</pre>
                    </div>
                </div>
            </div>
        `;
        
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
        
        window.appendMessage('Analyzing build failure...', 'system');
        
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
                this.displayAnalysisResults(analysis);
            } else {
                window.appendMessage(`Analysis failed: ${analysis.error}`, 'system');
            }
            
        } catch (error) {
            window.appendMessage(`Error analyzing build: ${error.message}`, 'system');
        }
    }
    
    displayAnalysisResults(analysis) {
        // Display error summary
        window.appendMessage(`Analysis complete for ${analysis.job_name} #${analysis.build_number}`, 'system');
        window.appendMessage(`Error Summary: ${analysis.error_summary}`, 'ai');
        window.appendMessage(`Root Cause: ${analysis.root_cause}`, 'ai');
        
        if (analysis.error_categories && analysis.error_categories.length > 0) {
            window.appendMessage(`Categories: ${analysis.error_categories.join(', ')}`, 'ai');
        }
        
        // Display suggested commands
        if (analysis.suggested_commands && analysis.suggested_commands.length > 0) {
            const commandsDiv = document.createElement('div');
            commandsDiv.className = 'message ai suggested-commands';
            commandsDiv.innerHTML = `
                <strong>Suggested Fix Commands:</strong><br>
                ${analysis.suggested_commands.map(cmd => `• ${cmd}`).join('<br>')}
            `;
            document.getElementById('chat-container').appendChild(commandsDiv);
            
            // Show fix execution buttons
            this.showFixButtons(analysis);
        }
        
        // Display suggested playbook if available
        if (analysis.suggested_playbook) {
            const playbookDiv = document.createElement('div');
            playbookDiv.className = 'message ai suggested-playbook';
            playbookDiv.innerHTML = `
                <strong>Suggested Ansible Playbook:</strong> ${analysis.suggested_playbook.name}<br>
                <em>Path:</em> ${analysis.suggested_playbook.path}
            `;
            document.getElementById('chat-container').appendChild(playbookDiv);
        }
        
        document.getElementById('chat-container').scrollTop = document.getElementById('chat-container').scrollHeight;
    }
    
    showFixButtons(analysis) {
        const container = document.getElementById('chat-container');
        const btnGroup = document.createElement('div');
        btnGroup.className = 'confirm-buttons fix-buttons';
        
        const executeBtn = document.createElement('button');
        executeBtn.textContent = 'Execute Fix Commands';
        executeBtn.className = 'fix-action-btn';
        executeBtn.onclick = () => this.executeFix(analysis, btnGroup);
        btnGroup.appendChild(executeBtn);
        
        const cancelBtn = document.createElement('button');
        cancelBtn.textContent = 'Cancel';
        cancelBtn.className = 'fix-cancel-btn';
        cancelBtn.onclick = () => {
            window.appendMessage('Fix cancelled by user', 'system');
            btnGroup.remove();
        };
        btnGroup.appendChild(cancelBtn);
        
        container.appendChild(btnGroup);
        container.scrollTop = container.scrollHeight;
    }
    
    async executeFix(analysis, buttonContainer) {
        if (!analysis.suggested_commands || analysis.suggested_commands.length === 0) {
            window.appendMessage('No fix commands to execute', 'system');
            return;
        }
        
        window.appendMessage('Executing fix commands...', 'system');
        buttonContainer.remove();
        
        try {
            const response = await fetch('/cicd/fix/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    fix_history_id: analysis.fix_history_id,
                    commands: analysis.suggested_commands,
                    host: currentHost,
                    username: currentUser
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Display results
                data.results.forEach(result => {
                    const resultDiv = document.createElement('div');
                    resultDiv.className = `message system fix-result ${result.success ? 'success' : 'error'}`;
                    resultDiv.innerHTML = `
                        <strong>Command:</strong> ${result.command}<br>
                        <strong>Output:</strong> <pre>${result.output || '(no output)'}</pre>
                        ${result.error ? `<strong>Error:</strong> <pre>${result.error}</pre>` : ''}
                        <strong>Status:</strong> ${result.success ? '✅ Success' : '❌ Failed'}
                    `;
                    document.getElementById('chat-container').appendChild(resultDiv);
                });
                
                const summaryMsg = data.all_success 
                    ? '✅ All fix commands executed successfully!' 
                    : '⚠️ Some commands failed. Check the results above.';
                window.appendMessage(summaryMsg, 'system');
            } else {
                window.appendMessage(`Fix execution failed: ${data.error}`, 'system');
            }
            
        } catch (error) {
            window.appendMessage(`Error executing fix: ${error.message}`, 'system');
        }
        
        document.getElementById('chat-container').scrollTop = document.getElementById('chat-container').scrollHeight;
    }
    
    showJenkinsConfigModal() {
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
            
            window.setButtonLoading(saveBtn, true);
            
            try {
                await this.saveJenkinsConfig(name, baseUrl, username, password, apiToken);
                closeModal();
            } catch (error) {
                console.error('Error saving Jenkins config:', error);
            } finally {
                window.setButtonLoading(saveBtn, false);
            }
        };
        
        // Focus first input
        setTimeout(() => {
            document.getElementById('jenkins-name').focus();
        }, 100);
    }
    
    showAnsibleConfigModal() {
        // For now, show a simple prompt. In a real app, create a proper modal
        const name = prompt('Enter configuration name:');
        const localPath = prompt('Enter local Ansible path:');
        const gitRepo = prompt('Enter Git repository URL (optional):') || '';
        
        if (name && localPath) {
            this.saveAnsibleConfig(name, localPath, gitRepo);
        }
    }
    
    async saveJenkinsConfig(name, baseUrl, username, password, apiToken) {
        try {
            const requestBody = {
                name,
                base_url: baseUrl,
                username,
                api_token: apiToken,
                user_id: 'system' // In real app, use current user
            };
            
            // Only include password if provided (optional)
            if (password && password.trim()) {
                requestBody.password = password.trim();
            }
            
            const response = await fetch('/cicd/jenkins/connect', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            });
            
            const data = await response.json();
            
            if (data.success) {
                window.appendMessage(`Jenkins configuration '${name}' saved successfully`, 'system');
                await this.loadConfigurations(); // Reload configs
            } else {
                window.appendMessage(`Failed to save Jenkins config: ${data.error}`, 'system');
            }
            
        } catch (error) {
            window.appendMessage(`Error saving Jenkins config: ${error.message}`, 'system');
        }
    }
    
    async saveAnsibleConfig(name, localPath, gitRepo) {
        try {
            const response = await fetch('/cicd/ansible/connect', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name,
                    local_path: localPath,
                    git_repo_url: gitRepo,
                    user_id: 'system' // In real app, use current user
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                window.appendMessage(`Ansible configuration '${name}' saved successfully`, 'system');
                await this.loadConfigurations(); // Reload configs
            } else {
                window.appendMessage(`Failed to save Ansible config: ${data.error}`, 'system');
            }
            
        } catch (error) {
            window.appendMessage(`Error saving Ansible config: ${error.message}`, 'system');
        }
    }
}

// Initialize logs mode when DOM is loaded
let logsMode = null;

document.addEventListener('DOMContentLoaded', () => {
    // Initialize logs mode after a short delay to ensure other components are ready
    setTimeout(() => {
        logsMode = new LogsMode();
    }, 100);
});