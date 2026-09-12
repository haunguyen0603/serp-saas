from uuid import uuid4

from app.services.domain_matching import DomainMatcher, MatchableDomain
from app.services.serp import OrganicResult


def organic(position: int, hostname: str) -> OrganicResult:
    return OrganicResult(
        position,
        hostname,
        f"https://{hostname}/page-{position}",
        hostname,
    )


def test_exact_www_and_no_arbitrary_subdomain_matching() -> None:
    exact_site, bare_site, subdomain_site = uuid4(), uuid4(), uuid4()
    domains = [
        MatchableDomain(exact_site, uuid4(), "Exact", "www.exact.example"),
        MatchableDomain(bare_site, uuid4(), "Bare", "bare.example"),
        MatchableDomain(subdomain_site, uuid4(), "Blog", "blog.site.example"),
    ]
    matches = DomainMatcher().match(
        (
            organic(1, "www.exact.example"),
            organic(2, "www.bare.example"),
            organic(3, "site.example"),
            organic(4, "shop.site.example"),
        ),
        domains,
    )
    assert [(value.tracked_site_id, value.position) for value in matches] == [
        (exact_site, 1),
        (bare_site, 2),
    ]


def test_exact_wins_and_same_site_aliases_collapse_to_best_position() -> None:
    site_a, site_b = uuid4(), uuid4()
    old_domain, new_domain, exact_www = uuid4(), uuid4(), uuid4()
    domains = [
        MatchableDomain(site_a, old_domain, "Site A", "old.example"),
        MatchableDomain(site_a, new_domain, "Site A", "new.example"),
        MatchableDomain(site_b, exact_www, "Site B", "www.old.example"),
    ]
    matches = DomainMatcher().match(
        (
            organic(2, "old.example"),
            organic(5, "new.example"),
            organic(7, "www.old.example"),
        ),
        domains,
    )
    assert [(value.tracked_site_id, value.position) for value in matches] == [
        (site_a, 2),
        (site_b, 7),
    ]
    assert matches[0].tracked_domain_id == old_domain


def test_reverse_www_equivalence_and_multiple_sites() -> None:
    site_a, site_b = uuid4(), uuid4()
    matches = DomainMatcher().match(
        (organic(3, "example.com"), organic(8, "second.example")),
        [
            MatchableDomain(site_a, uuid4(), "A", "www.example.com"),
            MatchableDomain(site_b, uuid4(), "B", "second.example"),
        ],
    )
    assert {value.tracked_site_id: value.position for value in matches} == {
        site_a: 3,
        site_b: 8,
    }
