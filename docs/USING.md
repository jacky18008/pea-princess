**English** · [繁體中文](USING.zh-TW.md) · [简体中文](USING.zh-CN.md)

# You can start with a conversation

Part of Pea Princess by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

Tell the assistant what you want to understand. You do not need to write code, complete a questionnaire or choose technical settings before it can help.

After installing the skill using the [installation guide](INSTALL.md), try:

- “I'm moving to London in October. Show me some examples and explain how to choose.”
- “I want a quiet one-bedroom home. My total monthly cost, including rent and bills, should stay below £2,200.”
- “Compare these two listings, and tell me what to check at a viewing.”
- “Pause the comparison: what does a guarantor do?”

It starts with useful examples or the evidence you provide, explains a trade-off, and learns what matters from your reaction. Usually it asks zero to two questions at a time, never more than three essential clarifications. You can say “not sure”. A complete set of preferences is not required before making progress.

The assistant uses real rental examples with source links and dates. A public advert is not a guarantee of availability. If a source cannot be reached, it continues with supported information and asks for the missing extract; it does not switch to fictional homes. Invented teaching examples are used only if you request them. Your assistant may need you to paste a listing or attach a floor plan. It explains what is needed and why, while continuing other checks. If your app supports a choice panel, it can use that; otherwise you answer in ordinary text.

**Handing over a listing page.** The skill never opens listing links (the sites' terms do not allow programs to read for you), so give it the page itself. On a computer: File → Save Page As → "Webpage, Complete", then attach the `.html` — it carries more than the screen shows, including the full postcode. On an iPhone: Safari's share sheet, either with the one-tap shortcut described at the top of `skills/vet-flat/scripts/capture_page.js` or with Options → Web Archive. A PDF or the copied text also works, with less in it. Photos and the floor plan are pictures: save them, or print the page to PDF.

### Speak instead of typing

If speaking is easier, use your device's built-in dictation or an app you already like to enter text in the assistant's chat box. [Typeless](https://www.typeless.com/pricing) and [Wispr Flow](https://wisprflow.ai/pricing) are optional examples; both list free plans with usage limits, which vary by plan or platform (checked 11 September 2026). Check the linked pages for current allowances; installing or paying for another app is not required.

Describe in your own words what you want, the rentals or stays that were especially good or especially bad, even a shopping experience you still remember — it all helps the assistant understand you. You can change your mind midway. Before sending, just glance at the text to check it was transcribed correctly.

### Learn by comparing

Start with differences you can react to: a shorter commute versus more space, a quiet bedroom versus a busy road, lower rent versus uncertain bills. The assistant explains the likely consequences, then helps you inspect the evidence or prepare a viewing check. You can ask about London areas, rental budgets, paperwork or common problems whenever they become relevant. For claims about the current market or the law, you can ask the assistant to attach the sources it checked.

### Read the recommendation

The answer begins with what to do next and why. Numbers keep their source and uncertainty: “landlord estimate: 20 minutes, not checked” is different from a journey planner prediction for your destination and arrival time. A quote matching the landlord's message does not prove the claim is true. Unknown information remains unknown; a low estimate alone does not confirm that a home meets your limit.

A fuller report covers the money, paperwork, size, bills, move-in timing and other checks relevant to the home. These are things the assistant works through, not a form you must fill out before it helps. It asks for the few missing items that matter next and keeps other gaps visible.

### Change your mind or interrupt

Say “Raise my total monthly limit to £2,300”, “Quiet matters more than light”, or “A longer commute is okay, but never over 45 minutes”. The assistant applies clear instructions, explains the effect in plain words and preserves conditions and previous requirements. It asks only when your meaning is materially ambiguous or it proposes a change itself.

Ask a side question at any point. It should answer it, keep the original work available, and resume without making you repeat your preferences. Saving across conversations depends on the host's file and memory support; the assistant must say when it cannot save something.

### Before arriving or committing

Compare temporary accommodation if it would give you time to view longer-term homes. Check actual cancellation, payment and departure terms; no accommodation type guarantees a refund or same-day exit. Build an arrival plan from your dates and verified costs, leaving gaps explicit.

Use the report to decide what to investigate, then see the flat and speak with the agent or landlord. Take the agreement away to read; do not sign at the viewing. The assistant gives legal and payment guidance at the decision it affects, with the applicable date and agreement type.

**Your own little secretary.** Anything personal or local that the shared skill does not check — the walk to your gym, a school's catchment, a noise source you know about, a data set you trust — goes into `extensions/` in your copy as a one-page add-on (or just tell the assistant the whole list and let it put it in). These extras are labelled in the report, never change the verdict by themselves, read no listing or review sites, and never describe an area by who lives there.

**Share what you learned, not where you live.** Ask the assistant for your seed and post it: it carries your taste, deal-breakers and the questions you make every flat answer, never where you go each day or when you move. Around it, say what helped you; leave out your employer, school, station and moving date. There is no version that includes them: a friend who needs everything gets your profile file, not a seed.
