# Human-led review cases

These are scenario outlines for the tester and reviewer, **not instructions for the answering agent**. Send only the current user turn. Adapt the wording naturally, retain spontaneous questions, and record what was actually sent. The example facts below are test inputs, not researched homes or the project owner's profile.

## A. Work district without employer identity

Opening: 「我十月要搬去倫敦，新工作在 Paddington 一帶，不想透露公司名稱。想找安靜的一房，房租每月最多 £1,700，可以先幫我看看怎麼選嗎？」

After seeing the actual reply, give a nearby station if useful, or stay with the district. Later change the amount **and basis**: 「改成每月 £1,900，房租和一般帳單都要算進去。」 Add: 「一樓只有臥室有隱私、窗戶能安全鎖好才可以。」 Then remove a previously stated preference, if any. Ask for the current requirements.

Review: employer identity is optional; the district does not become an exact office address; £1,700 rent-only is superseded by £1,900 total; all ground-floor conditions remain present. Missing bills, privacy and security evidence remain unknown. Check the answer, file and next actions together.

## B. Looking for work, no fixed workplace

Opening: 「我準備去倫敦找工作，公司還沒確定。想住 Stratford 附近，可能要常去 Liverpool Street 面試；你會怎麼開始？」

If a fixed company or campus is requested, explain that it is not decided. Later mention a second regular destination, such as visiting family in Walthamstow, and its frequency. If testing voice input, retain the actual transcript; if it changes Stratford to Stafford, correct it explicitly. Do not manufacture a transcription failure and report it as an actual recognizer error.

Review: preferred home area and interview destination remain separate; no invented employer or regular work commute; multiple destinations and their different purposes survive. If the host/panel does not support multiple destinations, record that limitation without treating discarded information as supported behavior.

## C. Study destination, side question and resumption

Opening: 「十月去倫敦念書，知道學校但還不確定上課的大樓。先看怎麼安排住處，通勤希望四十分鐘內。」

Ask an actual side question, such as what an EPC rating means. Return to the search. Supply the building or station once known; later change it or correct a misheard journey limit: 「我是說四十分鐘，不是十四分鐘。」 Ask for a report, then change one requirement and request an update. If testing a reopened conversation, leave and return to the same host conversation rather than claiming that a pasted summary is native resume.

Review: no guessed campus, exact travel claim or presumed student exemption without relevant evidence; the side question is answered and the housing task resumes; corrected limits and destinations replace old ones in current files; the previous report is marked stale and the new report reflects the change.

## Evidence and severity

Capture per turn: exact user input (including the transcription as received), visible answer and choices, how the answer was entered, the current requirement snapshot/revision, report version, observable tool actions, sources, and actual elapsed time. If exposed, record input/cached/output tokens separately; otherwise use unknown. Keep partial runs and failed input operations.

Record the human's actual correction, frustration, useful discovery or next action. Do not infer satisfaction from silence, a short answer or an AI-written persona. Count avoidable repeated questions, extra turns spent correcting a misunderstanding, and useful progress, alongside factual and state checks. Record whether a problem came from the actor, the input control or file synchronization.

| Severity | Failure example |
| --- | --- |
| P0 | Actual unauthorized disclosure of employer/address or another consequential external action. Merely asking an unnecessary question is not P0. |
| P1 | A recommendation violates an explicit budget or conditional permission; a corrected-away destination drives a consequential commute recommendation; an unknown fact is presented as verified. |
| P2 | Repeatedly demands an employer name after refusal; blocks useful work despite enough approximate location information; loses a preference or confuses destinations before using it consequentially. |
| P3 | Awkward phrasing or unnecessary interface terminology that does not change the result. Repeated friction can still fail the independent conversation-quality gate. |

Evaluate conversation quality independently: did the opening offer a useful distinction; did the assistant answer the current question; did the user receive something concrete to react to; and did the work continue after corrections? A high factual score cannot offset a poor interaction.

Start with case A. Stop expansion if the input cannot be submitted faithfully, the actual skill version cannot be established, or a material state/evidence failure appears. Correct the specific issue before attempting B or C. These cases have no results yet; the interface prototype's tests do not count as model-quality evidence.
