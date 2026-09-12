# Domain matching

For each Rank Check, one owner-scoped join loads active Domain Aliases whose
Tracked Site is also active. Domains from other users, inactive aliases, and
archived Sites never enter the matcher.

Each normalized organic hostname is looked up by exact hostname first. Only when
that fails, the matcher toggles one leading `www.` and tries again. It does not use
suffix matching, registrable-domain collapse, redirect resolution, or arbitrary
subdomain equivalence. Thus `blog.example.com` does not match `example.com`.

Exact-match precedence matters when both `example.com` and `www.example.com` are
owned aliases. Multiple Sites may match different results from one SERP. When
multiple aliases or results map to the same logical Site, only that Site's lowest
organic position is persisted. The Ranking snapshot stores the exact alias selected,
the actual result hostname, and the full result URL.
