// GLM Workbench desktop shell.
// Spawns the R Shiny server as a child process, waits for its "Listening on"
// line, shows the app in a native Electron window, and shuts the R process
// down again when the window closes.
//
// The only thing an end user has to provide is an R installation. Required R
// packages are detected on every start and, if missing, installed
// automatically into the user's package library (first-run setup with a live
// progress window). R lookup order:
//   1. r-portable/ bundled in the app resources (zero-install EUC distribution)
//   2. r-portable/ next to the portable .exe (PORTABLE_EXECUTABLE_DIR)
//   3. GLM_WORKBENCH_RSCRIPT environment variable
//   4. Windows registry (HKLM\SOFTWARE\R-core\R InstallPath)
//   5. newest R under C:\Program Files\R

const { app, BrowserWindow, shell } = require('electron');
const { spawn, spawnSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const SMOKE_TEST = !!process.env.GLM_WORKBENCH_SMOKE_TEST;
const SMOKE_ALLOW_INSTALL = !!process.env.GLM_WORKBENCH_SMOKE_ALLOW_INSTALL;
const STARTUP_TIMEOUT_MS = 60_000;

const REQUIRED_PACKAGES = [
  'shiny', 'bslib', 'DT', 'nanoparquet',
  'dplyr', 'tidyr', 'purrr', 'readr', 'tibble',
];

let rProcess = null;
let installerProcess = null;
let quitting = false;
let stderrTail = [];

function resourceDir() {
  return app.isPackaged ? process.resourcesPath : __dirname;
}

function findRscript() {
  const candidates = [path.join(resourceDir(), 'r-portable', 'bin', 'Rscript.exe')];

  if (process.env.PORTABLE_EXECUTABLE_DIR) {
    candidates.push(
      path.join(process.env.PORTABLE_EXECUTABLE_DIR, 'r-portable', 'bin', 'Rscript.exe')
    );
  }

  if (process.env.GLM_WORKBENCH_RSCRIPT) {
    candidates.push(process.env.GLM_WORKBENCH_RSCRIPT);
  }

  const reg = spawnSync(
    'reg',
    ['query', 'HKLM\\SOFTWARE\\R-core\\R', '/v', 'InstallPath'],
    { encoding: 'utf8' }
  );
  const match = reg.stdout && reg.stdout.match(/InstallPath\s+REG_SZ\s+(.+)/);
  if (match) {
    candidates.push(path.join(match[1].trim(), 'bin', 'Rscript.exe'));
  }

  const base = 'C:\\Program Files\\R';
  if (fs.existsSync(base)) {
    const versions = fs
      .readdirSync(base)
      .filter((d) => d.startsWith('R-'))
      .sort()
      .reverse();
    for (const v of versions) {
      candidates.push(path.join(base, v, 'bin', 'Rscript.exe'));
    }
  }

  return candidates.find((c) => fs.existsSync(c)) || null;
}

function shinyAppDir() {
  return app.isPackaged
    ? path.join(process.resourcesPath, 'shiny')
    : path.join(__dirname, '..');
}

// Returns [] when all packages are present, a list of missing package names,
// or null when the check itself could not be run (then just try to start).
function missingPackages(rscript) {
  const quoted = REQUIRED_PACKAGES.map((p) => `'${p}'`).join(',');
  const res = spawnSync(
    rscript,
    ['-e', `cat(setdiff(c(${quoted}), rownames(installed.packages())))`],
    { encoding: 'utf8', timeout: 60_000 }
  );
  if (res.status !== 0 || typeof res.stdout !== 'string') return null;
  return res.stdout.trim().split(/\s+/).filter(Boolean);
}

function killTree(proc) {
  if (proc && !proc.killed) {
    spawnSync('taskkill', ['/pid', String(proc.pid), '/f', '/t']);
  }
}

function stopChildProcesses() {
  killTree(rProcess);
  rProcess = null;
  killTree(installerProcess);
  installerProcess = null;
}

function escapeHtml(text) {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;');
}

function pageHtml(title, body) {
  return `<!doctype html><html><head><meta charset="utf-8"><title>${title}</title>
  <style>
    body { font-family: "Segoe UI", sans-serif; margin: 2.5em auto; max-width: 46em;
           padding: 0 1.5em; color: #1a1a2e; line-height: 1.55; }
    h1 { font-size: 1.4em; } h2 { font-size: 1.1em; margin-top: 1.6em; }
    code, pre { background: #f0f1f5; border-radius: 4px; font-size: 0.95em; }
    code { padding: 0.1em 0.35em; }
    pre { padding: 0.8em 1em; overflow-x: auto; user-select: all; }
    .note { background: #fff6df; border-left: 4px solid #e0a800; padding: 0.6em 1em; }
    a { color: #16537e; }
  </style>
  <script>
    function appendLog(t) {
      var el = document.getElementById('log');
      if (el) { el.textContent += t; el.scrollTop = el.scrollHeight; }
    }
  </script></head><body>${body}</body></html>`;
}

function loadPage(win, title, body) {
  win.loadURL(
    'data:text/html;charset=utf-8,' + encodeURIComponent(pageHtml(title, body))
  );
}

function newWindow(width, height, title) {
  const win = new BrowserWindow({ width, height, title, autoHideMenuBar: true });
  // Open all links in the system browser, not inside this window.
  win.webContents.on('will-navigate', (e, url) => {
    e.preventDefault();
    shell.openExternal(url);
  });
  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });
  return win;
}

