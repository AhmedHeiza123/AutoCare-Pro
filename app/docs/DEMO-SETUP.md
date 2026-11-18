# Private demo password setup

The demo generator no longer contains a default password. It requires `AUTOCARE_DEMO_PASSWORD` before it imports database configuration or creates any database. Use at least 8 characters; a long unique password is preferable. The demo username remains `demo`.

From the backend folder in PowerShell, collect the password without putting it into command history:

```powershell
$demoSecure = Read-Host 'Choose a unique demo password' -AsSecureString
try {
    $env:AUTOCARE_DEMO_PASSWORD = [System.Net.NetworkCredential]::new('', $demoSecure).Password
    python -m app.sample_data --database autocare_demo
} finally {
    Remove-Item Env:AUTOCARE_DEMO_PASSWORD -ErrorAction SilentlyContinue
    $demoSecure.Dispose()
}
```

Keep the password privately so you can sign in. Do not put it in source files, documentation, screenshots or a public issue. The script prints the demo username and a masked database connection URL, not the demo password.

The generator still requires a working backend environment, PostgreSQL configuration and the FastAPI test-client dependency (`httpx`), which was not listed in the original production requirements. No complete demo creation or database test was run for this change.

Changing the generator does not change an existing demo account or revoke existing sessions. For an already-created database, change the account password through the application; password change/reset paths revoke sessions as implemented by the backend. Never reuse demo credentials on a live installation.

The database-name and already-initialized-database checks remain in place. Do not point demonstration work at real workshop records.
