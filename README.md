# RolePath

Career exploration and study planning for students seeking internships.

## Cloud setup

Deploy `cloud_app.py` with Python 3.13 and the included requirements.txt and packages.txt.
Use a dedicated Supabase project; run deploy/supabase.sql once. Set the project URL and publishable key in deploy/public_config.json. Never use an administrator key.
Configure verified email signup with a production SMTP service and set the Auth Site URL to the deployed app address before opening registration.

Each authenticated account owns its plans, tasks, study logs, document text and analysis reports. PostgreSQL row-level policies enforce account separation. The application uses the signed-in user's token for all database operations.

AI calls use each visitor's own Alibaba Bailian API configuration, retained only in the current session. No operator API key or local personal records are included. Refreshing requires login again; saved records remain in the database.

Images are processed with server-side OCR on Linux; original images are not retained. Handwriting and diagrams can be inaccurate. The cloud deployment currently supports keyword retrieval only. Resource coverage is limited to the included catalog.

## Release validation

Database account isolation checked with temporary transactional test users and rolled back. Public signup, Linux OCR and the deployed site must be verified separately before launch.
