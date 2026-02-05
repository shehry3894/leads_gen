# Developer Tools

This directory contains tools used by developers to manage the application.
These tools are **NOT** bundled with the distributed application.

## Tools

### `generate_license.py`

License key generator for creating machine-bound licenses.

**Usage:**
```bash
# Show help
python tools/generate_license.py --help

# Generate trial license
python tools/generate_license.py \
  --fingerprint <hash> \
  --days 30 \
  --max-results 500

# Generate full license
python tools/generate_license.py \
  --fingerprint <hash> \
  --months 12 \
  --max-results 5000 \
  --save
```

See `docs/licensing/LICENSING_GUIDE.md` for detailed instructions.

---

## Adding New Tools

When adding new developer tools:
1. Place the script in this directory
2. Add documentation to this README
3. Add `#!/usr/bin/env python3` shebang
4. Make executable: `chmod +x toolname.py`
5. Update `.gitignore` if tool generates sensitive data
