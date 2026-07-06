# Graph Report - new site for swipies  (2026-06-09)

## Corpus Check
- 65 files · ~164,229 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 123 nodes · 129 edges · 26 communities (7 shown, 19 thin omitted)
- Extraction: 74% EXTRACTED · 26% INFERRED · 0% AMBIGUOUS · INFERRED: 33 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b4b9ad98`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]

## God Nodes (most connected - your core abstractions)
1. `Design System: Composio` - 13 edges
2. `DesignSystemGenerator` - 11 edges
3. `Popular Web Designs Skill` - 10 edges
4. `_search_csv()` - 8 edges
5. `BM25` - 7 edges
6. `search()` - 7 edges
7. `generate_design_system()` - 7 edges
8. `persist_design_system()` - 5 edges
9. `_generate_intelligent_overrides()` - 5 edges
10. `Resend Design System` - 5 edges

## Surprising Connections (you probably didn't know these)
- `_generate_intelligent_overrides()` --calls--> `search()`  [INFERRED]
  .agent/skills/ui-ux-pro-max/scripts/design_system.py → .agent/skills/ui-ux-pro-max/scripts/core.py
- `NVIDIA Design System` --conceptually_related_to--> `Resend Design System`  [INFERRED]
  .agent/skills/popular-web-designs/templates/nvidia.md → .agent/skills/popular-web-designs/templates/resend.md
- `Raycast Design System` --conceptually_related_to--> `Resend Design System`  [INFERRED]
  .agent/skills/popular-web-designs/templates/raycast.md → .agent/skills/popular-web-designs/templates/resend.md
- `Resend Design System` --conceptually_related_to--> `Sanity Design System`  [INFERRED]
  .agent/skills/popular-web-designs/templates/resend.md → .agent/skills/popular-web-designs/templates/sanity.md
- `Revolut Design System` --conceptually_related_to--> `Resend Design System`  [INFERRED]
  .agent/skills/popular-web-designs/templates/revolut.md → .agent/skills/popular-web-designs/templates/resend.md

## Import Cycles
- None detected.

## Communities (26 total, 19 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.15
Nodes (15): BM25, detect_domain(), _load_csv(), Lowercase, split, remove punctuation, filter short words, Build BM25 index from documents, Score all documents against query, Load CSV and return list of dicts, Core search function using BM25 (+7 more)

### Community 1 - "Community 1"
Cohesion: 0.17
Nodes (16): _detect_page_type(), format_ascii_box(), format_markdown(), format_master_md(), format_page_override_md(), generate_design_system(), _generate_intelligent_overrides(), persist_design_system() (+8 more)

### Community 2 - "Community 2"
Cohesion: 0.16
Nodes (9): DesignSystemGenerator, Select best matching result based on priority keywords., Extract results list from search result dict., Generate complete design system recommendation., Generates design system recommendations from aggregated searches., Load reasoning rules from CSV., Execute searches across multiple domains., Find matching reasoning rule for a category. (+1 more)

### Community 3 - "Community 3"
Cohesion: 0.14
Nodes (14): Design System: Composio, Design System: Cursor, Design System: ElevenLabs, Design System: Expo, Design System: Figma, Design System: Framer, Design System: HashiCorp, Design System: IBM (+6 more)

### Community 4 - "Community 4"
Cohesion: 0.19
Nodes (14): Mistral AI Design System, MongoDB Design System, Notion Design System, NVIDIA Design System, Ollama Design System, OpenCode Design System, Pinterest Design System, PostHog Design System (+6 more)

### Community 5 - "Community 5"
Cohesion: 0.18
Nodes (11): Popular Web Designs Skill, Airbnb Design System, Airtable Design System, Apple Design System, BMW Design System, Cal.com Design System, Claude (Anthropic) Design System, Clay Design System (+3 more)

### Community 6 - "Community 6"
Cohesion: 0.50
Nodes (4): Anti-Slop Design Color References, Anti-Slop Design Layout References, Anti-Slop Design Typography References, Anti-Slop Design Skill

## Knowledge Gaps
- **37 isolated node(s):** `T`, `icons`, `revealObserver`, `Admin HTML`, `Zapier Design System` (+32 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **19 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `search()` connect `Community 0` to `Community 1`, `Community 2`?**
  _High betweenness centrality (0.093) - this node is a cross-community bridge._
- **Why does `DesignSystemGenerator` connect `Community 2` to `Community 1`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Are the 13 inferred relationships involving `Design System: Composio` (e.g. with `Design System: Cursor` and `Design System: ElevenLabs`) actually correct?**
  _`Design System: Composio` has 13 INFERRED edges - model-reasoned connections that need verification._
- **What connects `T`, `BM25 ranking algorithm for text search`, `Lowercase, split, remove punctuation, filter short words` to the rest of the system?**
  _76 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.14736842105263157 - nodes in this community are weakly interconnected._
- **Should `Community 3` be split into smaller, more focused modules?**
  _Cohesion score 0.14285714285714285 - nodes in this community are weakly interconnected._