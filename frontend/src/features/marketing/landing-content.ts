export type LandingContent = {
  path: string;
  title: string;
  description: string;
  heading: string;
  eyebrow: string;
  lead: string;
  note: string;
  workflow: { heading: string; steps: string[] };
  sections: { heading: string; paragraphs: string[]; items?: string[] }[];
  midCta: { heading: string; description: string; label: string };
  finalCta: { heading: string; description: string; label: string };
  guide: { path: string; label: string; description: string };
};

export const googleRankTracker: LandingContent = {
  path: "/google-serp-rank-tracker",
  title: "Google SERP Rank Tracker for Keyword Position Monitoring | SERP SaaS",
  description:
    "Track Google keyword positions, compare ranking changes, monitor competitors, and review ranking history with SERP SaaS.",
  heading: "Google SERP Rank Tracker",
  eyebrow: "Your keyword tracking workflow",
  lead: "Track keyword positions in Google, compare ranking changes over time, and monitor the sites that matter to your SEO workflow.",
  note: "Current checks cover the Top 10. Desktop and Mobile are tracked in separate Projects.",
  workflow: {
    heading: "From a keyword to a useful observation",
    steps: [
      "Connect a Tracked Site and its domain aliases.",
      "Create a Project with a consistent country, language, location and device.",
      "Add your keywords and run a ranking check.",
      "Review positions, matched URLs and changes in Ranking Explorer.",
    ],
  },
  sections: [
    {
      heading: "Track keyword positions in one place",
      paragraphs: [
        "SERP SaaS keeps your search environment, keyword list and completed checks together in a Project. Open ranking history to review the dates and results behind a keyword instead of maintaining a separate spreadsheet of spot checks.",
        "Tracked Sites give your domains a reusable identity. Include legitimate current and historical aliases so a domain move can stay associated with the same SEO asset. Review alias changes when interpreting history: current active aliases affect matching against stored results.",
      ],
    },
    {
      heading: "Compare ranking movement over time",
      paragraphs: [
        "Use Ranking Explorer to compare available successful observations in a selected period. Inspect baseline and current timestamps alongside the positions before deciding which pages deserve attention.",
        "The movement categories distinguish improved, declined and unchanged positions from entering or leaving the checked depth. A visibility transition has a different meaning from a numeric position change; a missing observation is not an unchanged rank.",
      ],
      items: [
        "Filter a review to the movement you want to investigate.",
        "Check the matched URL as well as the position.",
        "Keep the keyword cohort and search environment consistent.",
      ],
    },
    {
      heading: "Monitor competitors alongside your site",
      paragraphs: [
        "Compare selected competitors with your primary site using the same stored checks. Competitor analytics helps you inspect coverage, trends and keywords where a selected competitor appears while your site is absent from a complete checked result set.",
        "These opportunities are investigation leads. Coverage describes presence in the checked keyword dataset; it does not estimate market share, traffic or conversions. A competitor with no match in incomplete evidence remains unknown.",
      ],
    },
    {
      heading: "Organize keyword sets for focused reviews",
      paragraphs: [
        "Use Groups for durable topics such as services or locations, and Tags for campaign, intent or review priority. Ranking Explorer filters let you work through one meaningful subset rather than scanning the entire Project.",
        "Check ANY or ALL tag matching before interpreting a summary. Organizing your keywords makes comparisons easier to explain without adding invented search-volume or difficulty estimates.",
      ],
    },
    {
      heading: "Export and share ranking data",
      paragraphs: [
        "Use CSV exports for further analysis and PDF reports for a readable project summary. Preview the selected period, sites and filters before sharing the output through your usual communication process.",
        "Where report email delivery is configured, scheduled reports go to the account’s own verified email. Report delivery and scheduled ranking checks are separate workflows; a report summarizes available observations rather than guaranteeing a new measurement for every date.",
      ],
    },
    {
      heading: "Understand what SERP SaaS measures",
      paragraphs: [
        "Track whether your site appears within the configured SERP checked depth and compare ranking movement over time. Current checks cover the Top 10: no match in a complete successful check means not found within that depth, not an exact position beyond it. Failed checks and incomplete observations do not establish absence.",
        "Desktop and Mobile results belong to separate Projects and Plans. Keep country, language, location and device consistent when comparing history. A tracker observation records one search environment and time, so it may differ from a personalized manual search or a Search Console average.",
      ],
    },
  ],
  midCta: {
    heading: "Build a baseline you can return to",
    description:
      "Start with one site, one search environment and a purposeful keyword set. Compare Plans for the scope you want to track.",
    label: "Create your first project",
  },
  finalCta: {
    heading: "Start tracking Google rankings",
    description:
      "Bring your keywords and sites into SERP SaaS, then review your first completed check with its measurement context.",
    label: "Start tracking rankings",
  },
  guide: {
    path: "/blog/how-to-track-google-rankings",
    label: "Read the Google ranking baseline guide",
    description:
      "Learn how to choose a keyword set, define an environment and interpret your first ranking observations.",
  },
};

