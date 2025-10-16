async function fetchCiRuns() {
	const res = await fetch('/ci/runs');
	return await res.json();
}

async function fetchCiRun(runId) {
	const res = await fetch(`/ci/runs/${encodeURIComponent(runId)}`);
	return await res.json();
}

async function renderCiDashboard() {
	const container = document.getElementById('ci-dashboard');
	if (!container) return;
	container.innerHTML = '<div class="section-title">CI Runs</div><div id="ci-runs-list" class="runs-list"></div><div id="ci-run-detail" class="run-detail"></div>';
	const data = await fetchCiRuns();
	const listEl = document.getElementById('ci-runs-list');
	listEl.innerHTML = '';
	(data.runs || []).forEach(run => {
		const item = document.createElement('div');
		item.className = 'run-item';
		item.innerHTML = `
			<div class="run-title">${run.job_name || 'unknown'} <span class="run-id">#${run.jenkins_build_id || run.id}</span></div>
			<div class="run-meta">status: ${run.status || 'unknown'} | updated: ${new Date((run.updated_at||0)*1000).toLocaleString()}</div>
			<div class="run-link">${run.links ? `<a href="${run.links}" target="_blank">Open Jenkins</a>` : ''}</div>
		`;
		item.addEventListener('click', async () => {
			const detail = await fetchCiRun(run.id);
			renderRunDetail(detail.run);
		});
		listEl.appendChild(item);
	});
	const params = new URLSearchParams(window.location.search);
	const runId = params.get('run');
	if (runId) {
		const detail = await fetchCiRun(runId);
		renderRunDetail(detail.run);
	}
}

function renderRunDetail(run) {
	const detailEl = document.getElementById('ci-run-detail');
	if (!detailEl) return;
	detailEl.innerHTML = `
		<div class="section-title">Run Detail</div>
		<div><strong>Run ID:</strong> ${run.id}</div>
		<div><strong>Job:</strong> ${run.job_name || 'unknown'}</div>
		<div><strong>Status:</strong> ${run.status || 'unknown'}</div>
		<div class="events-title">Events</div>
		<div class="events">${(run.events||[]).map(e => `<pre class="event">[${new Date((e.created_at||0)*1000).toLocaleString()}] ${e.type}\n${escapeHtml(e.payload||'')}</pre>`).join('')}</div>
	`;
}

function escapeHtml(s) {
	return String(s)
		.replaceAll('&', '&amp;')
		.replaceAll('<', '&lt;')
		.replaceAll('>', '&gt;');
}

document.addEventListener('DOMContentLoaded', () => {
	const navBtn = document.getElementById('nav-ci');
	if (navBtn) {
		navBtn.addEventListener('click', (e) => {
			e.preventDefault();
			window.location.href = '/opspilot?view=ci';
		});
	}
	const url = new URL(window.location.href);
	if (url.searchParams.get('view') === 'ci') {
		const main = document.getElementById('main-screen');
		if (main) {
			main.classList.remove('hidden');
			main.innerHTML = '<div id="ci-dashboard" class="ci-dashboard"></div>';
			renderCiDashboard();
		}
	}
});


