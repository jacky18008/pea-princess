Pea Princess seed — example-quiet-postgraduate-one-bed
what I am looking for, and nothing about where I live, what I earn or who I am.

I want a one-bedroom flat, on floors 3-12, at £1,500–1,900 all-in; it must have washing_machine_in_flat, separate_bedroom_door and openable_windows; and I rank quiet, commute and price in that order.
I will not take: main windows facing a main road or a railway (L4); active building works next door during the tenancy (L5); heat network without a written tariff and a named billing company (L6); management with no resident route to replace it (L7); reviews that are all incentivised or years old (L8).
Price sits last of my three priorities: I will pay towards the top of the band for a benefit I can name, and quiet wins when quiet and light conflict. I plan on a hotel or an operator-run stay for the first weeks.

seed:
  name: example-quiet-postgraduate-one-bed
  flat_type: one_bed
  budget_band: "£1,500–1,900 all-in"
  budget_mode: standard
  # My questions — every report has to answer each of these by name, at the stage in brackets
  my_questions:
    - "[compare] If this flat is unusually cheap, unusually good or unusually available next to its neighbours, what is the hidden problem? Cheap has a reason."
    - "[compare] If it is pricier than its neighbours, am I buying visible value I actually care about (quiet side, floor, light, management), or just paying more?"
  priorities:
    - quiet
    - commute
    - price
  must_haves:
    - washing_machine_in_flat
    - separate_bedroom_door
    - openable_windows
    - parcel_room_or_concierge
  avoid:
    - main windows facing a main road or a railway (L4)
    - active building works next door during the tenancy (L5)
    - heat network without a written tariff and a named billing company (L6)
    - management with no resident route to replace it (L7)
    - reviews that are all incentivised or years old (L8)
    - short-let or hotel-style neighbours in the building (L9)
    - damp or mould signs on a ground or lower-ground flat (L10 damp check)
    - no cooling and shared ventilation that carries neighbours' smoke (L11)
  floors:
    prefer_floor_band: "3-12"
  light:
    reject_no_sky: yes
  quiet_over_light: yes
  first_weeks: hotel_or_operator
  story_summary: >-
    Moved to London for a one-year course after years of city-flat living, and cares more
    about sleeping well and a home that runs itself than about views. Has been burned by a
    damp lower-ground short let, by an advertised size that included the balcony, and by
    bills that only appeared after signing. Would rather pay a little more for a quiet side,
    a real bedroom door and someone who answers when the heating fails.

seed code (paste it into any AI agent that has the Pea Princess skill, and it will set itself up the way I did):
PP1.eyJhdiI6WyJtYWluIHdpbmRvd3MgZmFjaW5nIGEgbWFpbiByb2FkIG9yIGEgcmFpbHdheSAoTDQpIiwiYWN0aXZlIGJ1aWxkaW5nIHdvcmtzIG5leHQgZG9vciBkdXJpbmcgdGhlIHRlbmFuY3kgKEw1KSIsImhlYXQgbmV0d29yayB3aXRob3V0IGEgd3JpdHRlbiB0YXJpZmYgYW5kIGEgbmFtZWQgYmlsbGluZyBjb21wYW55IChMNikiLCJtYW5hZ2VtZW50IHdpdGggbm8gcmVzaWRlbnQgcm91dGUgdG8gcmVwbGFjZSBpdCAoTDcpIiwicmV2aWV3cyB0aGF0IGFyZSBhbGwgaW5jZW50aXZpc2VkIG9yIHllYXJzIG9sZCAoTDgpIiwic2hvcnQtbGV0IG9yIGhvdGVsLXN0eWxlIG5laWdoYm91cnMgaW4gdGhlIGJ1aWxkaW5nIChMOSkiLCJkYW1wIG9yIG1vdWxkIHNpZ25zIG9uIGEgZ3JvdW5kIG9yIGxvd2VyLWdyb3VuZCBmbGF0IChMMTAgZGFtcCBjaGVjaykiLCJubyBjb29saW5nIGFuZCBzaGFyZWQgdmVudGlsYXRpb24gdGhhdCBjYXJyaWVzIG5laWdoYm91cnMnIHNtb2tlIChMMTEpIl0sImIiOiLCozEsNTAw4oCTMSw5MDAgYWxsLWluIiwiZmwiOnsicHJlZmVyX2Zsb29yX2JhbmQiOiIzLTEyIn0sImZ3IjoiaG90ZWxfb3Jfb3BlcmF0b3IiLCJsaSI6eyJyZWplY3Rfbm9fc2t5Ijp0cnVlfSwibSI6InN0YW5kYXJkIiwibWgiOlsid2FzaGluZ19tYWNoaW5lX2luX2ZsYXQiLCJzZXBhcmF0ZV9iZWRyb29tX2Rvb3IiLCJvcGVuYWJsZV93aW5kb3dzIiwicGFyY2VsX3Jvb21fb3JfY29uY2llcmdlIl0sIm4iOiJleGFtcGxlLXF1aWV0LXBvc3RncmFkdWF0ZS1vbmUtYmVkIiwicHIiOlsicXVpZXQiLCJjb21tdXRlIiwicHJpY2UiXSwicSI6dHJ1ZSwicXMiOlt7ImtpbmQiOiJhbnN3ZXIiLCJ0ZXh0IjoiSWYgdGhpcyBmbGF0IGlzIHVudXN1YWxseSBjaGVhcCwgdW51c3VhbGx5IGdvb2Qgb3IgdW51c3VhbGx5IGF2YWlsYWJsZSBuZXh0IHRvIGl0cyBuZWlnaGJvdXJzLCB3aGF0IGlzIHRoZSBoaWRkZW4gcHJvYmxlbT8gQ2hlYXAgaGFzIGEgcmVhc29uLiIsIndoZW4iOiJjb21wYXJlIn0seyJraW5kIjoiYW5zd2VyIiwidGV4dCI6IklmIGl0IGlzIHByaWNpZXIgdGhhbiBpdHMgbmVpZ2hib3VycywgYW0gSSBidXlpbmcgdmlzaWJsZSB2YWx1ZSBJIGFjdHVhbGx5IGNhcmUgYWJvdXQgKHF1aWV0IHNpZGUsIGZsb29yLCBsaWdodCwgbWFuYWdlbWVudCksIG9yIGp1c3QgcGF5aW5nIG1vcmU_Iiwid2hlbiI6ImNvbXBhcmUifV0sInQiOiJvbmVfYmVkIiwidiI6MX0
(the code leaves out the story_summary to stay short enough to paste; it is on the card above)