export const dailySerpTracker: LandingContent = {
  path: "/daily-serp-tracker",
  title: "Daily SERP Tracker for Google Keyword Rankings | SERP SaaS",
  description:
    "Monitor Google keyword ranking changes on a recurring schedule, review movement over time, and investigate meaningful SERP changes with SERP SaaS.",
  heading: "Daily SERP Tracker",
  eyebrow: "A repeatable monitoring cadence",
  lead: "Monitor recurring Google ranking changes without manually checking every keyword each day.",
  note: "Daily or weekly scheduling is available according to Plan entitlement. Current checks cover the Top 10.",
  workflow: {
    heading: "A recurring check, followed by a focused review",
    steps: [
      "Define the keyword cohort and search environment.",
      "Choose an eligible daily or weekly Project schedule.",
      "Review completed and failed execution status.",
      "Compare history and investigate meaningful movement.",
    ],
  },
  sections: [
    {
      heading: "Why daily SERP tracking matters",
      paragraphs: [
        "A launch, content update or migration can justify closer observation of a focused keyword set. Recurring checks build a dated history you can revisit when asking whether a change persisted or affected related queries.",
        "Choose the cadence you can actually review. Daily observations provide more checkpoints; weekly monitoring can suit a steadier review routine. Frequency alone does not explain a ranking change or guarantee better search performance.",
      ],
    },
    {
      heading: "Schedule recurring ranking checks",
      paragraphs: [
        "Configure a Project schedule for a stable set of keywords and the intended search environment. Daily or weekly scheduling is available according to Plan entitlement. Review the current Pricing catalog for scheduling availability and monthly check capacity before expanding your routine.",
        "Desktop and Mobile have separate Projects, Plans and usage limits. Manual checks remain useful when you need a specific observation. Scheduled checks are recurring runs, so always inspect their execution status and the actual timestamps in history.",
      ],
      items: [
        "Keep the same country, language, location and device for comparisons.",
        "Size the keyword cohort to your available monthly checks.",
        "Make time to review results after the scheduled run.",
      ],
    },
    {
      heading: "See what changed between observations",
      paragraphs: [
        "Ranking Explorer separates improved, declined and unchanged positions from keywords entering or leaving the checked depth. Use Group and Tag filters to review a campaign or service area without mixing unrelated queries into the comparison.",
        "The selected date range uses available observations, so check the baseline and current dates shown in the results. A day without a successful check is a gap in the record, not proof that a position stayed the same.",
      ],
    },
    {
      heading: "Investigate ranking drops with context",
      paragraphs: [
        "Open ranking history to inspect the matched URL, environment and execution status. Compare selected competitors in the same stored checks to understand the surrounding results before deciding which page to investigate.",
        "SERP SaaS currently checks the Top 10. If a site leaves a complete checked result set, its exact position beyond that depth is unknown. A failed run or incomplete result set is a different state. Use your own Search Console, analytics and page review to investigate causes rather than attributing a drop from one observation alone.",
      ],
    },
    {
      heading: "Keep reporting consistent",
      paragraphs: [
        "Reuse a defined period and keyword cohort for CSV or PDF reports. Preview the dates, sites and filters so each update communicates comparable evidence. Note keyword additions or alias changes when they alter the meaning of a summary.",
        "Scheduled report delivery, where configured, sends reports to the account’s verified email. Its cadence is separate from ranking checks. Reports describe stored observations and should keep gaps and checked-depth limits visible.",
      ],
    },
    {
      heading: "Daily tracking without unnecessary complexity",
      paragraphs: [
        "Keep execution, history and investigation in one Project workflow. Groups and Tags help you prioritize the set you want to review, while usage information makes the cost of expanding that routine easier to assess.",
        "Start with a manageable cohort and eligible cadence, then broaden tracking when you can use the additional evidence. SERP SaaS supports a monitoring routine that leads to decisions instead of requiring you to watch every keyword throughout the day.",
      ],
    },
  ],
  midCta: {
    heading: "Choose a cadence your Plan supports",
    description:
      "Compare scheduling entitlement and usage capacity, then create the Project you want to monitor regularly.",
    label: "Set up your tracking project",
  },
  finalCta: {
    heading: "Start monitoring ranking changes",
    description:
      "Create an account, establish a baseline and choose a supported checking schedule for your SEO routine.",
    label: "Start monitoring rankings",
  },
  guide: {
    path: "/blog/how-to-monitor-keyword-ranking",
    label: "Read the keyword monitoring guide",
    description:
      "Build a stable review cohort and learn how to investigate drops without overstating the evidence.",
  },
};

