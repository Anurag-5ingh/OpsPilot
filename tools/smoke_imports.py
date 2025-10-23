import importlib
import traceback
import sys
import pathlib

# Ensure project root is on sys.path so local packages can be imported
project_root = str(pathlib.Path(__file__).resolve().parents[1])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

modules_to_test = [
    'flask',
    'flask_socketio',
    'paramiko',
    'eventlet',
    'joblib',
    'sklearn',
    'numpy',
    'pandas',
    'openai',
    'ai_shell_agent',
    'ai_shell_agent.modules.cicd',
    'ai_shell_agent.modules.ssh',
    'ai_shell_agent.modules.command_generation',
    'ai_shell_agent.modules.monitoring.real_time_monitor',
    'ai_shell_agent.modules.prediction.failure_predictor'
]

results = {}
for mod in modules_to_test:
    try:
        importlib.import_module(mod)
        results[mod] = ('ok', '')
    except Exception as e:
        results[mod] = ('error', traceback.format_exc())

print('Smoke import test results:')
for mod, (status, info) in results.items():
    print(f'{mod}: {status}')
    if status == 'error':
        print(info)

# Exit code for CI use
import sys
ok = all(status == 'ok' for status, _ in results.values())
if not ok:
    sys.exit(2)
else:
    sys.exit(0)
