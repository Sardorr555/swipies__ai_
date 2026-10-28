# Flat landing presentation — 2026-10-28

Branch: `swipies_26`. The owner approved the local homepage preview for publication.

The homepage adds two presentation-only stylesheets: an amber agent-access
section and flat surfaces across the homepage (solid backgrounds, smaller card
radii, no shadows/glows or hover lifts). Existing fonts, text, layout, images,
translations, discovery links and setup logic remain unchanged. Other pages
do not load these stylesheets.

Validation: the release homepage equals the approved preview except stylesheet
cache versions; removing the two stylesheet links reproduces the previous
homepage byte for byte. IDs, anchors, inline JavaScript and structured data pass.
Browser checks confirm solid card backgrounds, no shadows, 4px card corners,
the retained amber palette, no horizontal overflow and no broken loaded images.

Publication scope: only `index.html`, `agent-yellow.css`, `flat-preview.css`
under `/var/www/html`. Install CSS before the homepage, guard the old revisions,
make a private backup and restore these files if HTTPS verification fails.
Use `[skip ci]` on this static release to prevent the application deployment
workflow from rebuilding/restarting the platform. No backend, container, database,
Nginx or credential changes belong to this release.