export const agencySerpTracking: LandingContent = {
  path: "/serp-tracking-for-agencies",
  title: "SERP Tracking for SEO Agencies | Client Rank Tracking | SERP SaaS",
  description:
    "Organize client keyword tracking, compare competitors, monitor ranking movement, and create reports with SERP SaaS.",
  heading: "SERP Tracking for SEO Agencies",
  eyebrow: "Client tracking with clear context",
  lead: "Organize client ranking projects, monitor keyword movement, compare competitors, and create repeatable SEO reports.",
  note: "Manage multiple client Projects from one account. Current ranking checks cover the Top 10.",
  workflow: {
    heading: "A practical client reporting cycle",
    steps: [
      "Connect the client’s Tracked Site and define each Project environment.",
      "Organize keywords by service, location or campaign.",
      "Review movement and selected competitors in stored checks.",
      "Preview and export a report for your client update.",
    ],
  },
  sections: [
    {
      heading: "Keep client environments separated",
      paragraphs: [
        "Manage multiple client Projects from one account, with each Project defining a clear country, language, location and device. Name Projects so the client and environment are easy to identify before you run checks or prepare a report.",
        "Connect the correct Tracked Site and legitimate domain aliases. Desktop and Mobile belong to separate Projects and Plans. Account ownership is user-based; these Project boundaries organize tracking data within the account.",
      ],
    },
    {
      heading: "Organize client keyword sets",
      paragraphs: [
        "Use Groups for services, locations or product areas, then Tags for campaigns and review priorities that span those topics. This gives a client question a defined keyword cohort you can return to each reporting period.",
        "Filter Ranking Explorer by those labels and check ANY or ALL tag matching before exporting. Internal labels should make the work understandable to a client, so review what will appear in a shared file.",
      ],
    },
    {
      heading: "Track client and competitor visibility",
      paragraphs: [
        "Select the client’s primary site and relevant competitors, then compare them in the same stored ranking checks. Coverage, trends and opportunity views help identify queries where a selected competitor is visible and the client warrants further investigation.",
        "Current checks cover the Top 10. Coverage is presence in the selected checked dataset, not market share or an estimate of client traffic. No match in incomplete evidence remains unknown; absence from a complete Top 10 check does not supply an exact position beyond it.",
      ],
    },
    {
      heading: "Build repeatable client reports",
      paragraphs: [
        "Use report previews, CSV exports and PDF project summaries to prepare a consistent client update. Define the period, selected sites and filters before generating output, then review the file and share it through your existing client communication process.",
        "Where scheduled report delivery is configured, it sends to the account’s own verified email. Review that report before forwarding it to a client. Keep the environment, checked depth and observation gaps visible so the client can understand what the evidence supports.",
      ],
      items: [
        "State the Project, device and comparison period.",
        "Summarize observed movement with the affected keywords and URLs.",
        "Choose the next investigation using your client’s business context.",
      ],
    },
    {
      heading: "Review movement without scanning every keyword",
      paragraphs: [
        "Start a review with declined positions, keywords leaving the checked depth or a selected campaign Group. Ranking Explorer lets you narrow the list before opening individual histories and checking the URLs behind the movement.",
        "Keep improved and newly visible keywords in the review too. Separate execution failures from SEO movement, and record changes to keyword cohorts or site aliases in your own project notes before presenting a trend.",
      ],
    },
    {
      heading: "Scale tracking with clear Plan limits",
      paragraphs: [
        "Compare current Project, Keyword and monthly check limits in Pricing as you add clients and search environments. Daily or weekly ranking schedules depend on Plan entitlement; choose a cadence that fits the available capacity and your review process.",
        "Desktop and Mobile allowances are separate. Size each client’s keyword set deliberately, and expand it when the extra observations answer a useful reporting question. The live catalog keeps pricing and limits available without a fixed promise on this page.",
      ],
    },
    {
      heading: "A simpler workflow for small SEO teams",
      paragraphs: [
        "For a freelancer or agency operator handling client rank tracking, SERP SaaS brings Project organization, competitor comparison and reporting into the same account workflow. A repeatable review starts with a well-defined client question and ends with a report you have checked.",
        "Coordinate review responsibilities and client file sharing through your existing processes. User-based ownership makes this a workflow for the account holder; choose it with that operating model in mind.",
      ],
    },
  ],
  midCta: {
    heading: "Give your next client review a clear baseline",
    description:
      "Set up a client Project with its own keyword scope and search environment, then compare Plans as your tracking needs grow.",
    label: "Create a client project",
  },
  finalCta: {
    heading: "Start a client tracking project",
    description:
      "Organize the client’s sites and keywords, review comparable observations and prepare your next ranking report.",
    label: "Start client rank tracking",
  },
  guide: {
    path: "/blog/serp-tracking-for-agencies",
    label: "Read the agency reporting workflow guide",
    description:
      "Learn how to define client reporting questions, keep cohorts consistent and explain the evidence in a ranking report.",
  },
};
