# Optional Google Drive Storage Setup

V7 works immediately with local PDF storage under `media/movs/`. Use this for pre-orals if you want the most reliable offline demo.

If you later want PDFs stored in Google Drive, keep the current **Upload PDF** interface and change only the storage backend.

## Recommended demonstration path
1. Create a dedicated Google account for the Extension Office, not a personal student account.
2. In Google Drive, create a folder such as `EVSU Extension MOVs`.
3. Keep local uploads enabled first and verify TAEP/QPAR submission, review, approve, and return all work.
4. Create a Google Cloud project and enable the Google Drive API.
5. Configure OAuth for the dedicated Extension Office account.
6. Store the selected Drive folder ID in an environment variable such as `EVSU_DRIVE_FOLDER_ID`.
7. When Django receives a PDF, upload the file to that folder and save the returned Drive file ID/URL in the report record.
8. Do not remove local storage until Drive upload/retrieval is fully tested.

For pre-orals, local PDF storage is intentionally the default because it does not depend on internet access or OAuth tokens.
