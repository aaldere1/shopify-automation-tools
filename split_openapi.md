 # API Spec Splitter

 This document explains how to use the `split_openapi.py` script to split a large OpenAPI JSON specification into multiple smaller JSON files to avoid token limits.

 ## What it does
 - Reads `openapi.json` from the project root.
 - Splits:
   - `paths` into separate files under `openapi_split/paths/`
   - `components` (schemas, parameters, responses, examples, requestBodies, securitySchemes) under `openapi_split/components/`
   - `x-webhooks` into `openapi_split/x-webhooks/`
 - Emits a slim root spec at `openapi_split/openapi.json` that uses `$ref` to include each piece.

 ## How to run
 1. Ensure you are in the project root (where `openapi.json` and `split_openapi.py` live):
    ```bash
    pwd  # should show your project root
    ```
 2. Execute:
    ```bash
    python3 split_openapi.py
    ```
 3. On success you will see:
    ```
    Split complete: openapi_split
    ```

 ## After running
 - The `openapi_split/` directory contains:
   - `openapi.json` (entrypoint with `$ref` links)
   - `paths/` (individual path JSON files)
   - `components/` (subfolders for each component type)
   - `x-webhooks/` (individual webhook JSON files)
 - You can point Swagger UI or other OpenAPI tools at `openapi_split/openapi.json` for modular loading.
 - Commit or check in `openapi_split/` if desired to keep split files under version control.

 ## Tips
 - If you update `openapi.json`, re-run the script to regenerate the split files.
 - The original `openapi.json` remains untouched.