function showRNotFound() {
  const win = newWindow(820, 640, 'GLM Workbench — R is required');
  loadPage(
    win,
    'GLM Workbench — R is required',
    `<h1>R was not found on this computer</h1>
     <p>GLM Workbench needs the free statistics runtime <strong>R</strong> to do its
        calculations. Installing it is a one-time step and takes about 5 minutes.
        <strong>RStudio is NOT needed.</strong></p>
     <h2>Step 1 — install R</h2>
     <p>Download R for Windows from
        <a href="https://cran.r-project.org/bin/windows/base/">cran.r-project.org/bin/windows/base</a>
        and run the installer. The default settings are fine; administrator rights
        are not required if you choose an install "only for me".</p>
     <h2>Step 2 — restart GLM Workbench</h2>
     <p>That's it. On the next start GLM Workbench detects the new R installation and
        automatically sets up everything else it needs (this first start takes a few
        minutes and shows its progress).</p>
     <div class="note"><strong>Alternatives for administrators:</strong> place an
        <code>r-portable</code> folder (with the packages preinstalled) next to the
        GLM&nbsp;Workbench executable, or set the environment variable
        <code>GLM_WORKBENCH_RSCRIPT</code> to the full path of an
        <code>Rscript.exe</code>.</div>`
  );
}

function showInstallFailed(win, logTail) {
  loadPage(
    win,
    'GLM Workbench — setup failed',
    `<h1>Automatic package setup failed</h1>
     <p>GLM Workbench tried to install its required R packages but did not succeed.
        The last output is shown below — it usually names the problem (no internet
        access / a proxy, or a package that "has to be built from source").</p>
     <pre>${escapeHtml(logTail || '(no output captured)')}</pre>
     <h2>What to try</h2>
     <p>1. Check your internet connection and start GLM Workbench again — the setup
        resumes where it stopped.</p>
     <p>2. If a package "has to be built from source": install a current version of R
        from <a href="https://cran.r-project.org/bin/windows/base/">CRAN</a> (current
        versions get ready-made packages, no build tools needed) and start
        GLM&nbsp;Workbench again.</p>`
  );
}

function showServerCrashed(code) {
  const tail = stderrTail.join('\n').trim() || '(no output captured)';
  const win = newWindow(820, 640, 'GLM Workbench — start failed');
  loadPage(
    win,
    'GLM Workbench — start failed',
    `<h1>The R server stopped unexpectedly (code ${code})</h1>
     <p>The R runtime started but the app could not be launched. The last output
        from R is shown below. Restarting GLM Workbench re-runs the automatic
        setup check, which fixes most cases.</p>
     <pre>${escapeHtml(tail)}</pre>`
  );
}

function fatalSmoke(message) {
  console.error(message);
  quitting = true;
  stopChildProcesses();
  app.exit(1);
}

function showApp(url, reuseWin) {
  let win = reuseWin && !reuseWin.isDestroyed() ? reuseWin : null;
  if (win) {
    win.setSize(1280, 860);
    win.center();
  } else {
    win = newWindow(1280, 860, 'GLM Workbench');
  }
  win.loadURL(url);
  win.webContents.once('did-finish-load', () => {
    if (SMOKE_TEST) {
      console.log('SMOKE_OK ' + url);
      setTimeout(() => {
        quitting = true;
        stopChildProcesses();
        app.exit(0);
      }, 500);
    }
  });
}

