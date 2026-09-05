Pea Princess seed — example-student-shared-room
what I am looking for, and nothing about where I live, what I earn or who I am.

I want a flat, at £900–1,100 all-in; it must have lockable_bedroom_door, window_in_bedroom and washing_machine_in_flat; and I rank price, commute and quiet in that order.
I will not take: a joint tenancy with strangers where one person's unpaid rent becomes mine (L14 money gate); bills included with a hidden cap or a fair-use clause nobody can explain (L16); a house that needs an HMO licence and does not have one (L7); damp or mould on a ground or lower-ground room (L10 damp check); windows onto a main road (L4).
Price leads: I take the cheapest home that clears every rule above, and quiet wins when quiet and light conflict. I plan on a hotel or an operator-run stay for the first weeks. I ask of every flat: “Is everyone in this household a full-time student, and is the tenancy joint or individual?”

seed:
  name: example-student-shared-room
  flat_type: room_in_shared_flat
  budget_band: "£900–1,100 all-in"
  budget_mode: standard
  # My questions — every report has to answer each of these by name, at the stage in brackets
  my_questions:
    - "[filter · ask] Is everyone in this household a full-time student, and is the tenancy joint or individual?"
    - "[vet · ask] Are bills really included, and is there a cap after which I pay?"
    - "[compare] If this room is cheaper than the others on the street, why?"
  priorities:
    - price
    - commute
    - quiet
  must_haves:
    - lockable_bedroom_door
    - window_in_bedroom
    - washing_machine_in_flat
  avoid:
    - a joint tenancy with strangers where one person's unpaid rent becomes mine (L14 money gate)
    - bills included with a hidden cap or a fair-use clause nobody can explain (L16)
    - a house that needs an HMO licence and does not have one (L7)
    - damp or mould on a ground or lower-ground room (L10 damp check)
    - windows onto a main road (L4)
    - short-let or hotel-style neighbours (L9)
    - paying a holding fee before seeing the room or the contract (L15)
  light:
    reject_no_sky: yes
  quiet_over_light: yes
  first_weeks: hotel_or_operator
  story_summary: >-
    First time renting abroad, on a student budget, and would rather share a well-run flat
    near the campus than live alone far out. Has heard enough about deposits vanishing and
    bills surprises to insist on a protected deposit and a written answer on what "bills
    included" means.

seed code (paste it into any AI agent that has the Pea Princess skill, and it will set itself up the way I did):
PP1.eyJhdiI6WyJhIGpvaW50IHRlbmFuY3kgd2l0aCBzdHJhbmdlcnMgd2hlcmUgb25lIHBlcnNvbidzIHVucGFpZCByZW50IGJlY29tZXMgbWluZSAoTDE0IG1vbmV5IGdhdGUpIiwiYmlsbHMgaW5jbHVkZWQgd2l0aCBhIGhpZGRlbiBjYXAgb3IgYSBmYWlyLXVzZSBjbGF1c2Ugbm9ib2R5IGNhbiBleHBsYWluIChMMTYpIiwiYSBob3VzZSB0aGF0IG5lZWRzIGFuIEhNTyBsaWNlbmNlIGFuZCBkb2VzIG5vdCBoYXZlIG9uZSAoTDcpIiwiZGFtcCBvciBtb3VsZCBvbiBhIGdyb3VuZCBvciBsb3dlci1ncm91bmQgcm9vbSAoTDEwIGRhbXAgY2hlY2spIiwid2luZG93cyBvbnRvIGEgbWFpbiByb2FkIChMNCkiLCJzaG9ydC1sZXQgb3IgaG90ZWwtc3R5bGUgbmVpZ2hib3VycyAoTDkpIiwicGF5aW5nIGEgaG9sZGluZyBmZWUgYmVmb3JlIHNlZWluZyB0aGUgcm9vbSBvciB0aGUgY29udHJhY3QgKEwxNSkiXSwiYiI6IsKjOTAw4oCTMSwxMDAgYWxsLWluIiwiZnciOiJob3RlbF9vcl9vcGVyYXRvciIsImxpIjp7InJlamVjdF9ub19za3kiOnRydWV9LCJtIjoic3RhbmRhcmQiLCJtaCI6WyJsb2NrYWJsZV9iZWRyb29tX2Rvb3IiLCJ3aW5kb3dfaW5fYmVkcm9vbSIsIndhc2hpbmdfbWFjaGluZV9pbl9mbGF0Il0sIm4iOiJleGFtcGxlLXN0dWRlbnQtc2hhcmVkLXJvb20iLCJwciI6WyJwcmljZSIsImNvbW11dGUiLCJxdWlldCJdLCJxIjp0cnVlLCJxcyI6W3sia2luZCI6ImFzayIsInRleHQiOiJJcyBldmVyeW9uZSBpbiB0aGlzIGhvdXNlaG9sZCBhIGZ1bGwtdGltZSBzdHVkZW50LCBhbmQgaXMgdGhlIHRlbmFuY3kgam9pbnQgb3IgaW5kaXZpZHVhbD8iLCJ3aGVuIjoiZmlsdGVyIn0seyJraW5kIjoiYXNrIiwidGV4dCI6IkFyZSBiaWxscyByZWFsbHkgaW5jbHVkZWQsIGFuZCBpcyB0aGVyZSBhIGNhcCBhZnRlciB3aGljaCBJIHBheT8iLCJ3aGVuIjoidmV0In0seyJraW5kIjoiYW5zd2VyIiwidGV4dCI6IklmIHRoaXMgcm9vbSBpcyBjaGVhcGVyIHRoYW4gdGhlIG90aGVycyBvbiB0aGUgc3RyZWV0LCB3aHk_Iiwid2hlbiI6ImNvbXBhcmUifV0sInQiOiJyb29tX2luX3NoYXJlZF9mbGF0IiwidiI6MX0
(the code leaves out the story_summary to stay short enough to paste; it is on the card above)
