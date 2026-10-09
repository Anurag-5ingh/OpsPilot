/**
 * OpsPilot browser demo backend
 *
 * Loaded before the app's own scripts in the hosted demo (see demo/build.sh).
 * It replaces window.fetch for the app's API routes and window.io with a fake
 * Socket.IO connection to a simulated shell, so the real UI runs with no
 * server: canned AI answers and a pretend terminal. Nothing leaves the browser.
 */
(function () {
  'use strict';

  var REPO_URL = 'https://github.com/Anurag-5ingh/OpsPilot';

  // ---------------------------------------------------------------------------
  // Simulated machine
  // ---------------------------------------------------------------------------

  var machine = {
    user: 'demo',
    host: 'opspilot-demo',
    home: '/home/demo',
    cwd: '/home/demo',
    dirs: {
      '/home/demo': ['app', 'logs', 'backups', 'deploy.sh', 'notes.txt'],
      '/home/demo/app': ['app.py', 'requirements.txt', 'config.yaml', 'static'],
      '/home/demo/logs': ['app.log', 'error.log', 'access.log'],
      '/home/demo/backups': ['db-2026-10-01.sql.gz', 'db-2026-10-08.sql.gz'],
      '/var/log/nginx': ['access.log', 'error.log']
    }
  };

  function prompt() {
    var dir = machine.cwd === machine.home ? '~' : machine.cwd.replace(machine.home, '~');
    return '\x1b[1;32m' + machine.user + '@' + machine.host + '\x1b[0m:\x1b[1;34m' + dir + '\x1b[0m$ ';
  }

  function resolvePath(arg) {
    if (!arg || arg === '~') return machine.home;
    if (arg.indexOf('~/') === 0) arg = machine.home + arg.slice(1);
    var path = arg.charAt(0) === '/' ? arg : machine.cwd + '/' + arg;
    var parts = [];
    path.split('/').forEach(function (p) {
      if (!p || p === '.') return;
      if (p === '..') parts.pop(); else parts.push(p);
    });
    return '/' + parts.join('/');
  }

  var OUT = {
    df: [
      'Filesystem      Size  Used Avail Use% Mounted on',
      '/dev/sda1        80G   61G   19G  77% /',
      'tmpfs           2.0G     0  2.0G   0% /dev/shm',
      '/dev/sdb1       200G  142G   58G  72% /data'
    ],
    free: [
      '               total        used        free      shared  buff/cache   available',
      'Mem:           7.8Gi       5.1Gi       412Mi        96Mi       2.3Gi       2.3Gi',
      'Swap:          2.0Gi       640Mi       1.4Gi'
    ],
    ps: [
      'USER         PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND',
      'demo        2231 38.2 12.4 2481220 998312 ?     Sl   09:12  41:07 python3 app.py',
      'postgres     812 11.6  8.9 1302420 716244 ?     Ss   Oct08  92:15 postgres: writer',
      'www-data    1043  4.1  1.2 156844  98120 ?      S    Oct08   7:40 nginx: worker process',
      'root         644  1.3  0.9 1817720 74012 ?      Ssl  Oct08   3:02 dockerd',
      'demo        3310  0.4  0.3  28420  24112 pts/0  Ss   10:01   0:00 -bash'
    ],
    du: [
      '4.2G\t/home/demo/backups/db-2026-10-08.sql.gz',
      '4.1G\t/home/demo/backups/db-2026-10-01.sql.gz',
      '1.8G\t/home/demo/logs/app.log',
      '612M\t/home/demo/logs/access.log',
      '96M\t/home/demo/app/static'
    ],
    port: [
      'COMMAND   PID USER   FD   TYPE DEVICE SIZE/OFF NODE NAME',
      'python3  2231 demo    5u  IPv4  48213      0t0  TCP *:8080 (LISTEN)'
    ],
    ss: [
      'State   Recv-Q  Send-Q   Local Address:Port    Peer Address:Port  Process',
      'LISTEN  0       511            0.0.0.0:80           0.0.0.0:*      users:(("nginx",pid=1043))',
      'LISTEN  0       128            0.0.0.0:22           0.0.0.0:*      users:(("sshd",pid=702))',
      'LISTEN  0       244          127.0.0.1:5432         0.0.0.0:*      users:(("postgres",pid=812))',
      'LISTEN  0       2048           0.0.0.0:8080         0.0.0.0:*      users:(("python3",pid=2231))'
    ],
    nginx: [
      '\x1b[1;31m×\x1b[0m nginx.service - A high performance web server and a reverse proxy server',
      '     Loaded: loaded (/lib/systemd/system/nginx.service; enabled; vendor preset: enabled)',
      '     Active: \x1b[1;31mfailed\x1b[0m (Result: exit-code) since Fri 2026-10-09 09:58:12 UTC; 3min ago',
      '    Process: 4120 ExecStartPre=/usr/sbin/nginx -t -q -g daemon on; (code=exited, status=1/FAILURE)',
      '',
      'Oct 09 09:58:12 opspilot-demo nginx[4120]: nginx: [emerg] unexpected "}" in /etc/nginx/sites-enabled/app:14',
      'Oct 09 09:58:12 opspilot-demo nginx[4120]: nginx: configuration file /etc/nginx/nginx.conf test failed',
      'Oct 09 09:58:12 opspilot-demo systemd[1]: nginx.service: Failed with result \'exit-code\'.'
    ],
    nginxTest: [
      'nginx: [emerg] unexpected "}" in /etc/nginx/sites-enabled/app:14',
      'nginx: configuration file /etc/nginx/nginx.conf test failed'
    ],
    nginxErrLog: [
      '2026/10/09 09:57:40 [error] 1043#1043: *8812 connect() failed (111: Connection refused) while connecting to upstream, client: 10.0.4.17, server: app.example.com, request: "GET /api/health HTTP/1.1", upstream: "http://127.0.0.1:8000/api/health"',
      '2026/10/09 09:57:52 [error] 1043#1043: *8820 connect() failed (111: Connection refused) while connecting to upstream, client: 10.0.4.17, server: app.example.com, request: "GET / HTTP/1.1", upstream: "http://127.0.0.1:8000/"',
      '2026/10/09 09:58:12 [emerg] 4120#4120: unexpected "}" in /etc/nginx/sites-enabled/app:14'
    ],
    appLog: [
      '2026-10-09 09:55:01 INFO  Starting worker pool (4 workers)',
      '2026-10-09 09:56:13 WARN  Slow query (2.8s): SELECT * FROM orders WHERE status = \'pending\'',
      '2026-10-09 09:57:38 ERROR Worker 3 crashed: MemoryError',
      '2026-10-09 09:57:39 INFO  Restarting worker 3',
      '2026-10-09 09:59:02 ERROR OSError: [Errno 28] No space left on device: \'/home/demo/logs/app.log\''
    ],
    docker: [
      'CONTAINER ID   IMAGE              COMMAND                  STATUS                  PORTS                    NAMES',
      '4f2a91c03b7e   postgres:16        "docker-entrypoint.s…"   Up 26 hours             0.0.0.0:5432->5432/tcp   db',
      '9c1d77e5a210   redis:7-alpine     "docker-entrypoint.s…"   Up 26 hours             6379/tcp                 cache',
      'b83e0f4c66d1   myapp/worker:1.4   "python worker.py"       Restarting (1) 8s ago                            worker'
    ],
    osRelease: [
      'PRETTY_NAME="Ubuntu 22.04.4 LTS"',
      'NAME="Ubuntu"',
      'VERSION_ID="22.04"',
      'VERSION="22.04.4 LTS (Jammy Jellyfish)"',
      'ID=ubuntu',
      'ID_LIKE=debian'
    ],
    ping: [
      'PING example.com (93.184.215.14) 56(84) bytes of data.',
      '64 bytes from 93.184.215.14: icmp_seq=1 ttl=56 time=11.8 ms',
      '64 bytes from 93.184.215.14: icmp_seq=2 ttl=56 time=12.1 ms',
      '64 bytes from 93.184.215.14: icmp_seq=3 ttl=56 time=11.6 ms',
      '',
      '--- example.com ping statistics ---',
      '3 packets transmitted, 3 received, 0% packet loss, time 2003ms',
      'rtt min/avg/max/mdev = 11.6/11.8/12.1/0.2 ms'
    ],
    curlHealth: ['curl: (7) Failed to connect to 127.0.0.1 port 8000 after 0 ms: Connection refused'],
    help: [
      'This is a simulated terminal running in your browser. Try:',
      '  ls, cd, pwd, whoami, hostname, uname -a, date, uptime',
      '  df -h, free -h, ps aux, du -ah ~ | sort -rh | head',
      '  systemctl status nginx, sudo nginx -t, docker ps',
      '  tail /var/log/nginx/error.log, tail ~/logs/app.log',
      '  lsof -i :8080, ss -tulpn, ping example.com',
      '',
      'Or ask the chat on the left. Run OpsPilot locally for a real terminal:',
      '  ' + REPO_URL
    ]
  };

  // Each entry: [test(cmd), output lines or function(cmd, args) -> lines]
  var COMMANDS = [
    [/^(help|\?)$/, OUT.help],
    [/^clear$/, function () { return '\x1b[2J\x1b[H'; }],
    [/^pwd$/, function () { return [machine.cwd]; }],
    [/^whoami$/, function () { return [machine.user]; }],
    [/^hostname$/, function () { return [machine.host]; }],
    [/^id$/, function () { return ['uid=1000(demo) gid=1000(demo) groups=1000(demo),27(sudo),998(docker)']; }],
    [/^uname/, function (c) { return [/-a/.test(c) ? 'Linux opspilot-demo 5.15.0-118-generic #128-Ubuntu SMP x86_64 GNU/Linux' : 'Linux']; }],
    [/^date/, function () { return [new Date().toUTCString()]; }],
    [/^uptime/, function () { return [' 10:02:44 up 1 day,  2:14,  1 user,  load average: 2.41, 1.97, 1.62']; }],
    [/^echo\b/, function (c) { return [c.replace(/^echo\s*/, '').replace(/^["']|["']$/g, '')]; }],
    [/^cat .*os-release/, OUT.osRelease],
    [/^cat .*notes\.txt/, function () { return ['TODO: rotate backups, fix nginx config, check disk usage on /']; }],
    [/^df\b/, OUT.df],
    [/^free\b/, OUT.free],
    [/^(top|htop)\b/, function () { return ['(interactive tools are not simulated; showing a snapshot)', ''].concat(OUT.ps); }],
    [/^ps\b/, OUT.ps],
    [/^du\b|^find .*-size/, OUT.du],
    [/^(sudo )?(lsof|fuser)\b/, OUT.port],
    [/^(sudo )?(ss|netstat)\b/, OUT.ss],
    [/^(sudo )?systemctl (status|is-active) nginx/, OUT.nginx],
    [/^(sudo )?systemctl (restart|start|reload) nginx/, function () { return ['Job for nginx.service failed because the control process exited with error code.', 'See "systemctl status nginx.service" and "journalctl -xeu nginx.service" for details.']; }],
    [/^(sudo )?journalctl/, function () { return OUT.nginx.slice(5); }],
    [/^(sudo )?nginx -t/, OUT.nginxTest],
    [/nginx\/error\.log/, OUT.nginxErrLog],
    [/app\.log|error\.log/, OUT.appLog],
    [/^(sudo )?docker (ps|container ls)/, OUT.docker],
    [/^(sudo )?docker logs/, function () { return ['Traceback (most recent call last):', '  File "/app/worker.py", line 12, in <module>', '    conn = redis.Redis(host=os.environ["REDIS_HOST"])', 'KeyError: \'REDIS_HOST\'']; }],
    [/^ping\b/, OUT.ping],
    [/^curl .*(8000|health)/, OUT.curlHealth],
    [/^(sudo )?(apt|apt-get|yum|dnf|brew|pip|npm)\b/, function () { return ['Package installs are not simulated in the demo.']; }],
    [/^(sudo )?(rm|mv|cp|chmod|chown|kill|pkill|reboot|shutdown)\b/, function (c) { return ['[demo] "' + c + '" would change the system, so it was not run. Nothing here is real.']; }],
    [/^(mkdir|touch)\s+\S/, function (c) {
      var parts = c.split(/\s+/);
      var list = machine.dirs[machine.cwd] || (machine.dirs[machine.cwd] = []);
      parts.slice(1).forEach(function (n) { if (n.charAt(0) !== '-' && list.indexOf(n) < 0) list.push(n); });
      return [];
    }],
    [/^cd\b/, function (c) {
      var target = resolvePath(c.split(/\s+/)[1]);
      if (machine.dirs[target] || target === '/') { machine.cwd = target; return []; }
      return ['bash: cd: ' + c.split(/\s+/)[1] + ': No such file or directory'];
    }],
    [/^ls\b/, function (c) {
      var arg = c.split(/\s+/).filter(function (a) { return a !== 'ls' && a.charAt(0) !== '-'; })[0];
      var dir = resolvePath(arg || machine.cwd);
      var items = machine.dirs[dir];
      if (!items) return ['ls: cannot access \'' + (arg || dir) + '\': No such file or directory'];
      if (/-\w*l/.test(c)) {
        return ['total ' + (items.length * 4)].concat(items.map(function (n) {
          var isDir = !!machine.dirs[dir + '/' + n];
          return (isDir ? 'drwxr-xr-x' : '-rw-r--r--') + ' 1 demo demo ' + (isDir ? ' 4096' : ' 1820') + ' Oct  9 09:41 ' + (isDir ? '\x1b[1;34m' + n + '\x1b[0m' : n);
        }));
      }
      return [items.map(function (n) { return machine.dirs[dir + '/' + n] ? '\x1b[1;34m' + n + '\x1b[0m' : n; }).join('  ')];
    }]
  ];

  function runCommand(line) {
    var cmd = line.trim();
    if (!cmd) return '';
    for (var i = 0; i < COMMANDS.length; i++) {
      if (COMMANDS[i][0].test(cmd)) {
        var out = COMMANDS[i][1];
        out = typeof out === 'function' ? out(cmd) : out;
        if (typeof out === 'string') return out;
        return out.length ? out.join('\r\n') + '\r\n' : '';
      }
    }
    var name = cmd.split(/\s+/)[0];
    return '[demo] "' + name + '" isn\'t simulated here. Type "help" for what works, or run OpsPilot locally.\r\n';
  }

  // ---------------------------------------------------------------------------
  // Fake Socket.IO connection to the simulated shell
  // ---------------------------------------------------------------------------

  function FakeSocket() {
    this.connected = false;
    this._handlers = {};
    this._line = '';
    this._started = false;
    var self = this;
    setTimeout(function () { self.connected = true; self._fire('connect'); }, 150);
  }
  FakeSocket.prototype.on = function (event, cb) {
    (this._handlers[event] = this._handlers[event] || []).push(cb);
    return this;
  };
  FakeSocket.prototype.off = function (event) { delete this._handlers[event]; return this; };
  FakeSocket.prototype.connect = function () { return this; };
  FakeSocket.prototype.disconnect = function () { return this; };
  FakeSocket.prototype._fire = function (event, data) {
    (this._handlers[event] || []).forEach(function (cb) { try { cb(data); } catch (e) { console.error(e); } });
  };
  FakeSocket.prototype._write = function (text) {
    var self = this;
    setTimeout(function () { self._fire('terminal_output', { output: text }); }, 0);
  };
  FakeSocket.prototype.emit = function (event, data) {
    data = data || {};
    if ((event === 'start_local' || event === 'start_ssh') && this._started) {
      // The app requests a session more than once on connect; keep the current one
      return this;
    }
    if (event === 'start_local' || event === 'start_ssh') {
      if (event === 'start_ssh' && data.user) machine.user = String(data.user).replace(/[^\w.-]/g, '') || 'demo';
      if (event === 'start_ssh' && data.ip) machine.host = String(data.ip).replace(/[^\w.-]/g, '') || 'opspilot-demo';
      machine.home = machine.cwd = '/home/demo';
      this._line = '';
      this._write('Connected to ' + machine.host + ' (simulated demo terminal)\r\n' +
        'Nothing here is real. Type "help" to see what you can try.\r\n\r\n' + prompt());
      this._started = true;
    } else if (event === 'terminal_input' && this._started) {
      this._input(String(data.input || ''));
    }
    return this;
  };
  FakeSocket.prototype._input = function (text) {
    var out = '';
    for (var i = 0; i < text.length; i++) {
      var ch = text[i];
      if (ch === '\r' || ch === '\n') {
        if (ch === '\n' && text[i - 1] === '\r') continue;
        var line = this._line;
        this._line = '';
        out += '\r\n' + runCommand(line) + prompt();
      } else if (ch === '\x7f' || ch === '\b') {
        if (this._line.length) { this._line = this._line.slice(0, -1); out += '\b \b'; }
      } else if (ch === '\x03') {
        this._line = '';
        out += '^C\r\n' + prompt();
      } else if (ch === '\x1b') {
        // Skip escape sequences (arrow keys etc.)
        while (i + 1 < text.length && !/[A-Za-z~]/.test(text[i + 1])) i++;
        i++;
      } else if (ch >= ' ') {
        this._line += ch;
        out += ch;
      }
    }
    if (out) this._write(out);
  };

  window.io = function () { return new FakeSocket(); };

  // ---------------------------------------------------------------------------
  // Canned AI answers
  // ---------------------------------------------------------------------------

  var RISKY = {
    requires_confirmation: true,
    risk_level: 'high',
    warning_message: 'This command can permanently delete data or interrupt running services.',
    affected_areas: ['Files under the target path', 'Running services that depend on them'],
    detailed_impacts: ['Deleted files cannot be recovered without a backup'],
    safety_recommendations: ['Preview what will be affected first (for example with ls or find)', 'Make sure a recent backup exists']
  };

  var ASK_RULES = [
    [/disk|space|storage|full/, 'Check disk usage on all mounted filesystems', 'df -h'],
    [/memory|ram|swap/, 'Show memory and swap usage', 'free -h'],
    [/(large|big)(est)? files?|what.*taking.*space/, 'List the 5 largest files in your home folder', 'du -ah ~ 2>/dev/null | sort -rh | head -n 5'],
    [/port|listening|8080/, 'Find which process is listening on port 8080', 'lsof -i :8080'],
    [/nginx/, 'Check the nginx service status', 'systemctl status nginx'],
    [/docker|container/, 'List running containers', 'docker ps'],
    [/process|cpu|slow|running/, 'Show running processes sorted by CPU usage', 'ps aux --sort=-%cpu | head -n 6'],
    [/log|error/, 'Show the last lines of the application log', 'tail -n 20 ~/logs/app.log'],
    [/os|version|distro|system/, 'Show the OS name and version', 'cat /etc/os-release'],
    [/uptime|load/, 'Show uptime and load average', 'uptime'],
    [/network|internet|ping|connect/, 'Check network connectivity', 'ping -c 3 example.com'],
    [/delete|remove|clean|purge/, 'Delete old backup files', 'rm -rf ~/backups/*', RISKY],
    [/kill|stop/, 'Stop the process using port 8080', 'kill 2231', {
      requires_confirmation: true, risk_level: 'medium',
      warning_message: 'This stops a running process. Anything it is doing will be interrupted.',
      affected_areas: ['python3 app.py (PID 2231)'], detailed_impacts: ['The app on port 8080 goes offline'],
      safety_recommendations: ['Check what the process is first with ps -p 2231 -f']
    }],
    [/files|list|folder|directory/, 'List files in the current folder', 'ls -la']
  ];

  function askAnswer(prompt) {
    var p = (prompt || '').toLowerCase();
    for (var i = 0; i < ASK_RULES.length; i++) {
      var r = ASK_RULES[i];
      if (r[0].test(p)) {
        return { action_text: r[1], final_command: r[2], risk_analysis: r[3] || { requires_confirmation: false, risk_level: 'low' } };
      }
    }
    return {
      action_text: 'The demo only knows a few requests (try "disk usage", "what is using port 8080", "is nginx running", "biggest files"). Here is a general overview',
      final_command: 'uptime',
      risk_analysis: { requires_confirmation: false, risk_level: 'low' }
    };
  }

  var TROUBLESHOOT_RULES = [
    [/nginx|502|bad gateway|upstream/, {
      analysis: 'nginx is failing its config test: there is a stray "}" on line 14 of /etc/nginx/sites-enabled/app. Separately, the upstream app on port 8000 is refusing connections, which causes the 502s.',
      diagnostic_commands: ['systemctl status nginx', 'sudo nginx -t', 'tail -n 20 /var/log/nginx/error.log'],
      fix_commands: ['sudo sed -n \'10,16p\' /etc/nginx/sites-enabled/app', 'sudo nginx -t && sudo systemctl reload nginx'],
      verification_commands: ['systemctl is-active nginx', 'curl -I http://localhost']
    }],
    [/address already in use|port.*(in use|busy)|eaddrinuse/, {
      analysis: 'Another process is already bound to the port. Here it is python3 app.py (PID 2231) listening on 8080.',
      diagnostic_commands: ['lsof -i :8080', 'ss -tulpn'],
      fix_commands: ['kill 2231', 'PORT=8081 python app.py'],
      verification_commands: ['lsof -i :8080']
    }],
    [/no space|disk full|errno 28/, {
      analysis: 'The root filesystem is filling up. Old database backups (8.3G) and a 1.8G app log are the largest items in /home/demo.',
      diagnostic_commands: ['df -h', 'du -ah ~ 2>/dev/null | sort -rh | head -n 5'],
      fix_commands: ['gzip ~/logs/app.log', 'rm ~/backups/db-2026-10-01.sql.gz'],
      verification_commands: ['df -h /']
    }],
    [/permission denied/, {
      analysis: 'The current user lacks permission for that file or action. Check the file owner and mode, then use sudo or fix ownership rather than chmod 777.',
      diagnostic_commands: ['id', 'ls -la'],
      fix_commands: ['sudo chown demo:demo ~/app/config.yaml', 'chmod 640 ~/app/config.yaml'],
      verification_commands: ['ls -la ~/app']
    }],
    [/connection refused|refused/, {
      analysis: 'Nothing is listening on the target port. The service is probably down or bound to a different address.',
      diagnostic_commands: ['ss -tulpn', 'curl -v http://127.0.0.1:8000/api/health'],
      fix_commands: ['sudo systemctl restart myapp', 'journalctl -u myapp -n 50'],
      verification_commands: ['curl -I http://127.0.0.1:8000/api/health']
    }],
    [/docker|container|restarting|keyerror/, {
      analysis: 'The worker container is crash-looping: worker.py reads REDIS_HOST from the environment, but it isn\'t set.',
      diagnostic_commands: ['docker ps', 'docker logs worker --tail 20'],
      fix_commands: ['docker rm -f worker && docker run -d --name worker -e REDIS_HOST=cache myapp/worker:1.4'],
      verification_commands: ['docker ps']
    }]
  ];

  function troubleshootAnswer(text) {
    var t = (text || '').toLowerCase();
    for (var i = 0; i < TROUBLESHOOT_RULES.length; i++) {
      if (TROUBLESHOOT_RULES[i][0].test(t)) return TROUBLESHOOT_RULES[i][1];
    }
    return {
      analysis: 'The demo recognizes a few common errors (try pasting "nginx 502 bad gateway", "address already in use", "No space left on device" or "connection refused"). Start by checking system health:',
      diagnostic_commands: ['uptime', 'df -h', 'free -h'],
      fix_commands: ['ps aux --sort=-%cpu | head -n 6'],
      verification_commands: []
    };
  }

  var JENKINS_LOG = [
    'Started by user demo',
    'Running in Durability level: MAX_SURVIVABILITY',
    '[Pipeline] Start of Pipeline',
    '[Pipeline] node',
    'Running on build-agent-2 in /var/lib/jenkins/workspace/web-app-deploy',
    '[Pipeline] stage (Checkout)',
    ' > git fetch --tags --progress origin +refs/heads/main:refs/remotes/origin/main',
    'Checking out Revision 8f3c2a1 (origin/main)',
    '[Pipeline] stage (Deploy)',
    '+ ansible-playbook -i inventory/prod deploy.yml',
    '',
    'PLAY [webservers] **************************************************************',
    '',
    'TASK [Gathering Facts] *********************************************************',
    'ok: [web-01]',
    'ok: [web-02]',
    '',
    'TASK [app : Install Python dependencies] ***************************************',
    'ok: [web-01]',
    'ok: [web-02]',
    '',
    'TASK [app : Render nginx site config] ******************************************',
    'changed: [web-01]',
    'changed: [web-02]',
    '',
    'TASK [app : Reload nginx] ******************************************************',
    'fatal: [web-01]: FAILED! => {"changed": false, "msg": "Unable to reload service nginx: Job for nginx.service failed because the control process exited with error code.\\nnginx: [emerg] unknown directive \\"proxy_passs\\" in /etc/nginx/sites-enabled/app:21"}',
    'fatal: [web-02]: FAILED! => {"changed": false, "msg": "Unable to reload service nginx: Job for nginx.service failed because the control process exited with error code.\\nnginx: [emerg] unknown directive \\"proxy_passs\\" in /etc/nginx/sites-enabled/app:21"}',
    '',
    'PLAY RECAP *********************************************************************',
    'web-01                     : ok=3    changed=1    unreachable=0    failed=1    skipped=0',
    'web-02                     : ok=3    changed=1    unreachable=0    failed=1    skipped=0',
    '',
    '[Pipeline] }',
    'ERROR: script returned exit code 2',
    'Finished: FAILURE'
  ].join('\n');

  var JENKINS_ANALYSIS = {
    success: true,
    root_cause: 'Typo in the nginx site template: "proxy_passs" (three s) on line 21 of /etc/nginx/sites-enabled/app, so nginx rejects the config and the reload task fails on every host.',
    error_summary: 'Ansible task "app : Reload nginx" failed on web-01 and web-02: unknown directive "proxy_passs".',
    confidence: 0.94,
    suggested_steps: [
      'Fix the directive name to "proxy_pass" in the role template (roles/app/templates/nginx-site.conf.j2).',
      'Add a validate step to the template task, e.g. validate: "nginx -t -c %s", so a bad config is never installed.',
      'Re-run the pipeline, or run: ansible-playbook -i inventory/prod deploy.yml --tags nginx'
    ],
    suggested_playbook: [
      '- name: Render nginx site config',
      '  template:',
      '    src: nginx-site.conf.j2',
      '    dest: /etc/nginx/sites-enabled/app',
      '    validate: "nginx -t -c /etc/nginx/nginx.conf"',
      '  notify: Reload nginx'
    ].join('\n')
  };

  // ---------------------------------------------------------------------------
  // fetch() routes
  // ---------------------------------------------------------------------------

  function jobFromUrl(url) {
    var jobs = [];
    var re = /\/job\/([^/]+)/g, m;
    while ((m = re.exec(url))) jobs.push(decodeURIComponent(m[1]));
    var build = (url.match(/\/(\d+)\/console/) || [])[1] || '42';
    return { job_name: jobs.join('/') || 'web-app-deploy', build_number: build };
  }

  var DISABLED = { status: 403, body: { success: false, error: 'This is disabled in the demo. Run OpsPilot locally to use it.' } };

  var ROUTES = [
    ['GET', /^\/guest\/status$/, function () { return { available: true }; }],
    ['POST', /^\/run$/, function (b) { return b.host && b.command ? { output: 'connected\n', error: '' } : { status: 400, body: { error: 'host and command are required' } }; }],
    ['POST', /^\/ask$/, function (b) {
      var a = askAnswer(b.prompt);
      return { ai_command: a.final_command, ai_response: a, original_prompt: b.prompt };
    }],
    ['POST', /^\/profile$/, function (b) {
      return {
        success: true,
        profile: { os: 'Ubuntu 22.04', package_manager: 'apt', init_system: 'systemd' },
        summary: 'Host: ' + (b.host || machine.host) + ' (simulated)\nOS: Ubuntu 22.04.4 LTS (x86_64)\nPackage manager: apt\nInit system: systemd\nTools: docker, nginx, python3, git, postgresql'
      };
    }],
    ['GET', /^\/profile\/(summary|suggestions\/.*)$/, function () { return { success: true, suggestions: [], summary: '' }; }],
    ['POST', /^\/troubleshoot(\/analyze)?$/, function (b) { return troubleshootAnswer(b.error_text); }],
    ['POST', /^\/troubleshoot\/suggest-fix$/, function (b) {
      var text = (b.diagnostic_results || []).map(function (r) { return (r.command || '') + ' ' + (r.output || ''); }).join(' ');
      var a = troubleshootAnswer(text);
      return { reasoning: a.analysis, fix_commands: a.fix_commands, verification_commands: a.verification_commands };
    }],
    ['POST', /^\/analyze-failure$/, function () {
      return { failure_analysis: { root_cause: 'The command failed in the simulated environment.' }, alternative_solutions: [] };
    }],
    ['GET', /^\/ssh\/list$/, function () { return []; }],
    ['POST', /^\/ssh\/(save|test)$/, function () { return DISABLED; }],
    ['DELETE', /^\/ssh\/delete\//, function () { return DISABLED; }],
    ['GET', /^\/cicd\/(jenkins|ansible)\/configs/, function () { return { success: true, configs: [] }; }],
    ['POST', /^\/cicd\/(jenkins|ansible)\/connect$/, function () { return DISABLED; }],
    ['POST', /^\/cicd\/jenkins\/console$/, function (b) {
      var job = jobFromUrl(b.console_url || '');
      return { success: true, job_name: job.job_name, build_number: job.build_number, console_log: JENKINS_LOG };
    }],
    ['POST', /^\/cicd\/(analyze\/console|builds\/\d+\/analyze)$/, function () { return { success: true, analysis: JENKINS_ANALYSIS }; }],
    ['GET', /^\/cicd\/builds/, function () { return { success: true, builds: [] }; }]
  ];

  var realFetch = window.fetch ? window.fetch.bind(window) : null;

  function jsonResponse(status, body) {
    return new Response(JSON.stringify(body), { status: status, headers: { 'Content-Type': 'application/json' } });
  }

  window.fetch = function (input, init) {
    var url = typeof input === 'string' ? input : (input && input.url) || '';
    var parsed;
    try { parsed = new URL(url, window.location.href); } catch (_) { parsed = null; }
    // Only intercept the app's own API calls (absolute paths like "/ask")
    var isApi = parsed && parsed.origin === window.location.origin && url.charAt(0) === '/';
    if (!isApi) return realFetch ? realFetch(input, init) : Promise.reject(new Error('fetch unavailable'));

    var method = ((init && init.method) || 'GET').toUpperCase();
    var body = {};
    try { body = init && init.body ? JSON.parse(init.body) : {}; } catch (_) {}

    var route = null;
    for (var i = 0; i < ROUTES.length; i++) {
      if (ROUTES[i][0] === method && ROUTES[i][1].test(parsed.pathname)) { route = ROUTES[i]; break; }
    }
    var result = route ? route[2](body, parsed) : { status: 404, body: { success: false, error: 'Not available in the demo' } };
    var status = 200;
    if (result && typeof result.status === 'number' && 'body' in result) { status = result.status; result = result.body; }

    // AI-backed routes get a short "thinking" delay so the UI's loading states show
    var slow = /^\/(ask|troubleshoot|cicd\/(analyze|builds\/\d+\/analyze)|profile$)/.test(parsed.pathname);
    var delay = slow ? 700 + Math.random() * 600 : 120;
    return new Promise(function (resolve) {
      setTimeout(function () { resolve(jsonResponse(status, result)); }, delay);
    });
  };

  // ---------------------------------------------------------------------------
  // Demo banner and login hints
  // ---------------------------------------------------------------------------

  document.addEventListener('DOMContentLoaded', function () {
    // Small corner badge: the app fills the viewport exactly, so a full-width
    // bar would cover its input controls
    var badge = document.createElement('div');
    badge.setAttribute('role', 'note');
    badge.style.cssText = 'position:fixed;right:12px;bottom:12px;z-index:99999;display:flex;gap:10px;align-items:center;max-width:calc(100vw - 24px);padding:7px 8px 7px 12px;border-radius:8px;font:12px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:rgba(30,41,59,.92);color:#e2e8f0;border:1px solid #334155;box-shadow:0 4px 14px rgba(0,0,0,.3);';
    badge.innerHTML = '<span><strong>Live demo</strong> · simulated, nothing leaves your browser</span>' +
      '<a href="' + REPO_URL + '#quick-start" target="_blank" rel="noopener" style="color:#93c5fd;white-space:nowrap">Run it for real</a>' +
      '<button type="button" aria-label="Hide demo notice" style="background:none;border:0;color:#94a3b8;font-size:16px;line-height:1;cursor:pointer;padding:0 4px">×</button>';
    badge.querySelector('button').onclick = function () { badge.remove(); };
    document.body.appendChild(badge);

    // Explain the demo on the login card
    var card = document.getElementById('login-error');
    if (card && card.parentNode) {
      var note = document.createElement('p');
      note.style.cssText = 'margin:12px 0 0;padding:10px 12px;border-radius:6px;background:rgba(37,99,235,.12);font-size:13px;line-height:1.5;';
      note.innerHTML = '<strong>This is a live demo.</strong> The terminal and AI answers are simulated. ' +
        'Click <em>Guest Mode</em>, or enter any host and username and click Connect.';
      card.parentNode.insertBefore(note, card);
    }

    var host = document.getElementById('host');
    var user = document.getElementById('user');
    if (host && !host.value) host.placeholder = 'any host, e.g. web-01 (simulated)';
    if (user && !user.value) user.placeholder = 'any username (simulated)';
  });
})();