// First-run setup: install the missing packages into the user library with a
// live progress window, then continue into launchServer. Closing the window
// cancels the setup and quits the app.
function runInstaller(rscript, missing) {
  const win = newWindow(760, 560, 'GLM Workbench — first-time setup');
  loadPage(
    win,
    'GLM Workbench — first-time setup',
    `<h1>Setting up GLM Workbench</h1>
     <p>The required R packages (<strong>${missing.join(', ')}</strong>) are being
        installed into your personal R library. This happens once and can take a few
        minutes — please leave this window open. The app starts automatically when
        the setup is done.</p>
     <pre id="log" style="height: 18em; overflow: auto"></pre>`
  );

  let pageReady = false;
  let pending = '';
  let fullLog = '';
  const append = (text) => {
    fullLog += text;
    if (win.isDestroyed()) return;
    if (!pageReady) {
      pending += text;
      return;
    }
    win.webContents.executeJavaScript(`appendLog(${JSON.stringify(text)})`).catch(() => {});
  };
  win.webContents.once('did-finish-load', () => {
    pageReady = true;
    if (pending) {
      const flush = pending;
      pending = '';
      win.webContents.executeJavaScript(`appendLog(${JSON.stringify(flush)})`).catch(() => {});
    }
  });

  const quoted = missing.map((p) => `'${p}'`).join(',');
  const setupExpr =
    `lib <- Sys.getenv('R_LIBS_USER'); ` +
    `dir.create(lib, recursive = TRUE, showWarnings = FALSE); ` +
    `.libPaths(c(lib, .libPaths())); ` +
    `options(repos = c(CRAN = 'https://cloud.r-project.org')); ` +
    `install.packages(c(${quoted}), lib = lib)`;
  installerProcess = spawn(rscript, ['-e', setupExpr]);
  installerProcess.stdout.on('data', (c) => append(c.toString()));
  installerProcess.stderr.on('data', (c) => append(c.toString()));

  installerProcess.on('exit', () => {
    installerProcess = null;
    if (quitting || win.isDestroyed()) return;
    const stillMissing = missingPackages(rscript);
    if (stillMissing && stillMissing.length > 0) {
      if (SMOKE_TEST) return fatalSmoke('setup failed, still missing: ' + stillMissing.join(', '));
      showInstallFailed(win, fullLog.split(/\r?\n/).slice(-25).join('\n'));
      return;
    }
    append('\nSetup finished — starting GLM Workbench …\n');
    launchServer(rscript, win);
  });
}

function launchServer(rscript, reuseWin) {
  const appDir = shinyAppDir().replace(/\\/g, '/');
  rProcess = spawn(rscript, [
    '-e',
    `shiny::runApp('${appDir}', launch.browser = FALSE)`,
  ]);

  let started = false;
  const timeout = setTimeout(() => {
    if (!started) {
      if (SMOKE_TEST) return fatalSmoke('startup timeout');
      stopChildProcesses();
      showServerCrashed('timeout after 60s');
    }
  }, STARTUP_TIMEOUT_MS);

  // Shiny prints "Listening on http://127.0.0.1:<port>" (a random free port)
  // on stderr; use that instead of hardcoding a port.
  const onData = (chunk) => {
    const text = chunk.toString();
    stderrTail = stderrTail.concat(text.split(/\r?\n/)).slice(-30);
    if (!started) {
      const m = text.match(/Listening on (http:\/\/[\d.]+:\d+)/);
      if (m) {
        started = true;
        clearTimeout(timeout);
        showApp(m[1], reuseWin);
      }
    }
  };
  rProcess.stderr.on('data', onData);
  rProcess.stdout.on('data', onData);

  rProcess.on('exit', (code) => {
    if (!quitting) {
      clearTimeout(timeout);
      if (SMOKE_TEST) return fatalSmoke(`R exited unexpectedly (code ${code})`);
      showServerCrashed(code);
    }
  });
}

function start() {
  const rscript = findRscript();
  if (!rscript) {
    if (SMOKE_TEST) return fatalSmoke('R not found');
    showRNotFound();
    return;
  }

  const missing = missingPackages(rscript);
  if (missing && missing.length > 0) {
    if (SMOKE_TEST && !SMOKE_ALLOW_INSTALL) {
      return fatalSmoke('missing packages: ' + missing.join(', '));
    }
    runInstaller(rscript, missing);
    return;
  }
  launchServer(rscript, null);
}

app.whenReady().then(start);

app.on('window-all-closed', () => {
  quitting = true;
  stopChildProcesses();
  app.quit();
});

app.on('before-quit', () => {
  quitting = true;
  stopChildProcesses();
});
