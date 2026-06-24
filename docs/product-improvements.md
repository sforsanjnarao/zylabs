# Product & Business Thinking

## Weaknesses in the Current Product Design

1. **No source-level grounding per claim.** The report cites sources as a list at
   the bottom, but individual statements aren't linked to the source they came
   from. A user can't quickly verify a specific claim, which matters for a
   trust-sensitive sales-prep use case.

2. **Quality check is subjective and costly.** Quality is judged by a single LLM
   call with a yes/no verdict. It is non-deterministic, frequently triggers a
   retry, and roughly doubles latency and cost without a clear, measurable bar
   for "good enough."

3. **Shallow, generic research depth.** Research is a single broad Tavily query.
   For well-known companies it works, but for smaller or ambiguous companies it
   can return thin or off-target results, and it doesn't disambiguate companies
   with similar names.

4. **No editing or human-in-the-loop.** The report is take-it-or-leave-it. A
   seller can't correct a wrong fact, remove an irrelevant section, or steer the
   research, even though they often know more about the prospect than the model.

5. **Limited freshness and recency signals.** "Business Signals" can mix old and
   new information without dates. For sales timing (funding rounds, leadership
   changes, launches) recency is the whole point, and the current design doesn't
   prioritize or timestamp it.

Additional weaknesses worth noting: no authentication / multi-user separation;
no rate-limiting or cost controls on the LLM/search APIs; and no export
(PDF/email/CRM) of the briefing.

## Top 3 Improvements to Build Next

1. **Inline citations.** Attribute each sentence/section to specific source URLs
   so users can verify claims at a glance. This is the single biggest trust win
   and directly raises the perceived quality of every report.

2. **Deeper, multi-query research with disambiguation.** Have the planner emit
   several targeted queries (products, funding, leadership, recent news) and a
   disambiguation step that confirms the right company from the website. This
   fixes the most common failure mode (thin/wrong research) at the root.

3. **Human-in-the-loop editing + re-run.** Let users edit any section, flag a
   section to "research more," and regenerate just that part. LangGraph's
   checkpointing makes partial re-runs natural, and it turns the tool from a
   one-shot generator into a collaborator.

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

**Biggest risks.** *Cost/scaling:* every report is multiple LLM + search calls;
the retry loop multiplies this, so per-report cost and API rate limits are the
main scaling risk. *Reliability:* dependence on third-party LLM/search uptime and
the risk of confidently wrong (hallucinated) facts damaging seller trust.

**Feature to remove.** The strict automatic quality-retry loop in its current
form — it adds the most cost/latency for the least visible user value. I'd
replace it with cheap structural checks plus a user-triggered "improve" action.

**Feature to add.** CRM integration (push the briefing into Salesforce/HubSpot on
the relevant contact/opportunity) so research lives where sellers already work.

**What I'd change first if I owned it.** Inline citations, because trust is the
core value proposition for research and it compounds the value of everything else.
