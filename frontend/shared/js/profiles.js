/**
 * SSH Profiles Management
 * Handles creation, editing, and management of SSH connection profiles
 */

// Global state for profiles
let profiles = [];
let currentEditingProfile = null;

/**
 * Initialize profile management
 */
function initializeProfiles() {
  setupProfileEventListeners();
  loadProfiles();
}

/**
 * Set up event listeners for profile management
 */
function setupProfileEventListeners() {
  // Profile buttons
  document.getElementById('profiles-button').addEventListener('click', showProfilesModal);
  document.getElementById('add-profile-btn').addEventListener('click', showProfileForm);
  
  // Modal close buttons
  document.getElementById('close-profiles-modal').addEventListener('click', hideProfilesModal);
  document.getElementById('close-profile-form-modal').addEventListener('click', hideProfileForm);
  
  // Profile form
  document.getElementById('profile-form').addEventListener('submit', handleProfileSave);
  document.getElementById('test-connection-btn').addEventListener('click', testConnection);
  
  // Auth method change
  document.getElementById('profile-auth-method').addEventListener('change', handleAuthMethodChange);
  
  // Bastion toggle
  document.getElementById('profile-bastion-enabled').addEventListener('change', handleBastionToggle);
  
  // Profile selector
  document.getElementById('connect-profile-btn').addEventListener('click', connectWithProfile);
  
  // Close modals when clicking outside
  document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal')) {
      if (e.target.id === 'profiles-modal') hideProfilesModal();
      if (e.target.id === 'profile-form-modal') hideProfileForm();
    }
  });
}

/**
 * Load profiles from server
 */
async function loadProfiles() {
  try {
    // Show loading indicator
    const container = document.getElementById('profiles-list-container');
    if (container) {
      let loadingEl = container.querySelector('#profiles-loading');
      if (!loadingEl) {
        loadingEl = document.createElement('div');
        loadingEl.id = 'profiles-loading';
        loadingEl.className = 'loading-indicator';
        loadingEl.textContent = '🔄 Loading profiles...';
        container.appendChild(loadingEl);
      }
    }
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000);
    
    const response = await fetch('/ssh/list', {
      method: 'GET',
      headers: { 'Accept': 'application/json', 'Cache-Control': 'no-cache' },
      signal: controller.signal
    });
    clearTimeout(timeoutId);
    if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    
    const data = await response.json();
    profiles = data || [];
    
    const containerAfter = document.getElementById('profiles-list-container');
    if (containerAfter) {
      const loadingEl = containerAfter.querySelector('#profiles-loading');
      if (loadingEl) loadingEl.remove();
    }

    updateProfilesList();
    updateProfileSelector();
    
  } catch (error) {
    console.error('Error loading profiles:', error);
    const container = document.getElementById('profiles-list-container');
    if (container) {
      let errorMessage = 'Failed to load profiles';
      if (error.name === 'AbortError') errorMessage = 'Request timeout - server may not be ready';
      else if (error.message && error.message.includes('Failed to fetch')) errorMessage = 'Cannot connect to server - make sure the application is running';
      else {
        const existingTransient = container.querySelector('.error-message-transient');
        if (existingTransient) existingTransient.remove();
        const transient = document.createElement('div');
        transient.className = 'error-message-transient';
        transient.textContent = `${errorMessage}: ${error.message || 'Unknown error'}`;
        container.appendChild(transient);
        setTimeout(() => transient.remove(), 5000);
        return;
      }
      container.innerHTML = `
        <div class="error-state">
          <div class="error-icon">❌</div>
          <div class="error-message">${errorMessage}</div>
          <button class="retry-btn" onclick="loadProfiles()">Retry</button>
        </div>
      `;
    }
  }
}

