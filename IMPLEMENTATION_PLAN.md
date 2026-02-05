# **Google Maps Lead Generator**

## **Full Implementation Plan with Licensing & Enforcement**

---

## **0\. Product Definition (Authoritative)**

This product is a **local-first desktop lead generation application** delivered as a **standalone executable**.

All execution happens on the user’s machine.

The application:

1. Scrapes Google Maps for business listings

2. Optionally scrapes linked business websites

3. Displays structured results in a UI

4. Exports results to Excel

5. Enforces **license-based restrictions** tied to a machine identifier and time window

No cloud services.  
 No backend servers.  
 No remote validation.

---

# **EPIC 1: Core Architecture & Execution Environment**

## **Goal**

Build a stable modular application that behaves correctly when packaged as a **PyInstaller onefile executable**.

---

## **Story 1.1 – Project Structure & Responsibilities**

### **Tasks**

* Define strict module boundaries:

  * UI orchestration

  * Google Maps scraping

  * Website scraping

  * Data normalization

  * Excel generation

  * Licensing & enforcement

* Prevent UI code from containing business logic

* Prevent scraper code from accessing UI state directly

* Ensure all modules are importable in frozen mode

---

## **Story 1.2 – EXE-Safe Path & Runtime Detection**

### **Tasks**

* Detect frozen execution (`sys.frozen`)

* Define a single `BASE_DIR` resolver

* Route all file operations through a centralized path utility

* Create application directories at runtime:

  * logs/

  * output/

  * license/

---

## **Story 1.3 – Logging Infrastructure**

### **Tasks**

* Implement structured logging

* Ensure logs persist across runs

* Write logs to disk, not memory

* Include:

  * Timestamp

  * App version

  * Machine fingerprint (hashed)

  * License status

  * Enforcement actions taken

---

# **EPIC 2: Google Maps Scraping Engine**

## **Goal**

Extract business listings reliably from Google Maps.

---

## **Story 2.1 – Query Execution**

### **Tasks**

* Accept user query input

* Open Google Maps

* Submit query

* Wait for results panel

* Retry safely on slow loads

---

## **Story 2.2 – Results Discovery & Scrolling**

### **Tasks**

* Detect results container

* Scroll until:

  * Result limit reached OR

  * No new listings loaded

* Track already-seen listings

* Enforce result cap dynamically (licensing-aware)

---

## **Story 2.3 – Business Data Extraction**

### **Tasks**

* Extract:

  * Business name

  * Address

  * Phone number

  * Website

  * Rating

  * Review count

* Handle missing fields gracefully

* Normalize values

---

# **EPIC 3: Website & Social Data Extraction**

## **Goal**

Extract additional lead data from business websites.

---

## **Story 3.1 – Website Navigation**

### **Tasks**

* Validate website URLs

* Handle redirects

* Apply request timeouts

* Abort safely on failure

---

## **Story 3.2 – Social Media & Contact Extraction**

### **Tasks**

* Extract social links:

  * Facebook

  * Instagram

  * LinkedIn

  * Twitter/X

* Extract emails

* Extract WhatsApp links

* Deduplicate results

* Restrict crawling to homepage only

---

# **EPIC 4: Data Normalization & Validation**

## **Goal**

Ensure output data is consistent, clean, and usable.

---

## **Story 4.1 – Canonical Data Model**

### **Tasks**

* Define fixed column schema

* Ensure one row per business

* Convert list fields to strings

* Normalize empty values

---

## **Story 4.2 – Deduplication & Cleanup**

### **Tasks**

* Deduplicate using:

  * Website OR

  * Business name \+ address

* Normalize phone numbers

* Trim whitespace

* Sanitize strings for Excel

---

# **EPIC 5: Excel Output & Persistence**

## **Goal**

Generate reliable Excel files that work in desktop builds.

---

## **Story 5.1 – Excel Writer Module**

### **Tasks**

* Write DataFrame to `.xlsx`

* Enable clickable hyperlinks

* Adjust column widths

* Handle large datasets

---

## **Story 5.2 – EXE-Safe Download Strategy**

### **Tasks**

* Persist Excel files to disk before UI download

* Never rely on ephemeral memory-only buffers

* Track generated file path in session state

* Ensure reruns do not delete files

