def call(Closure body) {
	def runId = UUID.randomUUID().toString()
	try {
		notifyOpsPilot(runId, [event: 'stage_start', jobName: env.JOB_NAME, buildId: env.BUILD_ID, url: env.BUILD_URL])
		body()
		notifyOpsPilot(runId, [event: 'stage_success'])
	} catch (err) {
		notifyOpsPilot(runId, [event: 'stage_failure', error: err.toString()])
		throw err
	} finally {
		notifyOpsPilot(runId, [event: 'stage_end'])
	}
}

def notifyOpsPilot(String runId, Map payload) {
	def data = payload + [run_id: runId]
	sh "curl -s -X POST -H 'Content-Type: application/json' -d '${groovy.json.JsonOutput.toJson(data)}' ${env.OPSPILOT_URL ?: 'http://localhost:8080'}/ci/jenkins/webhook || true"
}