function updateProfilesList() {
  const container = document.getElementById('profiles-list-container');
  let noProfilesMsg = document.getElementById('no-profiles-message');
  if (!noProfilesMsg && container) {
    noProfilesMsg = document.createElement('div');
    noProfilesMsg.className = 'no-profiles';
    noProfilesMsg.id = 'no-profiles-message';
    noProfilesMsg.textContent = 'No profiles saved. Click "Add Profile" to create your first connection profile.';
    container.appendChild(noProfilesMsg);
  }
  if (profiles.length === 0) {
    if (noProfilesMsg) noProfilesMsg.classList.remove('hidden');
    if (container) Array.from(container.querySelectorAll('.profile-item, .error-state')).forEach(el => el.remove());
    return;
  }
  if (noProfilesMsg) noProfilesMsg.classList.add('hidden');
  const profilesHTML = profiles.map(profile => `
    <div class="profile-item" data-profile-id="${profile.id}">
      <div class="profile-info">
        <div class="profile-name">${escapeHtml(profile.name)}</div>
        <div class="profile-details">${escapeHtml(profile.username)}@${escapeHtml(profile.host)}:${profile.port} (${profile.auth_method})</div>
      </div>
      <div class="profile-actions">
        <button class="edit-profile-btn" data-profile-id="${profile.id}">Edit</button>
        <button class="test-profile-btn" data-profile-id="${profile.id}">Test</button>
        <button class="delete-profile-btn" data-profile-id="${profile.id}">Delete</button>
      </div>
    </div>`).join('');
  container.innerHTML = profilesHTML;
  container.querySelectorAll('.edit-profile-btn').forEach(btn => btn.addEventListener('click', (e) => editProfile(e.target.dataset.profileId)));
  container.querySelectorAll('.test-profile-btn').forEach(btn => btn.addEventListener('click', (e) => testProfileConnection(e.target.dataset.profileId)));
  container.querySelectorAll('.delete-profile-btn').forEach(btn => btn.addEventListener('click', (e) => deleteProfile(e.target.dataset.profileId)));
}

function updateProfileSelector() {
  const selector = document.getElementById('profile-select');
  const selectorContainer = document.getElementById('profile-selector');
  const connectBtn = document.getElementById('connect-profile-btn');
  while (selector.children.length > 1) selector.removeChild(selector.lastChild);
  if (profiles.length > 0) {
    profiles.forEach(profile => {
      const option = document.createElement('option');
      option.value = profile.id;
      option.textContent = `${profile.name} (${profile.username}@${profile.host})`;
      selector.appendChild(option);
    });
  }
  selectorContainer.classList.remove('hidden');
  if (connectBtn) connectBtn.disabled = profiles.length === 0;
}

function showProfilesModal() {
  document.getElementById('profiles-modal').classList.remove('hidden');
  loadProfiles();
}
function hideProfilesModal() {
  document.getElementById('profiles-modal').classList.add('hidden');
}

