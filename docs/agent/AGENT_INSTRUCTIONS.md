# Project Instruction File  
## Google Maps Lead Generation Desktop Application

### Role of the Coding Agent
You are a senior software engineer building a **desktop lead-generation application**.  
The final deliverable is a **standalone executable (EXE / macOS app)** that runs entirely on the user’s local machine.

The application must be reliable when packaged using **PyInstaller (onefile)** and must not rely on any cloud services or external backends.

---

## 1. Product Goal (What We Are Building)

This product is a **local, desktop-based lead generation tool**.

Its primary purpose is:

> To generate structured business leads by scraping **Google Maps** and **business websites**, and exporting the results into an **Excel file**, while also displaying the data in a UI table.

### Example User Story
- User starts a gym-wear business
- User wants to find **gyms in New York**
- User enters query: gyms in New York

- The app:
1. Searches Google Maps
2. Scrapes gym listings and metadata
3. Visits gym websites (if available)
4. Extracts social/contact info
5. Saves everything into an Excel file
6. Displays results in a table inside the UI

---

## 2. Execution Environment (Very Important)

- The app **runs entirely on the user’s PC**
- No backend servers
- No cloud APIs
- No SaaS dependencies

### Supported Run Modes
- Python (development)
- Docker (optional)
- **Standalone desktop executable (primary target)**

⚠️ **The EXE build is the main target.**
All design decisions must work correctly in:
- PyInstaller `--onefile`
- Streamlit Desktop App

---

## 3. Data Sources (Strict Scope)

The app is allowed to scrape data **only from**:

1. **Google Maps**
 - Business name
 - Address
 - Phone number
 - Website
 - Ratings / reviews
 - Last updated (if available)

2. **Business Website (if linked from Google Maps)**
 - Social media links:
   - Facebook
   - Instagram
   - LinkedIn
   - Twitter / X
 - WhatsApp links
 - Emails (mailto / visible text)

❌ Do NOT crawl the wider web  
❌ Do NOT use third-party lead databases

---

## 4. Core Functional Flow

### Step-by-Step Strategy

1. **User Input**
 - Search query (e.g. `gyms in New York`)
 - Optional:
   - Result limit
   - Output directory for Excel file

2. **Google Maps Scraping**
 - Open Google Maps
 - Search query
 - Scroll / zoom out to load results
 - Collect all visible business listings
 - Extract core metadata

3. **Website Scraping (Conditional)**
 - If a business has a website:
   - Visit website
   - Extract:
     - Social media links
     - Email addresses
     - WhatsApp links

4. **Data Aggregation**
 - Normalize all fields into a single table
 - One row = one business
 - Columns include:
   - Name
   - Address
   - Phone
   - Website
   - Rating
   - Reviews count
   - Social links
   - Email
   - WhatsApp
   - Source URLs

5. **Output**
 - Save data to Excel:
   - File name defaults to query (sanitized)
   - User may choose output location
 - Display results in UI:
   - Rows & columns
   - Clickable links

---

## 5. UI Requirements

- Built using **Streamlit**
- Desktop-friendly
- Must:
- Accept user input
- Show scraping progress/logs
- Display results as a table
- Allow Excel export

⚠️ **Excel export must work in a PyInstaller onefile build**
- Do NOT rely on ephemeral in-memory objects alone
- Persist Excel data safely (session state or filesystem)

---

## 6. File Handling Rules (Critical for EXE)

- Assume:
- App restarts can occur on UI interaction
- Memory may not persist between reruns

### Mandatory Rules
- Excel files must:
- Either be stored in `st.session_state`
- OR written to disk before download
- All paths must work when:
- `sys.frozen == True`
- App is running from a temp directory

---

## 7. Architecture Expectations

Recommended modular structure:
app.py # UI + orchestration
scraper/
google_maps.py # Maps scraping logic
website_scraper.py # Website & social extraction
utils/
excel_writer.py # Excel generation
normalizer.py # Data cleanup
paths.py # EXE-safe path handling


- UI logic must be thin
- Scraping logic must be reusable
- No hardcoded absolute paths

---

## 8. Non-Goals (Explicitly Out of Scope)

- ❌ User accounts or authentication
- ❌ Cloud sync
- ❌ Multi-user collaboration
- ❌ Automation scheduling
- ❌ CAPTCHA solving services
- ❌ Paid Google APIs

---

## 9. Quality Bar

The app must:
- Be stable as a desktop executable
- Handle reruns safely
- Avoid crashing on missing data
- Fail gracefully if:
  - Website is unreachable
  - Social links are not present
  - Google Maps layout changes slightly

---

## 10. Final Guiding Principle
> Do not create a .md file until it is explicitly asked to
> This is **not a web app**.  
> This is **not a SaaS product**.  
> This is a **local lead-generation tool** designed to feel like a professional desktop application.

Optimize for:
- Reliability
- Predictability
- Local-first execution


--- 
# TASKS MANAGEMENT using beads


This project uses **bd** (beads) for issue tracking. Run `bd onboard` to get started.

## Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --status in_progress  # Claim work
bd close <id>         # Complete work
bd sync               # Sync with git
```

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds

---

## End of Instructions

