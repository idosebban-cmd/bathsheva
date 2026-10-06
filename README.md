# bathsheva — Product Workbench

## Run on your Mac

Works on Apple Silicon and Intel Macs running macOS 11 (Big Sur) or newer. You need an
internet connection for the first setup, and about 3 GB of free disk space.

### 1. Download the code (once)

The repository is private, so you need to be signed in to GitHub. Pick **one** option.

**Option A: GitHub Desktop (easiest)**

1. Install [GitHub Desktop](https://desktop.github.com) and sign in with your GitHub account.
2. Choose **File → Clone Repository…**, pick `idosebban-cmd/bathsheva`, and click **Clone**.
   By default it goes to `Documents/GitHub/bathsheva`.

**Option B: Terminal**

If you already have [Homebrew](https://brew.sh):

```bash
brew install gh
gh auth login                       # choose GitHub.com, then "Login with a web browser"
gh repo clone idosebban-cmd/bathsheva ~/bathsheva
```

### 2. Run the setup (once)

Open Terminal in the `bathsheva` folder. In GitHub Desktop, use **Repository → Open in Terminal**.
Or type `cd ` (with a space), drag the `bathsheva` folder onto the Terminal window, and press Return.
Then run:

```bash
bash scripts/setup_mac.sh
```

The script checks for each tool it needs (Apple's Xcode command line tools, Homebrew, uv for
Python, and Node.js LTS). If a tool is missing, it asks before installing it. Homebrew asks for
your Mac login password. The first run takes about 5–10 minutes. It finishes by generating the
Faro lamp once as a self-test, then prints **Setup finished successfully** or says in plain
English which step failed and what to try.

Want to see what it would do first? Run `bash scripts/setup_mac.sh --dry-run`. It changes nothing.

### 3. Start the workbench (every time)

Double-click **`Start Workbench.command`** in the `bathsheva` folder. A Terminal window opens and
starts the app. Your browser opens at <http://127.0.0.1:5173> when the app is ready.

To stop the app, press **Ctrl-C** in that Terminal window, or close the window. If macOS asks
whether to terminate the running processes, click **Terminate**.

### Your data

Projects, uploads and generated CAD files are kept in **`~/Bathsheva Workbench/data`**, outside
the code folder. Updating or deleting the code never touches them. Setup logs are in
`~/Bathsheva Workbench/logs`. Before setup applies a database update, it saves a copy of the
database in `~/Bathsheva Workbench/data/backups`.

If you ran an older version that kept data in the `bathsheva/data` folder, the data is moved to
the new folder automatically. Nothing is moved if the new folder already holds data.

To keep data somewhere else, add this line to the file `~/.zshrc`, then open a new Terminal window:

```bash
export WORKBENCH_DATA_DIR="$HOME/Dropbox/Workbench data"
```

To turn on **Explain with AI**, add `export ANTHROPIC_API_KEY="sk-ant-…"` to `~/.zshrc` the same way.
Everything else works without a key.

### Updating later

1. Stop the workbench (Ctrl-C, or close its Terminal window).
2. Get the latest code. In GitHub Desktop, click **Fetch origin**, then **Pull origin**.
   In Terminal, run `git pull` from the `bathsheva` folder.
3. Run `bash scripts/setup_mac.sh` again. It only installs what changed and updates your
   database, keeping a backup copy first.
4. Double-click `Start Workbench.command`.

### Troubleshooting

- **"Start Workbench.command" can't be opened / "Apple could not verify…"** (Gatekeeper).
  Running the setup script usually fixes this. If not: Control-click the file, choose
  **Open**, then click **Open**. On macOS 15 or newer, open **System Settings → Privacy &
  Security**, scroll down, and click **Open Anyway**. Or, from the `bathsheva` folder in
  Terminal, run: `xattr -d com.apple.quarantine "Start Workbench.command"; chmod +x "Start Workbench.command"`
- **The CadQuery / backend packages step fails.** Check your internet connection and run the
  setup again. If it still fails:
  - Delete the `backend/.venv` folder and run the setup again. It rebuilds the folder with the
    tested Python version (3.12).
  - If you use Anaconda or Miniconda, run `conda deactivate` first.
  - Check your macOS version (Apple menu → About This Mac). CadQuery needs macOS 11 or newer.
  - Send `~/Bathsheva Workbench/logs/setup.log` to whoever maintains the workbench.
- **"Port 5173 (or 8000) is already in use".** The workbench is probably already running in
  another Terminal window. Close that window and try again. The launcher shows which program
  is using the port, and the command to stop it.
- **The browser doesn't open by itself.** Open <http://127.0.0.1:5173> yourself while the
  Terminal window is open.
- **Anything else.** Run `bash scripts/setup_mac.sh` again. It is safe to repeat, and it
  re-checks every step.

## For developers

See `CLAUDE.md` for the architecture and conventions, and `SPEC.md` for the product vision.
On Linux, or if you prefer the plain scripts: `./run.sh` starts both servers and `./run.sh test`
runs the tests.
