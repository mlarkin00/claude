# Pitfall

* [Updating an installed Claude Code plugin](plugin-updates.md) - claude plugin update needs the name@marketplace form, and `details` resolves the newest cached version rather than the loaded one — so a fix can look live while the session still runs old code.

# Runtime Behaviour

* [Injected context is stored as typed records, not as rendered system-reminder text](transcript-injected-context.md) - The transcript keeps structured attachment records; the <system-reminder> wrapping is applied at send time and never written, so grepping for it returns zero hits in a session full of injections.
