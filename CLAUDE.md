# CLAUDE.md — Rules for this project

## CRITICAL: Never remove safety checks before deleting listings

Deleting a listing on 2dehands.be is **permanent and unrecoverable**. This has already caused data loss once.

### post_listing must verify submission succeeded
After clicking submit, check that the URL navigated away from the form (`/plaats`). If the URL did not change, raise `RuntimeError` so `main.py` catches it and never calls `delete_old_listing`.

### delete_old_listing has two required checks — never remove either

1. **Two title matches required** — `//span[contains(text(), car.var_title)]` must return at least 2 results (old listing + new listing both visible on dashboard). If fewer than 2, skip delete.
2. **Old listing found by ID** — find the old listing via `car.edit_url`'s listing ID in an `<a>` href. If not found, skip delete.

Only after both checks pass may the delete proceed. The delete targets the old listing by its ID, not by title or index.

**When refactoring this code: preserve all three of these checks. No exceptions.**
