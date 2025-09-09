# Project Revamp: A Strategy for Stability and Recovery

This document outlines a comprehensive, multi-phase strategy to recover from the recent data loss, conduct a full audit of the system to understand the impact of data corruption, and implement a new, more reliable development and testing workflow. 

Our core principles for this revamp are **safety, transparency, and explicit user consent** before any destructive operations are performed.

---

## Phase 1: Data Salvage and Restoration (Highest Priority)

**Goal:** The first priority is to safely restore the database to the most complete state possible, minimizing the need for reprocessing. All actions in this phase are investigative until an explicit approval to restore is given.

### Checklist
- [ ] Investigate contents and timestamps of all files in the `backup/` directory.
- [ ] Analyze contents of the `db_export/` directory as a secondary recovery option.
- [ ] Present a formal report on the most viable backup file, including its date and likely completeness.
- [ ] **(Approval Gate)** Obtain explicit user consent before proceeding with any database restoration.
- [ ] Execute the database restoration from the single, approved backup file.

---

## Phase 2: System-Wide Audit and Impact Report

**Goal:** To fully understand the downstream effects of the previous data corruption. This involves a deep analysis of all services and routes to identify every function that was using the orphaned `DailyAnalysis` records.

### Checklist
- [ ] Read and analyze every file in the `routes/` directory to map all API endpoints.
- [ ] Read and analyze every file in the `services/` directory to trace business logic and data dependencies.
- [ ] Create a markdown report titled `Corruption Impact Analysis`.
- [ ] In the report, detail every affected endpoint (e.g., `/metrics`, `/charts/*`) and explain precisely how its output was skewed by the faulty data.
- [ ] Deliver the report for review.

---

## Phase 3: Implement the Curated Data Strategy

**Goal:** To create a new, safer workflow by developing a script that generates a small, representative, and verifiable sample of data for development and testing. This ends the reliance on large, all-or-nothing data files.

### Checklist
- [ ] Finalize the design of the data sampling logic.
- [ ] Create a new script at `utils/create_data_sample.py`.
- [ ] Implement the script's logic:
    - [ ] Read the large source JSON file (`attached_assets/FB17-23.json`).
    - [ ] Identify all unique dates on which messages were sent.
    - [ ] For each date, identify all conversations that were active.
    - [ ] Randomly select ~10 conversations for each date.
    - [ ] Write a new, smaller JSON file containing all messages from only the selected conversations.
- [ ] Test the script to ensure it produces a valid, well-structured JSON file.

---

## Phase 4: Enhance Development Tools

**Goal:** To modify the application's existing development tools to support a more rigorous and safe testing cycle, centered around the new curated dataset.

### Checklist
- [ ] Read and analyze the current `routes/dev.py` file.
- [ ] Add a new endpoint to `dev.py` to trigger the `create_data_sample.py` script on command.
- [ ] Add a new endpoint to `dev.py` that automatically resets the database and populates it using **only the small, curated sample file**.
- [ ] Add a new endpoint to `dev.py` that can act as a proxy to call any other internal API endpoint, allowing for easy inspection and verification of responses.

---

## Phase 5: Final Verification and Documentation

**Goal:** To verify the success of all previous phases and update all project documentation to reflect the new, stable state of the application and its recommended workflows.

### Checklist
- [ ] Use the enhanced `/dev` endpoint to call all APIs identified in the impact report.
- [ ] Verify that all endpoints return logical, consistent data (e.g., correct dates, non-zero message counts).
- [ ] Update `README.md` to include the new, recommended development workflow (e.g., using the dev endpoint to set up a test environment).
- [ ] Update `API_DOCUMENTATION.md` to reflect any and all changes made to the API responses.
- [ ] Conduct a final review of all code changes and documentation before concluding the revamp project.
