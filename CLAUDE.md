# CLAUDE.md — Rules for this project

## CRITICAL: Never remove safety checks

The delete flow in `poster.py` (`delete_old_listing`) has a two-part safety check before deleting any listing:

1. **New listing must be visible on the dashboard** — verified by searching for `car.var_title` in a span.
2. **Old listing must be findable by its listing ID** — verified by searching for `car.edit_url`'s listing ID in an `<a>` href.

**Never remove or bypass either of these checks, for any reason.** If the new listing was not successfully posted and the old one gets deleted, the listing is gone permanently with no recovery. This has already happened once.

When refactoring the delete function (e.g. changing how listings are located), always preserve both safety conditions before the actual delete steps execute.