function showProfileForm(profile = null) {
  currentEditingProfile = profile;
  const modal = document.getElementById('profile-form-modal');
  const title = document.getElementById('profile-form-title');
  if (profile) { title.textContent = 'Edit SSH Profile'; populateProfileForm(profile); }
  else { title.textContent = 'Add SSH Profile'; resetProfileForm(); }
  modal.classList.remove('hidden');
  document.getElementById('profile-name').focus();
}
function hideProfileForm() {
  document.getElementById('profile-form-modal').classList.add('hidden');
  currentEditingProfile = null;
  resetProfileForm();
}
function resetProfileForm() {
  document.getElementById('profile-form').reset();
  document.getElementById('profile-port').value = '22';
  document.getElementById('profile-bastion-port').value = '22';
  document.getElementById('profile-host-key-checking').value = 'ask';
  handleAuthMethodChange();
  handleBastionToggle();
}
function populateProfileForm(profile) {
  document.getElementById('profile-name').value = profile.name;
  document.getElementById('profile-host').value = profile.host;
  document.getElementById('profile-port').value = profile.port;
  document.getElementById('profile-username').value = profile.username;
  document.getElementById('profile-auth-method').value = profile.auth_method;
  document.getElementById('profile-host-key-checking').value = profile.strict_host_key_checking || 'ask';
  if (profile.key_path) document.getElementById('profile-key-path').value = profile.key_path;
  if (profile.bastion) {
    document.getElementById('profile-bastion-enabled').checked = true;
    document.getElementById('profile-bastion-host').value = profile.bastion.host;
    document.getElementById('profile-bastion-port').value = profile.bastion.port;
    document.getElementById('profile-bastion-username').value = profile.bastion.username;
    document.getElementById('profile-bastion-auth').value = profile.bastion.auth_method;
  }
  handleAuthMethodChange();
  handleBastionToggle();
}
function handleAuthMethodChange() {
  const method = document.getElementById('profile-auth-method').value;
  const keyFields = document.getElementById('auth-key-fields');
  const passwordFields = document.getElementById('auth-password-fields');
  keyFields.classList.add('hidden');
  passwordFields.classList.add('hidden');
  if (method === 'key') keyFields.classList.remove('hidden');
  else if (method === 'password') passwordFields.classList.remove('hidden');
}
function handleBastionToggle() {
  const enabled = document.getElementById('profile-bastion-enabled').checked;
  const fields = document.getElementById('bastion-fields');
  if (enabled) fields.classList.remove('hidden'); else fields.classList.add('hidden');
}

