# Product & Business Thinking

> This reflects the product **after** the research-depth upgrade (facet-based
> multi-query research with disambiguation, recency-biased news, and inline
> `[n]` citations — see `engineering-decisions.md`, Decision 5). The weaknesses
> below are the ones that *remain*, and the top-3 are what I'd build next from
> here.

## Weaknesses in the Current Product Design

1. **No human-in-the-loop.** The report is take-it-or-leave-it. A seller can't
   correct a wrong fact, drop an irrelevant section, or steer the research toward
   what they already know about the prospect — even though they're often the
   domain expert in the room.

2. **Citations prove provenance, not support.** Each claim now carries an inline
   `[n]` that links to a real source, but nothing verifies that the cited source
   actually *supports* that specific sentence. A confidently-wrong claim with a
   plausible-looking citation is more dangerous than an uncited one, because it
   looks trustworthy.

3. **Quality bar is still partly subjective.** Quality is now cheaper and more
   deterministic (structural checks + one LLM verdict + targeted redo), but the
   "good enough" judgment still rests on a non-deterministic LLM call with no
   measurable acceptance threshold and no offline eval set to tune against.

4. **Higher per-report cost with no guardrails.** Deeper research means several
   Tavily calls plus multiple LLM passes per report, and a retry can add more.
   There is no per-user budget, rate limit, caching of repeated company lookups,
   or model fallback — so cost and third-party rate limits scale linearly with
   usage.

5. **The briefing is trapped in the app.** There's no export and no CRM
   integration. Sellers live in Salesforce/HubSpot/email/Slack, so research they
   have to re-open a separate tab for is research they'll often skip.

Additional weaknesses worth noting: no authentication / multi-user separation;
recency is *biased* (the news facet favors fresh results) but signals aren't
individually dated or marked "as of" in the report; and there's no feedback loop
to learn which reports were actually useful.

## Top 3 Improvements to Build Next

1. **Human-in-the-loop editing + targeted re-run.** Let users edit any section,
   flag a section to "research more," and regenerate just that part.
   LangGraph checkpointing keyed by session makes partial re-runs natural, and it
   turns the tool from a one-shot generator into a collaborator — the single
   biggest jump in perceived usefulness now that depth and citations exist.

2. **Claim-level verification.** For each cited sentence, check that the source
   snippet actually supports it (a lightweight verifier pass) and surface the
   exact snippet on hover. This closes the gap in weakness #2 and converts
   "citations present" into "citations you can trust," which is the core value
   proposition for research.

3. **CRM/export + cost guardrails.** Push the briefing into Salesforce/HubSpot
   (and a PDF/email export) so it lives where sellers work, and add per-user cost
   caps, response caching, and model fallbacks so the deeper pipeline stays
   affordable at scale. This pairs the biggest distribution win with the controls
   the deeper research now requires.

---

## Bonus — Business Thinking

**Who buys, who uses, why they pay.** The buyer is a sales leader (VP Sales / RevOps)
who wants reps spending time selling, not Googling. The users are account
executives and SDRs preparing for discovery calls. They pay because good pre-call
research measurably improves meeting quality and conversion, and doing it
manually costs 30–60 minutes per meeting — expensive rep time the tool replaces
for cents.

**Success metrics.** (1) Reports generated per active seller per week (adoption /
habit). (2) Median time-to-report and report acceptance rate (did they use it
without major edits?). (3) Downstream: meeting-to-opportunity conversion for
meetings where a report was used vs. not.

**Biggest risks.** *Cost/scaling:* every report is now several Tavily calls plus
multiple LLM passes (the multi-query research and any retry multiply this), so
per-report cost and API rate limits are the main scaling risk — and the reason
cost guardrails are in the top-3. *Reliability:* dependence on third-party
LLM/search uptime, and the risk of confidently wrong (but cited) facts damaging
seller trust.

**Feature to remove.** The automatic LLM quality *verdict*. The cheap structural
checks (empty/thin sections, citations present) already catch most real failures
deterministically; the extra LLM judgment adds cost and non-determinism for
marginal gain. I'd keep the structural gate and replace the LLM verdict with a
user-triggered "improve this section" action.

**Feature to add.** CRM integration (push the briefing into Salesforce/HubSpot on
the relevant contact/opportunity) so research lives where sellers already work.

**What I'd change first if I owned it.** Claim-level verification. Citations now
exist, but an unverified citation can be worse than none — it lends false
confidence to a wrong claim. For a trust-sensitive research product, making every
citation *checkable* compounds the value of everything else built so far.
