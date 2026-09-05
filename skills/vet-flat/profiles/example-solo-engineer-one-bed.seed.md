Pea Princess seed — example-solo-engineer-one-bed
what I am looking for, and nothing about where I live, what I earn or who I am.

I want a one-bedroom flat, on floors 2-10, at £1,800–2,200 all-in; it must have washing_machine_in_flat, separate_bedroom_door and openable_windows; and I rank safety_on_the_way_home, quiet and commute in that order.
I will not take: a walk home through unlit or empty stretches after dark (L3); entry without a working entry phone or a locked front door (L7 management); main windows facing a main road or a railway (L4); viewings or payments pushed before the landlord entity is verified (L12, L15); heat network without a written tariff (L6).
Price is not in my top three: I will pay to the top of the band for a benefit I can name, and quiet wins when quiet and light conflict. I plan on a hotel or an operator-run stay for the first weeks. I ask of every flat: “Would I feel fine walking from the station to the door alone at 11 pm? What is on that route?”

seed:
  name: example-solo-engineer-one-bed
  flat_type: one_bed
  budget_band: "£1,800–2,200 all-in"
  budget_mode: standard
  # My questions — every report has to answer each of these by name, at the stage in brackets
  my_questions:
    - "[viewing · check] Would I feel fine walking from the station to the door alone at 11 pm? What is on that route?"
    - "[filter] Who exactly am I renting from, and can I verify them before I hand over any money?"
    - "[compare] If this is cheaper than its neighbours, what is the reason?"
  priorities:
    - safety_on_the_way_home
    - quiet
    - commute
  must_haves:
    - washing_machine_in_flat
    - separate_bedroom_door
    - openable_windows
    - working_entry_phone_or_concierge
  avoid:
    - a walk home through unlit or empty stretches after dark (L3)
    - entry without a working entry phone or a locked front door (L7 management)
    - main windows facing a main road or a railway (L4)
    - viewings or payments pushed before the landlord entity is verified (L12, L15)
    - heat network without a written tariff (L6)
    - short-let or hotel-style neighbours (L9)
    - damp or mould signs on a ground or lower-ground flat (L10 damp check)
    - a headline price that is not the price (L16)
  floors:
    prefer_floor_band: "2-10"
  light:
    reject_no_sky: yes
  quiet_over_light: yes
  first_weeks: hotel_or_operator
  story_summary: >-
    Moving to London for a first job in the UK and renting alone for the first time. Wants a
    home that feels safe to come back to late, a bedroom that is dark and quiet, and a
    landlord who can be verified before any money moves. Has read enough scam warnings to
    refuse to pay before a viewing, and would rather pay a little more for a staffed
    building than save on a street that feels empty.

seed code (paste it into any AI agent that has the Pea Princess skill, and it will set itself up the way I did):
PP1.eyJhdiI6WyJhIHdhbGsgaG9tZSB0aHJvdWdoIHVubGl0IG9yIGVtcHR5IHN0cmV0Y2hlcyBhZnRlciBkYXJrIChMMykiLCJlbnRyeSB3aXRob3V0IGEgd29ya2luZyBlbnRyeSBwaG9uZSBvciBhIGxvY2tlZCBmcm9udCBkb29yIChMNyBtYW5hZ2VtZW50KSIsIm1haW4gd2luZG93cyBmYWNpbmcgYSBtYWluIHJvYWQgb3IgYSByYWlsd2F5IChMNCkiLCJ2aWV3aW5ncyBvciBwYXltZW50cyBwdXNoZWQgYmVmb3JlIHRoZSBsYW5kbG9yZCBlbnRpdHkgaXMgdmVyaWZpZWQgKEwxMiwgTDE1KSIsImhlYXQgbmV0d29yayB3aXRob3V0IGEgd3JpdHRlbiB0YXJpZmYgKEw2KSIsInNob3J0LWxldCBvciBob3RlbC1zdHlsZSBuZWlnaGJvdXJzIChMOSkiLCJkYW1wIG9yIG1vdWxkIHNpZ25zIG9uIGEgZ3JvdW5kIG9yIGxvd2VyLWdyb3VuZCBmbGF0IChMMTAgZGFtcCBjaGVjaykiLCJhIGhlYWRsaW5lIHByaWNlIHRoYXQgaXMgbm90IHRoZSBwcmljZSAoTDE2KSJdLCJiIjoiwqMxLDgwMOKAkzIsMjAwIGFsbC1pbiIsImZsIjp7InByZWZlcl9mbG9vcl9iYW5kIjoiMi0xMCJ9LCJmdyI6ImhvdGVsX29yX29wZXJhdG9yIiwibGkiOnsicmVqZWN0X25vX3NreSI6dHJ1ZX0sIm0iOiJzdGFuZGFyZCIsIm1oIjpbIndhc2hpbmdfbWFjaGluZV9pbl9mbGF0Iiwic2VwYXJhdGVfYmVkcm9vbV9kb29yIiwib3BlbmFibGVfd2luZG93cyIsIndvcmtpbmdfZW50cnlfcGhvbmVfb3JfY29uY2llcmdlIl0sIm4iOiJleGFtcGxlLXNvbG8tZW5naW5lZXItb25lLWJlZCIsInByIjpbInNhZmV0eV9vbl90aGVfd2F5X2hvbWUiLCJxdWlldCIsImNvbW11dGUiXSwicSI6dHJ1ZSwicXMiOlt7ImtpbmQiOiJjaGVjayIsInRleHQiOiJXb3VsZCBJIGZlZWwgZmluZSB3YWxraW5nIGZyb20gdGhlIHN0YXRpb24gdG8gdGhlIGRvb3IgYWxvbmUgYXQgMTEgcG0_IFdoYXQgaXMgb24gdGhhdCByb3V0ZT8iLCJ3aGVuIjoidmlld2luZyJ9LHsia2luZCI6ImFuc3dlciIsInRleHQiOiJXaG8gZXhhY3RseSBhbSBJIHJlbnRpbmcgZnJvbSwgYW5kIGNhbiBJIHZlcmlmeSB0aGVtIGJlZm9yZSBJIGhhbmQgb3ZlciBhbnkgbW9uZXk_Iiwid2hlbiI6ImZpbHRlciJ9LHsia2luZCI6ImFuc3dlciIsInRleHQiOiJJZiB0aGlzIGlzIGNoZWFwZXIgdGhhbiBpdHMgbmVpZ2hib3Vycywgd2hhdCBpcyB0aGUgcmVhc29uPyIsIndoZW4iOiJjb21wYXJlIn1dLCJ0Ijoib25lX2JlZCIsInYiOjF9
(the code leaves out the story_summary to stay short enough to paste; it is on the card above)
