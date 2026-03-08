# OrthoBraceForge Configuration Guide

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OCTOPRINT_URL` | No | `http://localhost:5000` | OctoPrint server URL |
| `OCTOPRINT_API_KEY` | For printing | *(empty)* | OctoPrint API key for printer control |

## Setting Up OctoPrint Credentials

### Option 1: Environment Variable (Recommended for Development)

Create a `.env` file in the project root (this file is git-ignored):

```
OCTOPRINT_URL=http://192.168.1.100:5000
OCTOPRINT_API_KEY=your-api-key-here
```

Load it before running the application:

```bash
export $(cat .env | xargs)
python main.py
```

### Option 2: OS Keyring (Recommended for Production)

Install the `keyring` library and store the key securely:

```bash
pip install keyring
python -c "import keyring; keyring.set_password('orthobraceforge', 'octoprint_api_key', 'YOUR_KEY')"
```

The application will automatically check the OS keyring if the environment variable is not set.

### Option 3: Direct Configuration

Edit `config.py` and set `OCTOPRINT_API_KEY` directly. **Not recommended** — never commit API keys to source control.

## Logging Configuration

Settings in `config.py`:

| Constant | Default | Description |
|----------|---------|-------------|
| `LOG_MAX_BYTES` | `5242880` (5 MB) | Max log file size before rotation |
| `LOG_BACKUP_COUNT` | `5` | Number of rotated log files to keep |
| `JSON_LOGGING_ENABLED` | `False` | Enable structured JSON log output to file |

Log files are stored at:
- **Linux/macOS**: `~/OrthoBraceForge/logs/orthobraceforge.log`
- **Windows**: `%APPDATA%/OrthoBraceForge/logs/orthobraceforge.log`

## Agent Timeouts

| Constant | Default | Description |
|----------|---------|-------------|
| `OPENSCAD_TIMEOUT_SEC` | `120` | OpenSCAD render subprocess timeout |
| `BUILD123D_TIMEOUT_SEC` | `180` | build123d script execution timeout |
| `OCTOPRINT_CONNECT_TIMEOUT_SEC` | `5` | OctoPrint HTTP request timeout |

## Orchestration Settings

| Constant | Default | Description |
|----------|---------|-------------|
| `MAX_AGENT_ITERATIONS` | `10` | Max retries per CAD agent |
| `VLM_CRITIQUE_MAX_ROUNDS` | `5` | Max VLM render-critique rounds |
| `HUMAN_REVIEW_REQUIRED` | `True` | Mandatory human approval gate (**never disable in production**) |
| `PREFERRED_CAD_ENGINE` | `build123d` | Primary CAD engine (`build123d`, `openscad`, `chat_to_stl`) |

## Security Notes

- Never commit `.env` files or API keys to version control
- The `.gitignore` excludes `.env`, `user_data/`, and `*.db` files
- OctoPrint communication defaults to `http://` for local network use; configure HTTPS if accessing over untrusted networks
- All file exports are restricted to `EXPORT_DIR` via path allowlist checks