async function handleProfileSave(e) {
  e.preventDefault();
  const saveBtn = document.querySelector('#profile-form button[type="submit"]');
  setButtonLoading(saveBtn, true);
  try {
    const formData = getProfileFormData();
    const response = await fetch('/ssh/save', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(formData) });
    const result = await response.json();
    if (response.ok) { showToast(`Profile "${formData.name}" saved`, 'success'); hideProfileForm(); loadProfiles(); }
    else { showToast(result.error || 'Failed to save profile', 'error'); }
  } catch (error) { showToast('Error saving profile: ' + error.message, 'error'); }
  finally { setButtonLoading(saveBtn, false); }
}
function getProfileFormData(forTest = false) {
  const data = {
    name: document.getElementById('profile-name').value.trim(),
    host: document.getElementById('profile-host').value.trim(),
    port: parseInt(document.getElementById('profile-port').value) || 22,
    username: document.getElementById('profile-username').value.trim(),
    auth_method: document.getElementById('profile-auth-method').value,
    strict_host_key_checking: document.getElementById('profile-host-key-checking').value
  };
  if (!forTest && !data.name) throw new Error('Profile name is required');
  if (!data.host) throw new Error('Host is required');
  if (!data.username) throw new Error('Username is required');
  if (currentEditingProfile) data.id = currentEditingProfile.id;
  if (data.auth_method === 'key') {
    const keyPath = document.getElementById('profile-key-path').value.trim();
    const passphrase = document.getElementById('profile-passphrase').value;
    if (keyPath) { data.key_path = keyPath; data.key_source = 'file'; }
    if (passphrase) data.passphrase = passphrase;
  } else if (data.auth_method === 'password') {
    const password = document.getElementById('profile-password').value; if (password) data.password = password;
  }
  if (document.getElementById('profile-bastion-enabled').checked) {
    const bastionHost = document.getElementById('profile-bastion-host').value.trim();
    const bastionUsername = document.getElementById('profile-bastion-username').value.trim();
    if (bastionHost && bastionUsername) {
      data.bastion_enabled = true;
      data.bastion_host = bastionHost;
      data.bastion_port = parseInt(document.getElementById('profile-bastion-port').value) || 22;
      data.bastion_username = bastionUsername;
      data.bastion_auth_method = document.getElementById('profile-bastion-auth').value;
    }
  }
  return data;
}
async function testConnection() {
  const testBtn = document.getElementById('test-connection-btn');
  setButtonLoading(testBtn, true);
  const msgEl = document.getElementById('profile-form-message');
  if (msgEl) { msgEl.className = 'profile-message'; msgEl.textContent = '🔄 Testing connection...'; msgEl.classList.remove('hidden'); }
  try {
    const formData = getProfileFormData(true);
    const response = await fetch('/ssh/test', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(formData) });
    const result = await response.json();
    if (response.ok && result.success) {
      if (msgEl) { msgEl.className = 'profile-message success'; msgEl.textContent = '✅ Connection test successful!'; } else { showSuccess('✅ Connection test successful!'); }
      const loginErr = document.getElementById('login-error');
      if (loginErr) { loginErr.textContent = '✅ Connection test successful!'; loginErr.style.color = 'green'; loginErr.style.display = 'block'; setTimeout(() => { loginErr.style.display = 'none'; loginErr.style.color = 'red'; }, 3000); }
    } else {
      const errorMsg = result.details || result.error || 'Connection test failed';
      if (msgEl) { msgEl.className = 'profile-message error'; msgEl.textContent = `❌ Connection test failed: ${errorMsg}`; } else { showError(`❌ Connection test failed: ${errorMsg}`); }
      const loginErr = document.getElementById('login-error');
      if (loginErr) { loginErr.textContent = `❌ Connection test failed: ${errorMsg}`; loginErr.style.color = 'red'; loginErr.style.display = 'block'; setTimeout(() => { loginErr.style.display = 'none'; }, 5000); }
    }
  } catch (error) {
    console.error('Test connection error:', error);
    const msg = '❌ Connection test error: ' + (error.message || error);
    if (msgEl) { msgEl.className = 'profile-message error'; msgEl.textContent = msg; } else { showError(msg); }
    const loginErr = document.getElementById('login-error');
    if (loginErr) { loginErr.textContent = msg; loginErr.style.color = 'red'; loginErr.style.display = 'block'; setTimeout(() => { loginErr.style.display = 'none'; }, 5000); }
  } finally {
    setButtonLoading(testBtn, false);
    if (msgEl) setTimeout(() => msgEl.classList.add('hidden'), 7000);
  }
}
async function testProfileConnection(profileId) {
  const profile = profiles.find(p => p.id === profileId);
  if (!profile) return;
  try {
    const response = await fetch('/ssh/test', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(profile) });
    const result = await response.json();
    if (result.success) showToast(`Connection test successful for "${profile.name}"`, 'success');
    else showToast(`Connection test failed for "${profile.name}": ${result.details || result.error}`, 'error');
  } catch (error) { showToast(`Connection test error for "${profile.name}": ${error.message}`, 'error'); }
}
function editProfile(profileId) { const profile = profiles.find(p => p.id === profileId); if (profile) { hideProfilesModal(); showProfileForm(profile); } }
async function deleteProfile(profileId) {
  const profile = profiles.find(p => p.id === profileId);
  if (!profile) { showError('Profile not found'); return; }
  if (!confirm(`Are you sure you want to delete profile "${profile.name}"?`)) { return; }
  try {
    const deleteBtn = document.querySelector(`[data-profile-id="${profileId}"].delete-profile-btn`);
    if (deleteBtn) { deleteBtn.disabled = true; deleteBtn.textContent = 'Deleting...'; }
    const response = await fetch(`/ssh/delete/${profileId}`, { method: 'DELETE' });
    const result = await response.json();
    if (response.ok) { showSuccess(`🗑️ Profile "${profile.name}" deleted successfully`); await loadProfiles(); }
    else { showError(result.error || 'Failed to delete profile'); }
  } catch (error) { console.error('Delete profile error:', error); showError('Error deleting profile: ' + error.message); }
  finally {
    const deleteBtn = document.querySelector(`[data-profile-id="${profileId}"].delete-profile-btn`);
    if (deleteBtn) { deleteBtn.disabled = false; deleteBtn.textContent = 'Delete'; }
  }
}
function connectWithProfile() {
  const profileId = document.getElementById('profile-select').value;
  if (!profileId) { showError('Please select a profile'); return; }
  const profile = profiles.find(p => p.id === profileId);
  if (!profile) { showError('Profile not found'); return; }
  state.currentHost = profile.host; state.currentUser = profile.username; state.selectedProfileId = profileId;
  document.getElementById('login-screen').classList.add('hidden');
  document.getElementById('main-screen').classList.remove('hidden');
  initializeTerminalWithProfile(profileId);
  document.getElementById('user-input').focus();
}
function initializeTerminalWithProfile(profileId) {
  state.selectedProfileId = profileId; initializeTerminal();
  if (state.socket) {
    state.socket.on('connect', () => { showToast('Connecting with profile...', 'info'); state.socket.emit('start_ssh', { profileId }); });
    state.socket.on('hostkey_unknown', data => { showHostKeyModal(data); });
    state.socket.on('auth_prompt', data => { showAuthPromptModal(data); });
  }
}
function showHostKeyModal(data) {
  document.getElementById('hostkey-hostname').textContent = data.hostname;
  document.getElementById('hostkey-type').textContent = data.key_type;
  document.getElementById('hostkey-fingerprint').textContent = data.fingerprint;
  const modal = document.getElementById('hostkey-modal'); modal.classList.remove('hidden');
  document.getElementById('hostkey-accept').onclick = () => { state.socket.emit('hostkey_trust', { decision: true }); modal.classList.add('hidden'); };
  document.getElementById('hostkey-reject').onclick = () => { state.socket.emit('hostkey_trust', { decision: false }); modal.classList.add('hidden'); };
}
function showAuthPromptModal(data) {
  document.getElementById('auth-prompt-title').textContent = data.title || 'Authentication Required';
  document.getElementById('auth-prompt-instructions').textContent = data.instructions || '';
  const fieldsContainer = document.getElementById('auth-prompt-fields');
  fieldsContainer.innerHTML = '';
  data.prompts.forEach((prompt, index) => {
    const div = document.createElement('div'); div.className = 'form-group';
    const label = document.createElement('label'); label.textContent = prompt.prompt;
    const input = document.createElement('input'); input.type = prompt.echo ? 'text' : 'password'; input.id = `auth-prompt-${index}`; input.placeholder = prompt.prompt;
    div.appendChild(label); div.appendChild(input); fieldsContainer.appendChild(div);
  });
  const modal = document.getElementById('auth-prompt-modal'); modal.classList.remove('hidden');
  const firstInput = fieldsContainer.querySelector('input'); if (firstInput) firstInput.focus();
  document.getElementById('auth-prompt-submit').onclick = () => { const answers = Array.from(fieldsContainer.querySelectorAll('input')).map(input => input.value); state.socket.emit('auth_response', { answers }); modal.classList.add('hidden'); };
  document.getElementById('auth-prompt-cancel').onclick = () => { state.socket.emit('auth_response', { answers: [] }); modal.classList.add('hidden'); };
}
function escapeHtml(text) { const div = document.createElement('div'); div.textContent = text; return div.innerHTML; }
function showError(message) { const errorDiv = document.getElementById('login-error'); if (errorDiv) { errorDiv.textContent = message; errorDiv.style.display = 'block'; setTimeout(() => { errorDiv.style.display = 'none'; }, 5000); } if (document.getElementById('main-screen') && !document.getElementById('main-screen').classList.contains('hidden')) { appendMessage(`❌ ${message}`, 'error'); } else { console.error(message); } }
function showSuccess(message) { if (document.getElementById('main-screen') && !document.getElementById('main-screen').classList.contains('hidden')) { appendMessage(`✅ ${message}`, 'system'); } else { const errorDiv = document.getElementById('login-error'); if (errorDiv) { errorDiv.textContent = message; errorDiv.style.color = 'green'; errorDiv.style.display = 'block'; setTimeout(() => { errorDiv.style.display = 'none'; errorDiv.style.color = 'red'; }, 3000); } } }
function delayedInitialize() { setTimeout(() => { initializeProfiles(); }, 1000); }
if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', delayedInitialize); } else { delayedInitialize(); }