---

# **EPIC 6: Streamlit UI & Interaction Model**

## **Goal**

Provide a stable, desktop-friendly UI.

---

## **Story 6.1 – User Inputs**

### **Tasks**

* Search query input

* Optional result limit

* Optional output directory

* Validate inputs before execution

---

## **Story 6.2 – Progress & Feedback**

### **Tasks**

* Show progress status

* Log each major phase

* Display non-blocking warnings

* Avoid UI freezes

---

## **Story 6.3 – Results Display**

### **Tasks**

* Display data in table form

* Make links clickable

* Limit rows for performance

* Show license-restricted warnings if applicable

---

# **EPIC 7: Licensing & Enforcement System**

## **Goal**

Control app usage using a **machine-bound, time-limited license key**.

---

## **Story 7.1 – Machine Fingerprint Generation**

### **Tasks**

* Retrieve machine MAC address

* Normalize MAC format

* Hash MAC address using a one-way algorithm

* Never expose raw MAC address in UI

* Store hashed fingerprint in logs

---

## **Story 7.2 – License Data Model**

### **License Parameters**

* Machine fingerprint

* Expiration date

* Max results per run

* Feature flags (optional)

### **Tasks**

* Define license schema

* Encode schema into an opaque string

* Ensure values are not human-readable

---

## **Story 7.3 – License Key Encoding (Offline)**

### **Tasks**

* Create a **separate offline script** (not bundled with app)

* Script inputs:

  * Machine fingerprint

  * Expiry date

  * Result limit

* Script outputs:

  * Encrypted / encoded license key

* Use:

  * Symmetric encryption OR

  * Signed payload with secret key

* Do not expose encoding logic in UI

---

## **Story 7.4 – License Key Storage**

### **Tasks**

* Load license key from:

  * File OR

  * User input field

* Store license key locally

* Never store decoded values in plaintext

* Validate license at app startup

---

## **Story 7.5 – License Validation Logic**

### **Tasks**

* Decode license key internally

* Extract hidden parameters

* Validate:

  * Machine fingerprint match

  * Expiry date not exceeded

  * Result limit allowed

* Fail validation gracefully

---

## **Story 7.6 – Enforcement Rules**

### **Tasks**

* If license is missing or invalid:

  * Restrict scraping to a small fixed number of results

  * Disable Excel export OR watermark output

* If license is expired:

  * Block scraping entirely OR

  * Allow preview-only mode

* Log all enforcement actions

---

# **EPIC 8: Logging, Auditing & Feedback Loop**

## **Goal**

Enable offline license issuance and auditing.

---

## **Story 8.1 – Runtime Logging**

### **Tasks**

* Log:

  * App start

  * Machine fingerprint

  * License validation result

  * Scraping attempts

  * Enforcement triggers

* Write logs to disk persistently

---

## **Story 8.2 – License Issuance Workflow**

### **Tasks**

* User runs app without license

* App generates logs

* User sends logs to developer

* Developer extracts machine fingerprint

* Developer generates license key

* User installs license key locally

---

# **EPIC 9: Packaging & Distribution**

## **Goal**

Deliver a professional standalone executable.

---

## **Story 9.1 – PyInstaller Configuration**

### **Tasks**

* Declare hidden imports

* Include data directories

* Validate Selenium in frozen mode

* Minimize bundle size

---

## **Story 9.2 – Cross-Platform Validation**

### **Tasks**

* Validate Windows execution

* Validate macOS execution

* Confirm path permissions

* Confirm license persistence across restarts

---

# **EPIC 10: Documentation & Handoff**

## **Goal**

Make the system understandable and maintainable.

---

## **Story 10.1 – Internal Engineering Docs**

### **Tasks**

* Explain licensing flow

* Explain enforcement logic

* Document failure modes

* Document rebuild process

---

## **Story 10.2 – User-Facing Instructions**

### **Tasks**

* How to run the app

* How to generate leads

* How to install a license

* What happens when license expires

---

# **Final Acceptance Criteria**

The project is complete when:

1. The app runs fully offline

2. License keys are machine-bound

3. Expiry and limits are enforced

4. Logs enable offline license issuance

5. Excel export works in EXE mode

6. Unauthorized usage is meaningfully restricted

